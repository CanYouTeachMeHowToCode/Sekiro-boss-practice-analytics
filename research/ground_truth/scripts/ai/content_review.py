"""Checklist of the product's Genichiro move texts for plan step 8 (V3.1 M6): what to keep, change or fill.

Usage: python -I content_review.py <out.csv> <out.md>

Reads semantic/genichiro_product_moveset.csv (names, phases) and backend/seed/bosses.json (the current texts). One row
per proposed change of one field of one move, and one "keep everything" row per move with no proposal. Every proposal
below names its evidence (AI script, TAE, recordings, the owner's own words); a proposed text is a draft for the owner
to accept, edit or reject. Texts the owner does not change stay as they are; the five new moves get no text for now
(owner, 2026-10-15). Fandom-derived texts keep the boss-level Fandom source (owner, 2026-10-15).
The owner's review is read back from the .md on regeneration, matched by (move, field).
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

moveset = list(csv.DictReader(open(GT / "semantic/genichiro_product_moveset.csv", encoding="utf-8")))
seed = next(b for b in json.load(open(REPO / "backend/seed/bosses.json", encoding="utf-8")) if b["id"] == "genichiro-ashina")
current = {}
for p in seed["phases"]:
    for m in p["moves"]:
        current.setdefault(m["id"], m)

FIELD_ZH = {"description": "描述", "telegraph": "预兆", "counter": "应对方法", "common_mistakes": "常见失误", "move_type": "招式类型",
            "source_label": "来源说明"}

# slug -> [(field, new English, new Chinese, evidence)]; new text None = clear the field. move_type: (field, type, "", evidence).
PROPOSALS = {
    "perilous-attack-follow-up-phase-3": [
        ("description",
         "Delivers an overhead smash while airborne, then one of three follow-ups: a Perilous Thrust, a Perilous Sweep, "
         "or a quick upward cut that, if perfectly deflected, is followed by a delayed Perilous Thrust.",
         "跃起在空中向下重砸，然后接三种后续之一：危·突刺、危·下段横扫，或者一记快速上挑；上挑被完美弹开后，他会再接一记延迟的危·突刺。",
         "只把\"被弹开\"改成\"被完美弹开\":你确认(2026-10-15)完美弹开 3032 才接 3080,不完美弹开不会;第二次录像 3:38.6、5:11.8 两次 3032 → 8604/8704 → 3080"),
    ],
    "perilous-grab": [
        ("counter",
         "Perfect-deflect it, or step back to dodge it.",
         "完美弹反，或者向后垫步躲开。",
         "只保留你在 A04 写的两条(你定:不能打断就去掉 Fandom 那句)。Fandom 说\"攻击他能打乱他的平衡\",引擎证据不支持:"
         "投技 3020 整段(0–1.97 秒)和侧跳斩 3037 收招段(1.23–1.80 秒)带破绽标记 3710040,这时你出刀,弹刀 AI 出特殊弹刀 3102"
         "(特效 200230\"特殊弹刀动画播放\"),是他弹开你;3037 起手时你抢先出刀,他普通弹刀或出 8010,整招中止(录像 9 次里 7 次),也不是打出硬直"),
    ],
    "closing-tide": [
        ("description",
         "Slides and shoots one or two arrows, then rolls forward and slashes once. In Phase 1, it is almost always his "
         "first attack.",
         "滑步射出一到两支箭，然后向前翻滚斩击一次。第一阶段他的第一招几乎总是这招。",
         "\"一定\"改成\"几乎总是\":开场时天守阁 AI 只给 3014 → 3015 权重 600,但你冲刺或倒地时别的选项也有权重;两次录像一阶段都是以 3014 开场"),
    ],
    "floating-passage": [
        ("description",
         "A deadly seven-hit combo ending in a guard-breaking strike. In Phase 2, if you are more than about 4 m away when "
         "he finishes the fourth hit, he stops and shoots an arrow instead; in Phase 1 he never does.",
         "致命的七连击，最后一击能破防。二阶段他打完第 4 刀时，如果你在约 4 米外，他会停下改射一箭；一阶段不会这样。",
         "原文\"随时中断改为射箭\"不准:TAE 里 3040 在 3.27 秒(第 4 刀之后)、3092 在 2.7 秒(第 4、5 刀之间)加特效 5031;"
         "AI 只在剩余忍杀数 ≤ 1(二阶段)且你在 4.1 米外时改出 3017。射箭取消按你的决定(B13)写进飞渡浮舟的描述"),
        ("common_mistakes",
         "Backing far away during the combo in Phase 2 - he stops after the fourth hit and shoots an arrow.",
         "二阶段连击中退得太远——他打完第 4 刀会停下来射你一箭。",
         "原文说退远了他会用\"破防射击\"打断,但取消时射的是 3017,不是破防射击 3023;而且只在二阶段"),
    ],
    "guard-breaking-shot": [
        ("description",
         "Notches an arrow with incredible force, capable of breaking guard when released. He also uses it about half the "
         "time after his Hawk Shot hits you.",
         "以极大的力道拉弓，射出后能破防。鹰射打中你之后，他也有大约一半的概率接这一箭。",
         "可选的补充:AI 里鹰射 3044 命中后加特效 3710050,这时 50% 出 3023。原来的描述保留"),
    ],
    "two-hit-combo": [
        ("description",
         "Spins his body, slashing, then kicks right after.",
         "转身斩击，紧接着踢一脚。",
         "删掉\"之后可能接破防射击\":AI 里这一招(P12-02)只有 3003 → 3045;录像里那次 3045 之后的破防射击,你确认是你喝药触发的"),
    ],
    "deaths-thrust": [
        ("description",
         "Lunges forward, thrusting over a long distance. He almost always opens Phase 3 with this move. If it hits you, "
         "he follows up with a Perilous Grab.",
         "向前扑刺，突刺距离很长。第三阶段他几乎总以这招开场。这一下打中你的话，他会接危·投技。",
         "\"一定开场\"改\"几乎总是\":三阶段开场 AI 给 3008 权重 30000,但你倒地时 3043 权重是 10¹²;第二次录像以 3008 开场。"
         "\"可能接危·投技\"改成\"打中你才接\":3009 只由特效 3711000(3008 命中)触发,录像 4 次都是 3008 命中后立刻接 3009。"
         "预兆\"危字\"不变:录像 3:11.8 截图看得到危字(那次正是你喝药触发的)"),
    ],
    "perilous-grab-phase-3": [
        ("description",
         "Follows his Sword Dive Thrust when it hits you: he grabs Wolf, throws him to the ground and stabs him in the chest.",
         "跳起突刺打中你之后接出：抓住狼，摔在地上并刺穿胸口。",
         "原文\"冲向狼试图抓住他\"像是单独出的招,但天守阁 AI 只在跳起突刺 3008 命中时(特效 3711000)出 3009;录像 4 次都是这样"),
    ],
    "perilous-attack": [
        ("description",
         "When you are knocked down within about 5 m of him, he leaps and stabs down at you.",
         "你倒地时，如果离他 5 米以内，他会跳起向下刺你。",
         "原文\"冲过来下落攻击\"没说触发:AI 里 3022 只在你倒地(玩家特效 109031/110125)且 5 米内时出;和你起的名字\"倒地后跳刺危攻击\"一致"),
        ("counter",
         "Hard to Mikiri Counter; dodge sideways.",
         "很难识破，只能侧闪。",
         "你在目录里给 3022 的标注:\"你倒地时出,很难识破,只能侧闪\""),
        ("move_type", "thrust", "",
         "可选:现在是 unblockable(不可防御);你标的是危·突刺,产品里危·突刺用的类型是 thrust"),
    ],
    "perilous-sweep": [
        ("description",
         "Sweeps the floor. In Phases 1 and 2 he follows up with an arrow shot; in Phase 3 he does not.",
         "贴地横扫。一二阶段之后会接一箭，三阶段不接。",
         "三阶段加进来的两种(B06 侧步 5202 → 3007、B22 单独的 3067)都不接射箭;一二阶段是 3007 → 3011(一箭)"),
        ("counter",
         "Jump over it. Kicking him from the jump while the sweep is active deals eight times the usual posture damage.",
         "跳起来躲开。横扫期间跳起踩他，躯干伤害是平时的 8 倍。",
         "TAE:3007、3067 在 0–2.23 秒带特效 400200,参数表里\"对地攻击\"的躯干伤害倍率是 8.0(社区名:姿态低时跳踩有效)"),
    ],
    "receding-tide": [
        ("description",
         "Slides back and shoots two arrows at the same time, then closes in with an Iaijutsu, a quick drawn strike; about "
         "half the time he adds two more slashes.",
         "向后滑步同时射出两支箭，然后突进一记居合斩（快速拔刀斩）；大约一半的时候还会再接两刀。",
         "居合斩并进了退潮(A19):AI 里 3018(一个动画两支箭)→ 3019,之后 50% 再接 3029(两击);原来居合斩的描述\"快速拔刀斩\"并进来"),
        ("move_type", "combo", "",
         "现在是 ranged(远程);并进居合斩之后这一招有近战部分,和涨潮(射箭 + 翻滚斩,combo)一样改成 combo"),
    ],
    "floating-passage-phase-3": [
        ("description",
         "A deadly seven-hit combo ending in a guard-breaking strike. If you perfectly deflect the last hit, he follows "
         "with a delayed Perilous Thrust; otherwise the first variant ends with a Perilous Sweep. In the first variant, if "
         "you are far away when he finishes the fourth hit, he switches: a Sword Dive Thrust at about 5.5–11 m, two arrows "
         "beyond 11 m.",
         "致命的七连击，最后一击能破防。完美弹开最后一下，他会再接一记延迟的危·突刺；没有完美弹开的话，第一套最后接危·下段横扫。"
         "第一套打完第 4 刀时如果你离得远：约 5.5–11 米改出跳起突刺，11 米以外改射两箭。",
         "AI:3040 在 3.3 秒加特效 5029,5.5–11 米出 3008、11 米外出 3018(一次两箭),第二套 3092 没有这个检查点;第一套是 3040 → 3041 → 3067;"
         "完美弹开最后一下(攻击判定 292)放 8604,三阶段接 3080。射箭取消按你的决定(B14)写进三阶段飞渡浮舟"),
    ],
    "slash-combo": [("move_type", "combo", "", "新增招式,文字先留空(你在 2026-10-15 决定);类型按两段都是连斩定为 combo")],
    "horizontal-slash": [("move_type", "combo", "", "新增招式,文字先留空;单刀斩击,产品里近战普通攻击都用 combo")],
    "backstep-shot": [("move_type", "ranged", "", "新增招式,文字先留空;后撤后射一箭(c7100 的 3009 是飞行物动画)")],
    "counter-slash": [("move_type", "counter", "", "新增招式,文字先留空;拼刀后的反击。counter 类型现在用在两个猫头鹰的识破反击上,意思是\"他针对你的动作出的反击\"")],
    "deflect-counter-slash": [("move_type", "counter", "", "新增招式,文字先留空;他强弹开你之后的反击,同上")],
}
SOURCE_ROW = ("来源说明", "Source:", "来源：", "Some descriptions from:", "部分描述来自：",
              "招式表底部那行\"来源：Fandom\"是整个弦一郎招式表共用的。上面改写的描述有的不再出自 Fandom,新增招式也不是;"
              "改成\"部分描述来自：Fandom\"就不会让人以为所有内容都来自 Fandom。这是全站共用的一句,其他 Boss 也会显示成\"部分描述来自\"")

rows = []
by_slug = {r["slug"]: r for r in moveset}
for r in moveset:
    slug, cur = r["slug"], current.get(r["slug"], {})
    props = PROPOSALS.get(slug, [])
    if not props:
        texts = "；".join(f"{FIELD_ZH[f]}:{cur[f + '_zh']}" for f in ("description", "telegraph", "counter", "common_mistakes") if cur.get(f + "_zh"))
        rows.append({"slug": slug, "field": "keep", "name": r["name_zh"], "phases": r["phases"], "change": r["change"],
                     "current_zh": texts or "(没有文字)", "current_en": "", "new_zh": "全部保留", "new_en": "",
                     "evidence": "没有发现和 AI、TAE、录像矛盾的地方"})
    for field, new_en, new_zh, ev in props:
        if field == "move_type":
            now = cur.get("move_type", "(新增,还没有)")
            rows.append({"slug": slug, "field": field, "name": r["name_zh"], "phases": r["phases"], "change": r["change"],
                         "current_zh": now, "current_en": "", "new_zh": new_en, "new_en": "", "evidence": ev})
        else:
            rows.append({"slug": slug, "field": field, "name": r["name_zh"], "phases": r["phases"], "change": r["change"],
                         "current_zh": cur.get(field + "_zh") or "(空)", "current_en": cur.get(field) or "",
                         "new_zh": new_zh, "new_en": new_en, "evidence": ev})
rows.append({"slug": "(全部 Boss)", "field": "source_label", "name": SOURCE_ROW[0], "phases": "", "change": "",
             "current_zh": SOURCE_ROW[2], "current_en": SOURCE_ROW[1], "new_zh": SOURCE_ROW[4], "new_en": SOURCE_ROW[3],
             "evidence": SOURCE_ROW[5]})
assert all(s in by_slug for s in PROPOSALS), set(PROPOSALS) - set(by_slug)

# the owner's review, matched by (move, field)
reviews = {}
if Path(out_md).exists():
    for line in open(out_md, encoding="utf-8"):
        m = re.match(r"^\| (D\d{2}) \|([^|]*)\|([^|]*)\| `([^`]*)` \| [^|]*\| ([a-z_]+) \|", line)
        if m:
            reviews[(m.group(4), m.group(5))] = (m.group(2).strip() or "☐", m.group(3).strip())
for i, r in enumerate(rows, 1):
    r["key"] = f"D{i:02d}"
    r["review_mark"], r["owner_reason"] = reviews.get((r["slug"], r["field"]), ("☐", ""))
    r["owner_review"] = "不通过" if "❌" in r["review_mark"] else ("通过" if "✅" in r["review_mark"] else "待审核")
    r["character"] = "c7100"

FIELDS = ["key", "slug", "name", "phases", "change", "field", "current_zh", "current_en", "new_zh", "new_en", "evidence",
          "character", "owner_review", "owner_reason"]
with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\r\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in FIELDS})


def cell(x):
    return (x or "—").replace("|", "｜").replace("\n", " ")


n_change = sum(1 for r in rows if r["field"] != "keep")
md = ["# 第 8 步:弦一郎招式文字复核(待你决定)", "",
      "由 `scripts/ai/content_review.py` 生成,数据在 `genichiro_content_review.csv`。依据是招式清单 `genichiro_product_moveset.md` 和种子数据里现在的文字。", "",
      f"- {n_change} 条修改建议,每条是\"某个招式的某个字段\";{len(rows) - n_change} 个招式没发现问题,各一条\"全部保留\"。",
      "- 建议的文字是我按证据起的草稿,中英文都要进产品。你可以直接改:❌ 并在理由栏写你要的文字。",
      "- 新增的 5 个招式先不写描述、预兆和应对方法(你在 2026-10-15 决定),这里只定它们的招式类型。",
      "- 还在用 Fandom 文字的招式保留出处,新增招式不加来源(你在 2026-10-15 决定)。", "",
      "用鼠标:`python -I research/ground_truth/scripts/ai/catalog_review.py 8765 content`,然后在 VS Code 里打开 http://127.0.0.1:8765。", "",
      "| 编号 | 审核 | 理由 | 招式 | 招式名 | 字段 | 现在(中文) | 建议(中文) | 问题和证据 |",
      "|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['key']} | {r['review_mark']} | {r['owner_reason']} | `{r['slug']}` | {cell(r['name'])} | {r['field']} "
              f"| {cell(r['current_zh'])} | {cell(r['new_zh'])} | {cell(r['evidence'])} |")
md.append("")
with open(out_md, "w", encoding="utf-8", newline="") as fh:
    fh.write("\r\n".join(md))

sys.stdout.reconfigure(encoding="utf-8")
print(f"{len(rows)} rows: {n_change} proposals, {len(rows) - n_change} keep")
