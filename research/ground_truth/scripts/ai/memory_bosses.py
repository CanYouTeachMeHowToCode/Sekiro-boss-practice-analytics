"""List every vanilla boss that drops a Memory, with its map, character models, AI and evidence.

Usage: python -I memory_bosses.py <out.csv>

Game files are read (read-only) from game_dir in research/ground_truth/local.config. The chain, all from game data:
  1. msg/<lang>/item.msgbnd: アイテム名.fmg goods named "战斗记忆·…" are the Memories; NPC名.fmg names the health bars.
  2. ItemLotParam: the lot holding each Memory, and the lot just before it that starts the chain.
  3. event/common.emevd: event 0 calls common event 300 once per boss with (…, defeat flag, …, chain lot, …);
     the three Inner Memories are instead awarded directly (2003[04] AwardItemLot) by their own common events.
  4. event/<map>*.emevd: in the event that sets the defeat flag (2003[02] flag ON), the boss is the entity that a
     character condition (bank 4) tests and that has a health bar (2003[11] state ON, which also gives its name).
     If that event tests no character (Folding Screen Monkeys), the bosses are the health bars shown by the same
     event files. Earlier phases on another model: an event whose character condition tests A and which enables
     B (2004[05] B ON), both with health bars, makes A the phase before B (c7100 -> c7110, Tomoe -> Isshin).
  5. map/mapstudio/<map>.msb: the enemy part with that entity ID gives the model (cNNNN), NpcThinkParam, NpcParam;
     NpcThinkParam's first two ints are the AI logic / battle script numbers.
Inner bosses have no defeat flag in event 300; their boss is the health bar whose name equals the Memory's
name after "战斗记忆·".
same_family_parts lists the other placed parts in the same map whose NpcParam has the same first four digits
(e.g. the four c1260 monkeys behind the Screen Monkeys' shared health bar). It is context, not proof that they
take part in the fight.
Part layout (Sekiro MSB, enemy part): entity ID at +0x23C, think/NPC param at +0x298/+0x29C (as in encounters.py).
"""
import configparser
import csv
import os
import struct
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "engine"))
sys.path.insert(0, str(HERE))
from bnd_names import LOCAL_CONFIG, read_dcx  # noqa: E402
import emevd  # noqa: E402
from params import load_bnd, rows  # noqa: E402

cfg = configparser.ConfigParser()
cfg.read(LOCAL_CONFIG, encoding="utf-8")
GAME = Path(cfg["paths"]["game_dir"])
ENT, THINK, NPC = 0x23C, 0x298, 0x29C


def fmg(b):
    groups = struct.unpack_from("<i", b, 0x0C)[0]
    soff = struct.unpack_from("<q", b, 0x18)[0]
    out = {}
    for g in range(groups):
        idx, first, last, _ = struct.unpack_from("<iiii", b, 0x28 + 16 * g)
        for k, i in enumerate(range(first, last + 1)):
            p = struct.unpack_from("<q", b, soff + 8 * (idx + k))[0]
            if p:
                e = p
                while b[e:e + 2] != b"\0\0":
                    e += 2
                out[i] = b[p:e].decode("utf-16-le")
    return out


def texts(lang, name):
    return fmg(load_bnd(read_dcx(GAME / f"msg/{lang}/item.msgbnd.dcx"))[name])


def msb_parts(b):
    """Enemy parts named cNNNN_NNNN: {entity: (name, think, npc)}."""
    out = {}
    pat = "c".encode("utf-16-le")
    o = b.find(pat)
    while o != -1:
        e = o
        while b[e:e + 2] != b"\0\0":
            e += 2
        name = b[o:e].decode("utf-16-le", "replace")
        if len(name) == 10 and name[1:5].isdigit() and name[5] == "_" and name[6:].isdigit():
            start = next((c for c in range(max(0, o - 0x400), o, 8) if struct.unpack_from("<q", b, c)[0] == o - c), None)
            if start is not None and start + NPC + 4 <= len(b):
                ent, think, npc = (struct.unpack_from("<i", b, start + x)[0] for x in (ENT, THINK, NPC))
                if ent > 1000000:
                    out[ent] = (name, think, npc)
        o = b.find(pat, o + 2)
    return out


def load_events():
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for f in sorted(os.listdir(GAME / "event")):
            if f.endswith(".emevd.dcx"):
                p = Path(tmp) / "e.emevd"
                p.write_bytes(read_dcx(GAME / "event" / f))
                out[f[:-len(".emevd.dcx")]] = emevd.load(str(p))
    return out


goods_zh, goods_en = texts("zhocn", "アイテム名.fmg"), texts("engus", "アイテム名.fmg")
npc_zh, npc_en = texts("zhocn", "NPC名.fmg"), texts("engus", "NPC名.fmg")
memories = {i: t for i, t in goods_zh.items() if t.startswith("战斗记忆·")}

P = load_bnd(read_dcx(GAME / "param/gameparam/gameparam.parambnd.dcx"))
lots, lsize = rows(P["ItemLotParam.param"])
think_rows, _ = rows(P["NpcThinkParam.param"])
lot_of = {}
for rid, r in lots.items():
    for v in struct.unpack_from("<8i", r, 0):
        if v in memories:
            lot_of[v] = rid
chain = {}
for m, lot in lot_of.items():
    base = max((x for x in range(lot - 3, lot + 1) if x in lots and (x == lot or x + 1 in lots)), default=lot)
    while base - 1 in lots and base - 1 >= lot - 3 and base > lot - 3:
        base -= 1
    chain[m] = [x for x in range(base, lot + 1) if x in lots]

