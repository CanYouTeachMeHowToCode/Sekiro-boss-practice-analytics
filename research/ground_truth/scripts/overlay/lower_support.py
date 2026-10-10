"""Split lower-line runs into those supported by a visually verified line-1 run of the same ID nearby
(within PAD frames) and unsupported ones that need a visual check; draw review sheets for the latter.

Usage: python -I lower_support.py <data_dir> <sheet_prefix>
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

PAD = 15
data, prefix = Path(sys.argv[1]), sys.argv[2]
r1 = list(csv.DictReader(open(data / "frames4.csv", encoding="utf-8")))
N = len(r1)
line1 = [r["anim"] if r["line"] == "1" else "" for r in r1]
arrs = {k: np.load(data / f"line{k}_min.npy", mmap_mode="r") for k in (2, 3, 4, 5)}
arrs[1] = np.load(data / "line_min.npy", mmap_mode="r")
uns, total = [], 0
for k in (2, 3, 4, 5):
    for r in csv.DictReader(open(data / f"runs_line{k}.csv", encoding="utf-8")):
        total += 1
        a, b = int(r["start_frame"]), int(r["end_frame"])
        if r["anim"] in set(line1[max(0, a - PAD): min(N, b + PAD + 1)]):
            continue
        uns.append((k, r["anim"], a, b))
print("lower-line runs:", total, "unsupported:", len(uns))
blocks = []
for idx, (k, anim, a, b) in enumerate(uns):
    f = (a + b) // 2
    stack = np.vstack([np.asarray(arrs[j][f, 3:28, 20:400]) for j in (1, 2, 3, 4, 5)])
    img = cv2.resize(stack, None, fx=1.3, fy=1.3, interpolation=cv2.INTER_NEAREST)
    lab = np.zeros((img.shape[0], 230), np.uint8)
    cv2.putText(lab, "U%d L%d %s" % (idx + 1, k, anim[5:]), (4, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 255, 1)
    cv2.putText(lab, "f%d (%d fr)" % (f, b - a + 1), (4, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 255, 1)
    blocks.append(np.vstack([np.hstack([lab, img]), np.full((5, lab.shape[1] + img.shape[1]), 90, np.uint8)]))
per = 12
for p in range(0, len(blocks), per):
    cv2.imwrite(f"{prefix}_{p // per + 1:02d}.png", np.vstack(blocks[p:p + per]))
with open(data / "lower_unsupported.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["id", "line", "anim", "start_frame", "end_frame"])
    w.writerows([[i + 1, *u] for i, u in enumerate(uns)])
from collections import Counter
print("unsupported by ID:", Counter(u[1][5:] for u in uns).most_common())
print("sheets:", (len(blocks) + per - 1) // per)
