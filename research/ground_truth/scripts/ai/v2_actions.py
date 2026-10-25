"""Draft the version-2 action → move table for castle Genichiro (V4 M3 step 1), for the owner to review row by row.

Usage: python -I v2_actions.py

The owner's rule (2026-10-25): a failure is classified by the action that hit the player and the response it needs,
not by the AI chain the boss was playing. Read here as:
- an action that needs its own response (an arrow, a perilous attack: Mikiri, jump, dodge, lightning reversal) is
  classified by that response, whatever combo it is part of;
- an ordinary attack, which is deflected like any other, stays with the move (combo) it is part of, since what the
  player practises there is that combo's rhythm; an animation two moves share is still told apart by what comes
  before and after it, as now.

Inputs: semantic/genichiro_catalog.csv (entries, hits, owner labels), semantic/genichiro_product_moveset.csv (the
current moves), engine/genichiro_attack_windows.csv (attack, projectile and 危 windows). Writes
semantic/genichiro_v2_actions.csv and .md: one row per animation that can hit, with its current move(s), the proposed
version-2 move, the reason and the open question, if any. The proposals are written below as rules with their
reason; none of them is ground truth until the owner approves it. The owner's marks in the .md (审核 ☐ / ✅ / ❌ and
理由) are read back on regeneration, matched by character and animation.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

GT = Path(__file__).resolve().parents[2]
OUT_CSV, OUT_MD = GT / "semantic/genichiro_v2_actions.csv", GT / "semantic/genichiro_v2_actions.md"
PHASES = {"c7100": "1、2", "c7110": "3"}

# Arrows that open or end a combo (the owner chose option B, 2026-10-25): a hit by one is "射箭"; the report may say
# what followed it. 3011 (after the perilous sweep) and 3012 (before the lightning) are in their own question.
OPENING_ARROWS = {3013, 3014, 3017, 3018, 3031, 3034, 3036}
# by character: c7110 uses 3009 for its perilous grab
STANDALONE_SHOTS = {("c7100", 3009): "后撤射击", ("c7100", 3023): "破防射击", ("c7100", 3044): "鹰射（后撤/四连射击）"}
# Perilous attacks by the response they need. The owner's labels name them for c7100; c7110 shares the animation IDs
# and the windows, so its 3025 and 3067 are read the same way (marked as inferred).
MIKIRI = {3025, 3062, 3080}
SWEEP = {3007, 3067}
GRAB = {("c7100", 3020), ("c7110", 3009)}
LIGHTNING = {3039, 3042}

QUESTIONS = {
    "Q1": "危·下段（要跳）要不要也像危·突刺一样，不管在哪一招里都合成一招？涉及 3007（危·下段横扫）和 3067（跳劈后续、三阶段飞渡浮舟里的下段）。",
    "Q2": "一二阶段的危·投技（3020）和三阶段的危·投技（c7110 3009）应对一样，要不要合成一招？",
    "Q3": "巴之雷：3039（危·雷电，射击）和 3042（危·雷电，斩击）都要雷返，要不要合成一招\"巴之雷\"？3043（巴之雷·砸击）也有危字窗口，但你只标了招式名，它是不是雷电、要怎么应对？",
    "Q4": "跳起突刺（c7110 3008）有危字窗口，但还没有你的标签：它是要识破的突刺（并进危·突刺），还是别的应对？",
    "Q5": "单独的射击招式（后撤射击 3009、破防射击 3023、鹰射 3044）保持各自一招，还是也并进\"射箭\"？危·下段横扫之后的那一箭（3011）和巴之雷·射击开头的那一箭（c7110 3012）算\"射箭\"吗？",
    "Q6": "拆完以后几招的名字要改：涨潮只剩前滚劈砍，退潮只剩居合斩，跳劈后续只剩跳劈和上挑，巴之雷·射击只剩雷电（如果 3012 算射箭）。新招式\"射箭\"\"危·突刺（合并后）\"的中英文名字也请你定。",
}


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def proposal(ch, anim, kinds, current, label):
    """(proposed move, reason, question) for one animation."""
    if anim in OPENING_ARROWS:
        return "射箭", "连招开头（或结尾）的箭：被箭打中就算射箭（你选的方案 B）", ""
    if (ch, anim) in STANDALONE_SHOTS:
        return STANDALONE_SHOTS[(ch, anim)], "单独的射击招式，先保持原样", "Q5"
    if anim in (3011, 3012):
        return "射箭（待定）", "接在别的招式前后的箭", "Q5"
    if "peril" in kinds or "bullet" in kinds and anim in LIGHTNING:
        if anim == 3022:
            return "倒地后跳刺危攻击", "只能侧闪、不能识破（你标的），应对不同，单独保留", ""
        if anim in MIKIRI:
            inferred = "（c7110 按一二阶段同编号推断）" if ch == "c7110" and anim != 3062 and anim != 3080 else ""
            return "危·突刺", "要识破的危·突刺，不管在哪一招里都合成一招（你定的原则）" + inferred, ""
        if anim in SWEEP:
            inferred = "（c7110 按一二阶段同编号推断）" if ch == "c7110" and anim == 3067 else ""
            return "危·下段（待定）", "要跳的危·下段" + inferred, "Q1"
        if (ch, anim) in GRAB:
            return "危·投技（待定）", "要躲开的危·投技", "Q2"
        if anim in LIGHTNING:
            return "巴之雷（待定）", "要雷返的危·雷电", "Q3"
        if anim == 3043:
            return "巴之雷·砸击", "有危字窗口，应对待你确认", "Q3"
        if anim == 3008:
            return "跳起突刺", "有危字窗口，应对待你确认", "Q4"
    if len(current) > 1:
        return " / ".join(current), "普通攻击，几招共用这个动画：按前后动作决定是哪一招（同现在）", ""
    return current[0], "普通攻击：还算它所在的那一招", ""


def previous_marks():
    """The owner's 审核 and 理由 cells from the existing .md, by (character, animation)."""
    if not OUT_MD.exists():
        return {}
    marks = {}
    for line in OUT_MD.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| (c71[01]0) \| (\d+) \|([^|]*)\|([^|]*)\|", line)
        if m:
            marks[(m.group(1), m.group(2))] = (m.group(3).strip() or "☐", m.group(4).strip())
    return marks


