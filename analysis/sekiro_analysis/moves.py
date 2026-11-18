"""Recognise the move behind each failure from the boss crops around the hit (version 2, frozen 2026-11-12).

The research script research/failure_attribution/scripts/move_match.py builds the references (from the dev-menu
recordings' overlay and the owner's labels), evaluates, and writes each recording's failure_predictions.csv with
predict_rows() below; the recording worker runs predict_rows() with the same references, read from its data folder
(references.py).

A failure is compared with the references: the boss crops from WINDOW seconds before the HP drop to AFTER seconds after
it, against the crops around each reference hit, letting the drop come 0–LAG_ATTACK after the reference's attack window
opens (0–LAG_BULLET after a shot is fired; ± LAG_DROP crops for a reference that is itself an HP drop the owner
labelled). The seconds after the hit matter for animations several moves share: the arrow 3018 opens both tides and the
lightning smash, and only what follows tells them apart. The similarity is the mean cosine of the DINOv2 features of
the aligned crops; crops without a lock-on dot are left out. Moves are ranked by their best reference, among the moves
of the failure's phase.

Without the overlay there is no AI chain to say which hits came from one play of a move, so a hit within the move's
merge window (merge_gaps(): the move's longest play, never under MERGE_GAP) of the last one joins its failure when the
failure's top move is among the hit's top two; a posture break, the hit that broke it and the hits while Wolf is
staggered are one failure, as is a death with the hit that killed (the owner's rules). A failure's moves are ranked by
the mean score over its hits (the posture break alone when there is one). `confidence` is the top score minus the best
score of a move that does not count as the same (SAME_MOTION), and the answer is `certain` from SURE_MARGIN on; below it
the failure report says the move is uncertain and names the candidates.

SURE_MARGIN was set on the 82 failures of the M1 recordings (2026-10-19) and kept for version 2: on the 154 failures of
the 16 development recordings, every wrong first candidate was under 0.022.
"""
import csv
from pathlib import Path

import numpy as np

from . import sampling

LAG_ATTACK, LAG_BULLET, RATE = 0.2, 1.5, sampling.SAMPLES_PER_S   # RATE: crops per second (boss_track.py)
LAG_DROP = 2       # crops either side for a labelled reference: both times are HP drops read by the same detector
MERGE_GAP, BREAK_WITH, PUNISH_WINDOW = 2.0, 0.3, 2.0
SURE_MARGIN = 0.025
# a death whose killing hit left no mark on the HP bar (events.py puts it 2.4 s before the death screen): the hit came
# 1.6-2.9 s before the 死 on the reviewed deaths, so every moment of that span is tried and each move keeps its best
UNSEEN_SPAN, UNSEEN_STEP = (-0.5, 0.8), 0.1
SEVERITY = {"death": 3, "posture_break": 2, "damage": 1}
# the owner's rules (2026-10-16, 2026-11-12): Counter Slash and Deflect Counter Slash move almost the same, so they
# always count for each other; the phase-1 Perilous Attack Follow Up is mainly its Mikiri thrust, so it and Perilous
# Thrust count for each other
SAME_MOTION = [{"counter-slash", "deflect-counter-slash"}, {"perilous-attack-follow-up", "perilous-thrust"}]
# how version 2 was run: DINOv2 small14 class tokens, 1.5 s before and 1 s after the hit, 0.5 s detrend, the owner's
# labelled hits as references, merge windows per move
SETTINGS = {"model": "small14", "part": "cls", "window": 1.5, "after": 1.0, "trend": 0.5, "labelled": True, "gaps": True}
FIELDS = ["key", "time_s", "type", "types", "phase", "events", "hits", "anims", "chain", "entries", "move", "move_zh",
          "move_en", "flags", "candidates", "confidence", "certain"]


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def phase_at(t, blows, ends):
    """The fight's phase at t: 1 plus the deathblows since the last death that ended the fight."""
    start = max([e for e in ends if e < t], default=-1.0)
    return 1 + sum(1 for b in blows if start < b < t)


