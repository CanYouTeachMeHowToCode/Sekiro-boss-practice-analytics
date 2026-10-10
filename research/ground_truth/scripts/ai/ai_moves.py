"""Which animation IDs can a decompiled battle goal request, and through which functions?

Usage: python -I ai_moves.py <decompiled_battle.txt> <out.json>

The JSON also lists `cooldown_ids`: animation IDs that only appear as the key of a SetCoolTime call in
Activate / Kengeki_Activate (a cooldown on that animation, not a request to play it).

Reads the pseudo-Lua written by lua50_decompile.py. For every function it collects the IDs passed as the
third argument of AddSubGoal (literal numbers, or a register holding numbers assigned in that function).
Reachability:
  - Activate gives weights to Act functions (table r3[N] = w > 0)  -> those Acts are "selected by Activate";
  - Kengeki_Activate gives weights to Kengeki functions (r5[N] = w > 0) -> "selected after a deflect exchange";
  - any function called directly (p0.ActNN(...), p0.Parry(...), p0.Damaged(...)) or the Interrupt handler
    is reachable through that call;
  - a defined Act/Kengeki that nothing weights or calls is "never selected" (dead code in this script).
"""
import json
import re
import sys
from collections import defaultdict

text = open(sys.argv[1], encoding="utf-8").read()
funcs = {}
order = []
for block in re.split(r"(?m)^-- function #\d+: ", text)[1:]:
    name = block.split("  (", 1)[0].strip()
    funcs[name] = block
    order.append(name)

ADD = re.compile(r"AddSubGoal\((GOAL_\w+), ([^,]+), ([^,)]+)")
ASSIGN_NUM = re.compile(r"\b(r\d+) = (\d+)\b\s*$", re.M)


def requested(body):
    regs = defaultdict(set)
    for reg, val in ASSIGN_NUM.findall(body):
        regs[reg].add(int(val))
    out = []
    for goal, _time, arg in ADD.findall(body):
        arg = arg.strip()
        if arg.isdigit():
            out.append((goal, int(arg)))
        elif arg in regs:
            for v in sorted(regs[arg]):
                if v >= 1000:
                    out.append((goal, v))
    return out


def weights(body, table):
    """Act numbers given a positive weight in this function: `table[N] = w`, w > 0 or a non-literal."""
    got = defaultdict(list)
    for n, w in re.findall(rf"\b{table}\[(\d+)\] = ([^\n]+)", body):
        w = w.strip()
        if w.startswith("SetCoolTime"):
            continue
        try:
            v = float(w)
        except ValueError:
            v = None
        got[int(n)].append(v)
    return {n: vs for n, vs in got.items() if any(v is None or v > 0 for v in vs)}


calls = defaultdict(set)
for name in order:
    for callee in re.findall(r"p0\.(\w+)\(", funcs[name]):
        calls[name].add(callee)

act_w = weights(funcs.get("Goal.Activate", ""), "r3")
keng_w = weights(funcs.get("Goal.Kengeki_Activate", ""), "r5")
cooldown = sorted({int(x) for name in ("Goal.Activate", "Goal.Kengeki_Activate")
                   for x in re.findall(r"SetCoolTime\(p\d, p\d, (\d+),", funcs.get(name, ""))})
result = {"functions": {}, "activate_weights": {str(k): v for k, v in act_w.items()},
          "kengeki_weights": {str(k): v for k, v in keng_w.items()}, "cooldown_ids": cooldown}
called = {c for cs in calls.values() for c in cs}
for name in order:
    short = name.replace("Goal.", "")
    reasons = []
    m = re.fullmatch(r"Act(\d+)", short)
    if m and int(m.group(1)) in act_w:
        reasons.append("weighted in Activate")
    m = re.fullmatch(r"Kengeki(\d+)", short)
    if m and int(m.group(1)) in keng_w:
        reasons.append("weighted in Kengeki_Activate")
    if short in called:
        callers = sorted(n.replace("Goal.", "") for n, cs in calls.items() if short in cs)
        reasons.append("called from " + ", ".join(callers))
    if short in ("Activate", "Interrupt", "Kengeki_Activate", "Update", "Terminate", "Initialize"):
        reasons.append("engine entry point")
    result["functions"][short] = {"requests": requested(funcs[name]), "reachable_by": reasons}
json.dump(result, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# readable summary
sys.stdout.reconfigure(encoding="utf-8")
undefined = sorted(n for n in act_w if f"Act{n:02d}" not in result["functions"])
print("Acts weighted in Activate but not defined (no effect):", undefined)
undefined_k = sorted(n for n in keng_w if f"Kengeki{n:02d}" not in result["functions"])
print("Kengeki weighted but not defined:", undefined_k)
for short, f in result["functions"].items():
    if not f["requests"] and short.startswith(("Act", "Kengeki")) is False:
        continue
    ids = sorted({i for _, i in f["requests"]})
    flag = "" if f["reachable_by"] else "   <-- never selected"
    print(f"{short:22s} {', '.join(f['reachable_by']) or '-':45s} {' '.join(map(str, ids))}{flag}")
