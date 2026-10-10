"""Draw the move-selection logic of a decompiled battle goal as Markdown: Mermaid flowcharts and trees.

Usage: python -I ai_flowchart.py <decompiled_battle.txt> <title> >> out.md

Input is the pseudo-Lua written by lua50_decompile.py. Output, for one battle goal:
  1. a Mermaid flowchart of Activate: the decision ladder and the weight each branch gives to each ActNN;
  2. the adjustments Activate makes after the ladder (cooldown-style overrides);
  3. a tree of Kengeki_Activate (the choice after a deflect/clash) and of Interrupt (reactions to triggers);
  4. a table: each Act/Kengeki function and the animations it requests, in order, with its inner branches.
Conditions are shown with readable names for the few values whose meaning is plain from the call
(distance, HP, posture/SP, remaining deathblows, random rolls); special-effect, timer and counter numbers are
kept as numbers because their meaning is not known.
"""
import re
import sys

ACT_LIKE = re.compile(r"^Goal\.(Act\d+|Kengeki\d+|Parry|Damaged|ShootReaction)$")


# ----------------------------------------------------------------------------- parsing
def split_functions(text):
    funcs = {}
    for block in re.split(r"(?m)^-- function #\d+: ", text)[1:]:
        name = block.split("  (", 1)[0].strip()
        lines = block.splitlines()[2:]                  # drop header and `function(...)`
        while lines and lines[-1].strip() in ("", "end"):
            last = lines.pop()
            if last.strip() == "end":
                break
        funcs[name] = lines
    return funcs


GOTO = re.compile(r"goto (L\d+)")


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


def block_end(lines, i, indent, end):
    """First line index at or after i (below end) that leaves the block at this indent."""
    while i < end:
        s = lines[i].strip()
        if s and not s.startswith("::") and indent_of(lines[i]) < indent:
            return i
        i += 1
    return end


def find_label(lines, i, end, label):
    for k in range(i, end):
        if lines[k].strip() == f"::{label}::":
            return k
    return None


def exit_label(body):
    """The label a block always leaves through at its end (a final goto, or an if/else whose every branch
    ends in a goto to the same label), else None."""
    if not body:
        return None
    kind, x = body[-1]
    if kind == "stmt":
        m = GOTO.fullmatch(x)
        return m.group(1) if m else None
    if kind == "if" and x[-1][0] is None:
        labels = {exit_label(b) for _, b in x}
        return labels.pop() if len(labels) == 1 and None not in labels else None
    return None


def strip_gotos(items):
    out = []
    for kind, x in items:
        if kind == "stmt" and GOTO.fullmatch(x):
            continue
        out.append((kind, [(c, strip_gotos(b)) for c, b in x]) if kind == "if" else (kind, x))
    return out


def parse_block(lines, i, indent, end=None):
    """Parse one indented block into ("stmt", s) / ("label", L) / ("if", [(cond or None, items)]).
    An `if` that leaves through a forward goto (and has no else) takes the statements it jumps over as its
    else branch, so "if C then X goto L end; Y; ::L::" reads as "if C then X else Y"."""
    end = len(lines) if end is None else end
    items = []
    while i < end:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
            continue
        if s.startswith("::"):
            items.append(("label", s.strip(":")))
            i += 1
            continue
        if indent_of(line) < indent or s == "end" or s == "else" or (s.startswith("elseif ") and s.endswith(" then")):
            break
        single = re.fullmatch(r"if (.+) then goto (L\d+) end", s)
        if s.startswith("if ") and s.endswith(" then"):
            branches = []
            body, i = parse_block(lines, i + 1, indent + 4, end)
            branches.append((s[3:-5], body))
            while i < end:
                t = lines[i].strip()
                if t.startswith("elseif ") and t.endswith(" then"):
                    body, i = parse_block(lines, i + 1, indent + 4, end)
                    branches.append((t[7:-5], body))
                elif t == "else":
                    body, i = parse_block(lines, i + 1, indent + 4, end)
                    branches.append((None, body))
                elif t == "end":
                    i += 1
                    break
                else:
                    i += 1
            jump = exit_label(branches[0][1]) if len(branches) == 1 else None
            if jump:
                stop = block_end(lines, i, indent, end)
                j = find_label(lines, i, stop, jump)
                rest, _ = parse_block(lines, i, indent, j if j is not None else stop)
                branches = [branches[0], (None, rest)]
                i = j if j is not None else stop
            items.append(("if", branches))
            continue
        if single:
            i += 1
            stop = block_end(lines, i, indent, end)
            j = find_label(lines, i, stop, single.group(2))
            rest, _ = parse_block(lines, i, indent, j if j is not None else stop)
            items.append(("if", [(single.group(1), [("stmt", "<skip>")]), (None, rest)]))
            i = j if j is not None else stop
            continue
        items.append(("stmt", s))
        i += 1
    return items, i


