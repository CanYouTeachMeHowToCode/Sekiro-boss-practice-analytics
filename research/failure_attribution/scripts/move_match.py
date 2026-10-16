"""Recognise the move behind a failure from the boss crops before the hit (M1 step 4, first version).

Usage: python -I move_match.py eval [--model small14] [--part cls|patch|both] [--window 1.5] [--after 1.0]
                                   [--detrend 0.5] [--refs all|other]

References: every hit of a boss animation in the dev-menu recordings, at the moment its TAE attack window opens
(projectiles: the moment the shot is fired), labelled from the overlay with the same mapping as failure_answers.py:
animation, hit number, catalog entries, product move. A failure is compared with the references of the other
recordings: the boss crops from WINDOW seconds before the HP drop to AFTER seconds after it, against the crops around
each reference hit, letting the drop come 0–LAG_ATTACK after the window opens (0–LAG_BULLET after a shot). The seconds
after the hit matter for animations several moves share: the arrow 3018 opens both tides and the lightning smash, and
only what follows tells them apart. The similarity is
the mean cosine of the DINOv2 features of the aligned crops; crops without a lock-on dot are left out. Moves are ranked
by their best reference, among the moves of the failure's phase. The overlay's animation lines are read only from the
V3.1 tables, never from the crops (which went through mask_overlay()).

eval: over the owner-checked answers (failure_moves.csv). --refs other compares each failure only with the other
recordings (leave one recording out); --refs all also uses its own recording, leaving out EXCLUDE seconds around the
failure, which is closer to the final use, where both dev-menu recordings are references. Prints the top-1 and top-3
accuracy of the product move and of the animation; writes each failure's ranking to work/move_match_eval.csv.
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import GT, WORK, annotation_dir, recordings, work_dir  # noqa: E402
from failure_answers import BY_PREVIOUS, MOVES, WINDOWS, Overlay, moves_for, phase_at, read  # noqa: E402

LAG_ATTACK, LAG_BULLET, RATE = 0.2, 1.5, 30          # RATE: crops per second (boss_track.py --step 2)
EXCLUDE = 5.0
ZH = {m["slug"]: m["zh"] for m in MOVES}


def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def detrend(f, ok, seconds):
    """Subtract the mean feature of the surrounding `seconds` (crops with a dot only): what stays the same for a
    while (arena, light, camera distance) drops out, the boss's motion stays."""
    if seconds <= 0:
        return f
    k = round(seconds * RATE)
    w = ok.astype(np.float32)
    cs = np.cumsum(np.vstack([np.zeros((1, f.shape[1]), np.float32), f * w[:, None]]), 0)
    cw = np.cumsum(np.concatenate([[0.0], w]))
    lo, hi = np.clip(np.arange(len(f)) - k, 0, len(f)), np.clip(np.arange(len(f)) + k + 1, 0, len(f))
    mean = (cs[hi] - cs[lo]) / np.maximum(cw[hi] - cw[lo], 1)[:, None]
    out = f - mean
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-6)


class Rec:
    def __init__(self, rec_id, rec, model, part, trend=0.0):
        self.id, self.rec = rec_id, rec
        feats = np.load(work_dir(rec_id) / f"boss_feats_{model}.npy").astype(np.float32)
        d = feats.shape[1] // 2
        f = {"cls": feats[:, :d], "patch": feats[:, d:], "both": feats / np.sqrt(2)}[part]
        rows = read(work_dir(rec_id) / "boss_track.csv")
        self.t = np.array([float(r["time_s"]) for r in rows])
        self.ok = np.array([r["state"] != "none" for r in rows])
        self.f = detrend(f, self.ok, trend)
        events = read(work_dir(rec_id) / "events.csv")
        self.blows = [float(e["time_s"]) for e in events if e["type"] == "deathblow"]
        self.ends = [float(e["time_s"]) for e in events if e["type"] == "death" and e["note"].startswith("not resurrected")]

    def row(self, t):
        return int(np.clip(np.searchsorted(self.t, t), 0, len(self.t) - 1))

    def references(self):
        ov = Overlay(self.id, GT / "observations" / self.rec.get("ruleset", "vanilla") / "genichiro" / self.id)
        refs = []
        for anim, occs in ov.occ.items():
            for s, e, start in occs:
                wins = [w for w in WINDOWS.get((ov.chars[s], anim), ()) if w[0] in ("attack", "bullet")]
                if not wins:
                    continue
                entries, _, prev = ov.chain_of(anim, start)
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
                    moves = moves_for(entries, phase)
                    pick = BY_PREVIOUS.get(anim, {}).get(prev)
                    if len(moves) > 1 and pick in {m["slug"] for m in moves}:
                        moves = [m for m in moves if m["slug"] == pick]
                    refs.append({"rec": self, "anim": anim, "hit": hit, "kind": kind, "t": t, "phase": phase,
                                 "moves": [m["slug"] for m in moves]})
        return refs


