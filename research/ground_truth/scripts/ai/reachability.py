"""Which Genichiro animations can the Ashina Castle fight actually play, per phase, and why not the others?

Usage:
    python -I reachability.py <moves_dir> <tae_dir> <coverage.csv> <out.csv>

    moves_dir     ai_moves.py output: 710000_moves.json, 711000_moves.json, 710300_moves.json, 711300_moves.json
    tae_dir       tae_dump.py output: c7100_tae.json, c7110_tae.json
    coverage.csv  observations/vanilla/genichiro/<recording>/coverage.csv (recorded occurrences per phase)

One row per TAE entry of c7100 (compared with castle phases 1-2) and c7110 (castle phase 3).

Category, from the TAE events (an ImportOtherAnim entry uses the events of the entry it imports):
  attack      has InvokeAttackBehavior
  bullet      no attack, but InvokeBulletBehavior other than the marker below
  other       neither
  A bullet with judge 980-989 on DummyPoly 6 is a marker of unknown meaning, not a projectile.

Castle wiring (map m11_01, params, events; see characters/genichiro.json):
  phases 1-2  AI 710000, NpcParam 71001000: boss has SpEffect 200050, not 200051; remaining deathblows 2 then 1
  phase 3     AI 711000, NpcParam 71100000: boss has 200050, not 3711500
Read from the decompiled scripts and applied on top of ai_moves.py:
  710000  Kengeki20 is zeroed when the boss has 200050                     -> never chosen at the castle
          Interrupt 3017 needs remaining deathblows <= 1                   -> phase 2 only
          Kengeki38 ends with 3067 only when remaining deathblows <= 1      -> 3067 phase 2 only
  711000  Act40, Act41, Kengeki22 are weighted only with 3711500           -> never chosen at the castle
          Act09 ends with 3086, Act15/Act48 with 3087, only with 3711500   -> not at the castle
          Interrupt 3085 needs 3711500; 3086 needs SpEffect 5031, which only 3085/3087 emit
          Interrupt 3016 is skipped whenever random(1..100) > 0, i.e. always
Encounters of the other AIs: 710000 also runs the prologue fight (with 200051), 711000 the Way of Tomoe phase of the
Isshin fight (with 3711500), 710300 / 711300 run Inner Genichiro. Their reachability is not computed here.
"""
import csv
import json
import sys
from collections import defaultdict

moves_dir, tae_dir, cov_path, out_path = sys.argv[1:5]
CASTLE = {"710000": ("c7100", ("1", "2")), "711000": ("c7110", ("3",))}
INNER = {"c7100": "710300", "c7110": "711300"}
EXCLUDE_FUNCS = {"710000": {"Kengeki20": "Boss 带 200050 时权重被清零"},
                 "711000": {"Act40": "只在 Boss 带 3711500 时加权", "Act41": "只在 Boss 带 3711500 时加权",
                            "Kengeki22": "只在 Boss 带 3711500 时加权"}}
SPECIAL = {  # (ai, function, animation) -> castle phases where that request can happen, and why
    ("710000", "Interrupt", 3017): ({"2"}, "剩余忍杀数 ≤ 1"),
    ("710000", "Kengeki38", 3067): ({"2"}, "剩余忍杀数 ≤ 1"),
    ("711000", "Act09", 3086): (set(), "只在 Boss 带 3711500 时"),
    ("711000", "Act15", 3087): (set(), "只在 Boss 带 3711500 时"),
    ("711000", "Act48", 3087): (set(), "只在 Boss 带 3711500 时"),
    ("711000", "Interrupt", 3085): (set(), "只在 Boss 带 3711500 时"),
    ("711000", "Interrupt", 3086): (set(), "需要特效 5031,只有 3085/3087 会发出"),
    ("711000", "Interrupt", 3016): (set(), "随机数条件永远不成立"),
}
GATED_FUNCS_3711500 = {("711000", f) for f in ("Act40", "Act41", "Kengeki22")}
GATED_REQUESTS_3711500 = {k for k, (ph, why) in SPECIAL.items() if "3711500" in why or "5031" in why}

moves = {ai: json.load(open(f"{moves_dir}/{ai}_moves.json", encoding="utf-8")) for ai in ("710000", "711000", "710300", "711300")}
cov = {r["anim"]: r for r in csv.DictReader(open(cov_path, encoding="utf-8"))}