def parse_function(lines):
    items, _ = parse_block(lines, 0, 4)
    return strip_gotos(items)


# ----------------------------------------------------------------------------- humanizing
GETTERS = [
    (r"GetDist\(TARGET_ENE_0\)", "距离"), (r"GetDist_Parry\(\w+\)", "弹刀距离"), (r"GetSpRate\(TARGET_SELF\)", "SP比例"),
    (r"GetSp\(TARGET_SELF\)", "SP"), (r"GetHpRate\(TARGET_SELF\)", "HP比例"), (r"GetNinsatsuNum\(\)", "剩余忍杀数"),
    (r"GetNinsatsuMaxNum\(\)", "忍杀总数"), (r"ReturnKengekiSpecialEffect\(\w+\)", "拼刀类型"),
    (r"GetSpecialEffectActivateInterruptType\(0\)", "触发特效"), (r"GetSpecialEffectInactivateInterruptType\(0\)", "解除特效"),
    (r"GetRandam_Int\((\d+), (\d+)\)", r"随机\1-\2"), (r"GetEventRequest\(\)", "事件请求"),
    (r"HasSpecialEffectId\(TARGET_ENE_0, (\w+)\)", r"玩家有特效\1"), (r"HasSpecialEffectId\(TARGET_SELF, (\w+)\)", r"Boss有特效\1"),
]
DIRS = {"F": "前方", "B": "后方", "L": "左方", "R": "右方"}


def reg_names(lines):
    assigns = {}
    for line in lines:
        m = re.match(r"\s*(r\d+) = (.+)$", line)
        if m:
            assigns.setdefault(m.group(1), []).append(m.group(2))
    names = {}
    for reg, vals in assigns.items():
        if len(vals) != 1:
            continue
        for pat, label in GETTERS:
            m = re.fullmatch(r"(?:p\d:)?" + pat, vals[0])
            if m:
                names[reg] = m.expand(label)
    return names


def human(cond, regs):
    s = cond
    s = re.sub(r"p\d[.:]HasSpecialEffectId\(TARGET_ENE_0, (\w+)\)", r"玩家有特效\1", s)
    s = re.sub(r"p\d[.:]HasSpecialEffectId\(TARGET_SELF, (\w+)\)", r"Boss有特效\1", s)
    s = re.sub(r"p\d:IsInsideTarget\(TARGET_ENE_0, AI_DIR_TYPE_(\w), (\d+)\)", lambda m: f"玩家在{DIRS.get(m.group(1), m.group(1))}{m.group(2)}°内", s)
    s = re.sub(r"p\d:IsFinishTimer\((\d+)\) == true", r"计时器\1已到", s)
    s = re.sub(r"p\d:IsFinishTimer\((\d+)\) == false", r"计时器\1未到", s)
    s = re.sub(r"p\d:GetNumber\((\d+)\)", r"计数\1", s)
    s = re.sub(r"SpaceCheck\(p\d, p\d, (-?\d+), (\d+)\) == false", r"\1°方向\2m内无空间", s)
    s = re.sub(r"SpaceCheck\(p\d, p\d, (-?\d+), (\d+)\) == true", r"\1°方向\2m内有空间", s)
    s = re.sub(r"p\d:IsInterupt\(INTERUPT_(\w+)\)", r"打断:\1", s)
    for pat, label in GETTERS:
        s = re.sub(r"p\d:" + pat, lambda m, l=label: m.expand(l), s)
    for reg, name in regs.items():
        s = re.sub(rf"\b{reg}\b", name, s)
    s = re.sub(r"p\d[.:]", "", s)
    for a, b in ((" <= ", " ≤ "), (" >= ", " ≥ "), (" < ", " ＜ "), (" > ", " ＞ "), (" == ", " = "), (" ~= ", " ≠ "),
                 (" and ", " 且 "), (" or ", " 或 "), ("not ", "非 ")):
        s = s.replace(a, b)
    s = re.sub(r" - GetMapHitRadius\(TARGET_SELF\)", "", s)
    return s.replace('"', "'")


