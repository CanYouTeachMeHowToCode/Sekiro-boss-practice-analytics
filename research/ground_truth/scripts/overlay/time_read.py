"""Read the "(u.th)" animation-time field with binary templates and check it for monotonic growth within runs.

Usage: python -I time_read.py <data_dir>
Uses templates_bootstrap.npy (binary digit templates from the second pass) at the fixed time cells.
Writes time_bin.npy (N,) with the read time (nan where no line) and time_margin.npy.
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import CELL_Y0, CELL_Y1, ID_PITCH

TIME_X = (199, 221, 235)
data = Path(sys.argv[1])
lines = np.load(data / "line_min.npy", mmap_mode="r")
T = np.load(data / "templates_bootstrap.npy")            # (10, H, 14) binary means
r2 = list(csv.DictReader(open(data / "frames2.csv", encoding="utf-8")))
r3 = list(csv.DictReader(open(data / "frames3.csv", encoding="utf-8")))
N = len(r2)
present = np.array([r["line"] == "1" for r in r2])
anim = [r["anim"] for r in r2]

tb = np.full(N, np.nan)
tm = np.zeros(N)
for s in range(0, N, 2000):
    L = np.asarray(lines[s:s + 2000])
    for thr in (225,):
        M = (L > thr).astype(np.float32)
        cells = np.stack([M[:, CELL_Y0:CELL_Y1, x:x + ID_PITCH] for x in TIME_X], axis=1)   # (n, 3, H, 14)
        d = np.abs(cells[:, :, None] - T[None, None]).mean(axis=(3, 4))                    # (n, 3, 10)
        dig = d.argmin(axis=2)
        ds = np.sort(d, axis=2)
        marg = (ds[:, :, 1] - ds[:, :, 0]).min(axis=1)
        val = dig[:, 0] + dig[:, 1] / 10 + dig[:, 2] / 100
        tb[s:s + len(L)] = np.where(present[s:s + len(L)], val, np.nan)
        tm[s:s + len(L)] = marg
np.save(data / "time_bin.npy", tb)
np.save(data / "time_margin.npy", tm)

t3 = np.array([float(r["anim_time"]) if present[i] else np.nan for i, r in enumerate(r3)])


def judge(t, name):
    same = np.array([present[i] and present[i - 1] and anim[i] == anim[i - 1] for i in range(N)])
    same[0] = False
    dt = np.full(N, np.nan)
    dt[1:] = t[1:] - t[:-1]
    ok = same & (dt >= -0.001) & (dt <= 0.051)
    big_drop = same & (dt < -0.05)
    other = same & ~ok & ~big_drop
    print(f"{name}: consecutive same-ID pairs {same.sum()}, plausible step {ok.sum()}, drops {big_drop.sum()}, other jumps {other.sum()}")
    return dt, same


dtb, same = judge(tb, "binary")
dt3, _ = judge(t3, "grayscale")
agree = present & (np.abs(tb - t3) < 0.001)
print("binary == grayscale time:", int(agree.sum()), "/", int(present.sum()))
# start-of-run times: a fresh animation should start near 0
starts = [i for i in range(N) if present[i] and (i == 0 or not present[i - 1] or anim[i] != anim[i - 1])]
print("run-start binary time pct 50/90/99:", np.nanpercentile(tb[starts], [50, 90, 99]).round(2))
print("example run starts (frame, anim, t_bin, t_gray):", [(i, anim[i][5:], tb[i], t3[i]) for i in starts[:12]])
