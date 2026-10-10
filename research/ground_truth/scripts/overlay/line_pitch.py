"""Find the vertical offsets of further 'Active Anime' lines by matching the 'a000_' prefix at shifted rows.

Usage: python -I line_pitch.py <video> <data_dir> <frame> [...]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import CELL_Y0, CELL_Y1, LINE_X0, LINE_Y0, PREFIX_X0, PREFIX_X1

video, data = sys.argv[1], Path(sys.argv[2])
frames = sorted(int(f) for f in sys.argv[3:])
lines = np.load(data / "line_min.npy", mmap_mode="r")


def z(a):
    a = a.astype(np.float32) - a.mean()
    return a / max(a.std(), 1e-3)


# the prefix as seen on line 1 in many frames (a000_ is identical on every line)
prefix = z(np.mean([lines[n, CELL_Y0:CELL_Y1, PREFIX_X0 + 10:PREFIX_X1] for n in range(1000, 16000, 50)], axis=0))
cap = cv2.VideoCapture(video)
n, want = 0, set(frames)
while want:
    ok, f = cap.read()
    if not ok:
        break
    if n in want:
        g = f.min(axis=2)
        scores = []
        for dy in range(-5, 120):
            y = LINE_Y0 + CELL_Y0 + dy
            patch = g[y:y + (CELL_Y1 - CELL_Y0), LINE_X0 + PREFIX_X0 + 10: LINE_X0 + PREFIX_X1]
            scores.append((float((z(patch) * prefix).mean()), dy))
        peaks = [(round(s, 2), dy) for s, dy in scores if s > 0.5]
        print(n, "rows where 'a000_' matches (ncc, dy):", peaks)
        want.discard(n)
    n += 1
