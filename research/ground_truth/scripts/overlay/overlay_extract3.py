"""Third pass: grayscale normalized-correlation decoding of the overlay (ID, animation time, character).

Usage: python -I overlay_extract3.py <data_dir>
Reads line_min.npy / char_min.npy (cache_crops.py), frames2.csv (second pass, for bootstrap labels and comparison),
whitelist_c7100_c7110.txt and video.json. Writes frames3.csv.

Unlike the binary passes, every cell is compared as a zero-mean, unit-variance grayscale patch, so dimmer text
(phase 3) and light background text behind the overlay do not break strokes apart.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from overlay_extract import CELL_Y0, CELL_Y1, ID_DIGITS, ID_PITCH, ID_X0, LABELED, PREFIX_X0, PREFIX_X1

TIME_X = (199, 221, 235)          # "(u.th)" digit cells inside the line crop
data = Path(sys.argv[1])
lines = np.load(data / "line_min.npy", mmap_mode="r")
chars = np.load(data / "char_min.npy", mmap_mode="r")
fps = json.load(open(data / "video.json"))["fps"]
rows2 = list(csv.DictReader(open(data / "frames2.csv", encoding="utf-8")))
whitelist = sorted(l.strip() for l in open(data / "whitelist_c7100_c7110.txt") if l.strip())
wl_digits = np.array([[int(c) for c in w[5:]] for w in whitelist])
N = len(lines)


def z(a):
    a = a.astype(np.float32)
    a = a - a.mean(axis=(-2, -1), keepdims=True)
    return a / np.maximum(a.std(axis=(-2, -1), keepdims=True), 1e-3)


def ncc(cells, templates):                    # cells (..., h, w), templates (d, h, w) -> (..., d)
    return np.einsum("...hw,dhw->...d", z(cells), templates) / (cells.shape[-1] * cells.shape[-2])


# 1. grayscale digit templates from the middle of long second-pass runs
present2 = np.array([r["line"] == "1" for r in rows2])
anim2 = [r["anim"] for r in rows2]
stable = [n for n in range(5, N - 5) if present2[n] and all(anim2[n + d] == anim2[n] for d in range(-5, 6))]
samples = {d: [] for d in range(10)}
for n in stable[::2]:
    for k in range(ID_DIGITS):
        samples[int(anim2[n][5 + k])].append(lines[n, CELL_Y0:CELL_Y1, ID_X0 + k * ID_PITCH: ID_X0 + (k + 1) * ID_PITCH])
T = z(np.stack([z(np.stack(samples[d])).mean(axis=0) for d in range(10)]))
prefix_T = z(z(np.stack([lines[n, CELL_Y0:CELL_Y1, PREFIX_X0:PREFIX_X1] for n in stable[::20]])).mean(axis=0))[None]

# 2. character templates from the hand-labeled frames (+-10 frames each) and the pixels where they differ
char_samples = {}
for t, _, c in LABELED:
    f0 = int(round(t * fps))
    char_samples.setdefault(c, []).extend(chars[f0 - 10: f0 + 11])
char_names = sorted(char_samples)
char_mean = {c: z(np.stack(char_samples[c])).mean(axis=0) for c in char_names}
diff = np.abs(char_mean[char_names[0]] - char_mean[char_names[1]])
char_mask = diff > np.percentile(diff, 90)                       # the most discriminative 10% of pixels
char_T = np.stack([z(char_mean[c][None])[0] for c in char_names])
char_full = np.stack([z(char_mean[c][None])[0] for c in char_names])
print("char discriminative columns:", sorted(set(np.where(char_mask)[1].tolist()))[:5], "...", int(char_mask.sum()), "pixels")

out_rows = []
B = 2000
for s in range(0, N, B):
    L = np.asarray(lines[s:s + B]).astype(np.float32)
    C = np.asarray(chars[s:s + B]).astype(np.float32)
    n = len(L)
    pre = ncc(L[:, CELL_Y0:CELL_Y1, PREFIX_X0:PREFIX_X1], prefix_T)[:, 0]
    cells = np.stack([L[:, CELL_Y0:CELL_Y1, ID_X0 + k * ID_PITCH: ID_X0 + (k + 1) * ID_PITCH] for k in range(ID_DIGITS)], axis=1)
    c = ncc(cells, T)                                             # (n, 6, 10)
    free = c.argmax(axis=2)
    cost = (1 - c)[:, np.arange(ID_DIGITS)[None, :], wl_digits].sum(axis=2)   # (n, W)
    order = np.argsort(cost, axis=1)
    best, second = order[:, 0], order[:, 1]
    bcost = cost[np.arange(n), best]
    margin = cost[np.arange(n), second] - bcost
    worst_cell = c[np.arange(n)[:, None], np.arange(ID_DIGITS)[None, :], wl_digits[best]].min(axis=1)
    tc = np.stack([L[:, CELL_Y0:CELL_Y1, x:x + ID_PITCH] for x in TIME_X], axis=1)
    tn = ncc(tc, T)                                               # (n, 3, 10)
    tdig = tn.argmax(axis=2)
    ts = np.sort(tn, axis=2)
    tmargin = (ts[:, :, -1] - ts[:, :, -2]).min(axis=1)
    tbest = ts[:, :, -1].min(axis=1)
    # character: correlation over the discriminative pixels only
    Cm = C[:, char_mask]
    Cm = (Cm - Cm.mean(axis=1, keepdims=True)) / np.maximum(Cm.std(axis=1, keepdims=True), 1e-3)
    Tm = char_T[:, char_mask]
    Tm = (Tm - Tm.mean(axis=1, keepdims=True)) / Tm.std(axis=1, keepdims=True)
    cs = Cm @ Tm.T / Tm.shape[1]                                  # (n, 2)
    cfull = ncc(C, char_full)                                     # whole-line correlation, to see if the line is there
    for i in range(n):
        f = s + i
        out_rows.append([f, f"{f / fps:.3f}", f"{pre[i]:.3f}", whitelist[best[i]], f"{bcost[i]:.3f}", f"{margin[i]:.3f}",
                         f"{worst_cell[i]:.3f}", int((free[i] == wl_digits[best[i]]).all()),
                         f"{tdig[i, 0]}.{tdig[i, 1]}{tdig[i, 2]}", f"{tbest[i]:.3f}", f"{tmargin[i]:.3f}",
                         char_names[int(cs[i].argmax())], f"{cs[i].max():.3f}", f"{abs(cs[i, 0] - cs[i, 1]):.3f}",
                         f"{cfull[i].max():.3f}"])
    print("frames", s + n, flush=True)

with open(data / "frames3.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["frame", "time", "prefix_ncc", "anim", "cost", "margin", "worst_cell_ncc", "free_agrees",
                "anim_time", "time_worst_ncc", "time_margin", "char", "char_ncc", "char_margin", "char_line_ncc"])
    w.writerows(out_rows)
