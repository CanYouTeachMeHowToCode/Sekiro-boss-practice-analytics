"""Animation-time reader with position-specific templates, for lines 1..5.

Usage: python -I time_read2.py <data_dir>
Labels: line-1 frames where the binary (time_bin.npy) and grayscale (frames3.csv) time reads agree.
Templates: per time cell (units / tenths / hundredths) and digit, the mean binary mask at the frame's adaptive
threshold (frames4.csv thr for line 1). Each line is then re-read at its own per-frame threshold.
Writes time2_line{k}.npy (N,) with nan where the line is absent, and prints a monotonicity check.
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import CELL_Y0, CELL_Y1, ID_PITCH

TIME_X = (199, 221, 235)
data = Path(sys.argv[1])
r4 = list(csv.DictReader(open(data / "frames4.csv", encoding="utf-8")))
r3 = list(csv.DictReader(open(data / "frames3.csv", encoding="utf-8")))
tb = np.load(data / "time_bin.npy")
N = len(r4)
present1 = np.array([r["line"] == "1" for r in r4])
tg = np.array([float(r3[i]["anim_time"]) if present1[i] else np.nan for i in range(N)])
agree = present1 & (np.abs(tb - tg) < 0.001)
thr1 = np.array([int(r["thr"]) if r["thr"] else 225 for r in r4])
L1 = np.load(data / "line_min.npy", mmap_mode="r")

sums = np.zeros((3, 10, CELL_Y1 - CELL_Y0, ID_PITCH))
counts = np.zeros((3, 10))
idx = np.where(agree)[0]
for s in range(0, len(idx), 2000):
    ii = idx[s:s + 2000]
    L = np.asarray(L1[ii])
    M = (L > thr1[ii][:, None, None]).astype(np.float32)
    v = np.round(tb[ii] * 100).astype(int)
    digs = np.stack([v // 100, (v // 10) % 10, v % 10], axis=1)
    for p, x in enumerate(TIME_X):
        cells = M[:, CELL_Y0:CELL_Y1, x:x + ID_PITCH]
        for d in range(10):
            sel = digs[:, p] == d
            sums[p, d] += cells[sel].sum(axis=0)
            counts[p, d] += sel.sum()
print("label counts per position (units/tenths/hundredths):\n", counts.astype(int))
T = sums / np.maximum(counts[:, :, None, None], 1)
# positions with no sample for a digit fall back to the same digit at another position
for p in range(3):
    for d in range(10):
        if counts[p, d] == 0:
            q = int(np.argmax(counts[:, d]))
            T[p, d] = T[q, d]
np.save(data / "time_templates.npy", T)


def read(L, thr):
    M = (L > thr[:, None, None]).astype(np.float32)
    out, marg = [], []
    for p, x in enumerate(TIME_X):
        cells = M[:, CELL_Y0:CELL_Y1, x:x + ID_PITCH]
        d = np.abs(cells[:, None] - T[p][None]).mean(axis=(2, 3))
        srt = np.sort(d, axis=1)
        out.append(d.argmin(axis=1))
        marg.append(srt[:, 1] - srt[:, 0])
    return out[0] + out[1] / 10 + out[2] / 100, np.min(marg, axis=0)


for k in range(1, 6):
    if k == 1:
        arr, thr, pres = L1, thr1, present1
    else:
        rk = list(csv.DictReader(open(data / f"line{k}.csv", encoding="utf-8")))
        arr = np.load(data / f"line{k}_min.npy", mmap_mode="r")
        thr = np.array([int(r["thr"]) for r in rk])
        pres = present1 & np.array([float(r["prefix_ncc"]) > 0.45 for r in rk])
    t = np.full(N, np.nan)
    m = np.zeros(N)
    for s in range(0, N, 2000):
        v, mm = read(np.asarray(arr[s:s + 2000]), thr[s:s + 2000])
        t[s:s + 2000] = np.where(pres[s:s + 2000], v, np.nan)
        m[s:s + 2000] = mm
    np.save(data / f"time2_line{k}.npy", t)
    np.save(data / f"time2_margin_line{k}.npy", m)
    if k == 1:
        anim = [r["anim"] for r in r4]
        for lo, hi in [(0, 16571), (19494, N)]:
            same = [i for i in range(lo + 1, hi) if pres[i] and pres[i - 1] and anim[i] == anim[i - 1]]
            dt = np.array([t[i] - t[i - 1] for i in same])
            ok = ((dt >= -0.001) & (dt <= 0.051)).sum()
            print(f"line 1 frames {lo}-{hi}: plausible step {ok}/{len(same)} ({ok / len(same):.2%}), drops<-0.05: {(dt < -0.05).sum()}")
        print("line 1 agreement with labels:", int((np.abs(t - tb)[agree] < 0.001).sum()), "/", int(agree.sum()))
