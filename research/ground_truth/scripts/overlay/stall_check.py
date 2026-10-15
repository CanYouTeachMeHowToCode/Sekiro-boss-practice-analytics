"""Explain duration/span gaps by stalls: frames where the animation time does not advance.

Usage: python -I stall_check.py <data_dir>
For each occurrence: gap = duration - (t_end - t_start); stall = (number of consecutive-frame pairs whose reads are
equal) / fps - (the part expected from 60 fps vs 2-decimal rounding is small and ignored). Unexplained = gap - stall.
"""
import csv
import sys
from pathlib import Path

import numpy as np

FPS = 59.995
data = Path(sys.argv[1])
frames = list(csv.DictReader(open(data / "occ_frames.csv", encoding="utf-8")))
occ = list(csv.DictReader(open(data / "occurrences.csv", encoding="utf-8")))
rows = []
for o in occ:
    a, b, anim = int(o["start_frame"]), int(o["end_frame"]), o["anim"][5:]
    seq = []
    for f in range(a, b + 1):
        v = next((frames[f][f"line{k}"] for k in range(1, 6) if frames[f][f"line{k}"].startswith(anim + "@")), None)
        if v:
            seq.append((f, float(v.split("@")[1])))
    if len(seq) < 6:
        continue
    t = np.array([s[1] for s in seq])
    span = float(np.median(t[-3:]) - np.median(t[:3]))
    dur = (seq[-1][0] - seq[0][0]) / FPS
    steps = np.diff(t)
    stall = float(((np.abs(steps) < 0.005) & (np.diff([s[0] for s in seq]) == 1)).sum()) / FPS
    # at 60 fps the 2-decimal display normally advances every frame; a frame without change is a stall
    rows.append((o["anim"], a, b, dur, span, dur - span, stall, dur - span - stall))
un = [r for r in rows if r[7] > 0.15]
print("occurrences:", len(rows), "with gap > 0.25:", sum(r[5] > 0.25 for r in rows), "unexplained by stalls (> 0.15 s):", len(un))
for r in sorted(rows, key=lambda r: -r[5])[:16]:
    print("  %s %d-%d dur %.2f span %.2f gap %+.2f stall %.2f unexplained %+.2f" % r)
