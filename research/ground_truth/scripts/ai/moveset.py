"""The product's Genichiro moveset after the owner's step-8 decisions (V4 M6).

Usage: python -I moveset.py <out.csv> <out.md>

Reads, from research/ground_truth:
    semantic/genichiro_product_decisions.csv   the owner-reviewed decision table (names, merges, approvals)
    semantic/genichiro_catalog.csv             the approved catalog (phases, animations, evidence)
and backend/seed/bosses.json for the current product moves.

RESOLVE below turns the decision table into product moves: every decision row goes to exactly one product move (a
row the owner merged goes to the move it was merged into), and the script checks that every catalog move ends up in
at least one product move. Names come from the owner's 招式名称 cells ("中文 / English"); NAME_FIX lists the corrections
proposed for obvious typos, each waiting for the owner. Nothing here changes the product; plan step 8 does that.
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT = HERE.parent.parent
REPO = GT.parent.parent
out_csv, out_md = sys.argv[1:3]

dec = {r["key"]: r for r in csv.DictReader(open(GT / "semantic/genichiro_product_decisions.csv", encoding="utf-8"))}
cat = {r["entry"]: r for r in csv.DictReader(open(GT / "semantic/genichiro_catalog.csv", encoding="utf-8")) if r["kind"] == "move"}
seed = next(b for b in json.load(open(REPO / "backend/seed/bosses.json", encoding="utf-8")) if b["id"] == "genichiro-ashina")
current = {}
for p in seed["phases"]:
    for m in p["moves"]:
        current.setdefault(m["id"], {"name": m["name"], "name_zh": m["name_zh"], "phases": set()})["phases"].add(p["phase_number"])

# product move slug -> decision rows it is made of (the first row gives the name). From the owner's review:
# A19 iaijutsu ❌ "和A20重复"; B12 → B04, B19/B24 → B18, B23 → B21 (❌ with "并入"); B03/B05/B09-B11/B15-B17/B20 follow
# the A row they point to; B06 → A16, B13 → A06, B14 → A21 (owner, 2026-10-15); B16 → A20, since A19 is A20.
RESOLVE = {
    "perilous-attack-follow-up": ["A01"],
    "perilous-attack-follow-up-phase-2": ["A02"],
    "perilous-attack-follow-up-phase-3": ["A03"],
    "perilous-grab": ["A04"],
    "closing-tide": ["A05", "B09", "B10", "B11"],
    "floating-passage": ["A06", "B13"],
    "guard-breaking-shot": ["A07"],
    "hawk-shot": ["A08"],
    "two-hit-combo": ["A09"],
    "deaths-thrust": ["A10"],
    "perilous-grab-phase-3": ["A11"],
    "lightning-of-tomoe-slash": ["A12"],
    "lightning-of-tomoe-smash": ["A13"],
    "perilous-attack": ["A14", "B17"],
    "perilous-thrust": ["A15", "B20"],
    "perilous-sweep": ["A16", "B06", "B22"],
    "advance": ["A17", "B03"],
    "chasing-slice": ["A18", "B05"],
    "receding-tide": ["A20", "A19", "B15", "B16"],
    "floating-passage-phase-3": ["A21", "B14"],
    "lightning-of-tomoe-shot": ["A22"],
    "slash-combo": ["B01"],
    "horizontal-slash": ["B04", "B12"],
    "backstep-shot": ["B08"],
    "counter-slash": ["B18", "B19", "B24"],
    "deflect-counter-slash": ["B21", "B23"],
}
# Product moves that cover only some phases of their catalog entries: P12-20 is one AI chain for phases 1-2 whose
# ending depends on the phase, and the product keeps one move per phase (the owner's names say 一阶段 / 二阶段).
PHASES = {"perilous-attack-follow-up": ["1"], "perilous-attack-follow-up-phase-2": ["2"]}
REMOVED = {"iaijutsu": ("receding-tide", "A19 你判为和 A20 重复:居合斩是退潮的后半段,并入退潮")}
# Proposed corrections of obvious typos in the owner's names; each needs the owner's OK.
NAME_FIX = {
    "perilous-attack-follow-up-phase-2": (None, "Phase 2 Perilous Attack Follow Up (Thrust/Sweep)",
                                          "英文写成了 Phase 1,末尾多一个括号"),
    "perilous-attack-follow-up-phase-3": ("三阶段跳劈后续（突刺危/下段危/上挑）", "Phase 3 Perilous Attack Follow Up (Thrust/Sweep/Upward Slash)",
                                          "中文多一个空格;英文末尾多一个括号,而且第三种结尾中文是“上挑”,英文却是 Leaping Slam"),
    "perilous-sweep": (None, "Perilous Sweep (Follow-up Shot Available)", "英文末尾多一个括号"),
    "hawk-shot": (None, "Hawk Shot (Step-back/4 Arrow Shot)", "英文用了全角括号"),
    "receding-tide": (None, "Receding Tide (Bow into Iaijutsu)", "Laijutsu 应为 Iaijutsu"),
}
NOTES = {
    "perilous-grab": "加上应对方法:1. 完美弹反 2. 向后垫步躲开(你在 A04 写的)",
    "floating-passage": "描述里写明:二阶段打到一半、你在 4.1 米外时改射一箭(射箭取消 3017)",
    "floating-passage-phase-3": "描述里写明:3040 打完第 4 刀时你在 11 米外改射两箭(3018);5.5–11 米时改出死亡突刺(见 deaths-thrust)",
    "perilous-attack-follow-up-phase-3": "第三种结尾 3032 被完美弹开后接突刺 3080(P3-30,和三阶段飞渡浮舟共用)",
}


def split_name(s):
    """"中文 / English" -> (中文, English): split at the first slash followed by a Latin letter."""
    m = re.search(r"\s*/\s*(?=[A-Za-z])", s)
    return (s[:m.start()].strip(), s[m.end():].strip()) if m else (s.strip(), "")


rows, seen = [], {}
for slug, keys in RESOLVE.items():
    for k in keys:
        assert k in dec, k
        assert k not in seen, (k, seen.get(k))
        seen[k] = slug
    entries = list(dict.fromkeys(e for k in keys for e in dec[k]["catalog_entries"].split()))
    phases = PHASES.get(slug) or sorted({p for e in entries for p in cat[e]["phases"].split("、")})
    first = dec[keys[0]]
    name_zh, name_en = split_name(first["owner_name"]) if first["owner_name"] else ("", "")
    cur = current.get(slug)
    if not name_zh and cur:
        name_zh, name_en = cur["name_zh"], cur["name"]
    fix = NAME_FIX.get(slug)
    if fix:
        name_zh, name_en = fix[0] or name_zh, fix[1] or name_en
    changes = []
    if not cur:
        changes.append("新增")
    else:
        if (name_zh, name_en) != (cur["name_zh"], cur["name"]):
            changes.append("改名")
        added = sorted(set(map(int, phases)) - cur["phases"])
        removed = sorted(cur["phases"] - set(map(int, phases)))
        if added:
            changes.append("加阶段 " + "、".join(map(str, added)))
        if removed:
            changes.append("去掉阶段 " + "、".join(map(str, removed)))
    absorbed = [s for s, (to, _) in REMOVED.items() if to == slug]
    if absorbed:
        changes.append("并入 " + "、".join(absorbed))
    ev = {cat[e]["evidence"] for e in entries}
    rows.append({"slug": slug, "name_zh": name_zh, "name_en": name_en, "phases": "、".join(phases),
                 "catalog_entries": " ".join(entries), "decision_rows": " ".join(keys),
                 "evidence": ev.pop() if len(ev) == 1 else "部分运行观察", "change": "；".join(changes) or "不变",
                 "name_fix": fix[2] if fix else "", "note": NOTES.get(slug, "")})

assert set(seen) == set(dec), set(dec) - set(seen)
assert {e for r in rows for e in r["catalog_entries"].split()} == set(cat)
assert set(current) - set(RESOLVE) == set(REMOVED), set(current) - set(RESOLVE)

FIELDS = list(rows[0])
with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)

new = [r for r in rows if r["change"] == "新增"]
md = ["# 第 8 步:产品里的弦一郎招式清单(按你的决定整理)", "",
      "由 `scripts/ai/moveset.py` 从你审完的决策表 `genichiro_product_decisions.md` 生成,数据在 `genichiro_product_moveset.csv`。"
      "这是改种子数据(`backend/seed/bosses.json`)的依据;产品现在还没有改。", "",
      f"- 现有 {len(current)} 个招式 → 改完后 {len(rows)} 个:删掉 {len(REMOVED)} 个,新增 {len(new)} 个。",
      f"- 目录里的 {len(cat)} 个招式全部对上了产品招式;P3-30(完美弹开后的突刺 3080)同时属于两个招式。",
      "- 新增招式的 slug 是我起的,你可以改。新增招式和改了含义的招式,描述、预兆、应对方法要另外定(wiki 没有的不编)。", "",
      "## 招式", "",
      "| slug | 中文名 | 英文名 | 阶段 | 改动 | 目录条目 | 决策表行 | 证据 | 备注 |",
      "|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| `{r['slug']}` | {r['name_zh']} | {r['name_en']} | {r['phases']} | {r['change']} | {r['catalog_entries']} "
              f"| {r['decision_rows']} | {r['evidence']} | {r['note'] or '—'} |")
md += ["", "## 删掉的招式", "", "| slug | 并入 | 原因 |", "|---|---|---|"]
md += [f"| `{s}` | `{to}` | {why} |" for s, (to, why) in REMOVED.items()]
md += ["", "已有练习记录指向这些招式的,迁移到并入的招式(CLAUDE.md 第 45 节)。数据库对招式删除有约束,有记录指向时删不掉,所以迁移必须在删除之前。", "",
       "## 名字里的笔误(待你确认)", "", "上面的表已经按建议改了;你不同意的话告诉我。", "", "| slug | 你写的 | 建议改成 | 原因 |", "|---|---|---|---|"]
for r in rows:
    if r["name_fix"]:
        orig = dec[RESOLVE[r["slug"]][0]]["owner_name"]
        md.append(f"| `{r['slug']}` | {orig} | {r['name_zh']} / {r['name_en']} | {r['name_fix']} |")
md.append("")
with open(out_md, "w", encoding="utf-8", newline="") as fh:
    fh.write("\r\n".join(md))

sys.stdout.reconfigure(encoding="utf-8")
print(f"{len(rows)} product moves ({len(new)} new), removed {len(REMOVED)}; every decision row and catalog move placed")
