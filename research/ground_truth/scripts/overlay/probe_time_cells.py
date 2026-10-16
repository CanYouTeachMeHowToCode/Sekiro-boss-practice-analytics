"""Find the x positions of the "(t.tt)" digit cells by sliding the ID digit templates.

Usage: python -I probe_time_cells.py <data_dir>
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import CELL_Y0, CELL_Y1, ID_PITCH, ID_X0

data = Path(sys.argv[1])
lines = np.load(data / "line_min.npy", mmap_mode="r")
rows = list(csv.DictReader(open(data / "frames2.csv", encoding="utf-8")))
present = np.array([r["line"] == "1" for r in rows])
anim = [r["anim"] for r in rows]


def z(a):
    a = a.astype(np.float32)
    a = a - a.mean(axis=(-2, -1), keepdims=True)
    return a / np.maximum(a.std(axis=(-2, -1), keepdims=True), 1e-3)


# grayscale ID templates from frames whose read is in the middle of a long run
idx = [n for n in range(5, len(rows) - 5) if present[n] and all(anim[n + d] == anim[n] for d in range(-5, 6))]
idx = idx[::3]
samples = {d: [] for d in range(10)}
for n in idx:
    for k in range(6):
        samples[int(anim[n][5 + k])].append(lines[n, CELL_Y0:CELL_Y1, ID_X0 + k * ID_PITCH: ID_X0 + (k + 1) * ID_PITCH])
T = z(np.stack([z(np.stack(samples[d])).mean(axis=0) for d in range(10)]))
print("template samples:", {d: len(s) for d, s in samples.items()})

probe = [n for n in np.where(present)[0][::25]]
for name, guess in [("units", 199), ("tenths", 221), ("hundredths", 235)]:
    res = []
    for x in range(guess - 4, guess + 5):
        cells = z(np.stack([lines[n, CELL_Y0:CELL_Y1, x:x + ID_PITCH] for n in probe]))
        ncc = np.einsum("nhw,dhw->nd", cells, T) / cells[0].size
        best = np.sort(ncc, axis=1)
        res.append((float(best[:, -1].mean()), float((best[:, -1] - best[:, -2]).mean()), x))
    for r in sorted(res, reverse=True)[:3]:
        print(name, "x=%d mean best ncc %.3f mean margin %.3f" % (r[2], r[0], r[1]))
