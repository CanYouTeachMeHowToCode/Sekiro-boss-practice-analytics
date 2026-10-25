"""Draft the version-2 action → move table for castle Genichiro (V4 M3 step 1), for the owner to review row by row.

Usage: python -I v2_actions.py

The owner's rule (2026-10-25): a failure is classified by the action that hit the player and the response it needs.
As the owner refined it the same day: the M2 moves and their full names stay, and a hit counts for the move whose
main content hit the player; only an action that needs a different response from that main content is classified
apart:
- a plain arrow inside another move (before or after it) is "普通射击"; the standalone shooting moves (后撤射击,
  破防射击, 鹰射) stay as they are;
- a perilous thrust that needs Mikiri (3025, 3080) is 危·突刺 wherever it comes (to be confirmed under the refined
  rule). A perilous sweep, which needs a jump, is never put with a thrust; it stays with its move, as do the grabs and
  the lightning attacks (owner: each needs its own response).
An animation two moves share is told apart by what comes before and after it, as now.

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

# Plain arrows inside another move, before or after its main content (owner, Q5 and Q6, 2026-10-25): a hit by one is
# "普通射击"; the report may say what followed it
PLAIN_ARROWS = {("c7100", a) for a in (3011, 3013, 3014, 3017, 3018, 3031, 3034, 3036)} |     {("c7110", a) for a in (3012, 3013, 3014, 3018, 3031, 3034, 3036)}
# by character: c7110 uses 3009 for its perilous grab
STANDALONE_SHOTS = {("c7100", 3009): "后撤射击", ("c7100", 3023): "破防射击", ("c7100", 3044): "鹰射（后撤/四连射击）"}
# Perilous attacks by the response they need. The owner's labels name them for c7100; c7110 shares the animation IDs
# and the windows, so its 3025 and 3067 are read the same way (marked as inferred).
MIKIRI_IN_OTHER_MOVES = {3025, 3080}

DECIDED = [
    "招式和名字沿用 M2 的版本；被一招的主要内容打中，就算这一招的全名（Q6）。",
    "招式前后附带的普通的箭算\"普通射击\"；单独的射击招式（后撤射击、破防射击、鹰射）各自保持一招（Q5）。",
    "下段危要跳、突刺危要识破，两者一定分开，就算前面的连招完全一样；下段危不跨招式合并，留在各自的招式里（Q1）。",
    "一二阶段的危·投技可以弹开，和三阶段的危·投技不合并（Q2）。",
    "巴之雷的几招都是雷电，但动画和应对不同，各自保持一招（Q3）。",
    "跳起突刺（c7110 3008）是要识破的突刺（Q4）。",
]
QUESTIONS = {
    "A": "需要识破的危·突刺还合并吗？就是把连斩的危·突刺收尾、跳劈后续里的突刺（3025）和完美弹开后的突刺（3080）都算\"危·突刺\"。"
         "我建议合并：M2 有两次就是把这种突刺认错成了别的突刺；而且合并以后，跳劈后续里的突刺和下段就自然分开了（Q1）。",
    "B": "跳起突刺本身就是一招，主要内容就是突刺：它保持\"跳起突刺\"这一招，还是也并进\"危·突刺\"？",
    "C": "新的一类叫什么：\"普通射击\"还是\"射箭\"？英文名呢（我建议 Arrow Shot）？",
}


def read(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def proposal(ch, anim, kinds, current, label):
    """(proposed move, reason, question) for one animation."""
    if (ch, anim) in PLAIN_ARROWS:
        return "普通射击", "招式前后附带的普通的箭（你定，Q5、Q6）", "C"
    if (ch, anim) in STANDALONE_SHOTS:
        return STANDALONE_SHOTS[(ch, anim)], "单独的射击招式，保持一招（你定，Q5）", ""
    if anim in MIKIRI_IN_OTHER_MOVES:
        inferred = "；c7110 的 3025 按一二阶段同编号推断" if ch == "c7110" and anim == 3025 else ""
        return "危·突刺（待你确认）", "要识破的突刺，在别的招式里；和下段危分开（Q1）" + inferred, "A"
    if ch == "c7110" and anim == 3008:
        return "跳起突刺（待定）", "要识破的突刺（你定，Q4）", "B"
    if "peril" in kinds:
        reason = {3007: "下段危，留在自己的招式里（你定，Q1）", 3067: "下段危，留在自己的招式里，按前后动作决定是哪一招（你定，Q1）",
                  3020: "一二阶段的危·投技可以弹开，不和三阶段合并（你定，Q2）", 3009: "三阶段的危·投技，不和一二阶段合并（你定，Q2）",
                  3039: "巴之雷各自保持一招（你定，Q3）", 3042: "巴之雷各自保持一招（你定，Q3）", 3043: "巴之雷各自保持一招（你定，Q3）",
                  3062: "要识破的危·突刺，本来就是这一招", 3022: "只能侧闪、不能识破（你标的），单独一招"}.get(anim, "危字攻击，留在自己的招式里")
        return " / ".join(current), reason, ""
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
          "失败按打中你的那个动作和它需要的应对来归类。招式和名字沿用 M2 的版本，只有应对和这一招主要内容不同的动作才单独归类。", "",
          "## 已定的事", ""]
    md += [f"- {x}" for x in DECIDED]
    md += ["", "## 还要你定的问题", ""]
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
