"""Find the death screen: the big grey 死 kanji (with "DEATH" under it) that Sekiro shows when Wolf dies.

Usage: python -I death_screen.py <recording id | all>

Wolf's HP bar alone cannot tell a death: a hit can leave a sliver of HP too thin to read, and Wolf fights on with an
empty-looking bar until the hit that really kills (rec 2026-10-16-castle-1: the bar reads 0 from 224.5 s, the 死 shows
at 241.2 s). So a death is confirmed by the 死 screen. The kanji is flat, opaque grey (V ≈ 126, S < 15) at a fixed place
in the middle of the screen. A frame shows it when nearly every pixel of the glyph mask has one flat grey colour while
the ring just outside the glyph mostly does not.

The glyph mask is cut once from a frame that shows the kanji (MASK_SOURCE, a registered recording) and kept in
work/death_mask.npy; it comes from the game's screen, so it stays local like the recordings.

Only the stretches where the HUD reads Wolf's HP as zero (hud.csv), and the SEARCH_AFTER seconds after each (the HUD
can go away on the death screen), are searched, every STEP seconds. Writes work/<recording id>/death_screens.csv: one
row per stretch of 死 frames (start_s, end_s).
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, recordings, video_path, work_dir  # noqa: E402
from overlay_mask import BASE_H, BASE_W  # noqa: E402

REGION = (1000, 420, 1560, 960)                    # x0, y0, x1, y1 at 2560×1440
MASK_SOURCE = ("2026-10-16-castle-1", 241.9)
STEP, SEARCH_AFTER, MIN_INSIDE, MAX_RING, ZERO = 0.1, 6.0, 0.8, 0.5, 0.003


def region(frame):
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = REGION
    part = frame[int(y0 * h / BASE_H):int(y1 * h / BASE_H), int(x0 * w / BASE_W):int(x1 * w / BASE_W)]
    return cv2.resize(part, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA) if w != BASE_W else part


def glyph_mask():
    path = WORK / "death_mask.npy"
    if path.exists():
        return np.load(path)
    rec_id, t = MASK_SOURCE
    cap = cv2.VideoCapture(str(video_path(recordings()[rec_id])))
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, frame = cap.read()
    hsv = cv2.cvtColor(region(frame), cv2.COLOR_BGR2HSV).astype(int)
    grey = ((hsv[..., 1] < 22) & (np.abs(hsv[..., 2] - 126) < 10)).astype(np.uint8)
    grey = cv2.morphologyEx(grey, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(grey)
    mask = np.isin(lab, [i for i in range(1, n) if st[i][4] > 1500 and st[i][1] < 400])
    WORK.mkdir(parents=True, exist_ok=True)
    np.save(path, mask)
    return mask


class Detector:
    def __init__(self):
        self.mask = glyph_mask()
        m = self.mask.astype(np.uint8)
        self.ring = (cv2.dilate(m, np.ones((31, 31), np.uint8)) > 0) & ~(cv2.dilate(m, np.ones((9, 9), np.uint8)) > 0)

    def score(self, frame):
        """(share of glyph pixels in one flat grey, share of ring pixels in that grey, the grey's V)."""
        hsv = cv2.cvtColor(region(frame), cv2.COLOR_BGR2HSV).astype(int)
        v, s = hsv[..., 2], hsv[..., 1]
        grey = float(np.median(v[self.mask]))
        flat = (np.abs(v - grey) < 12) & (s < 30)
        return float(flat[self.mask].mean()), float(flat[self.ring].mean()), grey

    def __call__(self, frame):
        inside, ring, grey = self.score(frame)
        return inside >= MIN_INSIDE and ring <= MAX_RING and 80 <= grey <= 180


def scan(rec_id, rec):
    rows = list(csv.DictReader(open(work_dir(rec_id) / "hud.csv", encoding="utf-8")))
    t = np.array([float(r["time_s"]) for r in rows])
    zero = np.array([r["hud"] == "1" and float(r["hp"]) <= ZERO for r in rows])
    spans, i = [], 0
    while i < len(t):
        if zero[i]:
            j = i
            while j + 1 < len(t) and (zero[j + 1] or rows[j + 1]["hud"] == "0"):
                j += 1
            spans.append((t[i], t[j] + SEARCH_AFTER))
            i = j + 1
        else:
            i += 1
    detect, cap = Detector(), cv2.VideoCapture(str(video_path(rec)))
    fps = cap.get(cv2.CAP_PROP_FPS)
    every = max(1, round(STEP * fps))
    hits = []
    for a, b in spans:                             # seek once per stretch, then read on: seeking HEVC is slow
        n = int(a * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, n)
        while n <= b * fps and cap.grab():
            if n % every == 0:
                ok, frame = cap.retrieve()
                if ok and detect(frame):
                    hits.append(n / fps)
            n += 1
    screens = []
    for x in hits:
        if screens and x - screens[-1][1] <= 2 * STEP + 1e-6:
            screens[-1][1] = x
        else:
            screens.append([x, x])
    with open(work_dir(rec_id) / "death_screens.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["start_s", "end_s"])
        w.writerows([[f"{a:.2f}", f"{b:.2f}"] for a, b in screens])
    print(f"{rec_id}: {len(spans)} zero-HP stretches searched, death screens at "
          + (", ".join(f"{a:.1f}-{b:.1f}s" for a, b in screens) or "none"))


def main():
    recs = recordings()
    for rec_id in (list(recs) if sys.argv[1] == "all" else [sys.argv[1]]):
        scan(rec_id, recs[rec_id])


if __name__ == "__main__":
    main()
