"""Decision table for plan step 8 (V4 M6): how the approved move catalog becomes the product's Genichiro moves.

Usage: python -I decisions.py <out.csv> <out.md>

Reads, from the repository:
    research/ground_truth/semantic/genichiro_catalog.csv              the owner-approved catalog (63 moves)
    research/ground_truth/semantic/wiki_mapping/genichiro-ashina.json the product's 22 moves against the two wikis
    backend/seed/bosses.json                                          the product's names and phases

Two sections:
    A  one row per existing product move: its candidate catalog entries, how strong the evidence is, and a proposal;
    B  one row per group of catalog moves with the same attack and projectile animations that no product move covers
       with medium or strong evidence (phases 1-2 and phase 3 share a row when their animations are the same).
       Weak A candidates also get a B row, so the owner can still add them if the A link is rejected.
The candidates are written out below with their evidence; none of them is ground truth until the owner approves.
Every row waits for the owner: ✅ accepts the proposal, ❌ with a reason gives the owner's own decision (merge, rename,
remove...). Every move whose Chinese name has no wiki source (all of B, and the A moves named by translation) has a
招式名称 cell for the owner's own name. The owner's cells are read back on regeneration.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT = HERE.parent.parent
REPO = GT.parent.parent
out_csv, out_md = sys.argv[1:3]

catalog = [r for r in csv.DictReader(open(GT / "semantic/genichiro_catalog.csv", encoding="utf-8")) if r["kind"] == "move"]
by_entry = {r["entry"]: r for r in catalog}
wiki = {e["product_moves"][0]: e for e in json.load(open(GT / "semantic/wiki_mapping/genichiro-ashina.json", encoding="utf-8"))["entries"]}
seed = next(b for b in json.load(open(REPO / "backend/seed/bosses.json", encoding="utf-8")) if b["id"] == "genichiro-ashina")
product = {}
for p in seed["phases"]:
    for m in p["moves"]:
        product.setdefault(m["id"], {"name": m["name"], "name_zh": m["name_zh"], "name_zh_source": m["name_zh_source"],
                                     "phases": []})["phases"].append(p["phase_number"])

# Candidate catalog entries for each product move: (entries, strength, basis).
# 强 = the owner's own label or confirmation names the move; 中 = the AI structure matches the wiki description;
# 弱 = only hit counts, distances or a description suggest it.
FP_FAMILY = "你确认的飞渡浮舟三套(3040 → 3041、3068 → 3092 和起手 3063、3028)"
LINKS = {
    "perilous-attack-follow-up": (["P12-20"], "中",
        "AI 链 Kengeki38:3030 之后,一阶段(剩余忍杀数 ≥ 2)固定接 3025(你标危·突刺),和 wiki\"空中砸击、落地接危·突刺\"一致。和 A02 是同一个目录条目,只是结尾按阶段不同"),
    "perilous-attack-follow-up-phase-2": (["P12-20"], "中",
        "同一条 AI 链:二阶段(剩余忍杀数 ≤ 1)75% 接 3067(你标危·下段)、25% 接 3025,和 Fandom\"危·突刺或危·下段\"一致"),
    "perilous-attack-follow-up-phase-3": (["P3-17", "P3-30"], "中",
        "三阶段 Kengeki38:3030 之后各 1/3 接 3067、3025、3032,和 Fandom 的三种结尾一致。第三种\"上挑,被弹开后接延迟危·突刺\":"
        "你确认(2026-10-15)完美弹开 3032 之后接突刺 3080(P3-30),不完美弹开不会;第二次录像里有两次"),
    "perilous-grab": (["P12-17"], "强", "你把 3020 标为危·抓投;AI 链 3037 → 3020 的两段,和\"侧跳斩、肘击,打中后打肚子\"一致"),
    "closing-tide": (["P12-10", "P12-09", "P12-11", "P12-12"], "中",
        "Fandom:一阶段总是第一招。P12-10(3014 → 3015)就是开场第一招(权重 600),先射一箭再出攻击 3015。另外三条也是射箭后接同一个 3015"
        "(3013 一箭;3018、3036 一个动画两箭),是不是都算涨潮,需要你确认;不算的写在理由里,我移到 B 部分"),
    "floating-passage": ([], "强", FP_FAMILY + "。射箭取消 3017(floating-passage-cancel)你确认是飞渡浮舟的衍生,建议单独作为产品招式,见 B13;想并进这一招的话在理由里写"),
    "guard-breaking-shot": (["P12-19"], "中", "两个 wiki 都说用来惩罚喝药;3023 是飞行物,你使用道具时触发"),
    "hawk-shot": (["P12-23"], "中", "3044 一个动画里发射 4 次飞行物,和\"空中连射四箭\"一致;前面先后跳 5201"),
    "two-hit-combo": (["P12-02"], "强",
        "你确认(2026-10-15):就是 3003 → 3045 这个连招,3003 转身横斩,3045 踢一脚。TAE 里 3045 打中那一刻的音效挂在 4 号挂点"
        "(3003 挥刀用 7、10 号);第二次录像 0:07.6 起有一次完整的 3003 → 3045"),
    "deaths-thrust": (["P3-06"], "中", "三阶段开场第一招(几乎必出),和\"总是用它开始第三阶段\"一致;你使用道具时也触发,和 Fandom\"惩罚使用道具\"一致"),
    "perilous-grab-phase-3": (["P3-07"], "强", "你把三阶段 3009 标为危·投技;它在 3008 命中后触发(特效 3711000),和 wiki\"死亡突刺之后可能接危·投技\"一致"),
    "lightning-of-tomoe-slash": (["P3-21"], "强", "你确认(2026-10-15):3042 是斩击(跳起后向前横扫一道雷电)"),
    "lightning-of-tomoe-smash": (["P3-22", "P3-14"], "强", "你确认(2026-10-15):3043 是砸击(跳起后向下直劈带雷);P3-14 是 3018 之后接 3043"),
    "perilous-attack": (["P12-18"], "弱", "Fandom:冲过来向下刺。3022 只在你倒地时、5 米内出,你标为危·突刺(倒地时只能侧闪)。只凭描述推测"),
    "perilous-thrust": (["P12-26"], "中",
        "你把 3062 标为危·突刺,它单独出现(拼刀后 Kengeki43);但 3025 也是危·突刺(危攻击后续追击的结尾),产品的\"危·突刺\"指哪个需要你确认"),
    "perilous-sweep": (["P12-06"], "强",
        "你确认(2026-10-15)3007 是危·下段。P12-06 是危·下段横扫 3007 接一箭 3011,和 Fandom 的\"横扫地面后接一箭\"一致。"
        "一二阶段还没录到;三阶段的 3007(B06)录到 5 次,截图里看得到危字"),
    "advance": (["P12-03"], "弱", "\"边前进边横斩两次\"。3004 是 2 击、3–5 米出。只凭击数和距离推测,A18 的 3006 也可能是"),
    "chasing-slice": (["P12-05"], "弱", "\"跑一小段再斩两次\"。3006 是 2 击、≥ 5 米时权重 300。只凭击数和距离推测"),
    "iaijutsu": (["P12-15", "P12-16"], "弱",
        "Fandom 说退潮射两箭之后\"准备居合\";3019(或 3019 → 3029)只出现在 3018 或 3031 之后,所以可能是居合。只凭描述推测"),
    "receding-tide": (["P12-15"], "弱", "Fandom:后滑、同时射两箭,然后准备居合。3018 一个动画发射 2 个飞行物,P12-15 是 3018 之后接 3019。只凭描述推测"),
    "floating-passage-phase-3": ([], "强", FP_FAMILY + ",三阶段;加上完美弹开最后一下之后的突刺 3080"),
    "lightning-of-tomoe-shot": (["P3-19", "P3-08"], "中", "3039 是三阶段唯一的雷电飞行物,你标为危·雷电;P3-19 单独出,P3-08 是 3012 之后接 3039"),
}
# Catalog moves outside the product's moves with a proposal of their own (kept out of the family rows above).
OWN = {
    "P12-14": "并入 A06 飞渡浮舟(你确认,2026-10-15):射箭取消不单独成招,飞渡浮舟的描述里写明一二阶段中途改射一箭。"
              "二阶段第一套 3040 或第二套 3092 打完第 4 刀时你在 4.1 米外,停掉剩下的刀,改射一箭 3017",
    "P3-05": "并入 A16 危·下段横扫(你确认,2026-10-15):三阶段他弱弹开你之后侧步 5202 再出危·下段 3007,后面不接射箭",
    "P3-13": "并入 A21 三阶段飞渡浮舟(你确认,2026-10-15):3040 打完第 4 刀时你在 11 米外,改射 3018(一次两箭);"
             "5.5–11 米时改出死亡突刺 3008(见 A10)",
}
FAMILY = {"floating-passage": "c7100", "floating-passage-phase-3": "c7110"}
for slug, ch in FAMILY.items():
    LINKS[slug] = ([r["entry"] for r in catalog if r["family_proposed"].startswith("飞渡浮舟") and r["character"] == ch
                    and r["entry"] not in OWN],) + LINKS[slug][1:]
assert set(LINKS) == set(product) == set(wiki), set(LINKS) ^ set(product)
assert all(e in by_entry for ents, _, _ in LINKS.values() for e in ents)

REVIEW_HEAD = "| 编号 | 审核 | 理由 |"


def tokens(r):
    """The attack and projectile animations of an entry, typed, as the grouping key."""
    return tuple("攻击 " + t for t in r["attack_anims"].split()) + tuple("飞行物 " + t for t in r["bullet_anims"].split())


def anims(entries):
    return " ".join(dict.fromkeys(t.split("(")[0] for e in entries for t in (by_entry[e]["attack_anims"] + " " + by_entry[e]["bullet_anims"]).split()))


def phase_label(ch):
    return "一二阶段" if ch == "c7100" else "三阶段"


def recorded(entries):
    """Occurrences of each animation in both recordings, per character."""
    per = defaultdict(dict)
    for e in entries:
        r = by_entry[e]
        for x in r["recorded"].split():
            a, n = x.split(":")
            per[r["character"]][a] = n
    return ";".join(f"{phase_label(ch)} " + " ".join(f"{a}×{n}" for a, n in per[ch].items()) for ch in sorted(per))


def evidence(entries):
    ev = {by_entry[e]["evidence"] for e in entries}
    return ev.pop() if len(ev) == 1 else "部分运行观察"


def phases(entries):
    return "、".join(sorted({p for e in entries for p in by_entry[e]["phases"].split("、")}))


ANIM_LABEL = {}                             # the owner's labels by animation, wherever in the catalog they were given
for r in catalog:
    for part in filter(None, r["owner_labels"].split("；")):
        a, lab = part.split(" ", 1)
        ANIM_LABEL.setdefault(a, lab)


def labels(entries):
    return "；".join(f"{a} {ANIM_LABEL[a]}" for a in anims(entries).split() if a in ANIM_LABEL)


rows, a_of = [], defaultdict(list)          # a_of: catalog entry -> [(A key, slug, strength)]
for i, slug in enumerate(wiki, 1):
    key, pm = f"A{i:02d}", product[slug]
    ents, strength, basis = LINKS[slug]
    for e in ents:
        a_of[e].append((key, slug, strength))
    if not ents:
        proposal = "待你判断:没有证据对上目录里的任何一招。可以写它对应哪个目录条目或 B 部分哪一行,或者删除"
    elif strength == "弱":
        proposal = "待你看动画确认:同意就保留,对应这些目录条目;不同意就写它是什么,或者删除"
    else:
        proposal = "保留,对应这些目录条目" + ("" if len(ents) == 1 or strength == "强" else "(哪几条算,需要你确认)")
        if evidence(ents) != "已运行观察":
            proposal += ";其中有的还没录到"
    rows.append({"key": key, "section": "A", "product_slug": slug, "product_name": pm["name"], "product_name_zh": pm["name_zh"],
                 "name_source": pm["name_zh_source"],
                 "phases": "、".join(map(str, pm["phases"])), "catalog_entries": " ".join(ents),
                 "chains": "；".join(f"{e}: {by_entry[e]['chain']}" for e in ents), "anims": anims(ents),
                 "recorded": recorded(ents), "evidence": evidence(ents) if ents else "", "owner_labels": labels(ents),
                 "strength": strength, "basis": basis, "trigger": "", "proposal": proposal,
                 "wiki": "Fextralife:" + ("、".join(wiki[slug]["fextralife"]) or "—") + ";Fandom:" + "、".join(wiki[slug]["fandom"]),
                 "character": "c7110" if all(by_entry[e]["character"] == "c7110" for e in ents) and ents else "c7100"})

# The owner's review and names, kept across regeneration. Rows are matched by what they are (A: the product move,
# B: its catalog entries), and a B row keeps its number for as long as its entries stay the same, so a row that goes
# away leaves a gap instead of shifting the rows after it.
reviews, b_keys = {}, {}
if Path(out_md).exists():
    text = open(out_md, encoding="utf-8").read()
    has_name = "| 招式名称 |" in text
    for line in text.splitlines():
        m = re.match(r"^\| ([AB]\d{2}) \|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|", line)
        if not m:
            continue
        name = m.group(4).strip() if has_name else ""
        if m.group(1).startswith("A"):
            ident = ("A", re.search(r"`([^`]+)`", m.group(5) if has_name else m.group(4)).group(1))
        else:
            ident = ("B", (m.group(5) if has_name else m.group(4)).strip())
            b_keys[ident[1]] = m.group(1)
        reviews[ident] = (m.group(2).strip() or "☐", m.group(3).strip(), "" if name == "—" else name)

covered = {e for e, links in a_of.items() if any(s in ("强", "中") for _, _, s in links)}
groups = defaultdict(list)
for r in catalog:
    groups[tokens(r)].append(r["entry"])
j = max([int(k[1:]) for k in b_keys.values()] + [0])
for key in sorted(groups, key=lambda k: [int(re.search(r"\d+", t).group()) for t in k]):
    ents = [e for e in groups[key] if e not in covered]
    if not ents:
        continue
    if " ".join(ents) in b_keys:
        bkey = b_keys[" ".join(ents)]
    else:
        j += 1
        bkey = f"B{j:02d}"
    twins = [e for e in groups[key] if e in covered]
    weak = sorted({(k, s) for e in ents for k, s, st in a_of.get(e, []) if st == "弱"})
    if any(e in OWN for e in ents):
        proposal = next(OWN[e] for e in ents if e in OWN)
    elif twins:
        k, s, _ = a_of[twins[0]][0]
        proposal = f"和 {' '.join(twins)} 动画相同,跟随 {k}(`{s}`)的决定:同意的话这里的阶段也加进那个招式"
    elif weak:
        proposal = "看 " + "、".join(f"{k}(`{s}`)" for k, s in weak) + " 的决定:同意就并入那个招式(三阶段同样的动画也一起),不同意就新增为产品招式"
    elif evidence(ents) == "仅静态证据":
        proposal = "新增,但暂缺视觉样例:录到或用 DS Anim Studio 预览确认之后再进产品"
    else:
        proposal = "新增为产品招式(需要中英文名,可以写在理由里)"
    rows.append({"key": bkey, "section": "B", "product_slug": "", "product_name": "", "product_name_zh": "", "name_source": "",
                 "phases": phases(ents), "catalog_entries": " ".join(ents),
                 "chains": "；".join(f"{e}: {by_entry[e]['chain']}" for e in ents), "anims": " ".join(t.replace(" ", ":") for t in key),
                 "recorded": recorded(ents), "evidence": evidence(ents), "owner_labels": labels(ents), "strength": "",
                 "basis": "", "trigger": "；".join(f"{e}: {by_entry[e]['trigger']}" for e in ents), "proposal": proposal, "wiki": "",
                 "character": "c7110" if all(by_entry[e]["character"] == "c7110" for e in ents) else "c7100"})

# every catalog move is somewhere
assert {e for r in rows for e in r["catalog_entries"].split()} == set(by_entry)

def name_editable(r):
    """The owner names every move whose Chinese name has no wiki source: all of B, and the A moves named by translation."""
    return r["name_source"] != "wiki"


rows.sort(key=lambda r: (r["section"], int(r["key"][1:])))
idents = {(r["section"], r["product_slug"] if r["section"] == "A" else r["catalog_entries"]) for r in rows}
for ident, (mark, reason, name) in reviews.items():
    if ident not in idents and (mark != "☐" or reason or name):
        print(f"warning: the owner's review of {ident} has no row any more: {mark} {reason} {name}")
for r in rows:
    ident = (r["section"], r["product_slug"] if r["section"] == "A" else r["catalog_entries"])
    r["review_mark"], r["owner_reason"], r["owner_name"] = reviews.get(ident, ("☐", "", ""))
    if not name_editable(r):
        r["owner_name"] = ""
    r["owner_review"] = "不通过" if "❌" in r["review_mark"] else ("通过" if "✅" in r["review_mark"] else "待审核")

FIELDS = ["key", "section", "product_slug", "product_name", "product_name_zh", "name_source", "phases", "catalog_entries", "chains", "anims",
          "recorded", "evidence", "owner_labels", "strength", "basis", "trigger", "proposal", "wiki", "character",
          "owner_review", "owner_reason", "owner_name"]
with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\r\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in FIELDS})


def cell(x):
    return (str(x) if x not in ("", None) else "—").replace("|", "｜")


A = [r for r in rows if r["section"] == "A"]
B = [r for r in rows if r["section"] == "B"]
md = ["# 第 8 步决策表:招式目录 → 产品里的弦一郎招式(待你决定)", "",
      "由 `scripts/ai/decisions.py` 生成,数据在 `genichiro_product_decisions.csv`。依据是你审核通过的招式目录 `genichiro_catalog.md`"
      f"({len(by_entry)} 个招式)。这里的对应关系都是我的建议,你批了才算数。", "",
      f"- **A 部分({len(A)} 行)**:产品里现有的 {len(A)} 个弦一郎招式,每个列出目录里的候选条目、依据和建议。",
      f"- **B 部分({len(B)} 行)**:目录里还没有以中等以上依据对上产品招式的招式。攻击和飞行物动画相同的条目合成一行"
      "(一二阶段和三阶段动画相同的也合在一起)。A 部分只有弱依据的候选,在 B 部分也有一行,方便你不同意 A 时直接新增。",
      "- 编号固定:一行去掉以后编号留空,后面的行不改号(比如 B02 已经并进 A09)。",
      "- 依据强弱:强 = 你的标注或确认直接对上;中 = AI 结构和 wiki 描述一致;弱 = 只凭击数、距离或描述推测,需要你看动画确认。",
      "- 两次录像出现:每个动画在两次录像里一共出现几次(一二阶段和三阶段分开算)。",
      "- 你的标注:你在招式目录里给动画的标注,按动画编号列出,不管是在哪个条目里标的。", "",
      "## 怎么决定", "",
      "用鼠标:在终端运行 `python -I research/ground_truth/scripts/ai/catalog_review.py 8765 decisions`,"
      "然后在 VS Code 里 Ctrl+Shift+P → Simple Browser: Show,打开 http://127.0.0.1:8765。", "",
      "- ✅ = 同意这一行的建议。",
      "- ❌ = 不同意,在理由栏写你的决定,比如\"只算 P12-10\"\"合并到 A05\"\"对应 B07\"\"删除\"\"改名为……\"。", "",
      "**招式名称**:只有飞渡浮舟的中文名有 wiki 原文(biligame wiki),这两行不用填。其余产品招式的英文名是 Fandom 或 Fextralife 的社区叫法,"
      "中文名是翻译;想换名字就填,留空 = 用现在的名字。B 部分要新增的招式需要你起名。格式:`中文名 / English name`。", "",
      "删除或合并产品招式时,已有的练习记录会迁移到对应的新招式,不会丢。第 8 步实现时我会先统计每个招式被多少条记录引用,迁移方案再给你看。", "",
      f"## A. 产品现有的招式({len(A)} 个)", "",
      REVIEW_HEAD + " 招式名称 | 产品招式 | 产品阶段 | 候选目录条目 | 动画 | 两次录像出现 | 证据 | 依据强弱 | 依据 | 建议 |",
      "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in A:
    md.append(f"| {r['key']} | {r['review_mark']} | {r['owner_reason']} | {r['owner_name'] if name_editable(r) else '—'} "
              f"| `{r['product_slug']}` {r['product_name_zh']} | {r['phases']} "
              f"| {cell(r['catalog_entries'])} | {cell(r['anims'])} | {cell(r['recorded'])} | {cell(r['evidence'])} | {cell(r['strength'])} "
              f"| {cell(r['basis'])} | {cell(r['proposal'])} |")
md += ["", f"## B. 目录里还没对上产品的招式({len(B)} 行)", "",
       REVIEW_HEAD + " 招式名称 | 目录条目 | 阶段 | 动画(击数) | 两次录像出现 | 证据 | 你的标注 | 触发 | 建议 |",
       "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in B:
    md.append(f"| {r['key']} | {r['review_mark']} | {r['owner_reason']} | {r['owner_name']} | {r['catalog_entries']} | {r['phases']} | {cell(r['anims'])} "
              f"| {cell(r['recorded'])} | {cell(r['evidence'])} | {cell(r['owner_labels'])} | {cell(r['trigger'])} | {cell(r['proposal'])} |")
md.append("")
with open(out_md, "w", encoding="utf-8", newline="") as fh:
    fh.write("\r\n".join(md))

sys.stdout.reconfigure(encoding="utf-8")
print(f"A {len(A)} rows ({sum(1 for r in A if r['catalog_entries'])} with candidates; "
      f"{sum(1 for r in A if r['strength'] == '强')} 强, {sum(1 for r in A if r['strength'] == '中')} 中, {sum(1 for r in A if r['strength'] == '弱')} 弱); "
      f"B {len(B)} rows covering {sum(len(r['catalog_entries'].split()) for r in B)} catalog entries")
