"""Check the catalog's AI chains against the order of animations in the castle recordings.

Usage: python -I chain_check.py <out.csv> <out.md>

Reads, from research/ground_truth:
    semantic/genichiro_catalog.csv                         the owner-approved chains (the chain column)
    engine/genichiro_castle_tae_classes.csv, deferred/...  the class of every TAE entry (reactions, movement...)
    observations/vanilla/genichiro/*-castle/occurrences.csv every verified occurrence, with its frames

Each chain is turned into, per phase, the animations it can start with, the ones it can end with, and every
"a can be followed by b" step; the only phase condition in the chains (剩余忍杀数 ≤ 1, true in phase 2 only) is
resolved, so 3030 → 3067 is allowed in phase 2 and not in phase 1.

In each recording and phase, the animations that appear in some chain are put in order of their first frame. For
each one, with the previous one before it:
    链内衔接        "previous → this" is a step of some chain
    打断衔接        this is an Interrupt option and its trigger is visible (the rules are in INTERRUPTS, read from the
                    catalog's trigger column); some triggers, such as the player using an item, are not on screen
    拼刀后选招       this starts a Kengeki option, and a clash is visible: he deflected (3100-3103) or an
                    84xx-87xx reaction played in between
    主动选招 / 弹刀 / 被打中后   this starts an Act, Parry / ShootReaction or Damaged option
    对不上          none of the above
For a new option, the previous chain is "打完了" when the previous animation can end some chain, "被打断" when a
reaction (hit_reaction class) played in between or the new option is a Parry, ShootReaction or Damaged one, and
otherwise "中途停下" (an AI condition such as distance may have stopped it; listed for review).
Also lists the chain steps never seen in either recording.
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT = HERE.parent.parent
out_csv, out_md = sys.argv[1:3]
RECS = sorted(p for p in (GT / "observations/vanilla/genichiro").glob("*-castle*") if (p / "occurrences.csv").exists())


def parse(s):
    """Chain text → ("seq", items) | ("alt", [(cond, seq)]) | ("anim", id) | ("empty",)."""
    i = 0

    def ws():
        nonlocal i
        while i < len(s) and s[i] == " ":
            i += 1

    def seq():
        nonlocal i
        items = []
        while True:
            ws()
            if s[i] == "[":
                items.append(alt())
            elif s[i] == "—":
                i += 1
                items.append(("empty",))
            else:
                m = re.match(r"\d+", s[i:])
                assert m, s[i:i + 30]
                items.append(("anim", m.group()))
                i += len(m.group())
            ws()
            if i < len(s) and s[i] == "→":
                i += 1
                continue
            return ("seq", items)

    def alt():
        nonlocal i
        i += 1
        branches = []
        while True:
            j = s.index(":", i)
            cond = s[i:j].strip()
            i = j + 1
            branches.append((cond, seq()))
            ws()
            if s[i] == "｜":
                i += 1
                continue
            assert s[i] == "]", s[i:i + 30]
            i += 1
            return ("alt", branches)

    node = seq()
    assert i == len(s), s[i:]
    return node


def decide(cond, phase):
    """True / False when the condition is fixed in this phase of the castle fight, None when it is not."""
    if cond == "否则":
        return True
    if cond == "剩余忍杀数 ≤ 1":
        return phase == "2"
    return None


def walk(node, phase):
    """(first animations, last animations, can be empty, steps) of a chain node in one phase."""
    kind = node[0]
    if kind == "anim":
        return {node[1]}, {node[1]}, False, set()
    if kind == "empty":
        return set(), set(), True, set()
    if kind == "alt":
        first, last, steps, empty, closed = set(), set(), set(), False, False
        for cond, sub in node[1]:
            d = decide(cond, phase)
            if d is False:
                continue
            f, l, n, e = walk(sub, phase)
            first |= f
            last |= l
            steps |= e
            empty |= n
            if d is True:
                closed = True
                break
        return first, last, empty or not closed, steps
    first, last, empty, steps = set(), set(), True, set()
    for item in node[1]:
        f, l, n, e = walk(item, phase)
        steps |= e | {(x, y) for x in last for y in f}
        first |= f if empty else set()
        last = l | (last if n else set())
        empty = empty and n
    return first, last, empty, steps


catalog = list(csv.DictReader(open(GT / "semantic/genichiro_catalog.csv", encoding="utf-8")))
STEP = defaultdict(set)    # (character, phase, a, b) -> entries
START = defaultdict(set)   # (character, phase, b) -> {(entry, option kind)}
END = defaultdict(set)     # (character, phase, a) -> entries
MEMBERS = defaultdict(set)
for r in catalog:
    node = parse(r["chain"])
    kinds = {re.sub(r"\d+$", "", o.split(":")[1]) for o in r["ai_options"].split("、")}
    for ph in r["phases"].split("、"):
        f, l, _, e = walk(node, ph)
        for a, b in e:
            STEP[(r["character"], ph, a, b)].add(r["entry"])
        for b in f:
            START[(r["character"], ph, b)] |= {(r["entry"], k) for k in kinds}
        for a in l:
            END[(r["character"], ph, a)].add(r["entry"])
        MEMBERS[r["character"]] |= f | l | {x for st in e for x in st}

CLASS = {}
for f in ("engine/genichiro_castle_tae_classes.csv", "deferred/genichiro_castle_tae_deferred.csv"):
    for r in csv.DictReader(open(GT / f, encoding="utf-8")):
        CLASS[(r["character"], r["anim"][-6:].lstrip("0") or "0")] = r["class"]

# Interrupt options: what makes each fire, from the catalog's trigger column. (previous animations, reactions in
# between); a trigger that is not on screen is named in the third field.
INTERRUPTS = {
    ("c7100", "3092"): ({"3063", "3068"}, set(), ""),
    ("c7110", "3092"): ({"3063", "3068"}, set(), ""),
    ("c7100", "3017"): ({"3040", "3092"}, set(), ""),
    ("c7110", "3018"): ({"3040"}, set(), ""),
    ("c7110", "3008"): ({"3040"}, set(), "你使用道具"),
    ("c7110", "3009"): ({"3008"}, set(), ""),
    ("c7100", "3023"): ({"3044"}, set(), "你使用道具"),
    ("c7110", "3080"): (set(), {"8604", "8704"}, ""),
}
PARRY = {"3100", "3101", "3102", "3103"}
# Off-screen triggers the owner confirmed from the recordings (2026-10-15): (recording, time) -> what happened.
CONFIRMED = {
    ("2026-10-09-castle", "1:02.9"): "你喝药或使用道具(你确认)",
    ("2026-10-09-castle", "1:59.9"): "你喝药或使用道具(你确认)",
    ("2026-10-13-castle", "2:05.3"): "你喝药或使用道具(你确认)",
}


def clash(a, between):
    return a in PARRY or any(8400 <= int(x) < 8800 for x in between)


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


rows, seen_steps, reactions = [], set(), []
for rec in RECS:
    occ = list(csv.DictReader(open(rec / "occurrences.csv", encoding="utf-8")))
    for o in occ:
        o["id"], o["ch"] = o["anim"][-6:].lstrip("0") or "0", o["character"][:5]
        o["sf"], o["ef"] = int(o["start_frame"]), int(o["end_frame"])
        o["st"], o["et"] = float(o["start_time"]), float(o["end_time"])
    occ.sort(key=lambda o: (o["sf"], o["ef"]))
    for i, o in enumerate(occ):          # 8604 / 8704: the attack before and the attack after
        if o["id"] in ("8604", "8704"):
            atk = [x for x in occ if x["id"].startswith("30") and len(x["id"]) == 4]
            before = [x for x in atk if x["sf"] < o["sf"]][-1:]
            after = [x for x in atk if x["sf"] > o["sf"]][:1]
            reactions.append((rec.name, mmss(o["st"]), o["phase"], o["id"], before, after))
    prev = None
    for o in occ:
        ch, ph, b = o["ch"], o["phase"], o["id"]
        if b not in MEMBERS.get(ch, ()):
            continue
        if prev is None or prev["phase"] != ph:
            rows.append({"recording": rec.name, "time": mmss(o["st"]), "phase": ph, "character": ch, "prev": "",
                         "anim": b, "gap_s": "", "between": "", "verdict": "阶段开始", "chain": "",
                         "detail": f"第一次读到时已经播到 {o['t_first']} 秒" if float(o["t_first"]) > 0.3 else "",
                         "entries": " ".join(sorted({e for e, _ in START.get((ch, ph, b), ())}))})
            prev = o
            continue
        a = prev["id"]
        between = [x["id"] for x in occ if prev["sf"] < x["sf"] < o["sf"] and x["id"] not in MEMBERS[ch]]
        reaction = [x for x in between if CLASS.get((ch, x)) == "hit_reaction"]
        starts = START.get((ch, ph, b), set())
        kinds = {k for _, k in starts}
        verdict, detail, entries, chain = "", "", set(), ""
        if STEP.get((ch, ph, a, b)):
            verdict, entries = "链内衔接", STEP[(ch, ph, a, b)]
            seen_steps.add((ch, ph, a, b))
        else:
            rule = INTERRUPTS.get((ch, b)) if "Interrupt" in kinds else None
            if rule and (a in rule[0] or set(between) & rule[1]):
                verdict = "打断衔接"
                detail = f"前面是 {a}" if a in rule[0] else "中间有 " + " ".join(sorted(set(between) & rule[1]))
            elif "Kengeki" in kinds and clash(a, between):
                verdict, detail = "拼刀后选招", ("他弹刀 " + a) if a in PARRY else "中间有 " + " ".join(x for x in between if 8400 <= int(x) < 8800)
            elif "Act" in kinds:
                verdict = "主动选招"
            elif kinds & {"Parry", "ShootReaction"}:
                verdict = "弹刀"
            elif "Damaged" in kinds and reaction:
                verdict, detail = "被打中后", "中间有 " + " ".join(reaction)
            elif rule and rule[2]:
                verdict, detail = "打断衔接(触发看不到)", f"可能是{rule[2]};前面是 {a}"
            elif starts:
                verdict, detail = "对不上", "起手所属选项的触发在录像里看不到:" + "、".join(sorted(kinds))
            else:
                verdict, detail = "对不上", "不是任何链的起手,也不是上一个动画的后续"
            entries = {e for e, k in starts}
            if verdict != "对不上":
                if END.get((ch, ph, a)):
                    chain = "打完了"
                elif reaction or kinds & {"Parry", "ShootReaction", "Damaged"} and verdict in ("弹刀", "被打中后"):
                    chain = "被打断"
                else:
                    chain = "中途停下"
        if verdict == "打断衔接(触发看不到)" and (rec.name, mmss(o["st"])) in CONFIRMED:
            verdict, detail = "打断衔接(你确认)", CONFIRMED[(rec.name, mmss(o["st"]))]
        rows.append({"recording": rec.name, "time": mmss(o["st"]), "phase": ph, "character": ch, "prev": a, "anim": b,
                     "gap_s": f"{o['st'] - prev['et']:+.2f}", "between": " ".join(between), "verdict": verdict,
                     "chain": chain, "detail": detail, "entries": " ".join(sorted(entries))})
        prev = o

FIELDS = ["recording", "time", "phase", "character", "prev", "anim", "gap_s", "between", "verdict", "chain", "detail", "entries"]
with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\r\n")
    w.writeheader()
    w.writerows(rows)

# --- report -----------------------------------------------------------------------------------------------------
trans = [r for r in rows if r["verdict"] != "阶段开始"]
by_verdict = Counter(r["verdict"] for r in trans)
by_chain = Counter(r["chain"] for r in trans if r["chain"])
all_steps = {k: v for k, v in STEP.items()}
unseen = defaultdict(list)
for (ch, ph, a, b), ents in sorted(all_steps.items(), key=lambda kv: (kv[0][0], kv[0][1], int(kv[0][2]), int(kv[0][3]))):
    if (ch, ph, a, b) not in seen_steps:
        unseen[(a, b, ch)].append(ph)


def line(r):
    return (f"| {r['recording'][:10]} {r['time']} | {r['phase']} | {r['prev']} → {r['anim']} | {r['gap_s']} | {r['between'] or '—'} "
            f"| {r['verdict']} | {r['chain'] or '—'} | {r['detail'] or '—'} | {r['entries'] or '—'} |")


HEAD = "| 录像和时间 | 阶段 | 衔接 | 间隔(秒) | 中间的其他动画 | 结论 | 上一条链 | 说明 | 目录条目 |"
SEP = "|---|---|---|---|---|---|---|---|---|"
md = ["# 用录像核对 AI 推出的招式链", "",
      "由 `scripts/ai/chain_check.py` 生成,逐条数据在 `chain_check.csv`。依据是你审核通过的招式目录 `semantic/genichiro_catalog.md` 的动画链,"
      f"和 {len(RECS)} 次录像里经过校验的每一次动画({', '.join(p.name for p in RECS)})。", "",
      "## 方法", "",
      "- 把每条链拆成\"哪些动画可以起手、哪些可以收尾、哪个动画后面可以接哪个\",按阶段分别算。链里唯一和阶段有关的条件是\"剩余忍杀数 ≤ 1\"(只在二阶段成立)。",
      "- 每次录像的每个阶段,把出现在某条链里的动画按开始帧排好,逐个看它和前一个的关系:",
      "  - **链内衔接**:前一个 → 这一个,是某条链里的一步;",
      "  - **打断衔接**:这一个是打断选项,而且触发条件在录像里看得到(比如 3092 前面是 3068);",
      "  - **拼刀后选招**:这一个是拼刀后选项的起手,而且看得到拼刀:他弹刀(3100–3103),或者中间有 84xx–87xx 的拼刀反应;",
      "  - **主动选招 / 弹刀 / 被打中后**:这一个是主动选招、弹刀或被打中时选项的起手;",
      "  - **对不上**:以上都不是。",
      "- 换了新选项时,再看上一条链:**打完了**(上一个动画可以收尾)、**被打断**(中间有受击或拼刀反应,或者新选项是弹刀、被打中时的反应)、"
      "**中途停下**(都没有,可能是距离之类的 AI 条件让链停了)。",
      "- 只能核对\"录到的衔接是不是某个分支允许的\"。距离、躯干、随机数在录像里看不到,所以核对不了\"这一次为什么走这个分支\"。", "",
      "## 结果", "",
      f"共 {len(trans)} 次衔接(另有 {len(rows) - len(trans)} 个阶段开始)。", "",
      "| 结论 | 次数 |", "|---|---|"]
for v in ["链内衔接", "打断衔接", "打断衔接(你确认)", "打断衔接(触发看不到)", "拼刀后选招", "主动选招", "弹刀", "被打中后", "对不上"]:
    md.append(f"| {v} | {by_verdict.get(v, 0)} |")
md += ["", "换新选项时上一条链的情况:", "", "| 上一条链 | 次数 |", "|---|---|"]
for v in ["打完了", "被打断", "中途停下"]:
    md.append(f"| {v} | {by_chain.get(v, 0)} |")

bad = [r for r in trans if r["verdict"] == "对不上"]
md += ["", f"### 对不上({len(bad)} 次)", ""]
md += ([HEAD, SEP] + [line(r) for r in bad]) if bad else ["没有。每一次衔接都能用某条 AI 链、某个选项的起手或某个打断解释。"]
hidden = [r for r in trans if r["verdict"] in ("打断衔接(触发看不到)", "打断衔接(你确认)")]
md += ["", f"### 打断衔接,触发在录像里看不到({len(hidden)} 次)", "",
       "这些打断的触发之一是你使用道具,开发者菜单的叠加层不显示玩家的动作。标着\"你确认\"的,是你看过录像确认的(2026-10-15)。", ""]
md += [HEAD, SEP] + [line(r) for r in hidden]
stop = [r for r in trans if r["chain"] == "中途停下"]
md += ["", f"### 链中途停下,看不到原因({len(stop)} 次)", "",
       "上一条链没打完、中间也没有受击或拼刀反应就换了选项。目录里有的链每一段都要你还在距离内才接下一段(比如 P12-01),所以这些多半是距离条件;"
       "也可能是 AI 文件以外的东西让链停了。", ""]
md += [HEAD, SEP] + [line(r) for r in stop]
md += ["", "这三次都断在 AI 要求你还在一定距离内才接下一段的地方,而且他随后都走了几步(405010),换了一个适合更远距离的选项:", "",
       "- 3014 → 3006:Act15 里 3014 带约 7 米的距离条件,不满足就不接 3015;3006 是 ≥ 5 米时才选的招;",
       "- 3001 → 3006、3000 → 3016:三阶段 Act01 每一段都带 3.4–5 米的距离条件(和目录 P3-01 的说明一致)。", ""]
starts = [r for r in rows if r["verdict"] == "阶段开始"]
md += ["", "### 每个阶段的第一招", "", "| 录像 | 阶段 | 第一个动画 | 时间 | 可能的目录条目 | 说明 |", "|---|---|---|---|---|---|"]
md += [f"| {r['recording'][:10]} | {r['phase']} | {r['anim']} | {r['time']} | {r['entries'] or '—'} | {r['detail'] or '—'} |" for r in starts]
md += ["", "目录里一阶段的开场第一招是 3014 → 3015(P12-10,权重 600)。三阶段 AI 在开场时给 3008(Act20)权重 30000,"
       "但你倒地时(特效 109031 或 110125)3043(Act18)的权重是 10¹²,会压过它。二阶段没有固定的第一招。", "",
       "第一次录像的三阶段从 3043 开始,但那次录像 276.2–324.9 秒没有叠加层(转阶段过场,最后几秒你开着装备菜单),3043 第一次读到时已经播了 0.95 秒,"
       "所以看不到这一阶段真正的第一招,不算和目录矛盾。", ""]
md += ["", "### 8604 / 8704 前后的攻击:3080 的触发", "",
       "三阶段 AI(711000)在他身上出现特效 5030 时出 3080。TAE 里只有 8604 会加 5030(1.03 秒),8704 完全借用 8604。"
       "c7110 里带攻击判定 292 的动画是 3028、3032、3038、3041 和 8603(3092 完全借用它);一二阶段的 c7100 是 3028、3041、3049、8603。"
       "录像里 8604 / 8704 每次都在这几个动画之后:", "",
       "| 录像和时间 | 阶段 | 反应 | 之前的攻击 | 之后的攻击 |", "|---|---|---|---|---|"]
for rec, t, ph, rid, before, after in reactions:
    md.append(f"| {rec[:10]} {t} | {ph} | {rid} | " + (" ".join(f"{x['id']} ({mmss(x['st'])})" for x in before) or "—") + " | "
              + (" ".join(f"{x['id']} ({mmss(x['st'])})" for x in after) or "—") + " |")
md += ["", "**你确认(2026-10-15)**:完美弹开 3032 之后他会接 3080,不完美弹开不会。录像里三阶段的两次 8604 / 8704 都在你弹开 3032 之后"
       "(3032 是三阶段危攻击后续追击 P3-17 的第三种结尾),和 Fandom 对第三种结尾的描述“上挑,被弹开后接延迟危·突刺”一致;"
       "完美弹开飞渡浮舟之后的 3080 在录像里还没有出现过。已写进目录 P3-17、P3-30 的触发和说明,决策表 A03 加上了 P3-30(A21 不变)。", ""]
intr = [r for r in trans if r["verdict"] == "打断衔接"]
md += ["", f"### 看得到触发的打断衔接({len(intr)} 次)", "", HEAD, SEP] + [line(r) for r in intr]
md += ["", "### 两次录像都没录到的链内衔接", "",
       "下面这些\"a → b\"是 AI 链里的一步,但录像里一次都没出现。按动画和角色合并,括号里是阶段。", "",
       "| 衔接 | 角色 | 阶段 | 目录条目 |", "|---|---|---|---|"]
for (a, b, ch), phs in unseen.items():
    ents = sorted({e for ph in phs for e in STEP[(ch, ph, a, b)]})
    md.append(f"| {a} → {b} | {ch} | {'、'.join(phs)} | {' '.join(ents)} |")
md.append("")
with open(out_md, "w", encoding="utf-8", newline="") as fh:
    fh.write("\r\n".join(md))

sys.stdout.reconfigure(encoding="utf-8")
print(dict(by_verdict), dict(by_chain), f"unseen steps: {len(unseen)}")
