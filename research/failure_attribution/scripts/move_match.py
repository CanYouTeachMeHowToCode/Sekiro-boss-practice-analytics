"""Recognise the move behind a failure from the boss crops before the hit (M1 step 4, first version).

Usage: python -I move_match.py eval [--model small14] [--part cls|patch|both] [--window 1.5] [--after 1.0]
                                   [--detrend 0.5] [--refs all|other]
       python -I move_match.py predict <recording id | all> [the same options]

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

eval: over the owner-checked answers (failure_moves.csv), with the owner's rules on moves that look the same: Floating
Passage's opening two slashes without their follow-up may also be answered Two-Hit Slash, and Counter Slash and Deflect
Counter Slash count for each other (accepted()). --refs other compares each failure only with the other
recordings (leave one recording out); --refs all also uses its own recording, leaving out EXCLUDE seconds around the
failure, which is closer to the final use, where both dev-menu recordings are references. Prints the top-1 and top-3
accuracy of the product move and of the animation; writes each failure's ranking to work/move_match_eval.csv.

predict: the failure report proposal for a recording, from its HUD events (hud_pipeline.py) and boss features, with
every dev-menu recording but itself as references. Without the overlay there is no AI chain to say which hits came
from one play of a move, so a hit within MERGE_GAP of the last one joins its failure when the failure's top move is
among the hit's top two (Floating Passage's last hit can rank another move first); a
posture break, the hit that broke it and the hits while Wolf is staggered are one failure, as is a death with the hit
that killed (the owner's rules, as in failure_answers.py). A failure's moves are ranked by the mean score over its hits
(the posture break alone when there is one). Writes work/<recording id>/failure_predictions.csv: the columns of
failure_answers.csv, the top move as the answer, and the top three with their scores as `candidates`. The review page
shows it for a recording without the overlay, so the owner labels the moves with the candidates at hand.
"""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import GT, WORK, annotation_dir, observation_dir, recordings, work_dir  # noqa: E402
from failure_answers import BY_PREVIOUS, MOVES, WINDOWS, Overlay, moves_for, phase_at, read  # noqa: E402

LAG_ATTACK, LAG_BULLET, RATE = 0.2, 1.5, 30          # RATE: crops per second (boss_track.py --step 2)
EXCLUDE, MERGE_GAP, BREAK_WITH, PUNISH_WINDOW = 5.0, 2.0, 0.3, 2.0
# the owner's rule (2026-10-16): Floating Passage's opening two slashes (3068 or 3063) without the 3092 that follows a
# deflect look like Two-Hit Slash, so either answer is right for such a play
OPENERS, FOLLOW_UP = {3068, 3063}, 3092
TWO_SLASHES = {"advance", "floating-passage", "floating-passage-phase-3"}
# and (2026-10-16) Counter Slash and Deflect Counter Slash move almost the same, so they always count for each other
SAME_MOTION = [{"counter-slash", "deflect-counter-slash"}]


def accepted(truth, play):
    """The moves that count as right for a failure whose answer is `truth` and whose play is `play` ("3068 → 3092")."""
    anims = {int(a) for a in play.replace("｜", " ").replace("→", " ").split() if a.isdigit()}
    if truth in TWO_SLASHES and anims & OPENERS and FOLLOW_UP not in anims:
        return TWO_SLASHES
    return next((group for group in SAME_MOTION if truth in group), {truth})
# a death whose killing hit left no mark on the HP bar (events.py puts it 2.4 s before the death screen): the hit came
# 1.6-2.9 s before the 死 on the reviewed deaths, so every moment of that span is tried and each move keeps its best
UNSEEN_SPAN, UNSEEN_STEP = (-0.5, 0.8), 0.1
SEVERITY = {"death": 3, "posture_break": 2, "damage": 1}
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


def settings():
    return {"model": opt("--model", "small14"), "part": opt("--part", "cls"), "window": float(opt("--window", "1.5")),
            "after": float(opt("--after", "1.0")), "trend": float(opt("--detrend", "0.5"))}


def evaluate():
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


