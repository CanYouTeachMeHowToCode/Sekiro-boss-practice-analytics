"""Read one 'Active Anime' line from cached crops: presence, a-prefix digits, animation ID, animation time.

Usage: python -I read_line.py <data_dir> <lineK_min.npy> <out_csv>
Presence: grayscale correlation of the "a000_" region with the line-1 prefix. ID: per-frame adaptive threshold,
whitelist-constrained (cost, margin) plus an unconstrained per-cell read (free) to catch IDs outside the whitelist.
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import CELL_Y0, CELL_Y1, ID_DIGITS, ID_PITCH, ID_X0, PREFIX_X0, PREFIX_X1

THRESHOLDS = (150, 170, 185, 200, 212, 225, 238)
TIME_X = (199, 221, 235)
PREFIX_DIGIT_X = (43, 57, 71)
data, src, dst = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
line1 = np.load(data / "line_min.npy", mmap_mode="r")
lines = np.load(data / src, mmap_mode="r")
T = np.load(data / "templates_bootstrap.npy")
whitelist = sorted(l.strip() for l in open(data / "whitelist_c7100_c7110.txt") if l.strip())
wl = np.array([[int(c) for c in w[5:]] for w in whitelist])
N = len(lines)


def z(a):
    a = a.astype(np.float32)
    a = a - a.mean(axis=(-2, -1), keepdims=True)
    return a / np.maximum(a.std(axis=(-2, -1), keepdims=True), 1e-3)


prefix = z(z(np.stack([line1[n, CELL_Y0:CELL_Y1, PREFIX_X0:PREFIX_X1] for n in range(1000, 16000, 50)])).mean(axis=0))

rows = []
for s in range(0, N, 1000):
    L = np.asarray(lines[s:s + 1000])
    n = len(L)
    pre = (z(L[:, CELL_Y0:CELL_Y1, PREFIX_X0:PREFIX_X1]) * prefix).mean(axis=(1, 2))
    best = [None] * n
    bcost = np.full(n, np.inf)
    for thr in THRESHOLDS:
        M = (L > thr).astype(np.float32)
        cells = np.stack([M[:, CELL_Y0:CELL_Y1, ID_X0 + k * ID_PITCH: ID_X0 + (k + 1) * ID_PITCH] for k in range(ID_DIGITS)], axis=1)
        d = np.abs(cells[:, :, None] - T[None, None]).mean(axis=(3, 4))
        cost = d[:, np.arange(ID_DIGITS)[None, :], wl].sum(axis=2)
        order = np.argsort(cost, axis=1)
        b, sec = order[:, 0], order[:, 1]
        bc = cost[np.arange(n), b]
        margin = cost[np.arange(n), sec] - bc
        free = d.argmin(axis=2)
        pc = np.stack([M[:, CELL_Y0:CELL_Y1, x:x + ID_PITCH] for x in PREFIX_DIGIT_X], axis=1)
        pfree = np.abs(pc[:, :, None] - T[None, None]).mean(axis=(3, 4)).argmin(axis=2)
        tc = np.stack([M[:, CELL_Y0:CELL_Y1, x:x + ID_PITCH] for x in TIME_X], axis=1)
        tdig = np.abs(tc[:, :, None] - T[None, None]).mean(axis=(3, 4)).argmin(axis=2)
        for i in np.where(bc < bcost)[0]:
            bcost[i] = bc[i]
            best[i] = (thr, whitelist[b[i]], bc[i], margin[i], "".join(map(str, free[i])), "".join(map(str, pfree[i])),
                       tdig[i, 0] + tdig[i, 1] / 10 + tdig[i, 2] / 100)
    for i in range(n):
        thr, a, c, m, fr, pf, tv = best[i]
        rows.append([s + i, f"{pre[i]:.3f}", thr, a, f"{c:.4f}", f"{m:.4f}", fr, int(fr == a[5:]), pf, f"{tv:.2f}"])
    print("frames", s + n, flush=True)
with open(data / dst, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["frame", "prefix_ncc", "thr", "anim", "cost", "margin", "free", "free_agrees", "prefix_digits", "anim_time"])
    w.writerows(rows)
