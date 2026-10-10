"""Merge all 'Active Anime' lines into per-ID occurrences.

Usage: python -I occurrences.py <data_dir> <sheet_png> [W DROP] [--auto]
- frame f shows ID X if any of lines 1..5 reads X (lines 2..5 only while line 1 is visible and their prefix matches);
  manual corrections from corrections.csv are applied first.
- an occurrence of X is a maximal stretch of frames showing X, allowing gaps of at most GAP frames;
- it is split where X's animation time restarts (median of the next W reads at least 0.15 s below the previous W);
  once restart_review.csv exists, only the visually confirmed restarts are used.
Writes occ_frames.csv (frame, line1..line5 'ID@time') and occurrences.csv, and a sheet of restart points.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

GAP, W, DROP = 2, int(sys.argv[3]) if len(sys.argv) > 3 else 6, float(sys.argv[4]) if len(sys.argv) > 4 else 0.15
FPS = 59.995
data, sheet = Path(sys.argv[1]), sys.argv[2]
r1 = list(csv.DictReader(open(data / "frames4.csv", encoding="utf-8")))
N = len(r1)
shown = {1: [(r["anim"], float(r["anim_time"])) if r["line"] == "1" else None for r in r1]}
for k in (2, 3, 4, 5):
    rk = list(csv.DictReader(open(data / f"line{k}.csv", encoding="utf-8")))
    shown[k] = [(rk[i]["anim"], float(rk[i]["anim_time"])) if r1[i]["line"] == "1" and float(rk[i]["prefix_ncc"]) > 0.45 else None
                for i in range(N)]
# position-specific time reads (time_read2.py) replace the first-pass time reads when present
for k in shown:
    tp = data / f"time2_line{k}.npy"
    if tp.exists():
        t2 = np.load(tp)
        shown[k] = [(v[0], float(t2[f])) if v else None for f, v in enumerate(shown[k])]
for c in csv.DictReader(open(data / "corrections.csv", encoding="utf-8")):
    k, f = int(c["line"]), int(c["frame"])
    assert shown[k][f][0] == c["read"], (k, f, shown[k][f])
    shown[k][f] = (c["corrected"], shown[k][f][1])

with open(data / "occ_frames.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["frame", "time"] + [f"line{k}" for k in range(1, 6)])
    for f in range(N):
        w.writerow([f, f"{f / FPS:.3f}"] + [f"{shown[k][f][0][5:]}@{shown[k][f][1]:.2f}" if shown[k][f] else "" for k in range(1, 6)])

reviewed = None
if (data / "restart_review.csv").exists() and "--auto" not in sys.argv:
    reviewed, exact = defaultdict(list), set()
    for r in csv.DictReader(open(data / "restart_review.csv", encoding="utf-8")):
        if r["verdict"] == "restart":
            reviewed[r["anim"]].append(int(r["exact_frame"] or r["candidate_frame"]))
            if r["exact_frame"]:
                exact.add((r["anim"], int(r["exact_frame"])))
per_id = defaultdict(dict)                     # anim -> {frame: (line, time)}
for k in shown:
    for f, v in enumerate(shown[k]):
        if v:
            per_id[v[0]][f] = (k, v[1])
occ, restarts = [], []
for anim, fr in per_id.items():
    frames = sorted(fr)
    spans, s = [], frames[0]
    for a, b in zip(frames, frames[1:]):
        if b - a > GAP + 1:
            spans.append((s, a))
            s = b
    spans.append((s, frames[-1]))
    for s, e in spans:
        fs = [f for f in frames if s <= f <= e]
        t = np.array([fr[f][1] for f in fs])
        if reviewed is not None:
            # cut only at visually confirmed restarts, moved to the first frame whose time is clearly lower
            cuts = []
            for c in sorted(reviewed.get(anim, [])):
                if not s <= c <= e:
                    continue
                idx = fs.index(c) if c in fs else int(np.searchsorted(fs, c))
                best = idx
                for q in ([] if (anim, c) in exact else range(max(1, idx - W), min(len(t) - 1, idx + 8))):
                    after = np.median(t[q:q + 4])
                    if t[q] < t[q - 1] - 0.15 and after < t[q - 1] - 0.15:
                        best = q
                        break
                cuts.append(best)
                restarts.append((anim, fs[best], float(t[best - 1]), float(t[best])))
            cuts = sorted(set(cuts))
            k = len(t) + 1
        else:
            cuts, k = [], W
        while k <= len(t) - W:
            if np.median(t[k:k + W]) < np.median(t[k - W:k]) - DROP:
                win = range(max(1, k - W), min(len(t), k + W))
                kk = min(win, key=lambda q: t[q] - t[q - 1])
                cuts.append(kk)
                restarts.append((anim, fs[kk], float(np.median(t[k - W:k])), float(np.median(t[k:k + W]))))
                k = kk + 2 * W
                continue
            k += 1
        bounds = [0] + cuts + [len(fs)]
        for a, b in zip(bounds[:-1], bounds[1:]):
            part = fs[a:b]
            lines_used = sorted({fr[f][0] for f in part})
            occ.append({"anim": anim, "start_frame": part[0], "end_frame": part[-1],
                        "start_time": round(part[0] / FPS, 3), "end_time": round(part[-1] / FPS, 3),
                        "frames_shown": len(part), "lines": "".join(map(str, lines_used)),
                        "on_line1": int(1 in lines_used),
                        "t_first": fr[part[0]][1], "t_last": fr[part[-1]][1],
                        "starts_after_restart": int(a > 0)})
occ.sort(key=lambda o: (o["start_frame"], o["anim"]))
with open(data / "occurrences.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(occ[0]))
    w.writeheader()
    w.writerows(occ)
print("occurrences:", len(occ), " of which ever on line 1:", sum(o["on_line1"] for o in occ))
print("restart points:", len(restarts))
rows = []
arrs = {1: np.load(data / "line_min.npy", mmap_mode="r")}
for k in (2, 3, 4, 5):
    arrs[k] = np.load(data / f"line{k}_min.npy", mmap_mode="r")
for anim, f, mb, ma in sorted(restarts, key=lambda r: r[1]):
    crops = []
    for d in (-W, -1, 1, W):
        g = f + d
        k = per_id[anim].get(g, (None,))[0]
        crops.append(np.asarray(arrs[k][g, :, 180:400]) if k else np.zeros((30, 220), np.uint8))
    img = cv2.resize(np.hstack([np.hstack([c, np.zeros((30, 6), np.uint8)]) for c in crops]), None, fx=2, fy=2,
                     interpolation=cv2.INTER_NEAREST)
    lab = np.zeros((img.shape[0], 260), np.uint8)
    cv2.putText(lab, "%s f%d" % (anim[5:], f), (4, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 255, 1)
    rows.append(np.hstack([lab, img]))
    print(" ", anim, f, "%.2fs" % (f / FPS), "%.2f -> %.2f" % (mb, ma))
for p in range(0, len(rows), 30):
    cv2.imwrite(sheet.replace(".png", f"_{p // 30 + 1:02d}.png"), np.vstack(rows[p:p + 30]))
