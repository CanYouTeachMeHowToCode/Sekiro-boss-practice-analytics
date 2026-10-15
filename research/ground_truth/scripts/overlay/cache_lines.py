"""Cache min-channel crops of 'Active Anime' lines 2..5 (rows measured: +27, +54, +80, +107) for every frame.

Usage: python -I cache_lines23.py <video> <data_dir>
Writes line2_min.npy .. line5_min.npy, each (N, 30, 400), same layout as line_min.npy.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import LINE_X0, LINE_X1, LINE_Y0, LINE_Y1

OFFSETS = {2: 27, 3: 54, 4: 80, 5: 107}
video, data = sys.argv[1], Path(sys.argv[2])
cap = cv2.VideoCapture(video)
out = {k: [] for k in OFFSETS}
while True:
    ok, f = cap.read()
    if not ok:
        break
    for k in out:
        dy = OFFSETS[k]
        out[k].append(f[LINE_Y0 + dy:LINE_Y1 + dy, LINE_X0:LINE_X1].min(axis=2))
for k, v in out.items():
    np.save(data / f"line{k}_min.npy", np.stack(v))
print("frames", len(out[2]))
