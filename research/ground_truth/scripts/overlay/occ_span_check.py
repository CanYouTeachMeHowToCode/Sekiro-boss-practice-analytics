"""Hidden-restart check over all occurrences: wall-clock duration vs. animation-time span.

Usage: python -I occ_span_check.py <data_dir>
Robust start/end times are medians of the first/last 3 reads. An occurrence is flagged when
duration - span > 0.25 s (time advanced less than real time: a restart may hide inside, or the game paused/slowed)
or span - duration > 0.1 s (time advanced faster than real time). Flags are then grouped per ID, so a gap that
every occurrence of an ID shares (a property of that animation) stands apart from one-off gaps.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

FPS = 59.995
data = Path(sys.argv[1])
frames = list(csv.DictReader(open(data / "occ_frames.csv", encoding="utf-8")))
occ = list(csv.DictReader(open(data / "occurrences.csv", encoding="utf-8")))


def times(anim, a, b):
    out = []
    for f in range(a, b + 1):
        for k in range(1, 6):
            v = frames[f][f"line{k}"]
            if v and v.split("@")[0] == anim[5:]:
                out.append(float(v.split("@")[1]))
    return out


by_id = defaultdict(list)
flagged = []
for o in occ:
    a, b = int(o["start_frame"]), int(o["end_frame"])
    t = times(o["anim"], a, b)
    if len(t) < 6:
        continue
    span = float(np.median(t[-3:]) - np.median(t[:3]))
    dur = (b - a) / FPS
    gap = dur - span
    by_id[o["anim"]].append(gap)
    if gap > 0.25 or -gap > 0.1:
        flagged.append((o["anim"], a, b, round(dur, 2), round(float(np.median(t[:3])), 2), round(float(np.median(t[-3:])), 2), round(gap, 2)))
print("occurrences checked:", sum(len(v) for v in by_id.values()), "flagged:", len(flagged))
for f in flagged:
    gaps = by_id[f[0]]
    print("  %s frames %d-%d dur %.2f t %.2f->%.2f gap %+.2f | this ID: %d occ, median gap %+.2f" % (*f, len(gaps), float(np.median(gaps))))