def margin(moves, scores):
    """How far the top move is ahead of the best move that does not count as the same one."""
    if not moves:
        return 0.0
    same = next((group for group in SAME_MOTION if moves[0] in group), {moves[0]})
    return scores[moves[0]] - next((scores[m] for m in moves[1:] if m not in same), 0.0)


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
    """One recording's boss features and timeline, from its work folder (boss_feats_<model>.npy, boss_track.csv,
    events.csv), or from saved arrays (from_arrays, the worker's references)."""

    def __init__(self, work, model="small14", part="cls", trend=0.0):
        work = Path(work)
        feats = np.load(work / f"boss_feats_{model}.npy").astype(np.float32)
        d = feats.shape[1] // 2
        f = {"cls": feats[:, :d], "patch": feats[:, d:], "both": feats / np.sqrt(2)}[part]
        rows = read(work / "boss_track.csv")
        self.t = np.array([float(r["time_s"]) for r in rows])
        self.ok = np.array([r["state"] != "none" for r in rows])
        self.f = detrend(f, self.ok, trend)
        events = read(work / "events.csv")
        self.blows = [float(e["time_s"]) for e in events if e["type"] == "deathblow"]
        self.ends = [float(e["time_s"]) for e in events if e["type"] == "death" and e["note"].startswith("not resurrected")]

    @classmethod
    def from_arrays(cls, t, ok, f):
        """A reference recording from its saved arrays: times, crops with a dot, detrended features."""
        r = cls.__new__(cls)
        r.t, r.ok, r.f, r.blows, r.ends = t, ok, f, [], []
        return r

    def row(self, t):
        return int(np.clip(np.searchsorted(self.t, t), 0, len(self.t) - 1))


def merge_gaps(refs):
    """How far apart two hits of one failure may be, per move (version 2). One play of a long move such as Floating
    Passage hits over more than MERGE_GAP seconds, so its hits can land further apart. From the dev-menu references:
    a move's window is its longest play, first hit to last, plus LAG_ATTACK (an HP drop comes up to that long after
    the window opens), but less than the closest two of its plays came minus LAG_ATTACK, so that two plays stay two
    failures, and never under MERGE_GAP."""
    plays = {}
    for ref in refs:
        if ref.get("play") and ref["play"][1] is not None and len(ref["moves"]) == 1:
            plays.setdefault((ref["moves"][0], ref["play"]), []).append(ref["t"])
    span, closest, last = {}, {}, {}
    for (move, play), ts in sorted(plays.items(), key=lambda kv: (kv[0][1][0], min(kv[1]))):
        span[move] = max(span.get(move, 0.0), max(ts) - min(ts))
        if last.get(move, (None,))[0] == play[0]:
            closest[move] = min(closest.get(move, float("inf")), min(ts) - last[move][1])
        last[move] = (play[0], max(ts))
    return {m: max(MERGE_GAP, min(span[m] + LAG_ATTACK, closest.get(m, float("inf")) - LAG_ATTACK)) for m in span}


def similarity(q, qrow, r, rrow, before, after):
    if min(qrow, rrow) - before + 1 < 0 or qrow + after >= len(q.t) or rrow + after >= len(r.t):
        return -1.0
    a, b = q.f[qrow - before + 1:qrow + after + 1], r.f[rrow - before + 1:rrow + after + 1]
    m = q.ok[qrow - before + 1:qrow + after + 1] & r.ok[rrow - before + 1:rrow + after + 1]
    if m.sum() < (before + after) / 3:
        return -1.0
    return float((a[m] * b[m]).sum(1).mean())


