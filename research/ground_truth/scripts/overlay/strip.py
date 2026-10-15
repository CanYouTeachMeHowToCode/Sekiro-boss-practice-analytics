"""Render cached overlay lines for a list of frames (2 columns), labelled with the frame number.

Usage: python -I strip.py <data_dir> <out_png> <frame> [...]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

data, out, frames = Path(sys.argv[1]), sys.argv[2], [int(f) for f in sys.argv[3:]]
lines = np.load(data / "line_min.npy", mmap_mode="r")
cells = []
for f in frames:
    img = cv2.resize(np.asarray(lines[f, :, 20:400]), None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    label = np.zeros((img.shape[0], 110), np.uint8)
    cv2.putText(label, str(f), (4, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, 255, 1)
    cells.append(np.hstack([label, img, np.zeros((img.shape[0], 10), np.uint8)]))
if len(cells) % 2:
    cells.append(np.zeros_like(cells[0]))
half = len(cells) // 2
cv2.imwrite(out, np.hstack([np.vstack(cells[:half]), np.vstack(cells[half:])]))
