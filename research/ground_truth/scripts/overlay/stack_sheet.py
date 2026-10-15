"""Render lines 1..4 of the overlay (cached crops) for chosen frames, one block per frame.

Usage: python -I stack_sheet.py <data_dir> <out_png> <label:frame> [...]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

data, out = Path(sys.argv[1]), sys.argv[2]
arrs = [np.load(data / n, mmap_mode="r") for n in ("line_min.npy", "line2_min.npy", "line3_min.npy", "line4_min.npy")]
blocks = []
for item in sys.argv[3:]:
    label, f = item.rsplit(":", 1)
    f = int(f)
    stack = np.vstack([np.asarray(a[f, 3:28, 20:400]) for a in arrs])
    img = cv2.resize(stack, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_NEAREST)
    lab = np.zeros((img.shape[0], 250), np.uint8)
    cv2.putText(lab, label, (4, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 255, 1)
    cv2.putText(lab, "f%d" % f, (4, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 255, 1)
    blocks.append(np.hstack([lab, img]))
    blocks.append(np.full((6, blocks[-1].shape[1]), 90, np.uint8))
cv2.imwrite(out, np.vstack(blocks))
