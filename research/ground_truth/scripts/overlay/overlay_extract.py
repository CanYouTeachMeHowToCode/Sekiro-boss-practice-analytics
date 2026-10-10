"""Read Sekiro-Debug-Patch overlay values from every frame of a recording.

Usage:
    python -I overlay_extract.py templates <video> <out_dir>
    python -I overlay_extract.py extract <video> <out_dir>

Layout (2560x1440 recording, dev menu at its default top-left position):
- animation line: full-res rows 150..180, cols 125..525, text "◇a000_DDDDDD(t.tt)[ cur/ tot]"
- the six ID digits sit in fixed 14-px cells starting at line-crop x=95
- character line: full-res rows 86..106, compared against reference crops
Text is pure white, so a pixel is "text" when all channels exceed 225.
"""

import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

LINE_Y0, LINE_Y1, LINE_X0, LINE_X1 = 150, 180, 125, 525
CELL_Y0, CELL_Y1 = 6, 25          # rows inside the line crop
ID_X0, ID_PITCH, ID_DIGITS = 95, 14, 6
PREFIX_X0, PREFIX_X1 = 28, 92      # "a000_" inside the line crop
CHAR_Y0, CHAR_Y1, CHAR_X0, CHAR_X1 = 86, 106, 125, 400
COUNTER_X0 = 262

# Frames whose overlay was read by eye (time in seconds, animation ID digits, character ID).
LABELED = [
    (2, "003014", "c7100_0000"), (30, "008400", "c7100_0000"), (90, "405003", "c7100_0000"),
    (150, "008010", "c7100_0000"), (210, "003092", "c7100_0000"), (260, "003067", "c7100_0000"),
    (340, "008500", "c7110_0001"), (370, "003019", "c7110_0001"), (400, "008210", "c7110_0001"),
]


def text_mask(img):
    return (img.min(axis=2) > 225).astype(np.float32)


def frame_at(cap, t):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, f = cap.read()
    assert ok, t
    return f


def id_cells(line_mask):
    return [line_mask[CELL_Y0:CELL_Y1, ID_X0 + k * ID_PITCH: ID_X0 + (k + 1) * ID_PITCH] for k in range(ID_DIGITS)]


def build_templates(video, out_dir):
    cap = cv2.VideoCapture(video)
    samples = {str(d): [] for d in range(10)}
    prefixes, chars = [], {}
    for t, digits, char in LABELED:
        f = frame_at(cap, t)
        line = text_mask(f[LINE_Y0:LINE_Y1, LINE_X0:LINE_X1])
        for k, cell in enumerate(id_cells(line)):
            samples[digits[k]].append(cell)
        prefixes.append(line[CELL_Y0:CELL_Y1, PREFIX_X0:PREFIX_X1])
        chars.setdefault(char, []).append(text_mask(f[CHAR_Y0:CHAR_Y1, CHAR_X0:CHAR_X1]))
    missing = [d for d, s in samples.items() if not s]
    assert not missing, f"no samples for digits {missing}"
    digit_t = {d: np.mean(s, axis=0) for d, s in samples.items()}
    np.savez(Path(out_dir) / "templates.npz",
             **{f"digit_{d}": v for d, v in digit_t.items()},
             prefix=np.mean(prefixes, axis=0),
             **{f"char_{c}": np.mean(v, axis=0) for c, v in chars.items()})
    # Self-check: how different are the digit templates from each other?
    keys = sorted(digit_t)
    worst = min((np.abs(digit_t[a] - digit_t[b]).mean(), a, b) for i, a in enumerate(keys) for b in keys[i + 1:])
    print("samples per digit:", {d: len(s) for d, s in samples.items()})
    print("closest pair of digit templates (mean abs diff, a, b):", worst)


def load_templates(out_dir):
    z = np.load(Path(out_dir) / "templates.npz")
    digits = {k[6:]: z[k] for k in z.files if k.startswith("digit_")}
    chars = {k[5:]: z[k] for k in z.files if k.startswith("char_")}
    glyphs = {}
    for d, t in digits.items():
        ys, xs = np.where(t > 0.5)
        glyphs[d] = t[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1].astype(np.float32)
    return digits, z["prefix"], chars, glyphs


def classify(cell, templates):
    dists = sorted((float(np.abs(cell - t).mean()), d) for d, t in templates.items())
    return dists[0][1], dists[0][0], dists[1][0] - dists[0][0]


def read_counter(line, glyphs):
    region = line[CELL_Y0 - 2:CELL_Y1 + 2, COUNTER_X0:]
    hits = []
    for d, g in glyphs.items():
        if g.shape[0] > region.shape[0] or g.shape[1] > region.shape[1]:
            continue
        res = cv2.matchTemplate(region, g, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res > 0.80)
        for y, x in zip(ys, xs):
            hits.append((float(res[y, x]), int(x), d))
    hits.sort(reverse=True)
    kept = []
    for score, x, d in hits:
        if all(abs(x - kx) >= 9 for _, kx, _ in kept):
            kept.append((score, x, d))
    kept.sort(key=lambda h: h[1])
    if len(kept) < 2:
        return None, None
    xs = [h[1] for h in kept]
    gaps = [(xs[i + 1] - xs[i], i) for i in range(len(xs) - 1)]
    gap, split = max(gaps)
    if gap < 20:
        return None, None
    cur = "".join(h[2] for h in kept[: split + 1])
    tot = "".join(h[2] for h in kept[split + 1:])
    return int(cur), int(tot)


def extract(video, out_dir):
    digits, prefix, chars, glyphs = load_templates(out_dir)
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    out = open(Path(out_dir) / "frames.csv", "w", newline="", encoding="utf-8")
    w = csv.writer(out)
    w.writerow(["frame", "time", "line", "prefix_dist", "anim", "worst_dist", "worst_margin", "cur", "tot", "char", "char_dist"])
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        line = text_mask(f[LINE_Y0:LINE_Y1, LINE_X0:LINE_X1])
        pdist = float(np.abs(line[CELL_Y0:CELL_Y1, PREFIX_X0:PREFIX_X1] - prefix).mean())
        char_crop = text_mask(f[CHAR_Y0:CHAR_Y1, CHAR_X0:CHAR_X1])
        cdists = sorted((float(np.abs(char_crop - t).mean()), c) for c, t in chars.items())
        row = [i, f"{i / fps:.3f}", 0, f"{pdist:.4f}", "", "", "", "", "", cdists[0][1], f"{cdists[0][0]:.4f}"]
        if pdist < 0.08:
            reads = [classify(c, digits) for c in id_cells(line)]
            anim = "a000_" + "".join(r[0] for r in reads)
            cur, tot = read_counter(line, glyphs)
            row[2:9] = [1, f"{pdist:.4f}", anim, f"{max(r[1] for r in reads):.4f}",
                        f"{min(r[2] for r in reads):.4f}", "" if cur is None else cur, "" if tot is None else tot]
        w.writerow(row)
        i += 1
        if i % 3000 == 0:
            print("frames", i, flush=True)
    out.close()
    json.dump({"video": video, "fps": fps, "frames": i}, open(Path(out_dir) / "video.json", "w"))
    print("done", i, "frames at", fps)


if __name__ == "__main__":
    {"templates": build_templates, "extract": extract}[sys.argv[1]](sys.argv[2], sys.argv[3])
