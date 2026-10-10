"""Decode the recording once and cache the min-channel crops of the overlay lines.

Usage: python -I cache_crops.py <video> <data_dir>
Writes line_min.npy (N, 30, 400) for the animation line and char_min.npy (N, 20, 275) for the character line.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import CHAR_X0, CHAR_X1, CHAR_Y0, CHAR_Y1, LINE_X0, LINE_X1, LINE_Y0, LINE_Y1

video, data = sys.argv[1], Path(sys.argv[2])
cap = cv2.VideoCapture(video)
lines, chars = [], []
while True:
    ok, f = cap.read()
    if not ok:
        break
    lines.append(f[LINE_Y0:LINE_Y1, LINE_X0:LINE_X1].min(axis=2))
    chars.append(f[CHAR_Y0:CHAR_Y1, CHAR_X0:CHAR_X1].min(axis=2))
np.save(data / "line_min.npy", np.stack(lines))
np.save(data / "char_min.npy", np.stack(chars))
print("frames", len(lines))
