"""Recognise the move behind a failure from the boss crops before the hit: references, evaluation and predictions.

Usage: python -I move_match.py eval [--model small14] [--part cls|patch|both] [--window 1.5] [--after 1.0]
                                   [--detrend 0.5] [--refs all|other]
       python -I move_match.py predict <recording id | all> [the same options] [--labelled 1|0] [--gaps 1|0]

How a failure's move is recognised (scores, merging, how sure) is in the analysis package,
analysis/sekiro_analysis/moves.py, which the recording worker runs with the same references. Here:

References: every hit of a boss animation in the dev-menu recordings, at the moment its TAE attack window opens
(projectiles: the moment the shot is fired), labelled from the overlay with the same mapping as failure_answers.py:
animation, hit number, catalog entries, product move. The overlay's animation lines are read only from the V3.1
tables, never from the crops (which went through mask_overlay()). Version 2 (V4 M3, 2026-11-12) adds:
- labels: a reference hit by an animation the owner's action -> move table counts apart takes that move
  (failure_answers.moves_of_hit()): a plain arrow is Arrow Shot, a Mikiri thrust inside another move Perilous Thrust;
- references from the owner's labels (--labelled 1, labelled_refs.py): the hits of the failures the owner labelled
  in the development recordings without the overlay, at the moment the HP bar dropped. Of the recording being
  predicted, none;
- merge windows per move (--gaps 1, moves.merge_gaps()).

eval: over the owner-checked answers (failure_moves.csv), with the owner's rules on moves that look the same: Floating
Passage's opening two slashes without their follow-up may also be answered Two-Hit Slash, and Counter Slash and Deflect
Counter Slash count for each other (accepted()). --refs other compares each failure only with the other
recordings (leave one recording out); --refs all also uses its own recording, leaving out EXCLUDE seconds around the
failure. Prints the top-1 and top-3 accuracy of the product move and of the animation; writes each failure's ranking to
work/move_match_eval.csv.

predict: the failure report proposal for a recording, from its HUD events (hud_pipeline.py) and boss features, with
every dev-menu recording but itself as references. Writes work/<recording id>/failure_predictions.csv: the columns of
failure_answers.csv, the top move as the answer, the top three with their scores as `candidates`, `confidence` and
`certain`. The review page shows it for a recording without the overlay, so the owner labels the moves with the
candidates at hand.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (GT, TWO_SLASHES, WORK, accepted, annotation_dir, observation_dir,  # noqa: E402,F401
                    recordings, work_dir)
from failure_answers import MOVES, WINDOWS, Overlay, moves_of_hit, read  # noqa: E402
from sekiro_analysis import moves as mm  # noqa: E402
from sekiro_analysis.moves import (BREAK_WITH, LAG_ATTACK, LAG_BULLET, LAG_DROP, MERGE_GAP, PUNISH_WINDOW,  # noqa: E402,F401
                                   RATE, SAME_MOTION, SEVERITY, SURE_MARGIN, UNSEEN_SPAN, UNSEEN_STEP, detrend,
                                   margin, merge_gaps, phase_at, similarity)

EXCLUDE = 5.0
ZH = {m["slug"]: m["zh"] for m in MOVES}


def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


class Rec(mm.Rec):
    """A registered recording (its work folder), with the dev-menu references it holds."""

    def __init__(self, rec_id, rec, model, part, trend=0.0):
        super().__init__(work_dir(rec_id), model, part, trend)
        self.id, self.rec = rec_id, rec

    def references(self):
        ov = Overlay(self.id, GT / "observations" / self.rec.get("ruleset", "vanilla") / "genichiro" / self.id)
        refs = []
        for anim, occs in ov.occ.items():
            for s, e, start in occs:
                wins = [w for w in WINDOWS.get((ov.chars[s], anim), ()) if w[0] in ("attack", "bullet")]
                if not wins:
                    continue
                entries, chain, prev = ov.chain_of(anim, start)
                seen = set()
                for kind, hit, ws, _ in wins:
                    if (kind, round(ws, 2)) in seen:
                        continue
                    seen.add((kind, round(ws, 2)))
                    k = next((k for k in range(s, e + 1) if dict(ov.lines(k)).get(anim, -1.0) >= ws), None)
                    if k is None:
                        continue
                    t = float(ov.frames[k]["time_s"])
                    phase = phase_at(t, self.blows, self.ends)
                    moves, _ = moves_of_hit(ov.chars[s], anim, entries, phase, prev)
                    refs.append({"rec": self, "anim": anim, "hit": hit, "kind": kind, "t": t, "phase": phase,
                                 "moves": [m["slug"] for m in moves], "play": (self.id, chain)})
        return refs


def labelled_references(recs, st, skip):
    """The owner-labelled hits of the development recordings without the overlay (labelled_refs.py), but those of
    `skip`: each is the moment the HP bar dropped, labelled with the failure's move."""
    path = WORK / "labelled_refs.csv"
    by_rec = {}
    for x in (read(path) if path.exists() and st["labelled"] else []):
        if x["recording"] != skip:
            by_rec.setdefault(x["recording"], []).append(x)
    refs = []
    for j, xs in by_rec.items():
        r = Rec(j, recs[j], st["model"], st["part"], st["trend"])
        for x in xs:
            t = float(x["time_s"])
            refs.append({"rec": r, "anim": None, "hit": None, "kind": "drop", "t": t,
                         "phase": phase_at(t, r.blows, r.ends), "moves": [x["move"]]})
    return refs


