"""Group lines 2..4 into runs (only while line 1 is visible) and list IDs never seen on line 1.

Usage: python -I lines_union.py <data_dir>
Writes runs_line{2,3,4}.csv.
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

data = Path(sys.argv[1])
r1 = list(csv.DictReader(open(data / "frames4.csv", encoding="utf-8")))
line1_ids = Counter(r["anim"] for r in r1 if r["line"] == "1")
fps = 59.995
only_lower = defaultdict(list)
for k in (2, 3, 4, 5):
    rk = list(csv.DictReader(open(data / f"line{k}.csv", encoding="utf-8")))
    pres = [r1[i]["line"] == "1" and float(rk[i]["prefix_ncc"]) > 0.45 for i in range(len(rk))]
    runs, i = [], 0
    while i < len(rk):
        if not pres[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(rk) and pres[j + 1] and rk[j + 1]["anim"] == rk[i]["anim"]:
            j += 1
        seg = rk[i:j + 1]
        runs.append({"line": k, "anim": rk[i]["anim"], "start_frame": i, "end_frame": j, "frames": j - i + 1,
                     "start_time": round(i / fps, 3), "min_margin": min(float(x["margin"]) for x in seg),
                     "free_disagree": sum(x["free_agrees"] != "1" for x in seg),
                     "line1_anim_at_start": r1[i]["anim"]})
        i = j + 1
    with open(data / f"runs_line{k}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(runs[0]))
        w.writeheader()
        w.writerows(runs)
    print(f"line {k}: {len(runs)} runs, short(<4 frames) {sum(r['frames'] < 4 for r in runs)}, "
          f"with free-read disagreement {sum(r['free_disagree'] > 0 for r in runs)}")
    for r in runs:
        if r["anim"] not in line1_ids:
            only_lower[r["anim"]].append((k, r["start_frame"], r["frames"], r["start_time"], r["free_disagree"]))
print("IDs on lines 2-4 never read on line 1:", len(only_lower))
for a, occ in sorted(only_lower.items()):
    print(" ", a, "runs:", len(occ), "frames total:", sum(o[2] for o in occ), "first:", occ[:4])
