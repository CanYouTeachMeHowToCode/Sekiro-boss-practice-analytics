"""Show one ID's overlay line every STEP frames over a frame range (taken from whichever line shows it).

Usage: python -I occ_strip.py <data_dir> <out_png> <anim_digits> <from> <to> <step>
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

data, out, anim, a, b, step = Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
frames = list(csv.DictReader(open(data / "occ_frames.csv", encoding="utf-8")))
arrs = {1: np.load(data / "line_min.npy", mmap_mode="r")}
for k in (2, 3, 4, 5):
    arrs[k] = np.load(data / f"line{k}_min.npy", mmap_mode="r")
cells = []
for f in range(a, b + 1, step):
    k = next((k for k in range(1, 6) if frames[f][f"line{k}"].startswith(anim + "@")), None)
    crop = np.asarray(arrs[k][f, :, 100:400]) if k else np.zeros((30, 300), np.uint8)
    lab = np.zeros((30, 110), np.uint8)
    cv2.putText(lab, "%d L%s" % (f, k or "-"), (2, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 255, 1)
    cells.append(np.hstack([lab, crop, np.zeros((30, 8), np.uint8)]))
if len(cells) % 2:
    cells.append(np.zeros_like(cells[0]))
h = len(cells) // 2
img = np.hstack([np.vstack(cells[:h]), np.vstack(cells[h:])])
cv2.imwrite(out, cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_NEAREST))
