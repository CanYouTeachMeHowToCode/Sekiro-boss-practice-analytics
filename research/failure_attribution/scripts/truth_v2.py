"""The version-2 answers of the development recordings (V4 M3): failure_truth_v2.csv next to failure_truth.csv.

Usage: python -I truth_v2.py

Version 2 classifies a failure by the action that hit the player (the action -> move table the owner approved on
2026-11-11, research/ground_truth/semantic/genichiro_v2_actions.md). The version-1 answers stay as they are
(failure_truth.csv); this writes the version-2 ones beside them, in the same columns, for every development recording:
- a recording with the dev-menu overlay: failure_answers.csv, which version 2 of failure_answers.py derives from the
  overlay, keeping the owner's marks of the version-1 answers (two_slashes, merge_prev, note) on the failures whose
  events did not change. Where version 2 splits a version-1 failure (a plain arrow and the slash after it are two moves
  now), the note says so;
- a recording without it: the owner's version-1 answers, with the move of each failure the owner rechecked under
  version 2 (failure_v2_recheck.csv, the review page's 版本 2 复核 view) replaced by the rechecked one.
"""
import csv
import io
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import annotation_dir, observation_dir, recordings, work_dir  # noqa: E402

FIELDS = ["key", "time_s", "events", "move", "two_slashes", "merge_prev", "source", "note", "updated"]


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8"))) if path.exists() else []


def write(path, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8", newline="")
    os.replace(tmp, path)


def from_overlay(rec_id, v1):
    now = datetime.now().isoformat(timespec="seconds")
    old = {r["events"]: r for r in v1}
    by_event = {k: r for r in v1 for k in r["events"].split()}
    rows, changed = [], []
    for a in read(work_dir(rec_id) / "failure_answers.csv"):
        same = old.get(a["events"])
        if same is not None:
            row = dict(same, move=a["move"])
            if a["move"] != same["move"]:
                row["source"], row["updated"] = "version 2 of the overlay answers", now
                changed.append(f"{a['key']} {same['move']} -> {a['move']}")
        else:
            parent = next((by_event[k] for k in a["events"].split() if k in by_event), None)
            note = f"版本 2 从版本 1 的 {parent['key']}（{parent['move']}）拆出来" if parent else "版本 2 新出现"
            row = {"key": a["key"], "time_s": a["time_s"], "events": a["events"], "move": a["move"], "two_slashes": "",
                   "merge_prev": "", "source": "version 2 of the overlay answers", "note": note, "updated": now}
            changed.append(f"{a['key']} {note} -> {a['move']}")
        rows.append(row)
    covered = {k for r in rows for k in r["events"].split()}
    lost = [r["key"] for r in v1 if not set(r["events"].split()) & covered]
    if lost:
        raise SystemExit(f"{rec_id}: version-1 failures with no version-2 answer: {lost}")
    return rows, changed


def from_recheck(rec):
    v1 = read(annotation_dir(rec) / "failure_truth.csv")
    recheck = {r["key"]: r for r in read(annotation_dir(rec) / "failure_v2_recheck.csv")}
    rows, changed = [], []
    for t in v1:
        row = dict(t)
        r = recheck.pop(t["key"], None)
        if r is not None and r["v2_move"]:
            row["move"] = r["v2_move"]
            row["source"] = f"{t['source']}; version 2 recheck"
            row["note"] = " ".join(x for x in (t["note"], r["note"]) if x)
            row["updated"] = r["updated"]
            if r["v2_move"] != t["move"]:
                changed.append(f"{t['key']} {t['move']} -> {r['v2_move']}")
        rows.append(row)
    if recheck:
        raise SystemExit(f"{rec['id']}: rechecks with no version-1 failure: {sorted(recheck)}")
    return rows, changed


def main():
    for rec_id, rec in recordings().items():
        if rec.get("set") != "development":
            continue
        rec = dict(rec, id=rec_id)
        v1 = read(annotation_dir(rec) / "failure_truth.csv")
        if not v1:
            print(f"{rec_id}: no version-1 answers, skipped")
            continue
        rows, changed = from_overlay(rec_id, v1) if observation_dir(rec) else from_recheck(rec)
        write(annotation_dir(rec) / "failure_truth_v2.csv", rows)
        print(f"{rec_id}: {len(v1)} -> {len(rows)} failures, {len(changed)} changed")
        for c in changed:
            print(f"    {c}")


if __name__ == "__main__":
    main()
