"""Recoverable 10-second Blender Cycles renderer using verified PNG frames and 30-frame blocks."""
import argparse
import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2

from render_3d_prototype import synth_audio


def run_logged(command, log_path, env=None):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as log:
        log.write("$ " + " ".join(map(str, command)) + "\n")
        log.flush()
        result = subprocess.run(
            list(map(str, command)), stdout=log, stderr=subprocess.STDOUT,
            env=env, text=True, check=False
        )
    elapsed = time.perf_counter() - started
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}); inspect {log_path}"
        )
    return elapsed


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_png(path):
    try:
        if not path.is_file() or path.stat().st_size < 4096:
            return None
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None or image.shape[:2] != (1920, 1080):
            return None
        return {
            "file": path.name,
            "bytes": path.stat().st_size,
            "width": int(image.shape[1]),
            "height": int(image.shape[0]),
            "sha256": sha256(path),
        }
    except (OSError, cv2.error):
        return None


def contiguous_ranges(values):
    values = sorted(values)
    if not values:
        return []
    groups = []
    first = previous = values[0]
    for value in values[1:]:
        if value != previous + 1:
            groups.append((first, previous))
            first = value
        previous = value
    groups.append((first, previous))
    return groups


def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temp.replace(path)


def restore_checkpoint(resume_root, frames_dir, out):
    restored = 0
    if not resume_root or not resume_root.exists():
        return restored
    for source in resume_root.rglob("frame_*.png"):
        target = frames_dir / source.name
        if verify_png(target):
            continue
        info = verify_png(source)
        if info:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            restored += 1
    scene_target = out / "scene.blend"
    if not scene_target.exists():
        for candidate in resume_root.rglob("scene.blend"):
            if candidate.is_file() and candidate.stat().st_size > 1024 * 1024:
                shutil.copy2(candidate, scene_target)
                break
    return restored


def extract_evidence(frames_dir, out):
    groups = {
        "six_representative": [16, 66, 126, 166, 226, 286],
        "walk_consecutive": list(range(31, 37)),
        "door_consecutive": list(range(150, 156)),
        "shadow_consecutive": list(range(180, 186)),
    }
    for label, frame_numbers in groups.items():
        destination = out / "evidence" / label
        destination.mkdir(parents=True, exist_ok=True)
        for index, frame_number in enumerate(frame_numbers, 1):
            source = frames_dir / f"frame_{frame_number:04d}.png"
            if not verify_png(source):
                raise RuntimeError(f"Evidence source frame is missing or corrupt: {source}")
            shutil.copy2(source, destination / f"{index:02d}_frame_{frame_number:04d}.png")


