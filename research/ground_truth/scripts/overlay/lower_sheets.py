"""Compact review sheets for the unsupported lower-line runs: label + that line's crop at the run's middle frame.

Usage: python -I lower_sheets.py <data_dir> <sheet_prefix>
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

data, prefix = Path(sys.argv[1]), sys.argv[2]
arrs = {k: np.load(data / f"line{k}_min.npy", mmap_mode="r") for k in (2, 3, 4, 5)}
rows = []
for r in csv.DictReader(open(data / "lower_unsupported.csv", encoding="utf-8")):
    k, a, b = int(r["line"]), int(r["start_frame"]), int(r["end_frame"])
    f = (a + b) // 2
    crop = cv2.resize(np.asarray(arrs[k][f, :, 20:400]), None, fx=1.0, fy=1.0)
    crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    lab = np.zeros((30, 300, 3), np.uint8)
    cv2.putText(lab, "U%s L%d %s %dfr" % (r["id"], k, r["anim"][5:], b - a + 1), (4, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    rows.append(np.hstack([lab, crop]))
for p in range(0, len(rows), 40):
    cv2.imwrite(f"{prefix}_{p // 40 + 1:02d}.png", np.vstack(rows[p:p + 40]))
print("sheets:", (len(rows) + 39) // 40)