def rank(q, t_hit, phase, refs, window, after):
    return mm.rank(q, t_hit, phase, refs, window, after, MOVES)


def lead_time(row):
    """When the hit the failure is attributed to happened: the posture break, else the first hit."""
    items = [h.split(":")[0].split() for h in row["hits"].split(" ｜ ") if h]
    times = {role: float(t.rstrip("s")) for role, t in reversed(items)}
    return times.get("打崩", float(items[0][1].rstrip("s")))


def settings():
    return {"model": opt("--model", "small14"), "part": opt("--part", "cls"), "window": float(opt("--window", "1.5")),
            "after": float(opt("--after", "1.0")), "trend": float(opt("--detrend", "0.5")),
            "labelled": opt("--labelled", "1") == "1", "gaps": opt("--gaps", "1") == "1"}


def evaluate():
    import csv
    st = settings()
    model, part, window, after, trend = st["model"], st["part"], st["window"], st["after"], st["trend"]
    which = opt("--refs", "all")
    recs = {i: Rec(i, r, model, part, trend) for i, r in recordings().items() if observation_dir(r)}
    refs = {i: r.references() for i, r in recs.items()}
    results = []
    for rec_id, q in recs.items():
        answers = {r["key"]: r for r in read(work_dir(rec_id) / "failure_answers.csv")}
        reviewed = annotation_dir(q.rec) / "failure_moves.csv"
        for rev in (read(reviewed) if reviewed.exists() else []):      # a recording the owner has not reviewed yet
            a = answers.get(rev["key"])
            if a is None or rev["verdict"] not in ("correct", "wrong"):
                continue
            truth = rev["correct_move"] if rev["verdict"] == "wrong" else a["move"]
            truth_anim = int(a["anims"].split()[0]) if rev["verdict"] == "correct" and a["anims"] else None
            t_hit = lead_time(a)
            pool = [ref for j, rs in refs.items() for ref in rs
                    if j != rec_id or (which == "all" and abs(ref["t"] - t_hit) > EXCLUDE)]
            moves, anims, scores = rank(q, t_hit, int(a["phase"]), pool, window, after)
            ok = accepted(truth, a["chain"])
            results.append({"rec": rec_id, "key": a["key"], "phase": a["phase"], "truth": truth,
                            "move_rank": min((moves.index(m) + 1 for m in ok if m in moves), default=99),
                            "truth_anim": truth_anim,
                            "anim_rank": anims.index(truth_anim) + 1 if truth_anim in anims else 99,
                            "top3": " / ".join(f"{ZH.get(m, m)} {scores[m]:.3f}" for m in moves[:3]),
                            "top_anims": " ".join(map(str, anims[:3]))})
    out = WORK / "move_match_eval.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(results[0]), lineterminator="\r\n")
        w.writeheader()
        w.writerows(results)
    n = len(results)
    acc = lambda k, col: sum(r[col] <= k for r in results) / n  # noqa: E731
    print(f"model {model}, part {part}, window {window}s + {after}s, detrend {trend}s, refs {which}, {n} failures, "
          f"{sum(len(r) for r in refs.values())} references")
    print(f"  move: top-1 {acc(1, 'move_rank'):.0%}  top-3 {acc(3, 'move_rank'):.0%}   "
          f"animation: top-1 {acc(1, 'anim_rank'):.0%}  top-3 {acc(3, 'anim_rank'):.0%}   -> {out}")


def references(recs, st, skip=None):
    """Every reference a prediction uses but those of `skip`, and the merge windows (from the dev-menu ones only)."""
    refs = [ref for j, r in recs.items() if observation_dir(r) and j != skip
            for ref in Rec(j, r, st["model"], st["part"], st["trend"]).references()]
    gaps = merge_gaps(refs)
    return refs + labelled_references(recs, st, skip), gaps


def predict(rec_id):
    st, recs = settings(), recordings()
    q = Rec(rec_id, recs[rec_id], st["model"], st["part"], st["trend"])
    refs, gaps = references(recs, st, rec_id)
    events = read(work_dir(rec_id) / "events.csv")
    rows = mm.predict_rows(q, events, refs, gaps, MOVES, st)
    out = work_dir(rec_id) / "failure_predictions.csv"
    mm.write_rows(rows, out)
    print(f"{rec_id}: {len(rows)} failures from {sum(1 for e in events if 'scores' in e)} hits, "
          f"{len(refs)} references -> {out}")


if __name__ == "__main__":
    if sys.argv[1] == "eval":
        evaluate()
    elif sys.argv[1] == "predict":
        for rid, r in recordings().items():
            if sys.argv[2] in ("all", rid):
                predict(rid)