def main():
    moves_of = defaultdict(list)
    for m in read(GT / "semantic/genichiro_product_moveset.csv"):
        for e in m["catalog_entries"].split():
            moves_of[e].append(m["name_zh"])
    kinds = defaultdict(set)
    for w in read(GT / "engine/genichiro_attack_windows.csv"):
        kinds[(w["character"], int(w["anim"]))].add(w["kind"])
    rows = {}
    for r in read(GT / "semantic/genichiro_catalog.csv"):
        if r["kind"] != "move":
            continue
        labels = dict(x.split(" ", 1) for x in r["owner_labels"].split("；") if " " in x)
        recorded = dict(x.split(":") for x in r["recorded"].split())
        for a in (r["attack_anims"] + " " + r["bullet_anims"]).split():
            anim = int(a.split("(")[0])
            d = rows.setdefault((r["character"], anim), {"entries": [], "moves": [], "label": "", "recorded": "0",
                                                          "hits": a.split("(")[1].rstrip(")") if "(" in a else "飞行物"})
            d["entries"].append(r["entry"])
            d["moves"] += [m for m in moves_of[r["entry"]] if m not in d["moves"]]
            d["label"] = labels.get(str(anim), d["label"])
            d["recorded"] = recorded.get(str(anim), d["recorded"])
    marks = previous_marks()
    out = []
    for (ch, anim), d in sorted(rows.items()):
        k = kinds[(ch, anim)]
        move, reason, q = proposal(ch, anim, k, d["moves"], d["label"])
        kind = "危" if "peril" in k else ("飞行物" if "bullet" in k else "普通")
        mark, why = marks.get((ch, str(anim)), ("☐", ""))
        out.append({"character": ch, "phases": PHASES[ch], "anim": anim, "kind": kind, "hits": d["hits"],
                    "recorded": d["recorded"], "entries": " ".join(d["entries"]), "current_moves": " / ".join(d["moves"]),
                    "owner_label": d["label"], "proposed_move": move, "changed": "否" if move == " / ".join(d["moves"]) else "是",
                    "reason": reason, "question": q, "review_mark": mark, "owner_reason": why})
    fields = list(out[0])
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\r\n")
        w.writeheader()
        w.writerows(out)

    changed = [r for r in out if r["changed"] == "是"]
    md = ["# 版本 2：动作 → 招式对应表（天守阁弦一郎，草稿）", "",
          "由 `scripts/ai/v2_actions.py` 生成。每一行是一个会打中你的动画，以及按版本 2 的原则建议它算哪一招。"
          "**建议不是定论**：请在\"审核\"一栏标 ✅ 或 ❌，有意见写在\"理由\"里，重新生成时会保留。", "",
          "## 原则（你定，2026-10-25）", "",
          "失败按打中你的那个动作和它需要的应对来归类，不再按 AI 选的整套连招归类。具体是：", "",
          "- **需要特别应对的动作**（箭、危字攻击：识破、跳、躲开、雷返）按应对归类，不管它在哪一招里；",
          "- **普通攻击**（照常弹开就行）还算它所在的那一招，因为那里练的是这一招的节奏。几招共用的动画照旧按前后动作区分。", "",
          "## 要你定的问题", ""]
    md += [f"- **{k}**：{v}" for k, v in QUESTIONS.items()]
    md += ["", f"## 改了归类的动画（{len(changed)} 个）", "",
           "| 角色 | 动画 | 审核 | 理由 | 阶段 | 类型 | 现在算 | 建议算 | 依据 | 问题 | 你的标签 | 录到次数 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['character']} | {r['anim']} | {r['review_mark']} | {r['owner_reason']} | {r['phases']} | {r['kind']} | {r['current_moves']} "
           f"| **{r['proposed_move']}** | {r['reason']} | {r['question']} | {r['owner_label'] or '—'} | {r['recorded']} |" for r in changed]
    same = [r for r in out if r["changed"] == "否"]
    md += ["", f"## 归类不变的动画（{len(same)} 个）", "",
           "| 角色 | 动画 | 审核 | 理由 | 阶段 | 类型 | 招式 | 依据 | 问题 | 你的标签 | 录到次数 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    same.sort(key=lambda r: (r["kind"] == "普通", r["character"], r["anim"]))
    md += [f"| {r['character']} | {r['anim']} | {r['review_mark']} | {r['owner_reason']} | {r['phases']} | {r['kind']} | {r['current_moves']} "
           f"| {r['reason']} | {r['question']} | {r['owner_label'] or '—'} | {r['recorded']} |" for r in same]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{len(out)} animations, {len(changed)} reclassified -> {OUT_MD}")


if __name__ == "__main__":
    main()
