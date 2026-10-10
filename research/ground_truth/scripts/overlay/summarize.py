"""Per-ID summary of the verified occurrences against the TAE animation lists.

Usage: python -I summarize.py <data_dir> <phase_bounds_json>
phase_bounds_json: e.g. '{"1": [0, 10541], "2": [10541, 16571], "3": [19494, 24720]}' (frame ranges, end exclusive).
Writes ids.csv.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

data = Path(sys.argv[1])
bounds = {k: tuple(v) for k, v in json.loads(sys.argv[2]).items()}
occ = list(csv.DictReader(open(data / "occurrences.csv", encoding="utf-8")))
tae = {c: {l.strip() for l in open(data / f"{c}_tae_ids.txt") if l.strip()} for c in ("c7100", "c7110")}


def phase(f):
    return next((k for k, (a, b) in bounds.items() if a <= f < b), "?")


per = defaultdict(lambda: {"occ": defaultdict(int), "line1": 0, "lines": set(), "frames": 0, "first": None})
for o in occ:
    p = per[o["anim"]]
    p["occ"][phase(int(o["start_frame"]))] += 1
    p["line1"] += int(o["on_line1"])
    p["lines"] |= set(o["lines"])
    p["frames"] += int(o["frames_shown"])
    p["first"] = p["first"] if p["first"] is not None else float(o["start_time"])
rows = []
for a in sorted(per):
    p = per[a]
    rows.append({"anim": a, "in_c7100_tae": int(a in tae["c7100"]), "in_c7110_tae": int(a in tae["c7110"]),
                 **{f"occ_phase{k}": p["occ"].get(k, 0) for k in bounds}, "occ_total": sum(p["occ"].values()),
                 "occ_reaching_line1": p["line1"], "lines_seen": "".join(sorted(p["lines"])),
                 "frames_shown": p["frames"], "first_seen_s": p["first"]})
with open(data / "ids.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
obs = set(per)
print("occurrences:", len(occ), "distinct IDs:", len(obs))
for k in bounds:
    ids_k = {a for a in per if per[a]["occ"].get(k)}
    print(f"phase {k}: occurrences {sum(per[a]['occ'].get(k, 0) for a in per)}, distinct IDs {len(ids_k)}")
p12 = {a for a in per if per[a]["occ"].get("1") or per[a]["occ"].get("2")}
p3 = {a for a in per if per[a]["occ"].get("3")}
print("phase 1-2 IDs not in c7100 TAE:", sorted(p12 - tae["c7100"]))
print("phase 3 IDs not in c7110 TAE:", sorted(p3 - tae["c7110"]))
print("c7100 TAE IDs never seen in phases 1-2:", len(tae["c7100"] - p12), "of", len(tae["c7100"]))
print("c7110 TAE IDs never seen in phase 3:", len(tae["c7110"] - p3), "of", len(tae["c7110"]))
print("IDs seen only in phase 3:", sorted(p3 - p12))
print("IDs seen in phases 1-2 but not phase 3:", len(p12 - p3))
print("IDs never reaching line 1:", sorted(a for a in per if per[a]["line1"] == 0))
print("phase 1 only:", sorted(a[5:] for a in per if set(per[a]["occ"]) == {"1"}))
print("phase 2 only:", sorted(a[5:] for a in per if set(per[a]["occ"]) == {"2"}))