def assemble_video(out, frames_dir, ffmpeg):
    mp4 = out / "nexus_blender3d_10s.mp4"
    log = out / "logs" / "ffmpeg_assembly.log"
    command = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "info",
        "-framerate", "30", "-start_number", "1",
        "-i", str(frames_dir / "frame_%04d.png"),
        "-i", str(out / "audio_master.wav"),
        "-frames:v", "300", "-vf", "format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-r", "30", "-c:a", "aac", "-b:a", "160k",
        "-t", "10", "-movflags", "+faststart", str(mp4),
    ]
    run_logged(command, log)
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-count_frames", "-show_streams",
        "-show_format", "-of", "json", str(mp4)
    ], text=True)
    (out / "ffprobe.json").write_text(probe, encoding="utf-8")
    return mp4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/blender3d")
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--block-size", type=int, default=30)
    parser.add_argument("--resume", default="")
    args = parser.parse_args()
    if args.block_size not in (30, 50):
        raise SystemExit("--block-size must be 30 or 50")
    if args.samples < 1:
        raise SystemExit("--samples must be positive")

    started = time.perf_counter()
    out = Path(args.out).resolve()
    frames_dir = out / "frames"
    logs_dir = out / "logs"
    frames_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    blender = shutil.which("blender")
    ffmpeg = shutil.which("ffmpeg")
    if not blender or not ffmpeg:
        raise SystemExit("Blender and FFmpeg are required")

    resume_root = Path(args.resume).resolve() if args.resume else None
    restored_frames = restore_checkpoint(resume_root, frames_dir, out)
    audio = out / "audio_master.wav"
    if not audio.exists():
        synth_audio(out)

    scene_file = out / "scene.blend"
    build_seconds = 0.0
    if not scene_file.exists():
        scene_script = Path(__file__).resolve().parents[1] / "nexus_video3d" / "scene_factory.py"
        env = os.environ.copy()
        env.update({
            "NEXUS_RENDER_OUT": str(frames_dir),
            "NEXUS_SAMPLES": str(args.samples),
            "NEXUS_BUILD_ONLY": "1",
        })
        build_seconds = run_logged(
            [blender, "-b", "-t", "2", "--python", str(scene_script)],
            logs_dir / "blender_scene_build.log", env=env
        )
    if not scene_file.is_file():
        raise RuntimeError("Blender did not save scene.blend")

    state_path = out / "frame_state.json"
    timing_path = out / "block_timings.json"
    timings = []
    if timing_path.exists():
        try:
            timings = json.loads(timing_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            timings = []

    # The first missing block is the measured performance sample. 30 frames
    # keeps each checkpoint to about one-sixth of the previous 90-minute run.
    for block_start in range(1, 301, args.block_size):
        block_end = min(300, block_start + args.block_size - 1)
        missing = []
        block_infos = {}
        for frame_number in range(block_start, block_end + 1):
            frame_path = frames_dir / f"frame_{frame_number:04d}.png"
            info = verify_png(frame_path)
            if info:
                block_infos[str(frame_number)] = info
            else:
                if frame_path.exists():
                    frame_path.unlink()
                missing.append(frame_number)

        block_started = time.perf_counter()
        rendered = 0
        for range_start, range_end in contiguous_ranges(missing):
            expression = (
                "import bpy; "
                "s=bpy.context.scene; "
                f"s.frame_start={range_start}; s.frame_end={range_end}; "
                f"s.render.filepath={json.dumps(str(frames_dir / 'frame_'))}; "
                "bpy.ops.render.render(animation=True)"
            )
            log_name = f"blender_frames_{range_start:04d}_{range_end:04d}.log"
            run_logged(
                [blender, "-b", str(scene_file), "-t", "2", "--python-expr", expression],
                logs_dir / log_name
            )
            rendered += range_end - range_start + 1

        for frame_number in range(block_start, block_end + 1):
            frame_path = frames_dir / f"frame_{frame_number:04d}.png"
            info = verify_png(frame_path)
            if not info:
                raise RuntimeError(
                    f"Block {block_start}-{block_end} incomplete: frame {frame_number} failed PNG verification"
                )
            block_infos[str(frame_number)] = info

        elapsed = time.perf_counter() - block_started
        entry = {
            "block_start": block_start,
            "block_end": block_end,
            "frames_expected": block_end - block_start + 1,
            "frames_rendered_this_run": rendered,
            "frames_reused_and_verified": (block_end - block_start + 1) - rendered,
            "elapsed_seconds": round(elapsed, 3),
            "seconds_per_new_frame": round(elapsed / rendered, 3) if rendered else 0.0,
            "peak_child_rss_kb_cumulative": int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
            "status": "verified",
        }
        timings = [x for x in timings if not (
            x.get("block_start") == block_start and x.get("block_end") == block_end
        )]
        timings.append(entry)
        timings.sort(key=lambda x: x["block_start"])
        write_json(timing_path, timings)

        completed = {}
        for frame_number in range(1, 301):
            frame_path = frames_dir / f"frame_{frame_number:04d}.png"
            info = verify_png(frame_path)
            if info:
                completed[str(frame_number)] = info
        write_json(state_path, {
            "schema": 1,
            "total_frames": 300,
            "verified_frames": len(completed),
            "completed_frames": completed,
            "last_verified_block": [block_start, block_end],
            "updated_unix": int(time.time()),
        })
        print(json.dumps(entry), flush=True)

        # Benchmark the first block containing new work. The measured rate is
        # reported, not extrapolated as a completion claim.
        if rendered and not any(x.get("benchmark") for x in timings):
            entry["benchmark"] = True
            write_json(timing_path, timings)

    verified = [
        verify_png(frames_dir / f"frame_{frame_number:04d}.png")
        for frame_number in range(1, 301)
    ]
    if any(info is None for info in verified):
        raise RuntimeError("Refusing MP4 assembly: not all 300 frames are valid 1080x1920 PNGs")

    mp4 = assemble_video(out, frames_dir, ffmpeg)
    extract_evidence(frames_dir, out)
    rendered_total = sum(x.get("frames_rendered_this_run", 0) for x in timings)
    render_seconds = sum(x.get("elapsed_seconds", 0) for x in timings)
    measured_frames = sum(x.get("frames_rendered_this_run", 0) for x in timings)
    performance = {
        "status": "FRAMES_COMPLETE_MP4_ASSEMBLED",
        "engine": "Blender Cycles CPU",
        "resolution": [1080, 1920],
        "fps": 30,
        "total_frames": 300,
        "block_size": args.block_size,
        "samples": args.samples,
        "denoising": True,
        "restored_frames_from_previous_artifact": restored_frames,
        "frames_rendered_in_this_run": rendered_total,
        "verified_frames": 300,
        "render_seconds_recorded_in_blocks": round(render_seconds, 3),
        "mean_seconds_per_rendered_frame_in_this_run": round(
            render_seconds / measured_frames, 3
        ) if measured_frames else None,
        "scene_build_seconds": round(build_seconds, 3),
        "elapsed_seconds_this_run": round(time.perf_counter() - started, 3),
        "peak_child_rss_kb": int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
        "blocks": timings,
        "video_bytes": mp4.stat().st_size,
    }
    write_json(out / "performance_report.json", performance)
    (out / "memory_snapshot.txt").write_text(
        subprocess.check_output(["free", "-h"], text=True), encoding="utf-8"
    )
    print(json.dumps(performance, indent=2), flush=True)


if __name__ == "__main__":
    main()