def is_marker(e):
    return e["type"] == 2 and 980 <= e["params"].get("BehaviorJudgeID", 0) <= 989 and e["params"].get("DummyPolyID") == 6


def requests(ai, anim, live):
    """Functions of `ai` that request `anim`; live=True: functions the AI can choose or call."""
    return [fn for fn, f in moves[ai]["functions"].items()
            if any(i == anim for _, i in f["requests"]) and bool(f["reachable_by"]) == live]


rows = []
for ai, (char, phases) in CASTLE.items():
    tae = json.load(open(f"{tae_dir}/{char}_tae.json", encoding="utf-8"))["animations"]
    by = {a["id"]: a for a in tae}
    reach = defaultdict(lambda: defaultdict(list))
    for fn, info in moves[ai]["functions"].items():
        if not info["reachable_by"] or fn in EXCLUDE_FUNCS[ai]:
            continue
        for _, anim in info["requests"]:
            for ph in SPECIAL.get((ai, fn, anim), (set(phases), ""))[0]:
                if fn not in reach[anim][ph]:
                    reach[anim][ph].append(fn)
    for a in tae:
        src = a
        while src["kind"] == "import_other_anim":
            src = by[src["imports_from"]]
        evs = src["events"]
        attacks = [e for e in evs if e["type"] == 1]
        bullets = [e for e in evs if e["type"] == 2 and not is_marker(e)]
        anim = a["id_int"]
        c = cov[a["id"]]
        row = {
            "character": char, "anim": a["id"],
            "category": "attack" if attacks else "bullet" if bullets else "other",
            "reuse": f"imports {a['imports_from']}" if a["kind"] == "import_other_anim" else
                     (f"plays {a['hkx']}" if a.get("hkx") and a["hkx"] != a["id"] else ""),
        }
        for p in ("1", "2", "3"):
            row[f"recorded_phase{p}"] = c[f"occ_phase{p}"] if p in phases else ""
            row[f"castle_ai_phase{p}"] = ("yes" if reach[anim][p] else "no") if p in phases else ""
        row["castle_ai_paths"] = "; ".join(f"{ai}:{fn}" for fn in sorted({f for p in phases for f in reach[anim][p]}))
        recorded = any(int(c[f"occ_phase{p}"]) for p in phases)
        reachable = any(reach[anim][p] for p in phases)
        row["castle_status"] = ("recorded" if recorded else "reachable_not_recorded") if reachable else (
            "recorded_not_requested_by_ai" if recorded else "not_reachable")
        why = []
        if not reachable:
            gated = [fn for fn in requests(ai, anim, True) if fn in EXCLUDE_FUNCS[ai] or (ai, fn, anim) in SPECIAL]
            for fn in gated:
                why.append(f"{fn}: {EXCLUDE_FUNCS[ai].get(fn) or SPECIAL[(ai, fn, anim)][1]}")
            dead = requests(ai, anim, False)
            if dead:
                why.append("只在从不被选中的函数里: " + ", ".join(dead))
            if anim in moves[ai]["cooldown_ids"] and not gated and not dead:
                why.append("只作为冷却编号出现")
            if not why:
                why.append(f"{ai} 从不请求")
        row["castle_not_reachable_reason"] = "; ".join(why)
        other = []
        if any((ai, fn) in GATED_FUNCS_3711500 or (ai, fn, anim) in GATED_REQUESTS_3711500 for fn in requests(ai, anim, True)):
            other.append(f"{ai} 带 3711500(剑圣战巴流)")
        inner = requests(INNER[char], anim, True)
        if inner:
            other.append(f"{INNER[char]}(心中的弦一郎): " + ", ".join(inner))
        for o in ("710000", "711000", "710300", "711300"):
            if o not in (ai, INNER[char]) and requests(o, anim, True):
                other.append(f"{o}(另一个角色的 AI)")
        row["requested_by_other_ai"] = "; ".join(other)
        rows.append(row)

with open(out_path, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

sys.stdout.reconfigure(encoding="utf-8")
for char in ("c7100", "c7110"):
    rs = [r for r in rows if r["character"] == char]
    for cat in ("attack", "bullet", "other"):
        rc = [r for r in rs if r["category"] == cat]
        st = defaultdict(int)
        for r in rc:
            st[r["castle_status"]] += 1
        print(f"{char} {cat:6s} total {len(rc):3d} " + " ".join(f"{k} {v}" for k, v in sorted(st.items())))
