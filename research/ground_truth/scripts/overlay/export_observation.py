"""Write the committed observation files from a work directory.

Usage: python -I export_observation.py <data_dir> <out_dir> <phase_bounds_json>
phase_bounds_json: frame ranges (end exclusive), e.g. '{"1": [0, 10788], "2": [10788, 16571], "3": [19494, 24720]}'.
Writes frames.csv (one row per video frame: character ID and the five 'Active Anime' lines as ID@time),
occurrences.csv (with the phase), and copies ids.csv, corrections.csv, char_corrections.csv and
restart_review.csv.
"""
import csv
import json
import shutil
import sys
from pathlib import Path

CHAR_LINE_MIN_NCC = 0.5           # below this the character line is not on screen (phase transition)
data, out = Path(sys.argv[1]), Path(sys.argv[2])
bounds = {k: tuple(v) for k, v in json.loads(sys.argv[3]).items()}
out.mkdir(parents=True, exist_ok=True)

occ_frames = list(csv.DictReader(open(data / "occ_frames.csv", encoding="utf-8")))
r3 = list(csv.DictReader(open(data / "frames3.csv", encoding="utf-8")))
char = [r["char"] if float(r["char_line_ncc"]) > CHAR_LINE_MIN_NCC else "" for r in r3]
for c in csv.DictReader(open(data / "char_corrections.csv", encoding="utf-8")):
    for f in range(int(c["frame_from"]), int(c["frame_to"]) + 1):
        assert char[f] == c["read"], (f, char[f])
        char[f] = c["corrected"]
with open(out / "frames.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["frame", "time_s", "character", "line1", "line2", "line3", "line4", "line5"])
    for r in occ_frames:
        f = int(r["frame"])
        w.writerow([f, r["time"], char[f]] + [r[f"line{k}"] for k in range(1, 6)])


def phase(f):
    return next((k for k, (a, b) in bounds.items() if a <= f < b), "")


occ = list(csv.DictReader(open(data / "occurrences.csv", encoding="utf-8")))
with open(out / "occurrences.csv", "w", newline="", encoding="utf-8") as fh:
    fields = ["anim", "phase", "character", "start_frame", "end_frame", "start_time", "end_time",
              "frames_shown", "lines", "on_line1", "t_first", "t_last", "starts_after_restart"]
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    for o in occ:
        f = int(o["start_frame"])
        o["t_first"], o["t_last"] = f"{float(o['t_first']):.2f}", f"{float(o['t_last']):.2f}"
        w.writerow({**{k: o[k] for k in fields if k in o}, "phase": phase(f), "character": char[f]})
for name in ("ids.csv", "corrections.csv", "char_corrections.csv", "restart_review.csv"):
    shutil.copy(data / name, out / name)
print("frames:", len(occ_frames), "occurrences:", len(occ))
print("character per phase:", {k: sorted({char[f] for f in range(a, b)} - {""}) for k, (a, b) in bounds.items()})