def fmt_w(w):
    try:
        v = float(w)
    except ValueError:
        return w
    return f"{v:.0e}" if v >= 1e6 else (str(int(v)) if v == int(v) else str(v))


# ----------------------------------------------------------------------------- statements of interest
def weights_in(stmts, table):
    out = []
    for kind, s in stmts:
        if kind != "stmt":
            continue
        m = re.fullmatch(rf"{table}\[(\d+)\] = (.+)", s)
        if m and not m.group(2).startswith("SetCoolTime"):
            out.append((int(m.group(1)), fmt_w(m.group(2))))
    return out


def request(s, numregs):
    m = re.search(r"AddSubGoal\((GOAL_\w+), [^,]+, ([^,)]+)", s)
    if not m:
        return None
    arg = m.group(2).strip()
    if arg.isdigit():
        return arg
    if arg in numregs:
        return "/".join(numregs[arg])
    return None


def num_regs(lines):
    regs = {}
    for line in lines:
        m = re.match(r"\s*(r\d+) = (\d{4,})\s*$", line)
        if m:
            regs.setdefault(m.group(1), [])
            if m.group(2) not in regs[m.group(1)]:
                regs[m.group(1)].append(m.group(2))
    return regs


# ----------------------------------------------------------------------------- Activate as a Mermaid ladder
class Mermaid:
    def __init__(self):
        self.lines = ["flowchart TD"]
        self.n = 0

    def node(self, label, shape="box"):
        self.n += 1
        nid = f"n{self.n}"
        label = label.replace('"', "'")
        if shape == "dec":
            self.lines.append(f'    {nid}{{"{label}"}}')
        elif shape == "start":
            self.lines.append(f'    {nid}(["{label}"])')
        else:
            self.lines.append(f'    {nid}["{label}"]')
        return nid

    def edge(self, a, b, label=None):
        self.lines.append(f"    {a} -- {label} --> {b}" if label else f"    {a} --> {b}")


def draw_body(mm, items, parent, edge_label, table, regs, prefix):
    """Draw one branch body: a box with the weights it sets, then any nested decisions."""
    w = weights_in(items, table)
    skip = any(kind == "stmt" and s == "<skip>" for kind, s in items)
    nested = [it for it in items if it[0] == "if"]
    if w:
        label = " · ".join(f"{prefix}{n:02d} ×{v}" for n, v in w)
        box = mm.node(label)
        mm.edge(parent, box, edge_label)
        parent, edge_label = box, None
    elif skip:
        box = mm.node("(不再加权重)")
        mm.edge(parent, box, edge_label)
        return
    elif not nested:
        box = mm.node("(不设权重)")
        mm.edge(parent, box, edge_label)
        return
    for it in nested:
        draw_ladder(mm, it[1], parent, edge_label, table, regs, prefix)
        edge_label = None


def draw_ladder(mm, branches, parent, edge_label, table, regs, prefix):
    for cond, body in branches:
        if cond is None:
            draw_body(mm, body, parent, edge_label, table, regs, prefix)
            return
        d = mm.node(human(cond, regs), "dec")
        mm.edge(parent, d, edge_label)
        draw_body(mm, body, d, "是", table, regs, prefix)
        parent, edge_label = d, "否"


def weight_table(lines):
    for line in lines:
        m = re.search(r"Common_Clear_Param\((r\d+),", line)
        if m:
            return m.group(1)
    return None


def activate_chart(lines, prefix, title):
    items = parse_function(lines)
    regs = reg_names(lines)
    table = weight_table(lines)
    chains = [it for it in items if it[0] == "if" and len(it[1]) >= 4]
    if not chains:
        return "(没有找到决策链)\n", []
    chain = chains[0]
    mm = Mermaid()
    start = mm.node(title, "start")
    draw_ladder(mm, chain[1], start, None, table, regs, prefix)
    after = items[items.index(chain) + 1:]
    return "```mermaid\n" + "\n".join(mm.lines) + "\n```\n", after


