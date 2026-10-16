"""Fourth pass: per-frame adaptive threshold for the binary reader (ID and animation time).

Usage: python -I overlay_extract4.py <data_dir>
For each frame and each threshold in THRESHOLDS the line is binarized, the six ID cells are matched against the
whitelist (as in the second pass), and the threshold with the lowest whitelist cost wins. The animation time
"(u.th)" is read from the same binarized frame. Writes frames4.csv.
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import CELL_Y0, CELL_Y1, ID_DIGITS, ID_PITCH, ID_X0

THRESHOLDS = (150, 170, 185, 200, 212, 225, 238)
TIME_X = (199, 221, 235)
data = Path(sys.argv[1])
lines = np.load(data / "line_min.npy", mmap_mode="r")
T = np.load(data / "templates_bootstrap.npy")
r2 = list(csv.DictReader(open(data / "frames2.csv", encoding="utf-8")))
whitelist = sorted(l.strip() for l in open(data / "whitelist_c7100_c7110.txt") if l.strip())
wl = np.array([[int(c) for c in w[5:]] for w in whitelist])
N = len(r2)
present = np.array([r["line"] == "1" for r in r2])

out = []
for s in range(0, N, 1000):
    L = np.asarray(lines[s:s + 1000])
    n = len(L)
    best_cost = np.full(n, np.inf)
    res = [None] * n
    for thr in THRESHOLDS:
        M = (L > thr).astype(np.float32)
        cells = np.stack([M[:, CELL_Y0:CELL_Y1, ID_X0 + k * ID_PITCH: ID_X0 + (k + 1) * ID_PITCH] for k in range(ID_DIGITS)], axis=1)
        d = np.abs(cells[:, :, None] - T[None, None]).mean(axis=(3, 4))                 # (n, 6, 10)
        cost = d[:, np.arange(ID_DIGITS)[None, :], wl].sum(axis=2)                       # (n, W)
        order = np.argsort(cost, axis=1)
        b, sec = order[:, 0], order[:, 1]
        bc = cost[np.arange(n), b]
        margin = cost[np.arange(n), sec] - bc
        free_ok = (d.argmin(axis=2) == wl[b]).all(axis=1)
        tc = np.stack([M[:, CELL_Y0:CELL_Y1, x:x + ID_PITCH] for x in TIME_X], axis=1)
        td = np.abs(tc[:, :, None] - T[None, None]).mean(axis=(3, 4))                   # (n, 3, 10)
        tdig = td.argmin(axis=2)
        ts = np.sort(td, axis=2)
        tmarg = (ts[:, :, 1] - ts[:, :, 0]).min(axis=1)
        for i in np.where(bc < best_cost)[0]:
            best_cost[i] = bc[i]
            res[i] = (thr, whitelist[b[i]], bc[i], margin[i], int(free_ok[i]),
                      tdig[i, 0] + tdig[i, 1] / 10 + tdig[i, 2] / 100, tmarg[i])
    for i in range(n):
        f = s + i
        if not present[f]:
            out.append([f, 0, "", "", "", "", "", "", "", ""])
            continue
        thr, a, c, m, fo, tv, tm = res[i]
        out.append([f, 1, thr, a, f"{c:.4f}", f"{m:.4f}", fo, f"{tv:.2f}", f"{tm:.4f}", r2[f]["anim"]])
    print("frames", s + n, flush=True)

with open(data / "frames4.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["frame", "line", "thr", "anim", "cost", "margin", "free_agrees", "anim_time", "time_margin", "anim_pass2"])
    w.writerows(out)
