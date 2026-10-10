"""Second pass: bootstrapped templates, whitelist-constrained ID decoding, segmented counter reading.

Usage: python -I overlay_extract2.py <video> <data_dir>
Reads data_dir/frames.csv (first pass) and data_dir/whitelist_c7100_c7110.txt; writes frames2.csv.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import (CELL_Y0, CELL_Y1, COUNTER_X0, ID_DIGITS, ID_PITCH, ID_X0, LINE_X0, LINE_X1,
                             LINE_Y0, LINE_Y1, text_mask)

video, data = sys.argv[1], Path(sys.argv[2])
first = list(csv.DictReader(open(data / "frames.csv", encoding="utf-8")))
whitelist = sorted(l.strip() for l in open(data / "whitelist_c7100_c7110.txt") if l.strip())
wl_digits = np.array([[int(c) for c in w[5:]] for w in whitelist])  # (W, 6)

# 1. decode once and keep the binary cells and counter strip of every frame
cap = cv2.VideoCapture(video)
cells, strips = [], []
while True:
    ok, f = cap.read()
    if not ok:
        break
    line = text_mask(f[LINE_Y0:LINE_Y1, LINE_X0:LINE_X1])
    cells.append(np.stack([line[CELL_Y0:CELL_Y1, ID_X0 + k * ID_PITCH: ID_X0 + (k + 1) * ID_PITCH] for k in range(ID_DIGITS)]).astype(np.uint8))
    strips.append(line[CELL_Y0:CELL_Y1, COUNTER_X0:].astype(np.uint8))
cells = np.stack(cells)          # (N, 6, H, 14)
strips = np.stack(strips)        # (N, H, W)
N = len(cells)
assert N == len(first), (N, len(first))

# 2. bootstrap templates from stable, whitelisted first-pass reads
wl_set = set(whitelist)
anim = [r["anim"] if r["line"] == "1" else "" for r in first]
stable = np.zeros(N, bool)
i = 0
while i < N:
    j = i
    while j + 1 < N and anim[j + 1] == anim[i]:
        j += 1
    if anim[i] in wl_set and j - i + 1 >= 10:
        stable[i + 2: j - 1] = True     # skip the edges of each run
    i = j + 1
samples = {d: [] for d in range(10)}
for n in np.where(stable)[0]:
    for k in range(ID_DIGITS):
        samples[int(anim[n][5 + k])].append(cells[n, k])
templates = np.stack([np.mean(samples[d], axis=0) for d in range(10)])  # (10, H, 14)
print("bootstrap samples per digit:", {d: len(s) for d, s in samples.items()})

# 3. whitelist-constrained decoding: per-cell distance to each digit, summed over the six cells
line_present = np.array([r["line"] == "1" for r in first])
cellf = cells.astype(np.float32)
dist = np.abs(cellf[:, :, None] - templates[None, None]).mean(axis=(3, 4))   # (N, 6, 10)
free_digits = dist.argmin(axis=2)                                             # unconstrained per-cell read
score = dist[:, np.arange(ID_DIGITS)[None, :], wl_digits].sum(axis=2)         # (N, W)
order = np.argsort(score, axis=1)
best, second = order[:, 0], order[:, 1]
best_score = score[np.arange(N), best]
margin = score[np.arange(N), second] - best_score
free_matches_best = (free_digits == wl_digits[best]).all(axis=1)


# 4. counter: split the strip into glyph column-runs and classify each run by centroid-aligned template
tmpl_cx = [float(np.average(np.arange(14), weights=templates[d].sum(axis=0))) for d in range(10)]


def read_counter(strip):
    cols = strip.sum(axis=0)
    runs, s = [], None
    for x in range(len(cols) + 1):
        on = x < len(cols) and cols[x] > 0
        if on and s is None:
            s = x
        if not on and s is not None:
            runs.append((s, x - 1))
            s = None
    # merge runs separated by a 1-px gap (thin strokes breaking up a glyph)
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= 2 and r[1] - merged[-1][0] <= 10:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(r)
    glyphs = []
    for x0, x1 in merged:
        sub = strip[:, x0:x1 + 1].astype(np.float32)
        height = int((sub.sum(axis=1) > 0).sum())
        width = x1 - x0 + 1
        if width <= 2 and height >= 14:
            glyphs.append(("|", x0, 0.0))      # '[' or ']' (thin full-height bar)
            continue
        cx = x0 + float(np.average(np.arange(width), weights=sub.sum(axis=0)))
        best_d, best_digit = 9.0, None
        for d in range(10):
            left = int(round(cx - tmpl_cx[d]))
            if left < 0 or left + 14 > strip.shape[1]:
                continue
            cand = strip[:, left:left + 14].astype(np.float32)
            dd = float(np.abs(cand - templates[d]).mean())
            if dd < best_d:
                best_d, best_digit = dd, str(d)
        glyphs.append((best_digit if best_d < 0.09 else "?", x0, best_d))
    # keep the part between the first and last bar: "[ cur / tot ]"
    bars = [i for i, g in enumerate(glyphs) if g[0] == "|"]
    if len(bars) < 2:
        return None, None, 1.0
    inner = [g for g in glyphs[bars[0] + 1: bars[-1]] if g[0] != "?"]
    if len(inner) < 2:
        return None, None, 1.0
    xs = [g[1] for g in inner]
    gaps = [(xs[i + 1] - xs[i], i) for i in range(len(xs) - 1)]
    gap, split = max(gaps)
    if gap < 20:
        return None, None, 1.0
    cur = "".join(g[0] for g in inner[: split + 1])
    tot = "".join(g[0] for g in inner[split + 1:])
    worst = max(g[2] for g in inner)
    return int(cur), int(tot), worst


with open(data / "frames2.csv", "w", newline="", encoding="utf-8") as out:
    w = csv.writer(out)
    w.writerow(["frame", "time", "line", "anim", "score", "margin", "free_agrees", "cur", "tot", "counter_worst", "char"])
    for n in range(N):
        r = first[n]
        if not line_present[n]:
            w.writerow([n, r["time"], 0, "", "", "", "", "", "", "", r["char"]])
            continue
        cur, tot, cw = read_counter(strips[n])
        w.writerow([n, r["time"], 1, whitelist[best[n]], f"{best_score[n]:.4f}", f"{margin[n]:.4f}",
                    int(free_matches_best[n]), "" if cur is None else cur, "" if tot is None else tot, f"{cw:.4f}", r["char"]])

lp = line_present
print("frames with line:", int(lp.sum()))
print("free per-cell read == whitelist best:", int((free_matches_best & lp).sum()), "/", int(lp.sum()))
print("margin percentiles 0/0.1/1/5/50:", np.percentile(margin[lp], [0, 0.1, 1, 5, 50]).round(4))
rows2 = list(csv.DictReader(open(data / "frames2.csv", encoding="utf-8")))
print("counter read:", sum(1 for r in rows2 if r["cur"] != ""), "/", int(lp.sum()))
np.save(data / "templates_bootstrap.npy", templates)
