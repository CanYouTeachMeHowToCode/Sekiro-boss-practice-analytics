"""Run the HUD steps for one recording: cache, series, events and the review thumbnails.

Usage: python -I hud_pipeline.py <recording id | all> [--recache]

Reads the video named in recordings.json from recordings_dir (local.config); writes to work/<recording id>/:
hud_cache.npz (skipped when present, unless --recache), hud.csv, events.csv and thumbs/<event key>.jpg, and for a
dev-menu recording the move answers (failure_answers.py), which follow the events. A thumbnail
shows six moments around the event (-1.0 to +1.0 s), each with the HP and posture read at that moment; frames go
through mask_overlay() like everywhere else.
"""
import csv
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HERE, recordings, video_path, work_dir  # noqa: E402
from overlay_mask import mask_overlay  # noqa: E402

OFFSETS = (-1.0, -0.5, -0.15, 0.15, 0.5, 1.0)
THUMB_W, THUMB_H = 400, 225


def run(script, *args):
    subprocess.run([sys.executable, "-I", str(HERE / script), *map(str, args)], check=True)


def thumbnails(video, work):
    hud = list(csv.DictReader(open(work / "hud.csv", encoding="utf-8")))
    times = np.array([float(r["time_s"]) for r in hud])
    events = list(csv.DictReader(open(work / "events.csv", encoding="utf-8")))
    out = work / "thumbs"
    out.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    for e in events:
        cells = []
        for off in OFFSETS:
            t = float(e["time_s"]) + off
            cap.set(cv2.CAP_PROP_POS_MSEC, max(t, 0) * 1000)
            ok, frame = cap.read()
            if not ok:
                frame = np.zeros((1440, 2560, 3), np.uint8)
            cell = cv2.resize(mask_overlay(frame), (THUMB_W, THUMB_H), interpolation=cv2.INTER_AREA)
            r = hud[int(np.argmin(abs(times - t)))]
            label = f"{off:+.2f}s  HP {float(r['hp']):.2f}  posture {float(r['posture']):.2f}"
            cv2.rectangle(cell, (0, 0), (THUMB_W, 22), (0, 0, 0), -1)
            cv2.putText(cell, label, (6, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cells.append(cell)
        top, bottom = np.hstack(cells[:3]), np.hstack(cells[3:])
        cv2.imwrite(str(out / f"{e['key']}.jpg"), np.vstack([top, bottom]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f"{len(events)} thumbnails in {out}")


def main():
    recs = recordings()
    ids = list(recs) if sys.argv[1] == "all" else [sys.argv[1]]
    for rec_id in ids:
        rec, work = recs[rec_id], work_dir(rec_id)
        video = video_path(rec)
        print(f"== {rec_id}: {video.name}")
        if "--recache" in sys.argv or not (work / "hud_cache.npz").exists():
            run("hud_read.py", "cache", video, work / "hud_cache.npz")
        run("hud_read.py", "series", work / "hud_cache.npz", work / "hud.csv")
        run("events.py", work / "hud.csv", work / "events.csv")
        if rec.get("overlay"):
            run("failure_answers.py", rec_id)
        thumbnails(video, work)


if __name__ == "__main__":
    main()