def rank(q, t_hit, phase, refs, window, after, moves):
    """Best score per product move (moves of this phase only) and per animation."""
    before, after, qrow = round(window * RATE), round(after * RATE), q.row(t_hit)
    phase_moves = {m["slug"] for m in moves if str(phase) in m["phases"]}
    by_move, by_anim = {}, {}
    for ref in refs:
        ref_moves = [m for m in ref["moves"] if m in phase_moves]
        if not ref_moves:
            continue
        lags = range(0, round(LAG_ATTACK * RATE) + 1) if ref["kind"] == "attack" else \
            range(-LAG_DROP, LAG_DROP + 1) if ref["kind"] == "drop" else range(0, round(LAG_BULLET * RATE) + 1, 2)
        rrow = ref["rec"].row(ref["t"])
        score = max(similarity(q, qrow - lag, ref["rec"], rrow, before, after) for lag in lags)
        for m in ref_moves:
            by_move[m] = max(by_move.get(m, -1.0), score)
        if ref["anim"] is not None:
            by_anim[ref["anim"]] = max(by_anim.get(ref["anim"], -1.0), score)
    order = lambda d: sorted(d, key=d.get, reverse=True)  # noqa: E731
    return order(by_move), order(by_anim), by_move


def predict_rows(q, events, refs, gaps, moves, st=SETTINGS):
    """The failures of one recording and their moves: q its Rec, events its events.csv rows, refs the references,
    gaps merge_gaps() of the dev-menu references, moves the product moves of the boss (slug, zh, en, phases). Returns
    the rows of failure_predictions.csv (FIELDS)."""
    zh = {m["slug"]: m["zh"] for m in moves}
    for e in events:
        e["t"], e["phase"] = float(e["time_s"]), phase_at(float(e["time_s"]), q.blows, q.ends)
        if e["type"] in ("damage", "posture_break"):
            e["moves"], _, e["scores"] = rank(q, e["t"], e["phase"], refs, st["window"], st["after"], moves)
    top = lambda e: e["moves"][0] if e.get("moves") else None  # noqa: E731

    groups, run, stagger = [], None, None
    for e in (e for e in events if e["type"] in ("damage", "posture_break")):
        if stagger and e["t"] <= stagger["until"]:
            stagger["group"]["events"].append(e)
            continue
        last = run["events"][-1] if run else None
        gap = gaps.get(run["move"], MERGE_GAP) if st["gaps"] and run else MERGE_GAP
        same = last and e.get("moves") and run["move"] in e["moves"][:2] and e["t"] - last["t"] <= gap
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
                for m, sc in rank(q, lead["t"] + d, lead["phase"], refs, st["window"], st["after"], moves)[2].items():
                    total[m] = max(total.get(m, -1.0), sc)
        ranked = sorted(total, key=total.get, reverse=True)
        hits = [f"死亡 {lead['time_s']}s: 致命一击在血条上看不到，按「死」字前 1.6–2.9 秒估计"] if unseen else []
        for x in evs:
            if "scores" in x:
                role = "打崩" if x["type"] == "posture_break" else \
                    ("追击" if lead["type"] == "posture_break" and x["t"] > lead["t"] + BREAK_WITH else "扣血")
                hits.append(f"{role} {x['time_s']}s: 第一候选 {zh.get(top(x), '—')}")
        best = next((m for m in moves if ranked and m["slug"] == ranked[0]), None)
        lead_by = margin(ranked, total)
        sure = best is not None and lead_by >= SURE_MARGIN
        flags = "没有候选" if not best else ("" if sure else
                 f"没把握：第一候选只比别的招式高 {lead_by:.3f}（要 {SURE_MARGIN} 以上），报告里写成「可能是 "
                 f"{zh.get(ranked[0], ranked[0])} 或 {zh.get(ranked[1], ranked[1]) if len(ranked) > 1 else '—'}」")
        rows.append({
            "key": evs[0]["key"], "time_s": evs[0]["time_s"],
            "type": max((x["type"] for x in evs), key=SEVERITY.get),
            "types": " ".join(x["type"] for x in evs), "phase": evs[0]["phase"],
            "events": " ".join(x["key"] for x in evs), "hits": " ｜ ".join(hits), "anims": "", "chain": "",
            "entries": "", "move": best["slug"] if best else "", "move_zh": best["zh"] if best else "",
            "move_en": best["en"] if best else "", "flags": flags,
            "candidates": " ".join(f"{m}:{total[m]:.3f}" for m in ranked[:3]),
            "confidence": f"{lead_by:.3f}", "certain": "1" if sure else "0"})
    return rows


def write_rows(rows, out):
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else FIELDS, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
