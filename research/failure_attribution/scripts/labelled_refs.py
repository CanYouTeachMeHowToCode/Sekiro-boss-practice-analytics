"""References from the owner's labels (V4 M3, version 2): the hits of the failures the owner labelled in the
development recordings without the overlay, as references for move_match.py.

Usage: python -I labelled_refs.py

The dev-menu recordings give references at the animation level (move_match.Rec.references()). The recordings without
the overlay have no animation lines, but the owner labelled the move of each failure (reliability.py's answers,
version 2), so each of their hits is a reference too: the moment the HP bar dropped, labelled with the failure's move.
A hit counts when the owner confirmed its event and the failure's move is one product move: not `other` or `unsure`,
and not a Floating Passage opening marked two_slashes (Two-Hit Slash is right too, so the move is not one). Of a
failure with a posture break, only the hits up to the break count: the hits while Wolf is staggered can come from
another move (the owner's rule that a punish folds into the break). A death whose killing hit left no mark on the HP
bar has no hit to use.

Only recordings of set "development" are read, so a test recording is never a reference. move_match.py leaves out the
references of the recording it is predicting (leave one recording out).

Writes work/labelled_refs.csv: recording, key, time_s, type, move, truth_key.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import WORK, observation_dir, recordings  # noqa: E402
from reliability import Recording, key_time  # noqa: E402

FIELDS = ["recording", "key", "time_s", "type", "move", "truth_key"]
HIT_TYPES = ("damage", "posture_break")


def hits_of(r, t):
    """The hits of a truth failure to use as references: confirmed damage and posture-break events, up to the break."""
    events = sorted((e for e in r.detected if e["key"] in t["events"] and e["type"] in HIT_TYPES),
                    key=lambda e: float(e["time_s"]))
    out = []
    for e in events:
        out.append(e)
        if e["type"] == "posture_break":
            break
    return out


def main():
    rows = []
    for rec_id, rec in recordings().items():
        if rec.get("set") != "development" or observation_dir(rec):
            continue
        r = Recording(rec_id, rec)
        if r.problems:
            raise SystemExit(f"{rec_id}: the answers are not complete: {r.problems}")
        for t in r.truth:
            row = t["row"]
            if row["move"] in ("other", "unsure", "") or row.get("two_slashes"):
                continue
            for e in hits_of(r, t):
                rows.append({"recording": rec_id, "key": e["key"], "time_s": e["time_s"], "type": e["type"],
                             "move": row["move"], "truth_key": row["key"]})
    rows.sort(key=lambda x: (x["recording"], key_time(x["key"])))
    out = WORK / "labelled_refs.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
    per = {}
    for x in rows:
        per[x["move"]] = per.get(x["move"], 0) + 1
    print(f"{len(rows)} references from {len({x['recording'] for x in rows})} recordings -> {out}")
    print("  " + ", ".join(f"{m} {n}" for m, n in sorted(per.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
