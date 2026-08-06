#!/usr/bin/env python3
"""Extract start/middle/end frames from reviewed clips and build a labeled contact sheet."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def label_font(size: int = 22):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def duration(path: Path) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def extract(path: Path, at: float, output: Path) -> None:
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y", "-ss", f"{at:.3f}", "-i", str(path),
        "-frames:v", "1", "-vf", "scale=360:-2", str(output)
    ], check=True)


def fit_cell(image: Image.Image, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGB", (width, height), "#111111")
    copy = image.copy()
    copy.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas.paste(copy, ((width - copy.width) // 2, (height - copy.height) // 2))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("ffmpeg and ffprobe are required")
    root = Path(args.project).expanduser().resolve()
    shot_paths = sorted((root / "02_storyboard" / "shots").glob("*/shot.json"))
    rows = []
    missing = []
    with tempfile.TemporaryDirectory(prefix="ai-ad-contact-") as temp_name:
        temp = Path(temp_name)
        for shot_path in shot_paths:
            shot = json.loads(shot_path.read_text(encoding="utf-8"))
            video_value = shot.get("assets", {}).get("video", "")
            video = (root / video_value).resolve() if video_value else None
            if not video or not video.is_file():
                missing.append(shot.get("shot_id", shot_path.parent.name))
                continue
            total = duration(video)
            times = [0.0, max(0.0, total / 2), max(0.0, total - 0.08)]
            frames = []
            for index, at in enumerate(times):
                target = temp / f"{shot['shot_id']}-{index}.jpg"
                extract(video, at, target)
                frames.append(Image.open(target).convert("RGB"))
            rows.append((shot, frames))
        if not rows:
            raise SystemExit("No shot records reference an existing video file")

        cell_w, cell_h, label_h, gap = 360, 220, 54, 12
        sheet_w = cell_w * 3 + gap * 4
        sheet_h = (cell_h + label_h + gap) * len(rows) + gap
        sheet = Image.new("RGB", (sheet_w, sheet_h), "#202124")
        draw = ImageDraw.Draw(sheet)
        font = label_font()
        for row_index, (shot, frames) in enumerate(rows):
            y = gap + row_index * (cell_h + label_h + gap)
            label = f"{shot['shot_id']}  {shot.get('review', {}).get('status', 'draft')}  {shot.get('story_requirement', '')}"
            draw.text((gap, y), label[:150], fill="white", font=font)
            frame_y = y + label_h
            for column, frame in enumerate(frames):
                x = gap + column * (cell_w + gap)
                sheet.paste(fit_cell(frame, cell_w, cell_h), (x, frame_y))
        output = Path(args.output).expanduser().resolve() if args.output else root / "05_edit" / "contact-sheets" / "shot-contact-sheet.jpg"
        output.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(output, quality=92)
        report = {"output": str(output), "included_shots": [shot["shot_id"] for shot, _ in rows], "missing_video": missing}
        (output.parent / "contact-sheet-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