# ----------------------------------------------------------------------------- trees (Markdown lists)
def tree(items, regs, table, prefix, numregs, depth=0):
    out = []
    pad = "  " * depth
    w = weights_in(items, table) if table else []
    if w:
        out.append(f"{pad}- " + " · ".join(f"{prefix}{n:02d} ×{v}" for n, v in w))
    for kind, x in items:
        if kind == "stmt":
            r = request(x, numregs)
            if r:
                g = re.search(r"AddSubGoal\(GOAL_COMMON_(\w+)", x)
                out.append(f"{pad}- 出招 **{r}** ({g.group(1) if g else '?'})")
            m = re.search(r"\bp0\.(\w+)\(", x)
            if m and m.group(1) not in ("Kengeki_Activate",):
                out.append(f"{pad}- 转到 {m.group(1)}")
            if x.endswith("Replanning()"):
                out.append(f"{pad}- 重新选招")
        elif kind == "if":
            subs = [(cond, tree(body, regs, table, prefix, numregs, depth + 1), body) for cond, body in x]
            if not any(sub for _, sub, _ in subs):
                continue
            for k, (cond, sub, body) in enumerate(subs):
                if cond is None and not sub:
                    continue
                head = "否则" if cond is None else (("如果 " if k == 0 else "否则如果 ") + human(cond, regs))
                if sub:
                    out.append(f"{pad}- {head}:")
                    out.extend(sub)
                else:
                    skip = any(kk == "stmt" and ss == "<skip>" for kk, ss in body)
                    out.append(f"{pad}- {head}: {'跳过下面的设置' if skip else '—'}")
    return out


def inline(items, regs, numregs):
    parts = []
    for kind, x in items:
        if kind == "stmt":
            r = request(x, numregs)
            if r:
                parts.append(r)
        elif kind == "if":
            alts = []
            for cond, body in x:
                seq = inline(body, regs, numregs)
                if cond is None and not seq:
                    continue
                alts.append(f"{'否则' if cond is None else human(cond, regs)}: {seq or '—'}")
            if any(not a.endswith("—") for a in alts):
                parts.append("[" + " ｜ ".join(alts) + "]")
    return " → ".join(parts)


# ----------------------------------------------------------------------------- main
def main(path, title):
    funcs = split_functions(open(path, encoding="utf-8").read())
    out = [f"### {title}\n"]
    act = funcs["Goal.Activate"]
    chart, after = activate_chart(act, "Act", "每次选招 (Activate)")
    out.append("#### 选招流程 (Activate)\n")
    out.append("先检查是否刚发生拼刀或弹刀:是的话走下面的“拼刀后选招”,不走这张图。图中每个方框是这条分支给各个 Act 加的权重,"
               "最后按权重随机选一个 Act。\n")
    out.append(chart)
    regs = reg_names(act)
    table = weight_table(act)
    adj = tree([it for it in after if it[0] == "if"], regs, table, "Act", {})
    if adj:
        out.append("#### 决策链之后的权重调整(覆盖上面的值)\n")
        out.extend(adj)
        out.append("")
    if "Goal.Kengeki_Activate" in funcs:
        k = funcs["Goal.Kengeki_Activate"]
        out.append("#### 拼刀后选招 (Kengeki_Activate)\n")
        out.append("“拼刀类型”是刚刚那次拼刀或弹刀留下的特效编号。每条分支给 Kengeki 函数加权重,然后按权重选一个。\n")
        out.extend(tree(parse_function(k), reg_names(k), weight_table(k), "Kengeki", {}))
        out.append("")
    if "Goal.Interrupt" in funcs:
        it = funcs["Goal.Interrupt"]
        out.append("#### 打断反应 (Interrupt)\n")
        out.append("战斗中出现某个触发条件时,立即改出这些招。\n")
        out.extend(tree(parse_function(it), reg_names(it), None, "", num_regs(it)))
        out.append("")
    out.append("#### 每个选项请求的动画\n")
    out.append("| 函数 | 动画(按顺序;方括号里是函数内部的分支) |")
    out.append("|---|---|")
    for name, lines in funcs.items():
        if ACT_LIKE.match(name):
            seq = inline(parse_function(lines), reg_names(lines), num_regs(lines))
            if seq:
                out.append(f"| {name.replace('Goal.', '')} | {seq.replace('|', '｜')} |")
    out.append("")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