events = load_events()
flag_of, award_event = {}, {}
for eid_, ev in [(e["id"], e) for e in events["common"]]:
    for x in ev["instrs"]:
        if (x["bank"], x["id"]) == (2000, 0) and len(x["args"]) > 5 and x["args"][1] == 300:
            for m, ls in chain.items():
                if any(a in ls for a in x["args"][2:]):
                    flag_of[m] = x["args"][2]
        if (x["bank"], x["id"]) == (2003, 4):
            for m, lot in lot_of.items():
                if x["args"] and x["args"][0] == lot:
                    award_event[m] = eid_

parts = {}
for f in sorted(os.listdir(GAME / "map/mapstudio")):
    if f.endswith(".msb.dcx"):
        parts[f[:12]] = msb_parts(read_dcx(GAME / "map/mapstudio" / f))

bar_name = defaultdict(set)          # entity -> name ids
bar_files = defaultdict(set)
links = set()                        # (A, B): an event tests A and enables B

for f, evs in events.items():
    for ev in evs:
        for x in ev["instrs"]:
            if (x["bank"], x["id"]) == (2003, 11) and len(x["args"]) >= 4 and x["args"][1] > 1000000:
                if x["args"][0] == 1:
                    bar_name[x["args"][1]].add(x["args"][3])
                    bar_files[x["args"][1]].add(f)
        conds = {x["args"][1] for x in ev["instrs"] if x["bank"] == 4 and len(x["args"]) > 1}
        enabled = {x["args"][0] for x in ev["instrs"] if (x["bank"], x["id"]) == (2004, 5) and x["args"][1:2] == [1]}
        for a in conds:
            for b in enabled:
                if a != b:
                    links.add((a, b))

rows_out = []
for m in sorted(memories):
    boss_ents, defeat = [], []
    other = []
    if m in flag_of:
        for f, evs in events.items():
            msb = parts.get(f[:12], {})
            for ev in evs:
                if any((x["bank"], x["id"]) == (2003, 2) and x["args"][:2] == [flag_of[m], 1] for x in ev["instrs"]):
                    defeat.append(f"{f} event {ev['id']}")
                    refs = sorted({v for x in ev["instrs"] for v in x["args"] if v in msb})
                    tested = {x["args"][1] for x in ev["instrs"] if x["bank"] == 4 and len(x["args"]) > 1}
                    hit = [e for e in refs if e in bar_name and e in tested]
                    boss_ents += hit
                    other += [e for e in refs if e not in hit]
                    if not hit:
                        files = {f}
                        boss_ents += [e for e in bar_name if bar_files[e] & files and e in msb]
    else:
        want = memories[m].split("·", 1)[1]
        boss_ents = [e for e, ns in bar_name.items() if any(npc_zh.get(n) == want for n in ns)]
    boss_ents = sorted(set(boss_ents))
    members = []
    for e in boss_ents:                  # walk back through earlier phases: A -> ... -> e
        chain_ = [e]
        while True:
            prev = [a for a, b in links if b == chain_[0] and a in bar_name and a not in chain_]
            if not prev:
                break
            chain_.insert(0, prev[0])
        members += [x for x in chain_ if x not in members]
    map_ = sorted({mp for e in members for mp, ps in parts.items() if e in ps})
    info = []
    for e in members:
        mp = next(mp for mp, ps in parts.items() if e in ps)
        name, think, npc = parts[mp][e]
        logic, battle = struct.unpack_from("<ii", think_rows[think], 0) if think in think_rows else (None, None)
        info.append((e, mp, name, think, npc, logic, battle, sorted(bar_name[e]), sorted(bar_files[e])))
    family = []
    for e in members:
        mp = next(mp for mp, ps in parts.items() if e in ps)
        fam = parts[mp][e][2] // 10000
        family += [f"{n} ({x})" for x, (n, t, npc) in sorted(parts[mp].items())
                   if npc // 10000 == fam and x not in members and f"{n} ({x})" not in family]
    other_info = []
    for e in sorted(set(other) - set(members)):
        mp = next(mp for mp, ps in parts.items() if e in ps)
        other_info.append(f"{parts[mp][e][0]} ({e})")
    rows_out.append({
        "memory_goods_id": m,
        "memory_zh": memories[m],
        "memory_en": goods_en.get(m, ""),
        "boss_parts": "; ".join(f"{i[2]} ({i[0]})" for i in info),
        "health_bars": "; ".join(f"{i[2]}: " + "/".join(f"{n} {npc_zh.get(n)} | {npc_en.get(n)}" for n in i[7]) for i in info),
        "maps": "; ".join(map_),
        "event_files_with_bar": "; ".join(f"{i[2]}: {','.join(i[8])}" for i in info),
        "ai_logic_battle": "; ".join(f"{i[2]}: {i[5]}/{i[6]}" for i in info),
        "npc_think_param": "; ".join(f"{i[2]}: {i[4]}/{i[3]}" for i in info),
        "defeat_flag": flag_of.get(m, ""),
        "memory_lot_chain": "->".join(map(str, chain[m])),
        "awarded_by": f"common event 300 (flag {flag_of[m]})" if m in flag_of else f"common event {award_event.get(m)}",
        "defeat_flag_set_by": "; ".join(defeat),
        "same_family_parts": "; ".join(family),
        "other_parts_in_defeat_event": "; ".join(other_info),
    })

with open(sys.argv[1], "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0]))
    w.writeheader()
    w.writerows(rows_out)
sys.stdout.reconfigure(encoding="utf-8")
for r in rows_out:
    print(r["memory_zh"], "|", r["boss_parts"], "|", r["ai_logic_battle"], "|", r["maps"], "|", r["defeat_flag"], "|", r["same_family_parts"])
