"""Find every placed Genichiro (c7100 / c7110) in the game and what each placement is wired to.

Usage: python -I encounters.py <decompiled_ai_dir> <out.json>

Game files are read (read-only) from game_dir in research/ground_truth/local.config:
  map/mapstudio/*.msb.dcx              enemy parts named c7100_* / c7110_*: entity ID, NpcThinkParam, NpcParam, position
  param/gameparam/gameparam.parambnd   NpcThinkParam row -> AI script number; NpcParam row -> boss SpEffects
  event/*.emevd.dcx                    2003[11] (boss health bar): which event file shows a bar for the entity, and its name ID
  msg/engus|zhocn/item.msgbnd.dcx      NPC名.fmg: the name shown on that bar
For each NpcParam row, the script lists which of the "boss has SpEffect X" checks used by Genichiro's AI scripts
(found in <decompiled_ai_dir>/*_battle.txt) are present in that row.
Part layout (Sekiro MSB, enemy part): position at +0x20, entity ID at +0x23C, think/NPC param at +0x298/+0x29C,
measured on m11_01 and checked here against the param tables.
The encounter label of each placement is Claude's reading of this evidence (status: proposed).
"""
import json
import os
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "engine"))
sys.path.insert(0, str(HERE))
from bnd_names import LOCAL_CONFIG, read_dcx  # noqa: E402
import configparser  # noqa: E402
import emevd  # noqa: E402
from params import load_bnd, rows  # noqa: E402

ai_dir, out_path = sys.argv[1], sys.argv[2]
cfg = configparser.ConfigParser()
cfg.read(LOCAL_CONFIG, encoding="utf-8")
GAME = Path(cfg["paths"]["game_dir"])

LABELS = {  # entity -> (encounter, evidence summary); proposals for the project owner to confirm
    1110800: ("天守阁 苇名弦一郎 一、二阶段", "m11_01 天守阁顶;事件 11115810 开战;两次忍杀后事件 11115820 播转场并换成 1110801"),
    1110801: ("天守阁 巴流 苇名弦一郎 三阶段", "m11_01 与 1110800 同位置;由事件 11115820 启用"),
    1110890: ("心中的弦一郎 第一段 (c7100)", "m11_01 天守阁顶,与正式战同位置;只由回忆事件文件 m11_01_71_01 启用;血条名 907103"),
    1110891: ("心中的弦一郎 第二段 (c7110)", "同上;血条名 907103"),
    1120800: ("序章 苇名弦一郎", "m11_02 芦苇地;NpcParam 带 200051(在 AI 里关掉一批选项);血条名 907101;战后播过场 11020000/11020001"),
    1120830: ("剑圣战 第一阶段 巴流 苇名弦一郎", "m11_02 芦苇地;NpcParam 带 3711500;同一地图接着是 1120860 剑圣 苇名一心"),
    1100727: ("非战斗的演出摆放", "m11_00;NpcThinkParam=1,没有战斗 AI;没有血条;由模板事件 11105741 以参数 (1100726, 1100727, 0, 21001) 启动"),
}


def bnd_files(b):
    count = struct.unpack_from("<I", b, 0x0C)[0]
    esz = struct.unpack_from("<Q", b, 0x20)[0]
    out = {}
    for i in range(count):
        off = 0x40 + i * esz
        size = struct.unpack_from("<Q", b, off + 0x08)[0]
        doff = struct.unpack_from("<I", b, off + 0x18)[0]
        noff = struct.unpack_from("<I", b, off + 0x20)[0]
        e = noff
        while b[e:e + 2] != b"\0\0":
            e += 2
        out[b[noff:e].decode("utf-16-le").split("\\")[-1]] = b[doff:doff + size]
    return out


def fmg(b):
    groups = struct.unpack_from("<i", b, 0x0C)[0]
    soff = struct.unpack_from("<q", b, 0x18)[0]
    out = {}
    for g in range(groups):
        idx, first, last = struct.unpack_from("<iii", b, 0x28 + 16 * g)
        for k, i in enumerate(range(first, last + 1)):
            o = struct.unpack_from("<q", b, soff + 8 * (idx + k))[0]
            if o:
                e = o
                while b[e:e + 2] != b"\0\0":
                    e += 2
                out[i] = b[o:e].decode("utf-16-le")
    return out


