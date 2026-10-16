"""Propose the move behind every failure in a dev-menu recording, from the overlay's animation IDs.

Usage: python -I failure_answers.py <recording id | all>

Only for recordings with the dev-menu overlay (recordings.json "overlay": true) whose overlay readings are in
research/ground_truth/observations/<ruleset>/genichiro/<recording>/ (V3.1). Reads the HUD events of hud_pipeline.py
(work/<recording>/events.csv) and writes work/<recording>/failure_answers.csv for the review page; the owner's
verdicts go to the annotations (review_events.py). These are the automatic answers the plan counts on: the overlay
says which animation was playing when Wolf was hit. The animation lines are only read here, from the V3.1 tables,
never from the video.

For every damage or posture-break event:
  1. Which animation hit Wolf. At the frame the HP starts to drop, and up to HIT_LOOKBACK before it, the overlay gives
     every animation Genichiro is playing and how far into it he is. An animation is a candidate when that time is
     inside one of its attack windows (engine/genichiro_attack_windows.csv), give or take WINDOW_SLACK. Arrows and
     lightning hit after they are fired, so when no attack window fits, an animation that fired a projectile in the
     BULLET_FLIGHT before the drop is a candidate. Several candidates, or none, are flagged for the owner.
  2. Which catalog entry: the chain check (observations/vanilla/genichiro/chain_check.csv) gives, for every play of an
     animation, the entries whose AI chain explains it.
  3. Which product move: the moveset (semantic/genichiro_product_moveset.csv) lists each move's catalog entries and
     phases; P12-20 belongs to two moves, one per phase, so the phase picks. P3-30 (3080) belongs to two moves of
     phase 3, so the animation before it picks (BY_PREVIOUS).
Phase: 1 + Wolf's deathblows so far (each ends a phase); a death that is not resurrected ends the attempt.

Failures, merged by the owner's rules (plan.md, 2026-10-16):
  - hits from one play of a move are one failure: the same chain (a chain step or a visible interrupt continues it,
    any other option starts a new one) and the same product move;
  - a death joins the failure of the hit that killed;
  - a posture break joins the hit that broke it (within BREAK_WITH) and every hit taken while Wolf is still staggered
    (PUNISH_WINDOW after it); the failure is attributed to the move that broke the posture.
The failure's type is the most serious of its events: death, then posture break, then damage.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import GT, recordings, work_dir  # noqa: E402

HIT_LOOKBACK, WINDOW_SLACK, BULLET_FLIGHT = 0.1, 0.1, 1.5
BREAK_WITH, PUNISH_WINDOW = 0.3, 2.0
CONTINUES = {"链内衔接", "打断衔接", "打断衔接(你确认)"}
# an animation in two product moves of the same phase, settled by the animation before it. 3080 (P3-30) is the thrust
# after a perfect deflect: of 3032 it belongs to the phase-3 perilous follow-up, of the last hit of a Floating Passage
# set (3028, 3041, 3092) to Floating Passage (the owner's P3-30 label, 2026-10-15)
BY_PREVIOUS = {3080: {3032: "perilous-attack-follow-up-phase-3", 3028: "floating-passage-phase-3",
                      3041: "floating-passage-phase-3", 3092: "floating-passage-phase-3"}}
SEVERITY = {"death": 3, "posture_break": 2, "damage": 1}
FIELDS = ["key", "time_s", "type", "types", "phase", "events", "hits", "anims", "chain", "entries", "move", "move_zh",
          "move_en", "flags"]


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def mmss_to_s(s):
    m, sec = s.split(":")
    return int(m) * 60 + float(sec)


WINDOWS = defaultdict(list)       # (character, anim) -> [(kind, hit, start, end)]
for r in read(GT / "engine/genichiro_attack_windows.csv"):
    WINDOWS[(r["character"], int(r["anim"]))].append((r["kind"], r["hit"], float(r["start_s"]), float(r["end_s"])))
MOVES = [{"slug": r["slug"], "zh": r["name_zh"], "en": r["name_en"], "phases": set(r["phases"].split("、")),
          "entries": set(r["catalog_entries"].split())}
         for r in read(GT / "semantic/genichiro_product_moveset.csv")]


class Overlay:
    def __init__(self, rec_id, obs):
        self.frames = read(obs / "frames.csv")
        self.fps = (len(self.frames) - 1) / float(self.frames[-1]["time_s"])
        self.chars, last = [], "c7100"
        for r in self.frames:
            last = r["character"][:5] if r["character"] else last
            self.chars.append(last)
        self.occ = defaultdict(list)    # anim -> [(start_frame, end_frame, start_time)]
        for r in read(obs / "occurrences.csv"):
            self.occ[int(r["anim"][5:])].append((int(r["start_frame"]), int(r["end_frame"]), float(r["start_time"])))
        rows = [r for r in read(obs.parent / "chain_check.csv") if r["recording"] == rec_id]
        rows.sort(key=lambda r: mmss_to_s(r["time"]))
        self.chain, n, seg = [], 0, 0
        for r in rows:
            if r["verdict"] not in CONTINUES:
                n += 1
            if r["verdict"] != "链内衔接":
                seg += 1
            prev = int(r["prev"]) if r["prev"] else None
            self.chain.append((int(r["anim"]), mmss_to_s(r["time"]), set(r["entries"].split()), n, seg, prev))
        # an animation shared by several entries (the arrow 3018 opens both tides) is settled by the steps around it:
        # the entry must explain every step of the same chain
        steps = defaultdict(list)
        for c in self.chain:
            steps[c[4]].append(c[2])
        self.narrowed = {}
        for i, c in enumerate(self.chain):
            both = set.intersection(*steps[c[4]]) & c[2]
            self.narrowed[i] = both or c[2]

    def lines(self, k):
        r = self.frames[k]
        for i in range(1, 6):
            if r[f"line{i}"]:
                anim, t = r[f"line{i}"].split("@")
                yield int(anim), float(t)

    def occurrence(self, anim, k):
        return next(((s, e, t) for s, e, t in self.occ[anim] if s <= k <= e), None)

    def chain_of(self, anim, start_time):
        """Catalog entries, chain number and previous animation of the play of `anim` that started at start_time."""
        i = min((i for i, c in enumerate(self.chain) if c[0] == anim), key=lambda i: abs(self.chain[i][1] - start_time),
                default=None)
        if i is None or abs(self.chain[i][1] - start_time) > 0.15:
            return [], None, None
        return sorted(self.narrowed[i]), self.chain[i][3], self.chain[i][5]

    def play(self, n):
        """The animations of play number n, in order ("3018 → 3043")."""
        return " → ".join(str(c[0]) for c in self.chain if c[3] == n)

    def candidates(self, f):
        """Animations whose attack window (or a projectile fired just before) fits the hit at frame f."""
        found = {}
        for k in range(max(0, f - round(HIT_LOOKBACK * self.fps)), min(f, len(self.frames) - 1) + 1):
            for anim, at in self.lines(k):
                for kind, hit, s, e in WINDOWS.get((self.chars[k], anim), ()):
                    if kind == "attack" and s - WINDOW_SLACK <= at <= e + WINDOW_SLACK:
                        occ = self.occurrence(anim, k)
                        found.setdefault((anim, occ), {"anim": anim, "occ": occ, "how": f"第 {hit} 击", "at": at})
        if found:
            return list(found.values())
        for k in range(max(1, f - round(BULLET_FLIGHT * self.fps)), min(f, len(self.frames) - 1) + 1):
            before = dict(self.lines(k - 1))
            for anim, at in self.lines(k):
                for kind, hit, s, e in WINDOWS.get((self.chars[k], anim), ()):
                    if kind == "bullet" and at >= s and before.get(anim, -1.0) < s:
                        occ = self.occurrence(anim, k)
                        found.setdefault((anim, occ), {"anim": anim, "occ": occ, "at": at,
                                                       "how": f"飞行物（{(f - k) / self.fps:.2f} 秒前射出）"})
        return list(found.values())


def phase_at(t, blows, ends):
    start = max([e for e in ends if e < t], default=-1.0)
    return 1 + sum(1 for b in blows if start < b < t)


def moves_for(entries, phase):
    return [m for m in MOVES if m["entries"] & set(entries) and str(phase) in m["phases"]]


def answer(ov, e, phase):
    """The hit of one event: candidate animations, their entries, product moves and chain numbers."""
    cands = ov.candidates(int(e["frame"]))
    out = {"hits": [], "anims": [], "entries": set(), "moves": {}, "chains": set(), "plays": [], "flags": []}
    for c in cands:
        entries, chain, prev = ov.chain_of(c["anim"], c["occ"][2]) if c["occ"] else ([], None, None)
        out["hits"].append(f"{c['anim']} {c['how']} @{c['at']:.2f}s")
        out["anims"].append(str(c["anim"]))
        out["entries"] |= set(entries)
        out["chains"].add(chain)
        if chain is not None:
            out["plays"].append(ov.play(chain))
        moves = moves_for(entries, phase)
        pick = BY_PREVIOUS.get(c["anim"], {}).get(prev)
        if len(moves) > 1 and pick in {m["slug"] for m in moves}:
            moves = [m for m in moves if m["slug"] == pick]
            out["hits"][-1] += f"（前面是 {prev}）"
        for m in moves:
            out["moves"][m["slug"]] = m
        if not entries:
            out["flags"].append(f"{c['anim']} 在链核对里找不到")
    if not cands:
        out["flags"].append("没有候选动画")
    elif len(cands) > 1:
        out["flags"].append("多个候选动画")
    if len(out["moves"]) > 1:
        out["flags"].append("多个产品招式")
    return out


def build(rec_id, rec):
    obs = GT / "observations" / rec.get("ruleset", "vanilla") / "genichiro" / rec_id
    ov = Overlay(rec_id, obs)
    events = read(work_dir(rec_id) / "events.csv")
    for e in events:
        e["t"] = float(e["time_s"])
    blows = [e["t"] for e in events if e["type"] == "deathblow"]
    ends = [e["t"] for e in events if e["type"] == "death" and e["note"].startswith("not resurrected")]
    for e in events:
        e["phase"] = phase_at(e["t"], blows, ends)
        if e["type"] in ("damage", "posture_break"):
            e["ans"] = answer(ov, e, e["phase"])

    # the owner's merge rules, in time order: hits from one play of a move are one failure; a posture break takes the
    # hit that broke it and every hit while Wolf is staggered, and the failure goes to the move that broke the posture
    groups, run, stagger = [], None, None
    for e in (e for e in events if e["type"] in ("damage", "posture_break")):
        if stagger and e["t"] <= stagger["until"]:
            stagger["group"]["events"].append(e)
            continue
        last = run["events"][-1] if run else None
        same_play = last and e["ans"]["moves"] and set(last["ans"]["moves"]) == set(e["ans"]["moves"]) and \
            (last["ans"]["chains"] & e["ans"]["chains"]) - {None}
        broke = last and e["type"] == "posture_break" and e["t"] - last["t"] <= BREAK_WITH
        if same_play or broke:
            run["events"].append(e)
        else:
            run = {"events": [e], "lead": e}
            groups.append(run)
        if e["type"] == "posture_break":
            run["lead"] = e
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
        ans = lead.get("ans") or {"hits": [], "anims": [], "entries": set(), "moves": {}, "plays": [],
                                  "flags": ["没有被打中的事件"]}
        hits, flags = [], list(ans["flags"])
        for x in evs:
            if "ans" not in x:
                continue
            punish = lead["type"] == "posture_break" and x["t"] > lead["t"] + BREAK_WITH
            role = "打崩" if x["type"] == "posture_break" else ("追击" if punish else "扣血")
            text = "、".join(x["ans"]["hits"]) or "—"
            if x is not lead and set(x["ans"]["moves"]) != set(ans["moves"]):
                other = "、".join(m["zh"] for m in x["ans"]["moves"].values()) or "?"
                text += f"（{other}）"
                if not punish:
                    flags.append(f"{x['key']} 的招式不同")
            hits.append(f"{role} {x['time_s']}s: {text}")
        phases = {x["phase"] for x in evs}
        if len(phases) > 1:
            flags.append("跨阶段")
        moves = list(ans["moves"].values())
        rows.append({
            "key": evs[0]["key"], "time_s": evs[0]["time_s"],
            "type": max((x["type"] for x in evs), key=SEVERITY.get),
            "types": " ".join(x["type"] for x in evs), "phase": evs[0]["phase"],
            "events": " ".join(x["key"] for x in evs), "hits": " ｜ ".join(hits),
            "anims": " ".join(dict.fromkeys(ans["anims"])), "chain": " ｜ ".join(dict.fromkeys(ans["plays"])),
            "entries": " ".join(sorted(ans["entries"])),
            "move": " ".join(m["slug"] for m in moves), "move_zh": "、".join(m["zh"] for m in moves),
            "move_en": "; ".join(m["en"] for m in moves), "flags": "；".join(dict.fromkeys(flags))})

    out = work_dir(rec_id) / "failure_answers.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
    n = defaultdict(int)
    for r in rows:
        n[r["type"]] += 1
    print(f"wrote {out}: {len(rows)} failures {dict(n)}, {sum(1 for r in rows if r['flags'])} flagged")


def main():
    recs = recordings()
    ids = [i for i, r in recs.items() if r.get("overlay")] if sys.argv[1] == "all" else [sys.argv[1]]
    for rec_id in ids:
        if not recs[rec_id].get("overlay"):
            sys.exit(f"{rec_id} has no dev-menu overlay: its answers come from the owner's labels instead")
        build(rec_id, recs[rec_id])


if __name__ == "__main__":
    main()