def similarity(q, qrow, r, rrow, before, after):
    if min(qrow, rrow) - before + 1 < 0 or qrow + after >= len(q.t) or rrow + after >= len(r.t):
        return -1.0
    a, b = q.f[qrow - before + 1:qrow + after + 1], r.f[rrow - before + 1:rrow + after + 1]
    m = q.ok[qrow - before + 1:qrow + after + 1] & r.ok[rrow - before + 1:rrow + after + 1]
    if m.sum() < (before + after) / 3:
        return -1.0
    return float((a[m] * b[m]).sum(1).mean())


def rank(q, t_hit, phase, refs, window, after):
    """Best score per product move (moves of this phase only) and per animation."""
    before, after, qrow = round(window * RATE), round(after * RATE), q.row(t_hit)
    phase_moves = {m["slug"] for m in MOVES if str(phase) in m["phases"]}
    by_move, by_anim = {}, {}
    for ref in refs:
        moves = [m for m in ref["moves"] if m in phase_moves]
        if not moves:
            continue
        lags = range(0, round(LAG_ATTACK * RATE) + 1) if ref["kind"] == "attack" else \
            range(0, round(LAG_BULLET * RATE) + 1, 2)
        rrow = ref["rec"].row(ref["t"])
        score = max(similarity(q, qrow - lag, ref["rec"], rrow, before, after) for lag in lags)
        for m in moves:
            by_move[m] = max(by_move.get(m, -1.0), score)
        by_anim[ref["anim"]] = max(by_anim.get(ref["anim"], -1.0), score)
    order = lambda d: sorted(d, key=d.get, reverse=True)  # noqa: E731
    return order(by_move), order(by_anim), by_move


def lead_time(row):
    """When the hit the failure is attributed to happened: the posture break, else the first hit."""
    items = [h.split(":")[0].split() for h in row["hits"].split(" ｜ ") if h]
    times = {role: float(t.rstrip("s")) for role, t in reversed(items)}
    return times.get("打崩", float(items[0][1].rstrip("s")))


def evaluate():
    model, part, window = opt("--model", "small14"), opt("--part", "cls"), float(opt("--window", "1.5"))
    after, which, trend = float(opt("--after", "1.0")), opt("--refs", "all"), float(opt("--detrend", "0.5"))
    recs = {i: Rec(i, r, model, part, trend) for i, r in recordings().items() if r.get("overlay")}
    refs = {i: r.references() for i, r in recs.items()}
    results = []
    for rec_id, q in recs.items():
        answers = {r["key"]: r for r in read(work_dir(rec_id) / "failure_answers.csv")}
        for rev in read(annotation_dir(q.rec) / "failure_moves.csv"):
            a = answers.get(rev["key"])
            if a is None or rev["verdict"] not in ("correct", "wrong"):
                continue
            truth = rev["correct_move"] if rev["verdict"] == "wrong" else a["move"]
            truth_anim = int(a["anims"].split()[0]) if rev["verdict"] == "correct" and a["anims"] else None
            t_hit = lead_time(a)
            pool = [ref for j, rs in refs.items() for ref in rs
                    if j != rec_id or (which == "all" and abs(ref["t"] - t_hit) > EXCLUDE)]
            moves, anims, scores = rank(q, t_hit, int(a["phase"]), pool, window, after)
            results.append({"rec": rec_id, "key": a["key"], "phase": a["phase"], "truth": truth,
                            "move_rank": moves.index(truth) + 1 if truth in moves else 99,
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


if __name__ == "__main__":
    if sys.argv[1] == "eval":
        evaluate()
