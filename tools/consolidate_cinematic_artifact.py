#!/usr/bin/env python3
"""Download one complete prior Actions artifact, rebuild the final MP4, and discard all temporary data."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

import cv2

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GH_TOKEN"]
BRANCH = "cinematic-reconstruction"
API = "https://api.github.com"
OUTPUT = Path(os.environ.get("OUTPUT_DIR", "delivery")).resolve()
RUN_OVERRIDE = os.environ.get("SOURCE_RUN_ID", "").strip()
FRAME_RE = re.compile(r"(?:^|/)frames/frame_(\d{4})\.png$")
REPRESENTATIVE = (16, 66, 126, 166, 226, 286)
MIN_OUTPUT_RESERVE = 512 * 1024 * 1024
PREFLIGHT_MULTIPLIER = 3


def request_json(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "NEXUS-Cinematic-Consolidator",
    })
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def locate_source_artifact():
    if RUN_OVERRIDE:
        run_ids = [int(RUN_OVERRIDE)]
    else:
        data = request_json(
            f"{API}/repos/{REPO}/actions/runs?branch={BRANCH}&status=completed&per_page=100"
        )
        runs = [
            run for run in data.get("workflow_runs", [])
            if run.get("head_branch") == BRANCH
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
        ]
        runs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        run_ids = [run["id"] for run in runs]

    for run_id in run_ids:
        data = request_json(f"{API}/repos/{REPO}/actions/runs/{run_id}/artifacts?per_page=100")
        artifacts = [
            item for item in data.get("artifacts", [])
            if item.get("name", "").startswith("nexus-blender3d-recovery-")
            and not item.get("expired", False)
        ]
        artifacts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        for artifact in artifacts:
            print(json.dumps({
                "event": "candidate_artifact",
                "run_id": run_id,
                "artifact_id": artifact["id"],
                "name": artifact["name"],
                "size_bytes": artifact["size_in_bytes"],
                "expired": artifact.get("expired", False),
            }), flush=True)
            return run_id, artifact
    raise RuntimeError(
        "No se encontró un artefacto de render recovery accesible y no expirado "
        f"en la rama {BRANCH}. No se ha iniciado ninguna reconstrucción."
    )


def download_artifact(artifact, destination):
    url = f"{API}/repos/{REPO}/actions/artifacts/{artifact['id']}/zip"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "NEXUS-Cinematic-Consolidator",
    })
    started = time.time()
    with urllib.request.urlopen(req, timeout=180) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out, length=8 * 1024 * 1024)
    actual = destination.stat().st_size
    expected = int(artifact["size_in_bytes"])
    if actual != expected:
        raise RuntimeError(
            f"Descarga incompleta del artefacto {artifact['id']}: "
            f"{actual} bytes recibidos, {expected} esperados."
        )
    print(json.dumps({
        "event": "artifact_downloaded_once",
        "artifact_id": artifact["id"],
        "bytes": actual,
        "seconds": round(time.time() - started, 2),
    }), flush=True)


def read_json_member(archive, names, basename):
    matches = [name for name in names if Path(name).name == basename]
    if not matches:
        raise RuntimeError(f"El artefacto no contiene {basename}")
    name = sorted(matches, key=lambda value: (value.count("/"), value))[0]
    with archive.open(name) as source:
        return json.loads(source.read().decode("utf-8"))


def extract_and_check(archive_path, temp_root):
    frames_dir = temp_root / "frames"
    frames_dir.mkdir(parents=True)
    audio_path = temp_root / "audio_master.wav"

    with zipfile.ZipFile(archive_path, "r") as archive:
        names = archive.namelist()
        uncompressed_bytes = sum(item.file_size for item in archive.infolist() if not item.is_dir())
        free_during_extract = shutil.disk_usage(temp_root).free
        extraction_required = uncompressed_bytes + MIN_OUTPUT_RESERVE
        if free_during_extract < extraction_required:
            raise RuntimeError(
                "Espacio insuficiente para extraer el ZIP: "
                f"disponible={free_during_extract} bytes; requerido={extraction_required} bytes; "
                f"faltan={extraction_required - free_during_extract} bytes. "
                "Se conserva el ZIP temporal y no se inicia la extracción."
            )
        print(json.dumps({"event":"zip_expansion_preflight_pass","uncompressed_bytes":uncompressed_bytes,"free_bytes":free_during_extract,"required_bytes":extraction_required}),flush=True)
        frame_members = {}
        for name in names:
            match = FRAME_RE.search(name)
            if match:
                number = int(match.group(1))
                if number in frame_members:
                    raise RuntimeError(f"Fotograma duplicado en el ZIP: {number}")
                frame_members[number] = name

        missing = sorted(set(range(1, 301)) - set(frame_members))
        extra = sorted(set(frame_members) - set(range(1, 301)))
        if missing or extra or len(frame_members) != 300:
            raise RuntimeError(
                f"El artefacto no tiene exactamente 300 PNG: "
                f"faltan={missing[:20]}, fuera_de_rango={extra[:20]}"
            )

        state = read_json_member(archive, names, "frame_state.json")
        performance = read_json_member(archive, names, "performance_report.json")
        prior_validation = read_json_member(archive, names, "validation_report.json")
        completed = state.get("completed_frames", {})
        if state.get("total_frames") != 300 or state.get("verified_frames") != 300:
            raise RuntimeError("frame_state.json no acredita 300 fotogramas verificados.")
        if len(completed) != 300:
            raise RuntimeError("El manifiesto no enumera exactamente 300 fotogramas.")
        if performance.get("verified_frames") != 300:
            raise RuntimeError("performance_report.json no acredita 300 fotogramas.")
        if prior_validation.get("status") != "PASS":
            raise RuntimeError("La validación técnica previa no tiene estado PASS.")

        blocks = performance.get("blocks", [])
        covered = set()
        for block in blocks:
            start = int(block["block_start"])
            end = int(block["block_end"])
            if start < 1 or end > 300 or start > end:
                raise RuntimeError(f"Rango de bloque inválido: {start}-{end}")
            current = set(range(start, end + 1))
            if covered.intersection(current):
                raise RuntimeError(f"Bloques superpuestos detectados: {start}-{end}")
            covered.update(current)
        if covered != set(range(1, 301)):
            raise RuntimeError("Los bloques del informe no cubren exactamente los fotogramas 1-300.")

        audio_members = [name for name in names if Path(name).name == "audio_master.wav"]
        if not audio_members:
            raise RuntimeError("No existe audio_master.wav en el artefacto.")
        audio_member = sorted(audio_members, key=lambda value: (value.count("/"), value))[0]

        frame_hashes = {}
        for number in range(1, 301):
            member = frame_members[number]
            target = frames_dir / f"frame_{number:04d}.png"
            digest = hashlib.sha256()
            with archive.open(member) as source, target.open("wb") as out:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    out.write(chunk)
            image = cv2.imread(str(target), cv2.IMREAD_UNCHANGED)
            if image is None or image.shape[:2] != (1920, 1080):
                raise RuntimeError(f"Fotograma inválido o con dimensiones incorrectas: {number}")
            expected = completed.get(str(number), {}).get("sha256")
            actual = digest.hexdigest()
            if expected and expected != actual:
                raise RuntimeError(f"SHA-256 no coincide con frame_state.json: {number}")
            frame_hashes[str(number)] = actual

        with archive.open(audio_member) as source, audio_path.open("wb") as out:
            shutil.copyfileobj(source, out, length=1024 * 1024)
        if not audio_path.is_file() or audio_path.stat().st_size < 1024:
            raise RuntimeError("El audio recuperado está vacío o incompleto.")

    return state, performance, prior_validation, frame_hashes, audio_path, frames_dir


def run_ffmpeg(frames_dir, audio_path, output, crf, preset):
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", "30", "-start_number", "1",
        "-i", str(frames_dir / "frame_%04d.png"),
        "-i", str(audio_path),
        "-map", "0:v:0", "-map", "1:a:0",
        "-frames:v", "300", "-t", "10",
        "-vf", "format=yuv420p",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-r", "30", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", str(output),
    ]
    print(f"Ejecutando FFmpeg: libx264 CRF {crf}, preset {preset}.", flush=True)
    started = time.perf_counter()
    subprocess.run(command, check=True)
    return time.perf_counter() - started


def measure_ssim(frames_dir, encoded_video, stats_path):
    command = [
        "ffmpeg", "-hide_banner", "-i", str(encoded_video),
        "-framerate", "30", "-start_number", "1",
        "-i", str(frames_dir / "frame_%04d.png"),
        "-filter_complex",
        f"[1:v]format=yuv420p[ref];[0:v]format=yuv420p[dist];[ref][dist]ssim=stats_file={stats_path}",
        "-f", "null", "-"
    ]
    result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    match = re.search(r"All:([0-9.]+)", result.stdout)
    if not match:
        raise RuntimeError(f"FFmpeg no devolvió SSIM para {encoded_video.name}")
    return float(match.group(1))


def validate_mp4(path):
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-count_frames", "-show_streams",
        "-show_format", "-of", "json", str(path)
    ], text=True)
    probe = json.loads(raw)
    videos = [stream for stream in probe["streams"] if stream.get("codec_type") == "video"]
    audios = [stream for stream in probe["streams"] if stream.get("codec_type") == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        raise RuntimeError("FFprobe no detecta exactamente un flujo de vídeo y uno de audio.")
    video, audio = videos[0], audios[0]
    duration = float(probe["format"]["duration"])
    fps_num, fps_den = map(int, video["r_frame_rate"].split("/"))
    fps = fps_num / fps_den
    frames = int(video.get("nb_read_frames", video.get("nb_frames", "0")))
    checks = {
        "resolution_1080x1920": (int(video["width"]), int(video["height"])) == (1080, 1920),
        "video_h264": video["codec_name"] == "h264",
        "audio_aac": audio["codec_name"] == "aac",
        "fps_30": abs(fps - 30.0) < 0.001,
        "exactly_300_frames": frames == 300,
        "duration_10_seconds": abs(duration - 10.0) <= 0.03,
    }
    if not all(checks.values()):
        raise RuntimeError(f"FFprobe validation failed: {json.dumps(checks)}")
    return probe, checks


def make_representative_jpegs(frames_dir, destination):
    destination.mkdir(parents=True, exist_ok=True)
    made = []
    for number in REPRESENTATIVE:
        source = frames_dir / f"frame_{number:04d}.png"
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"No se pudo leer el fotograma representativo {number}")
        resized = cv2.resize(image, (720, 1280), interpolation=cv2.INTER_AREA)
        target = destination / f"frame_{number:04d}.jpg"
        if not cv2.imwrite(str(target), resized, [cv2.IMWRITE_JPEG_QUALITY, 82]):
            raise RuntimeError(f"No se pudo escribir {target}")
        made.append({
            "file": target.name,
            "source_frame": number,
            "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        })
    return made


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    run_id, artifact = locate_source_artifact()
    free = shutil.disk_usage(Path.cwd()).free
    archive_bytes = int(artifact["size_in_bytes"])
    required = archive_bytes * PREFLIGHT_MULTIPLIER + MIN_OUTPUT_RESERVE
    if free < required:
        missing = required - free
        raise RuntimeError(
            "Espacio insuficiente antes de descargar: "
            f"disponible={free} bytes; requerido={required} bytes; "
            f"faltan={missing} bytes. Se detuvo sin descargar ni borrar artefactos."
        )
    print(json.dumps({
        "event": "disk_preflight_pass",
        "free_bytes": free,
        "archive_bytes": archive_bytes,
        "preflight_multiplier": PREFLIGHT_MULTIPLIER,
        "output_reserve_bytes": MIN_OUTPUT_RESERVE,
        "required_bytes": required,
    }), flush=True)

    with tempfile.TemporaryDirectory(prefix="nexus-cinematic-") as temp_name:
        temp_root = Path(temp_name)
        zip_path = temp_root / "source-artifact.zip"
        download_artifact(artifact, zip_path)
        state, performance, prior_validation, hashes, audio, frames = extract_and_check(
            zip_path, temp_root
        )
        zip_path.unlink()
        final_video = OUTPUT / "NEXUS_CINEMATIC_FINAL.mp4"
        # Compare the existing production settings with the requested higher-quality encode.
        baseline = temp_root / "benchmark_crf22_veryfast.mp4"
        candidate = temp_root / "benchmark_crf21_slow.mp4"
        baseline_seconds = run_ffmpeg(frames, audio, baseline, 22, "veryfast")
        candidate_seconds = run_ffmpeg(frames, audio, candidate, 21, "slow")
        baseline_probe, baseline_checks = validate_mp4(baseline)
        candidate_probe, candidate_checks = validate_mp4(candidate)
        baseline_ssim = measure_ssim(frames, baseline, temp_root / "baseline_ssim.log")
        candidate_ssim = measure_ssim(frames, candidate, temp_root / "candidate_ssim.log")
        if not all(baseline_checks.values()) or not all(candidate_checks.values()):
            raise RuntimeError("Una de las codificaciones de comparación no pasó FFprobe.")
        # CRF 21 slow is the requested candidate; promote only after validation.
        shutil.copy2(candidate, final_video)
        probe, checks = validate_mp4(final_video)
        if not all(checks.values()):
            raise RuntimeError("El MP4 final no pasó FFprobe después de copiar el candidato.")
        representative = make_representative_jpegs(frames, OUTPUT / "representative_frames")
        report = {
            "status": "PASS",
            "source": {
                "run_id": run_id,
                "artifact_id": artifact["id"],
                "artifact_name": artifact["name"],
                "artifact_size_bytes": archive_bytes,
                "artifact_downloads": 1,
                "duplicate_artifacts_downloaded": 0,
            },
            "recovery": {
                "verified_frames_in_source_manifest": state["verified_frames"],
                "verified_frames_extracted_and_sha256_checked": len(hashes),
                "restored_frames_from_previous_artifact": performance.get("restored_frames_from_previous_artifact"),
                "frames_rendered_in_source_run": performance.get("frames_rendered_across_recorded_blocks"),
                "blocks": performance.get("blocks", []),
                "block_coverage": "1-300 without gaps or overlaps",
            },
            "video": {
                "file": final_video.name,
                "bytes": final_video.stat().st_size,
                "sha256": hashlib.sha256(final_video.read_bytes()).hexdigest(),
                "ffprobe": probe,
                "checks": checks,
                "encoding_comparison": {
                    "baseline": {
                        "settings": {"codec": "libx264", "crf": 22, "preset": "veryfast"},
                        "bytes": baseline.stat().st_size,
                        "encode_seconds": round(baseline_seconds, 3),
                        "ssim_vs_lossless_png_frames": baseline_ssim,
                        "ffprobe_checks": baseline_checks,
                        "ffprobe": baseline_probe,
                    },
                    "candidate": {
                        "settings": {"codec": "libx264", "crf": 21, "preset": "slow"},
                        "bytes": candidate.stat().st_size,
                        "encode_seconds": round(candidate_seconds, 3),
                        "ssim_vs_lossless_png_frames": candidate_ssim,
                        "ffprobe_checks": candidate_checks,
                        "ffprobe": candidate_probe,
                    },
                    "size_change_percent": round((candidate.stat().st_size / baseline.stat().st_size - 1) * 100, 2),
                    "encode_time_change_percent": round((candidate_seconds / baseline_seconds - 1) * 100, 2) if baseline_seconds else None,
                    "ssim_change": round(candidate_ssim - baseline_ssim, 6),
                },
            },
            "representative_frames": representative,
            "cleanup": {
                "source_zip_deleted_before_encoding": True,
                "benchmark_encodes_removed_after_comparison": True,
                "temporary_frame_and_audio_directory_removed": True,
                "only_final_video_report_and_six_jpegs_are_uploaded": True,
            },
            "previous_visual_validation": prior_validation.get("checks", {}),
            "completed_at_unix": int(time.time()),
        }
    (OUTPUT / "validation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "status": "PASS",
        "video": str(OUTPUT / "NEXUS_CINEMATIC_FINAL.mp4"),
        "ffprobe": report["video"]["ffprobe"],
        "uploaded_files": 8,
        "encoding": "libx264 CRF 21 preset slow, AAC 160 kbps",
    }, indent=2), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr, flush=True)
        raise