def utf16_at(b, o):
    e = o
    while b[e:e + 2] != b"\0\0":
        e += 2
    return b[o:e].decode("utf-16-le")


# ---- params
P = load_bnd(read_dcx(GAME / "param/gameparam/gameparam.parambnd.dcx"))
think, _ = rows(P["NpcThinkParam.param"])
npc, npc_size = rows(P["NpcParam.param"])
gates = set()
for f in os.listdir(ai_dir):
    if f.endswith("_battle.txt"):
        gates |= {int(x) for x in re.findall(r"HasSpecialEffectId\(TARGET_SELF, (\d+)\)", open(os.path.join(ai_dir, f), encoding="utf-8").read())}

# ---- names
names = {}
for lang in ("engus", "zhocn"):
    for n, b in bnd_files(read_dcx(GAME / f"msg/{lang}/item.msgbnd.dcx")).items():
        if n.startswith("NPC"):
            for k, v in fmg(b).items():
                names.setdefault(k, {})[lang] = v

# ---- map parts
parts = []
for f in sorted(os.listdir(GAME / "map/mapstudio")):
    if not f.endswith(".msb.dcx"):
        continue
    b = read_dcx(GAME / "map/mapstudio" / f)
    for model in ("c7100_", "c7110_"):
        pat = model.encode("utf-16-le")
        o = b.find(pat)
        while o != -1:
            start = next((s for s in range(o - 0x400, o, 8) if struct.unpack_from("<q", b, s)[0] == o - s), None)
            if start is not None:
                ent = struct.unpack_from("<i", b, start + 0x23C)[0]
                t, n = struct.unpack_from("<ii", b, start + 0x298)
                pos = struct.unpack_from("<3f", b, start + 0x20)
                assert t in think or t in (0, 1), (f, t)
                assert n in npc, (f, n)
                ints = struct.unpack_from(f"<{npc_size // 4}i", npc[n], 0)
                parts.append({
                    "map": f.split(".")[0], "part": utf16_at(b, o), "entity": ent,
                    "think_param": t, "ai_battle_goal": struct.unpack_from("<i", think[t], 4)[0] if t in think else None,
                    "npc_param": n, "boss_spEffects_checked_by_ai": sorted(g for g in gates if g in ints),
                    "position": [round(v, 1) for v in pos],
                })
            o = b.find(pat, o + 2)

# ---- boss bars
ents = {p["entity"] for p in parts}
bars = {}
for f in sorted(os.listdir(GAME / "event")):
    if not f.endswith(".emevd.dcx"):
        continue
    tmp = Path(out_path).with_suffix(".emevd.tmp")
    tmp.write_bytes(read_dcx(GAME / "event" / f))
    for ev in emevd.load(str(tmp)):
        for x in ev["instrs"]:
            if x["bank"] == 2003 and x["id"] == 11 and len(x["args"]) >= 4 and x["args"][1] in ents:
                bars.setdefault(x["args"][1], set()).add((f.split(".")[0], x["args"][3]))
    tmp.unlink()

for p in parts:
    p["boss_bars"] = [{"event_file": ef, "name_id": nid, "name": names.get(nid, {})} for ef, nid in sorted(bars.get(p["entity"], ()))]
    label, evidence = LABELS.get(p["entity"], ("未识别", ""))
    p["encounter_proposed"] = label
    p["evidence"] = evidence

json.dump({"status": "encounter labels proposed by Claude; the project owner confirms", "ruleset": "vanilla",
           "game_version": "1.06", "placements": parts}, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
sys.stdout.reconfigure(encoding="utf-8")
for p in parts:
    print(p["map"], p["part"], p["entity"], "AI", p["ai_battle_goal"], "npc", p["npc_param"], p["boss_spEffects_checked_by_ai"],
          [(b["name_id"], b["name"].get("zhocn")) for b in p["boss_bars"]], "->", p["encounter_proposed"])
