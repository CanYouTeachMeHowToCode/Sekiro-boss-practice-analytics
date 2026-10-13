"""Classify every TAE entry of castle Genichiro (c7100, c7110) for the completeness review (V4 M5), and draft the gap
report against the product's moves.

Usage: python -I classify.py <tae_dir> <out.csv> <out_review.md> <out_gap.md>

    tae_dir   tae_dump.py output: c7100_tae.json, c7110_tae.json

Also reads, from research/ground_truth:
    engine/genichiro_castle_ai_reachability.csv          castle AI requests and why not
    semantic/genichiro_catalog.csv                       the owner-approved move catalog
    observations/vanilla/genichiro/*-castle/occurrences.csv   every castle recording
    semantic/wiki_mapping/genichiro-ashina.json          the product's Genichiro moves

Classes (CLAUDE.md section 31): mapped_to_semantic_move, non_combat, locomotion, hit_reaction,
cinematic_or_scripted, duplicate_or_shared, unused_or_unreachable, unknown.

Only an entry with an attack or projectile event can hurt the player. Each of those is either in an approved catalog
entry, or the castle AI never requests it (with the reason). The other entries are sorted with the evidence named in
each row and a confidence:
    高  the owner confirmed it, or the AI and the recordings agree;
    中  a consistent pattern in the recordings (what comes right before or after it);
    低  only the ID block it belongs to, or the animation it reuses.
The owner reviews every row in the 审核 / 理由 columns of the review sheet; those cells are read back on regeneration.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT = HERE.parent.parent
tae_dir, out_csv, out_md, out_gap = sys.argv[1:5]

reach = {(r["character"], int(r["anim"][5:])): r
         for r in csv.DictReader(open(GT / "engine/genichiro_castle_ai_reachability.csv", encoding="utf-8"))}
catalog = list(csv.DictReader(open(GT / "semantic/genichiro_catalog.csv", encoding="utf-8")))
in_catalog = defaultdict(list)                     # (character, anim) -> catalog entries containing it
for r in catalog:
    for a in (r["attack_anims"] + " " + r["bullet_anims"] + " " + r["other_anims"]).split():
        in_catalog[(r["character"], int(a.split("(")[0]))].append(r)
counts = Counter()
for rec in sorted((GT / "observations/vanilla/genichiro").glob("*-castle")):
    for r in csv.DictReader(open(rec / "occurrences.csv", encoding="utf-8")):
        counts[(r["character"][:5], int(r["anim"][5:]))] += 1

# Non-attack entries: (class, basis, confidence when seen in the recordings, confidence otherwise). First match wins.
# The patterns quoted were counted in the two castle recordings (2026-10-09, 2026-10-13).
OTHER = [
    ({3100, 3101, 3102, 3103}, "non_combat", "他弹开你的动作(AI 的 Parry 选项;3101 是 1 秒内连续格挡后的强弹)", "高", "高"),
    ({5201, 5202, 5203}, "non_combat", "后跳、侧移(AI 的 Act22、Act24、Damaged、Kengeki02 选项)", "高", "高"),
    ({9600, 9700, 9501, 9502, 9503}, "hit_reaction", "被你弹开后的罚站(9600/9700 你已确认,带特效 3710030);9501-9503 借用 9500", "高", "低"),
    ({8604, 8605, 8704, 8705}, "hit_reaction", "飞渡浮舟最后一下被完美弹开后的动作(8604 你已确认;8704 完全借用 8604,录像里同样接 3080)", "高", "低"),
    ({8400, 8401}, "hit_reaction", "他强弹开你(3101)之后的拼刀动作:录像里 52/52、20/20 次都紧跟 3101", "高", "高"),
    ({8500, 8501, 8502, 8503, 8504, 8505, 8510, 8511, 8550, 8551}, "hit_reaction",
     "他弹开你之后的拼刀动作:8500/8501 录像里 45/45、61/61 次紧跟 3100;8502 跟 3102,8504/8505 跟 3103,8510、8551 跟 3100", "高", "低"),
    ({8600, 8601, 8650, 8651}, "hit_reaction", "他被你弹开(弾かれた)的反应:之后才会出只在\"他被弹开\"类型下出现的 3055", "高", "低"),
    ({8700, 8701}, "hit_reaction", "和 8604/8704 同段的被弹开反应(编号段推测)", "中", "低"),
    ({8210, 8220, 8230, 8240, 8250, 8260}, "hit_reaction",
     "推测是被雷反击中后的感电硬直:两次录像里 5 组 8210-8230 都在雷电招式 3042/3043 之后 2.0-3.4 秒;8240-8260 借用同一套动画", "中", "低"),
    ({8300, 8301, 8310, 8320}, "hit_reaction", "推测是体干崩溃:8300 两次都紧接着忍杀(013500、012000)", "中", "低"),
    ({8010, 8011, 8012, 8013, 8020, 8021, 8022, 8023, 8050, 8051, 8120, 8121, 8130, 8140, 8141, 8150, 8900}, "hit_reaction",
     "推测是受击:8010 录像里 58 次,39 次之后紧跟他弹开你(3100);8050/8140 借用 8010 的动画", "中", "低"),
    ({13800}, "hit_reaction", "推测是被识破(Mikiri)后的硬直:23 次里 12 次紧跟危·突刺 3025,之后多接 8010", "中", "低"),
    ({7100, 7120, 40000}, "hit_reaction", "推测是倒地和起身:录像里 4 次都是 3044 → 8140 → 7100 → 040000 → 7120 → 8010 这一串", "中", "低"),
    ({7000, 7010, 7020, 7110, 7200, 7210, 7220, 7600, 7610, 7620, 40001, 40010}, "hit_reaction",
     "和 7100/7120/040000 同段,推测是倒地和起身的其他方向(编号段推测)", "低", "低"),
    ({9500}, "hit_reaction", "推测是攻击被你挡住(普通防御)后的反应:多出现在他出招之后,之后常接 9600", "中", "低"),
    ({9999}, "non_combat", "只有 1 帧([0/1])的占位动画,不是动作", "中", "低"),
    ({12000, 12100, 12110, 12120, 13100, 13110, 13120, 13200, 13400, 13410, 13500, 13510, 13700, 20110, 20200}, "cinematic_or_scripted",
     "忍杀/处决:录像里 013100→013110、012100→012110 结束一阶段,013500→013510、012000 结束二阶段,最终忍杀是 012000 → 020200 → 013700", "高", "低"),
    ({10000, 10001}, "cinematic_or_scripted", "死亡:010001 是被最终忍杀后倒地不动(第二次录像结尾,画面有\"忍殺\")", "高", "低"),
    ({21000, 21001}, "cinematic_or_scripted", "原地站立的循环,用在苇名外围和神子同场的演出里(21001 你已确认)", "低", "低"),
    ({41500}, "non_combat", "推测是待机架势:60 帧循环,出现在开场和拼刀间隙", "中", "低"),
    ({405000, 405001, 405002, 405003, 405010, 405400, 405401, 405402, 405403}, "locomotion",
     "推测是移动(走、跑、转身):16-60 帧的循环,多出现在出招之前", "中", "低"),
    ({400000, 401050, 500000, 501040, 505000, 505001, 505002, 505003, 505400, 505401, 505402, 505403, 0}, "locomotion",
     "推测是移动或待机的基础动画(000000 借用 400000;505xxx 和 405xxx 编号对应;编号段推测)", "低", "低"),
]
ASK = "没有攻击判定和飞行物,不会伤到玩家"


def other_class(a, seen):
    for ids, cls, basis, conf_seen, conf_unseen in OTHER:
        if a in ids:
            return cls, basis, conf_seen if seen else conf_unseen
    return "unknown", ASK + ";录像里没出现,AI 也不请求,没有其他证据", "低"


rows = []
for c in ("c7100", "c7110"):
    tae = json.load(open(f"{tae_dir}/{c}_tae.json", encoding="utf-8"))["animations"]
    imports = {a["id_int"]: int(a["imports_from"][5:]) for a in tae if a["kind"] == "import_other_anim"}
    imported_by = defaultdict(list)
    for x, src in imports.items():
        imported_by[src].append(x)
    for a in tae:
        n = a["id_int"]
        r = reach[(c, n)]
        cat = r["category"]
        entries = in_catalog.get((c, n), [])
        moves = [e for e in entries if e["kind"] == "move"]
        seen = counts[(c, n)]
        ai = "会出" if r["castle_status"] in ("recorded", "reachable_not_recorded") else "不会出"
        note = ""
        if cat in ("attack", "bullet"):
            if moves:
                cls, conf = "mapped_to_semantic_move", "高"
                fam = sorted({e["family_proposed"] or "(未命名)" for e in moves})
                basis = "招式目录 " + "、".join(e["entry"] for e in moves) + "(你审核通过);招式族:" + "、".join(fam)
            elif any((c, s) in in_catalog for s in imported_by.get(n, [])):
                cls, conf = "duplicate_or_shared", "高"
                basis = "动画和事件被 " + "、".join(f"{s:06d}" for s in imported_by[n]) + " 完全借用,画面上显示的是借用它的编号"
            else:
                cls, conf = "unused_or_unreachable", "高"
                basis = "天守阁 AI 不会出:" + (r["castle_not_reachable_reason"] or "")
                if r["requested_by_other_ai"]:
                    basis += ";其他 AI:" + r["requested_by_other_ai"]
                if c == "c7110" and n in (3085, 3086, 3087):
                    basis += ";你已确认是剑圣战巴流的不死斩招式"
        else:
            cls, basis, conf = other_class(n, seen)
            if moves:
                note = "也出现在招式链 " + "、".join(e["entry"] for e in moves) + " 里"
        if n in imports:
            note = "；".join(x for x in (note, f"完全借用 {imports[n]:06d}") if x)
        rows.append({"key": f"{c} {n:06d}", "character": c, "anim": f"a000_{n:06d}", "tae_category": cat,
                     "castle_ai": ai, "castle_ai_paths": r["castle_ai_paths"], "recorded": seen,
                     "catalog_entries": " ".join(e["entry"] for e in entries),
                     "class": cls, "confidence": conf, "basis": basis, "note": note})

# ---------------------------------------------------------------- the owner's review, kept across regeneration
REVIEW_HEAD = "| 编号 | 审核 | 理由 |"
reviews = {}
if Path(out_md).exists():
    for line in open(out_md, encoding="utf-8"):
        m = re.match(r"^\| (c71[01]0 \d{6}) \|([^|]*)\|([^|]*)\|", line)
        if m:
            reviews[m.group(1)] = (m.group(2).strip() or "☐", m.group(3).strip())


def review_status(mark):
    return "不通过" if ("❌" in mark or "不通过" in mark) else ("通过" if ("✅" in mark or "通过" in mark) else "待审核")


for r in rows:
    r["review_mark"], r["owner_reason"] = reviews.get(r["key"], ("☐", ""))
    r["owner_review"] = review_status(r["review_mark"])

FIELDS = ["key", "character", "anim", "tae_category", "castle_ai", "castle_ai_paths", "recorded", "catalog_entries",
          "class", "confidence", "basis", "note", "owner_review", "owner_reason"]
with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in FIELDS})

# ---------------------------------------------------------------- review sheet
CLASS_ZH = {"mapped_to_semantic_move": "属于招式", "duplicate_or_shared": "被借用的源动画", "unused_or_unreachable": "天守阁 AI 不会出",
            "non_combat": "非招式(格挡、弹刀、侧步、待机)", "hit_reaction": "受击和反应", "locomotion": "移动",
            "cinematic_or_scripted": "忍杀、死亡和演出", "unknown": "unknown"}
ORDER = list(CLASS_ZH)


def cell(x):
    return (str(x) if x not in ("", None) else "—").replace("|", "｜")


combat = [r for r in rows if r["tae_category"] in ("attack", "bullet")]
md = ["# 天守阁弦一郎 TAE 全集分类(草稿,待你审核)", "",
      "由 `scripts/ai/classify.py` 生成,数据在 `engine/genichiro_castle_tae_classes.csv`。对应计划第 7 步(V4 M5)。", "",
      "- c7100(一、二阶段)和 c7110(三阶段)的每个 TAE 编号一行,共 %d 行。" % len(rows),
      "- **只有带攻击判定或飞行物的编号才可能伤到玩家。** 这类编号共 %d 个,每个要么属于你审核通过的招式目录,要么有 AI 证据说明天守阁不会出。"
      "其中分到 unknown 的:%d 个。" % (len(combat), sum(1 for r in combat if r["class"] == "unknown")),
      "- 其余编号没有攻击判定和飞行物,按证据分类,并标出置信度:", "",
      "| 置信度 | 含义 |", "|---|---|",
      "| 高 | 你已确认,或 AI 和录像一致 |",
      "| 中 | 两次录像里有稳定的规律(前后接什么) |",
      "| 低 | 只凭编号段,或它借用的动画 |", "",
      "## 怎么审核", "",
      "用鼠标审核:在终端运行 `python -I research/ground_truth/scripts/ai/catalog_review.py 8765 classification`,"
      "然后在 VS Code 里 Ctrl+Shift+P → Simple Browser: Show,打开 http://127.0.0.1:8765。页面上可以按置信度筛选。", "",
      "也可以直接改这个文件:把\"审核\"栏的 ☐ 改成 ✅ 或 ❌,不通过时写理由。", "",
      "建议重点看置信度为\"中\"\"低\"的行,可以在 DS Anim Studio 里打开对应编号看一眼。重新生成时你的审核会保留。", "",
      "## 统计", "",
      "| 分类 | c7100 | c7110 | 其中带攻击或飞行物 |", "|---|---|---|---|"]
for cls in ORDER:
    rc = [r for r in rows if r["class"] == cls]
    md.append(f"| {CLASS_ZH[cls]}(`{cls}`) | {sum(1 for r in rc if r['character'] == 'c7100')} | "
              f"{sum(1 for r in rc if r['character'] == 'c7110')} | {sum(1 for r in rc if r['tae_category'] in ('attack', 'bullet'))} |")
md.append(f"| 合计 | {sum(1 for r in rows if r['character'] == 'c7100')} | {sum(1 for r in rows if r['character'] == 'c7110')} | {len(combat)} |")
conf = Counter(r["confidence"] for r in rows)
md += ["", f"置信度:高 {conf['高']},中 {conf['中']},低 {conf['低']}。", ""]
for cls in ORDER:
    rc = [r for r in rows if r["class"] == cls]
    if not rc:
        continue
    md += [f"## {CLASS_ZH[cls]}(`{cls}`,{len(rc)} 个)", "",
           REVIEW_HEAD + " 类别 | 天守阁 AI | 两次录像出现 | 目录条目 | 置信度 | 依据 | 备注 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rc:
        md.append(f"| {r['key']} | {r['review_mark']} | {r['owner_reason']} | {r['tae_category']} | {r['castle_ai']} | {r['recorded']} "
                  f"| {cell(r['catalog_entries'])} | {r['confidence']} | {cell(r['basis'])} | {cell(r['note'])} |")
    md.append("")
open(out_md, "w", encoding="utf-8").write("\n".join(md))

# ---------------------------------------------------------------- gap report against the product's moves
wiki = json.load(open(GT / "semantic/wiki_mapping/genichiro-ashina.json", encoding="utf-8"))
moves = [r for r in catalog if r["kind"] == "move"]
gap = ["# 天守阁弦一郎:产品招式与招式目录的差距报告(草稿)", "",
       "由 `scripts/ai/classify.py` 生成。左边是产品里现有的 %d 个弦一郎招式(来自 `semantic/wiki_mapping/genichiro-ashina.json`),"
       "右边是招式目录里 `wiki 候选` 指向它的条目。目录条目的 wiki 候选只在有依据时才填,所以\"还没有对应\"不代表目录里没有这一招,"
       "只是还没有证据把它们对上。" % len(wiki["entries"]), "",
       "每一行最后由你判断属于哪一类:一一对应、需要拆分、需要合并、描述错误,或两个 wiki 都没有记载。", "",
       "| 产品招式 | Fextralife | Fandom | 目录条目(候选) | 依据 |", "|---|---|---|---|---|"]
linked = set()
for e in wiki["entries"]:
    slug = e["product_moves"][0]
    hits = [m for m in moves if re.search(rf"(^|[^\w-]){re.escape(slug)}($|[^\w-])", m["wiki_candidate"])
            or (slug.startswith("lightning-of-tomoe") and "lightning-of-tomoe" in m["wiki_candidate"])
            or any(name and name in m["wiki_candidate"] for name in e["fextralife"] + e["fandom"])]
    linked |= {m["entry"] for m in hits}
    gap.append(f"| `{slug}` | {cell('、'.join(e['fextralife']))} | {cell('、'.join(e['fandom']))} | "
               f"{cell(' '.join(m['entry'] for m in hits) or '还没有对应')} | {cell('；'.join(sorted({m['wiki_basis'] for m in hits if m['wiki_basis']})))} |")
rest = [m for m in moves if m["entry"] not in linked]
gap += ["", f"## 目录里还没有对上产品招式的条目({len(rest)} 个)", "",
        "这些招式在 AI 里存在、并经你审核通过,但还没有证据说明它们对应产品里的哪一招,或者产品里根本没有。", "",
        "| 条目 | 阶段 | 动画链 | 招式族 | 你的标注 |", "|---|---|---|---|---|"]
for m in rest:
    gap.append(f"| {m['entry']} | {m['phases']} | {cell(m['chain'])} | {cell(m['family_proposed'])} | {cell(m['owner_labels'])} |")
gap.append("")
open(out_gap, "w", encoding="utf-8").write("\n".join(gap))

sys.stdout.reconfigure(encoding="utf-8")
print(len(rows), "TAE entries;", len(combat), "with attack/projectile;", sum(1 for r in combat if r["class"] == "unknown"), "of them unknown")
for cls in ORDER:
    print(f"  {cls:25s}", sum(1 for r in rows if r["class"] == cls))
print("confidence:", dict(conf))
print("product moves linked:", sum(1 for line in gap if line.startswith("| `") and "还没有对应" not in line), "/", len(wiki["entries"]), "; catalog moves not linked:", len(rest))
