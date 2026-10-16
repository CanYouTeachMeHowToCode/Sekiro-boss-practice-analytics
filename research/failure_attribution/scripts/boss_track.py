"""Track the boss through a recording by the lock-on dot, and keep a crop of the boss for every frame read.

Usage: python -I boss_track.py <recording id | all> [--step N]

Every N-th frame (default 2, 30 per second) goes through mask_overlay() first, then lockon.Tracker finds the white
lock-on dot. The crop is a CROP-pixel square (at 2560×1440, scaled for other sizes) centred DROP pixels below the dot,
since the dot sits on the chest and the legs matter more than the sky; it is stored at OUT×OUT. When the dot is
missing (a flash, the camera too close), the last dot is used for up to HOLD seconds; after that the crop is the
centre of the screen and the row says so.

Writes to work/<recording id>/:
    boss_track.csv   frame, time_s, state (dot / held / none), x, y, ncc
    boss_crops.npz   the crops as JPEG bytes: data (all bytes), offsets (start of each crop; one more than rows)
"""
import csv
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import recordings, video_path, work_dir  # noqa: E402
from lockon import Tracker  # noqa: E402
from overlay_mask import BASE_H, BASE_W, mask_overlay  # noqa: E402

CROP, DROP, OUT, HOLD = 640, 80, 256, 1.0
CENTRE = (1280, 620)


def crop(frame, x, y):
    h, w = frame.shape[:2]
    s = w / BASE_W
    half, cx, cy = int(CROP * s / 2), int(x), int(y + DROP * s)
    pad = cv2.copyMakeBorder(frame, half, half, half, half, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    part = pad[cy:cy + 2 * half, cx:cx + 2 * half]
    return cv2.resize(part, (OUT, OUT), interpolation=cv2.INTER_AREA)


def track(rec_id, rec, step):
    video = video_path(rec)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    tracker, rows, blobs = Tracker(), [], []
    last, last_t, n, start = None, -1e9, 0, time.time()
    while cap.grab():
        if n % step == 0:
            ok, frame = cap.retrieve()
            frame = mask_overlay(frame)
            t = n / fps
            s = frame.shape[1] / BASE_W
            hit = tracker(frame)
            if hit:
                last, last_t = hit[:2], t
                state, (x, y), ncc = "dot", hit[:2], hit[2]
            elif last is not None and t - last_t <= HOLD:
                state, (x, y), ncc = "held", last, 0.0
            else:
                state, (x, y), ncc = "none", (CENTRE[0] * s, CENTRE[1] * frame.shape[0] / BASE_H), 0.0
            rows.append([n, f"{t:.3f}", state, int(x), int(y), f"{ncc:.3f}"])
            blobs.append(cv2.imencode(".jpg", crop(frame, x, y), [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes())
        n += 1
    work = work_dir(rec_id)
    with open(work / "boss_track.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["frame", "time_s", "state", "x", "y", "ncc"])
        w.writerows(rows)
    offsets = np.cumsum([0] + [len(b) for b in blobs])
    np.savez(work / "boss_crops.npz", data=np.frombuffer(b"".join(blobs), np.uint8), offsets=offsets)
    states = {k: sum(1 for r in rows if r[2] == k) for k in ("dot", "held", "none")}
    print(f"{rec_id}: {len(rows)} frames in {time.time() - start:.0f} s, {states}")


def load_crops(rec_id):
    """The crops of a recording, decoded: (rows, OUT, OUT, 3) uint8, in boss_track.csv order."""
    d = np.load(work_dir(rec_id) / "boss_crops.npz")
    data, off = d["data"], d["offsets"]
    return np.stack([cv2.imdecode(data[off[i]:off[i + 1]], cv2.IMREAD_COLOR) for i in range(len(off) - 1)])


def main():
    recs = recordings()
    step = int(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 2
    ids = list(recs) if sys.argv[1] == "all" else [sys.argv[1]]
    for rec_id in ids:
        track(rec_id, recs[rec_id], step)


if __name__ == "__main__":
    main()