def predict(rec_id):
    st, recs = settings(), recordings()
    q = Rec(rec_id, recs[rec_id], st["model"], st["part"], st["trend"])
    refs = [ref for j, r in recs.items() if observation_dir(r) and j != rec_id
            for ref in Rec(j, r, st["model"], st["part"], st["trend"]).references()]
    events = read(work_dir(rec_id) / "events.csv")
    for e in events:
        e["t"], e["phase"] = float(e["time_s"]), phase_at(float(e["time_s"]), q.blows, q.ends)
        if e["type"] in ("damage", "posture_break"):
            e["moves"], _, e["scores"] = rank(q, e["t"], e["phase"], refs, st["window"], st["after"])
    top = lambda e: e["moves"][0] if e.get("moves") else None  # noqa: E731

    groups, run, stagger = [], None, None
    for e in (e for e in events if e["type"] in ("damage", "posture_break")):
        if stagger and e["t"] <= stagger["until"]:
            stagger["group"]["events"].append(e)
            continue
        last = run["events"][-1] if run else None
        same = last and e.get("moves") and run["move"] in e["moves"][:2] and e["t"] - last["t"] <= MERGE_GAP
        broke = last and e["type"] == "posture_break" and e["t"] - last["t"] <= BREAK_WITH
        if same or broke:
            run["events"].append(e)
        else:
            run = {"events": [e], "lead": e, "move": top(e)}
            groups.append(run)
        if e["type"] == "posture_break":
            run["lead"], run["move"] = e, top(e)
            stagger = {"group": run, "until": e["t"] + PUNISH_WINDOW}
    by_key = {x["key"]: g for g in groups for x in g["events"]}
    for death in (e for e in events if e["type"] == "death"):
        g = by_key.get(death["linked"])
        if g is None:
            g = {"events": [], "lead": death}
            groups.append(g)
        g["events"].append(death)

    rows = []
    for g in sorted(groups, key=lambda g: min(x["t"] for x in g["events"])):
        evs = sorted(g["events"], key=lambda x: (x["t"], -SEVERITY[x["type"]]))
        lead = g["lead"]
        voters = [lead] if lead["type"] == "posture_break" else [x for x in evs if "scores" in x]
        total, unseen = {}, not voters and lead["type"] == "death"
        for x in voters:
            for m, sc in x.get("scores", {}).items():
                total[m] = total.get(m, 0.0) + sc / len(voters)
        if unseen:
            for d in np.arange(UNSEEN_SPAN[0], UNSEEN_SPAN[1] + 1e-6, UNSEEN_STEP):
                for m, sc in rank(q, lead["t"] + d, lead["phase"], refs, st["window"], st["after"])[2].items():
                    total[m] = max(total.get(m, -1.0), sc)
        moves = sorted(total, key=total.get, reverse=True)
        hits = [f"死亡 {lead['time_s']}s: 致命一击在血条上看不到，按「死」字前 1.6–2.9 秒估计"] if unseen else []
        for x in evs:
            if "scores" in x:
                role = "打崩" if x["type"] == "posture_break" else \
                    ("追击" if lead["type"] == "posture_break" and x["t"] > lead["t"] + BREAK_WITH else "扣血")
                hits.append(f"{role} {x['time_s']}s: 第一候选 {ZH.get(top(x), '—')}")
        best = next((m for m in MOVES if moves and m["slug"] == moves[0]), None)
        rows.append({
            "key": evs[0]["key"], "time_s": evs[0]["time_s"],
            "type": max((x["type"] for x in evs), key=SEVERITY.get),
            "types": " ".join(x["type"] for x in evs), "phase": evs[0]["phase"],
            "events": " ".join(x["key"] for x in evs), "hits": " ｜ ".join(hits), "anims": "", "chain": "",
            "entries": "", "move": best["slug"] if best else "", "move_zh": best["zh"] if best else "",
            "move_en": best["en"] if best else "", "flags": "" if best else "没有候选",
            "candidates": " ".join(f"{m}:{total[m]:.3f}" for m in moves[:3])})
    out = work_dir(rec_id) / "failure_predictions.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{rec_id}: {len(rows)} failures from {sum(1 for e in events if 'scores' in e)} hits, "
          f"{len(refs)} references -> {out}")


if __name__ == "__main__":
    if sys.argv[1] == "eval":
        evaluate()
    elif sys.argv[1] == "predict":
        for rid, r in recordings().items():
            if sys.argv[2] in ("all", rid):
                predict(rid)
