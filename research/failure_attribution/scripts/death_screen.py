"""Find the death screen (the 死 kanji) in a registered recording; the detector is analysis/sekiro_analysis/death_screen.py.

Usage: python -I death_screen.py <recording id | all>

The glyph mask is cut once from a frame that shows the kanji (MASK_SOURCE) and kept in work/death_mask.npy; it comes
from the game's screen, so it stays local like the recordings (the worker gets a copy in its data folder).
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, recordings, video_path, work_dir  # noqa: E402
from sekiro_analysis import death_screen as ds  # noqa: E402
from sekiro_analysis.death_screen import region  # noqa: E402

MASK_SOURCE = ("2026-10-16-castle-1", 241.9)


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


def scan(rec_id, rec):
    ds.scan(video_path(rec), work_dir(rec_id), glyph_mask())


def main():
    recs = recordings()
    for rec_id in (list(recs) if sys.argv[1] == "all" else [sys.argv[1]]):
        scan(rec_id, recs[rec_id])


if __name__ == "__main__":
    main()
