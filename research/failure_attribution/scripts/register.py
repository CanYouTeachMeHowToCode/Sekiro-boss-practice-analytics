"""Add the owner's new recordings to recordings.json.

Usage: python -I register.py [file name ...] [--overlay] [--use "text"]

With no file names, every video in recordings_dir (local.config) and its subfolders that recordings.json does not list
yet is added; file names are relative to recordings_dir ("测试录像/测试录像1.mp4").
Each entry gets an id from the file's date (modification time), "-castle" and a number (2026-10-16-castle-1, -2, ...),
its SHA-256, ruleset vanilla and game version 1.06 (the owner's setup for M1; edit the
entry if a recording differs), overlay false unless --overlay, and a `use` note. The video's size, frame rate and
length are printed so a recording that is not 2560×1440, 16:9 or 60 fps is noticed before the pipeline runs.
"""
import configparser
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FA, GT  # noqa: E402

VIDEO = {".mp4", ".mkv", ".mov"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    config = configparser.ConfigParser()
    config.read(GT / "local.config", encoding="utf-8")
    folder = Path(config["paths"]["recordings_dir"])
    registry_path = FA / "recordings.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    known = {r["file_name"] for r in registry["recordings"]}
    ids = {r["id"] for r in registry["recordings"]}
    args, names, overlay, use, i = sys.argv[1:], [], False, None, 0
    while i < len(args):
        if args[i] == "--overlay":
            overlay = True
        elif args[i] == "--use":
            use, i = args[i + 1], i + 1
        else:
            names.append(args[i])
        i += 1
    files = [folder / n for n in names] if names else sorted(p for p in folder.rglob("*") if p.suffix.lower() in VIDEO)
    use = use or ("reference: dev-menu fight recorded for V4 M1" if overlay
                  else "answer set: fight without the overlay, labelled by the owner")
    added = 0
    for path in files:
        name = path.relative_to(folder).as_posix()
        if name in known:
            continue
        if not path.exists():
            sys.exit(f"{path} not found")
        cap = cv2.VideoCapture(str(path))
        w, h, fps, n = (cap.get(p) for p in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS,
                                             cv2.CAP_PROP_FRAME_COUNT))
        day = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        rec_id = next(f"{day}-castle-{k}" for k in range(1, 1000) if f"{day}-castle-{k}" not in ids)
        ids.add(rec_id)
        registry["recordings"].append({"id": rec_id, "file_name": name, "sha256": sha256(path), "ruleset": "vanilla",
                                       "game_version": "1.06", "overlay": overlay, "use": use})
        warn = "" if (int(w), int(h)) == (2560, 1440) and abs(fps - 60) < 1 else "   <- not 2560×1440 at 60 fps"
        if abs(w / h - 16 / 9) > 0.01:
            warn += "   <- not 16:9: the HUD positions will not fit"
        print(f"{rec_id}: {name}  {int(w)}×{int(h)} {fps:.2f} fps {n / fps:.0f} s{warn}")
        added += 1
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{added} added to {registry_path}")


if __name__ == "__main__":
    main()
