"""Coverage table of one recording: one row per animation ID in the c7100 and c7110 TAE files.
Usage: python -I coverage.py <observation_dir> <c7100_tae_ids.txt> <c7110_tae_ids.txt>
Reads <observation_dir>/ids.csv (summarize.py) and writes <observation_dir>/coverage.csv with, for each TAE ID,
which TAE has it, how often it occurred in each phase, and whether it was seen as c7100 (phases 1-2) or as c7110
(phase 3).
"""
import csv
import sys
from pathlib import Path

obs, ids7100, ids7110 = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
tae = {c: {l.strip() for l in open(p) if l.strip()} for c, p in (("c7100", ids7100), ("c7110", ids7110))}
seen = {r["anim"]: r for r in csv.DictReader(open(obs / "ids.csv", encoding="utf-8"))}
rows = []
for a in sorted(tae["c7100"] | tae["c7110"]):
    s = seen.get(a, {})
    p = {k: int(s.get(f"occ_phase{k}", 0) or 0) for k in (1, 2, 3)}
    rows.append({"anim": a, "in_c7100_tae": int(a in tae["c7100"]), "in_c7110_tae": int(a in tae["c7110"]),
                 "occ_phase1": p[1], "occ_phase2": p[2], "occ_phase3": p[3],
                 "seen_as_c7100": int(p[1] + p[2] > 0), "seen_as_c7110": int(p[3] > 0)})
with open(obs / "coverage.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(len(rows), "TAE IDs;", sum(r["seen_as_c7100"] for r in rows), "seen as c7100;", sum(r["seen_as_c7110"] for r in rows), "seen as c7110")
