"""Runs of consecutive overlay frames with the same animation ID (no counter-based splitting)."""
import csv, json, sys
from collections import Counter
from pathlib import Path
data = Path(sys.argv[1])
rows = list(csv.DictReader(open(data / "frames2.csv", encoding="utf-8")))
fps = json.load(open(data / "video.json"))["fps"]
runs = []
for r in rows:
    f = int(r["frame"])
    if r["line"] != "1":
        continue
    if runs and runs[-1]["anim"] == r["anim"] and runs[-1]["end"] == f - 1:
        run = runs[-1]
    else:
        run = {"anim": r["anim"], "start": f, "end": f, "char": Counter(), "min_margin": 9.0, "disagree": 0}
        runs.append(run)
    run["end"] = f
    run["char"][r["char"]] += 1
    run["min_margin"] = min(run["min_margin"], float(r["margin"]))
    run["disagree"] += r["free_agrees"] != "1"
out = []
for i, r in enumerate(runs):
    n = r["end"] - r["start"] + 1
    flags = []
    if n < 4: flags.append("short")
    if r["min_margin"] < 0.01: flags.append("low_margin")
    if r["disagree"]: flags.append("per_cell_disagrees")
    out.append({"run": i + 1, "anim": r["anim"], "char": r["char"].most_common(1)[0][0], "start_frame": r["start"],
                "end_frame": r["end"], "frames": n, "start_time": round(r["start"] / fps, 3),
                "end_time": round(r["end"] / fps, 3), "min_margin": round(r["min_margin"], 4), "flags": ";".join(flags)})
with open(data / "runs.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print("runs:", len(out), "| flagged:", Counter(f for o in out for f in o["flags"].split(";") if f))
print("runs per character:", Counter(o["char"] for o in out))
print("frames-per-run percentiles:", sorted(o["frames"] for o in out)[::max(1, len(out)//10)])
