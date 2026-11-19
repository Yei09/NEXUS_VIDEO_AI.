from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat


def extract(video: Path, timestamp: float, target: Path) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-ss", f"{timestamp:.3f}", "-i", str(video),
        "-frames:v", "1", "-q:v", "2", str(target)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def find_video(root: Path) -> Path:
    matches = sorted(root.rglob("*.mp4"))
    if not matches:
        raise FileNotFoundError(f"No se encontró MP4 dentro de {root}")
    return matches[0]


def load_metadata(root: Path) -> dict:
    matches = list(root.rglob("metadata.json"))
    if not matches:
        raise FileNotFoundError(f"No se encontró metadata.json dentro de {root}")
    return json.loads(matches[0].read_text(encoding="utf-8"))


def event_time(event: dict) -> float:
    return float(event.get("start_seconds", 0)) + float(event.get("duration_seconds", 0)) * 0.55


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Uso: compare_v41_v42.py BASELINE_DIR CURRENT_DIR OUTPUT_DIR")
    baseline_root, current_root, output = map(Path, sys.argv[1:])
    output.mkdir(parents=True, exist_ok=True)
    baseline_video, current_video = find_video(baseline_root), find_video(current_root)
    baseline_meta, current_meta = load_metadata(baseline_root), load_metadata(current_root)
    old_events, new_events = baseline_meta["events"], current_meta["events"]
    if len(old_events) != 6 or len(new_events) != 6:
        raise RuntimeError("La comparación requiere exactamente seis escenas en ambas versiones.")
    cell_w, cell_h = 270, 480
    sheet = Image.new("RGB", (cell_w*2, (cell_h+34)*6), (7, 9, 14))
    draw = ImageDraw.Draw(sheet)
    rows = []
    for i, (old_event, new_event) in enumerate(zip(old_events, new_events), 1):
        old_frame = output / f"v4.1-scene-{i:02d}.jpg"
        new_frame = output / f"v4.2-scene-{i:02d}.jpg"
        extract(baseline_video, event_time(old_event), old_frame)
        extract(current_video, event_time(new_event), new_frame)
        old_img = Image.open(old_frame).convert("RGB").resize((cell_w, cell_h))
        new_img = Image.open(new_frame).convert("RGB").resize((cell_w, cell_h))
        score = round(sum(ImageStat.Stat(ImageChops.difference(old_img, new_img)).mean)/3, 3)
        y = (i-1)*(cell_h+34)
        sheet.paste(old_img, (0, y+34))
        sheet.paste(new_img, (cell_w, y+34))
        draw.text((10, y+10), f"V4.1 · {old_event.get('scene','scene')}", fill=(240,240,240))
        draw.text((cell_w+10, y+10), f"V4.2 · {new_event.get('scene','scene')}", fill=(240,240,240))
        rows.append({
            "index": i, "scene_v41": old_event.get("scene"),
            "scene_v42": new_event.get("scene"),
            "v41_timestamp_seconds": round(event_time(old_event), 3),
            "v42_timestamp_seconds": round(event_time(new_event), 3),
            "mean_absolute_rgb_difference": score,
            "v41_frame": old_frame.name, "v42_frame": new_frame.name
        })
    sheet_path = output / "v4.1-vs-v4.2-contact-sheet.jpg"
    sheet.save(sheet_path, quality=92)
    report = {
        "baseline_commit": "3ce3e34860b452e3cbbed7d31fffe681d2f0a4de",
        "baseline_run_id": 43819913441,
        "baseline_video": str(baseline_video),
        "current_video": str(current_video),
        "scene_count": 6,
        "comparison_method": "paired MP4 frame extraction at each event midpoint; RGB mean absolute difference is descriptive, not an aesthetic score",
        "scenes": rows,
        "contact_sheet": sheet_path.name
    }
    (output / "comparison_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
