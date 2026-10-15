"""Draft the castle Genichiro move catalog: one entry per animation chain the castle battle AI can request.

Usage:
    python -I catalog.py <decompiled_ai_dir> <tae_dir> <out.csv> <out.md>

    decompiled_ai_dir  lua50_decompile.py output: 710000_battle.txt, 711000_battle.txt
    tae_dir            tae_dump.py output: c7100_tae.json, c7110_tae.json

Also reads, from research/ground_truth:
    engine/genichiro_castle_ai_reachability.csv                  which AI options the castle fight uses, per animation
    observations/vanilla/genichiro/*-castle/occurrences.csv     every castle recording: occurrences per phase (summed)
                                                                and the first time each animation was seen

An AI option (ActNN, KengekiNN, a request inside Interrupt, Parry, Damaged) usually requests one complete move
chain. Options that request the same chain become one entry. The chain text comes from ai_flowchart.py, with the
castle's fixed facts applied: the boss has SpEffect 200050 and never 3711500, so branches that need 3711500 are
dropped and conditions on 200050 are always true.

An entry is a move candidate when its chain contains an attack or projectile animation; the rest (guards,
deflects, steps) are listed as not moves. Families, wiki candidates and triggers are proposals written from the
evidence named in each row. The project owner confirms every name, grouping and variant, in the 审核 and 理由 columns
of the .md; those are read back and kept when the catalog is regenerated.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import ai_flowchart as af  # noqa: E402

ai_dir, tae_dir, out_csv, out_md = sys.argv[1:5]
RECS = sorted(p for p in (GT / "observations/vanilla/genichiro").glob("*-castle") if (p / "occurrences.csv").exists())
CASTLE = {"710000": ("c7100", ("1", "2")), "711000": ("c7110", ("3",))}

# What makes the AI pick each option, read from the decompiled scripts (see engine/genichiro_castle_ai.md).
# "计数" is the AI's clash counter (counter 0): +1 per clash at close range, cleared by his big moves and deathblows.
TRIGGERS = {
    ("710000", "Act01"): "主动选招:3–5 米(权重 5,约 7%);你冲刺时任何距离(5)",
    ("710000", "Act02"): "主动选招:3–5 米(10);你冲刺时(5);他出 3063/3068 后 10 秒内不选",
    ("710000", "Act03"): "主动选招:≤ 3 米(15);你冲刺时(5);7 秒冷却",
    ("710000", "Act06"): "主动选招:3–5 米(30)",
    ("710000", "Act09"): "主动选招:3–7 米、体干剩余 ≤ 360、你没在冲刺;3–5 米约 80%;冷却 30 秒,与 3092、3028 共用",
    ("710000", "Act10"): "主动选招:≥ 5 米(300);你冲刺时(30)",
    ("710000", "Act11"): "主动选招:≤ 5 米(15);你冲刺时(5)",
    ("710000", "Act15"): "主动选招:开场第一招(600);≥ 7 米(600);你冲刺时不选",
    ("710000", "Act16"): "你倒地时(玩家特效 109031/110125)且 ≤ 5 米(100)",
    ("710000", "Act22"): "你在他身后时(权重 1,约 1%)",
    ("710000", "Act24"): "主动选招:≤ 3 米(30);3044 只在他体干剩余 ≤ 70% 时接",
    ("710000", "Act31"): "主动选招:≤ 3 米(30);你冲刺时不选",
    ("710000", "Act34"): "主动选招:5–7 米(100,约 12–20%)",
    ("710000", "Act48"): "主动选招:只在你冲刺时(30)",
    ("710000", "Damaged"): "被你打中时:15% 后跳 5201,另 15% 出 3009",
    ("710000", "Kengeki01"): "拼刀后:计数 < 2 时(他被弹开,< 2.5 米;或他弱弹开你),与 3055 轮流",
    ("710000", "Kengeki02"): "他强弹开你之后(100);3044 只在他体干剩余 ≤ 70% 时接",
    ("710000", "Kengeki03"): "拼刀后:计数 ≥ 2(他被弹开)或 ≥ 3(他弱弹开你)(60)",
    ("710000", "Kengeki04"): "拼刀后:他被弹开、< 2.5 米、计数 < 2,与 3050 轮流",
    ("710000", "Kengeki10"): "他强弹开你之后(200211)(50)",
    ("710000", "Kengeki14"): "他弱弹开你之后、计数 < 3(50)",
    ("710000", "Kengeki15"): "拼刀后:计数 ≥ 2、你弹开他、< 2.5 米(30,约 11–12%)",
    ("710000", "Kengeki17"): "他强弹开你之后(200210)(100)",
    ("710000", "Kengeki30"): "拼刀后:计数 ≥ 2、你弹开他(200200)(5,约 2%)",
    ("710000", "Kengeki31"): "他强弹开你之后(50,约 14–20%);计数 ≥ 3 后他弱弹开你(15)",
    ("710000", "Kengeki32"): "拼刀后:计数 ≥ 2,与 Kengeki33 轮流",
    ("710000", "Kengeki33"): "拼刀后:计数 ≥ 2,与 Kengeki32 轮流",
    ("710000", "Kengeki38"): "拼刀后:计数 ≥ 2(30–100);他强弹开你之后(50)",
    ("710000", "Kengeki39"): "拼刀后:计数 ≥ 2、你弹开他(30)",
    ("710000", "Kengeki40"): "任何拼刀后:他 HP ≤ 75% 且共用冷却已过(50)",
    ("710000", "Kengeki43"): "拼刀后:计数 ≥ 2(10–50)",
    ("710000", "Interrupt:3017"): "仅二阶段:3040 打完第 4 刀(约 3.27 秒)、或 3092 打完第 4 刀(约 2.7 秒)时,你在 4.1 米外",
    ("710000", "Interrupt:3023"): "你使用道具时(包括喝药);或他的 3044 命中后 50%(特效 3710050)",
    ("710000", "Interrupt:3092"): "你弹开 3063 或 3068 的第二刀(他带 3710032 时被弹开)",
    ("710000", "Parry"): "你攻击时他弹开你:第一刀 3100,1 秒内的下一刀 3101",
    ("710000", "ShootReaction"): "被你的飞行物打中时",
    ("711000", "Act01"): "主动选招:≤ 5 米(5);开场(1);你冲刺时(5)",
    ("711000", "Act02"): "主动选招:≤ 3 米(10);你冲刺时(5)",
    ("711000", "Act03"): "主动选招:≤ 3 米(5);你冲刺时(5);7 秒冷却",
    ("711000", "Act06"): "主动选招:3–7 米(5)",
    ("711000", "Act09"): "主动选招:5–7 米(30)、3–5 米(15)、≤ 3 米且体干剩余 ≤ 75%(300);你没在冲刺;冷却 20 秒,与 3092、3028 共用",
    ("711000", "Act10"): "主动选招:5–7 米(10);你冲刺时(30)",
    ("711000", "Act13"): "你在他身后时(100);3039 只在 15 秒冷却已过时接",
    ("711000", "Act15"): "主动选招:7–10 米(5,约 8–14%);你冲刺时不选",
    ("711000", "Act17"): "主动选招:≤ 3 米(30);15 秒冷却",
    ("711000", "Act18"): "主动选招:3–10 米(30);你倒地时几乎必出;15 秒冷却",
    ("711000", "Act19"): "主动选招:≤ 5 米(20–30);你冲刺且 ≤ 4 米(30);15 秒冷却",
    ("711000", "Act20"): "开场第一招(几乎必出);≥ 7 米(30);你冲刺时不选",
    ("711000", "Act22"): "你在他身后时(100,约一半)",
    ("711000", "Act48"): "主动选招:只在你冲刺时(30,约 40%)",
    ("711000", "Kengeki01"): "拼刀后:计数 < 2 时你弹开他;或他弱弹开你(50)",
    ("711000", "Kengeki02"): "拼刀后:计数 ≥ 2、你弹开他(10)",
    ("711000", "Kengeki04"): "拼刀类型 200206、弱弹计数 ≤ 4(100)",
    ("711000", "Kengeki14"): "拼刀类型 200206、弱弹计数 ≤ 4(50)",
    ("711000", "Kengeki15"): "拼刀后:计数 ≥ 2(10–30)",
    ("711000", "Kengeki17"): "他强弹开你之后(200210)(100)",
    ("711000", "Kengeki20"): "拼刀后(10–50);他两侧没有空间时不选",
    ("711000", "Kengeki30"): "拼刀后:计数 ≥ 2(5–45);弱弹计数 > 4 时(500)",
    ("711000", "Kengeki31"): "他强弹开你之后(50,约 25–50%);计数 ≥ 2 后的拼刀(5–15)",
    ("711000", "Kengeki32"): "拼刀后:计数 ≥ 2,与 Kengeki33 轮流(20–500)",
    ("711000", "Kengeki33"): "拼刀后:计数 ≥ 2,与 Kengeki32 轮流(20–500)",
    ("711000", "Kengeki35"): "拼刀类型 200206、弱弹计数 > 4(100)",
    ("711000", "Kengeki38"): "拼刀后:计数 ≥ 2(5–30);他强弹开你之后(50)",
    ("711000", "Kengeki39"): "拼刀后:计数 ≥ 2、他弱弹开你(10)",
    ("711000", "Kengeki40"): "任何拼刀后:他 HP ≤ 75% 且共用冷却已过(50)",
    ("711000", "Kengeki43"): "拼刀后:计数 ≥ 2、他弱弹开你(10)",
    ("711000", "Kengeki44"): "拼刀后:计数 ≥ 2、他弱弹开你(10)",
    ("711000", "Kengeki45"): "你弹开他、距离 ≥ 2.5 米(60);15 秒冷却",
    ("711000", "Kengeki46"): "拼刀后的多种情况(60–100);15 秒冷却",
    ("711000", "Interrupt:3008"): "你在 12.5 米内使用道具(包括喝药);或 3040 播到约 3.3 秒时你在 5.5–11 米",
    ("711000", "Interrupt:3009"): "触发特效 3711000(社区名:冲刺八艘飞突刺命中)",
    ("711000", "Interrupt:3018"): "3040 播到约 3.3 秒时你在 11 米外",
    ("711000", "Interrupt:3080"): "他放 8604 或 8704 时(两者都加特效 5030),100%:你完美弹开飞渡浮舟的最后一下或 3032 之后;不完美弹开不会出",
    ("711000", "Interrupt:3092"): "你弹开 3063 或 3068 的第二刀(他带 3710032 时被弹开)",
    ("711000", "Parry"): "你攻击时他弹开你:第一刀 3100,1 秒内的下一刀 3101",
    ("711000", "ShootReaction"): "被你的飞行物打中时",
}

# Family proposals: (family, variant, basis). "已确认" in the basis means the owner confirmed it.
FAMILY = {
    ("710000", "Act09"): ("飞渡浮舟", "第一套", "已确认(2026-10-12)"),
    ("711000", "Act09"): ("飞渡浮舟", "第一套(三阶段接 3067)", "已确认(2026-10-12)"),
    ("710000", "Kengeki31"): ("飞渡浮舟", "第二套的起手", "已确认:3068 + 3092 是第二套"),
    ("711000", "Kengeki31"): ("飞渡浮舟", "第二套的起手", "已确认:3068 + 3092 是第二套"),
    ("710000", "Interrupt:3092"): ("飞渡浮舟", "第二套", "已确认:3068 + 3092 是第二套"),
    ("711000", "Interrupt:3092"): ("飞渡浮舟", "第二套", "已确认:3068 + 3092 是第二套"),
    ("710000", "Kengeki40"): ("飞渡浮舟", "第三套", "已确认:3028 是完整的一套"),
    ("711000", "Kengeki40"): ("飞渡浮舟", "第三套", "已确认:3028 是完整的一套"),
    ("710000", "Kengeki30"): ("飞渡浮舟", "第二套的另一种起手", "已确认(2026-10-13):3063 也是飞渡浮舟的起手;两刀和 3068 完全相同,弹开第二刀同样接 3092"),
    ("711000", "Kengeki30"): ("飞渡浮舟", "第二套的另一种起手", "已确认(2026-10-13):3063 也是飞渡浮舟的起手;两刀和 3068 完全相同,弹开第二刀同样接 3092"),
    ("710000", "Interrupt:3017"): ("飞渡浮舟", "衍生:射箭取消 floating-passage-cancel(二阶段,第一套或第二套打到一半、你在 4.1 米外)",
                                   "已确认(2026-10-15):3017 是飞渡浮舟的衍生 floating-passage-cancel;2026-10-13 归入射箭招式族是你的疏忽,已改"),
    ("711000", "Interrupt:3080"): ("飞渡浮舟", "三阶段完美弹完之后的突刺;完美弹开 3032 之后也接它",
                                   "已确认:8604 之后三阶段固定出突刺;完美弹开 3032 之后也接 3080,不完美弹开不会(2026-10-15)"),
    ("710000", "Kengeki38"): ("危攻击后续追击(建议)", "", "3030 起手,一阶段接 3025(你标为危·突刺),二阶段 75% 接 3067(危·下段);两个 wiki 都写一阶段突刺、二阶段扫腿"),
    ("711000", "Kengeki38"): ("危攻击后续追击(建议)", "三阶段", "3030 起手后三选一(3067、3025、3032),对应 Fandom 写的三阶段三种结尾"),
    ("711000", "Act18"): ("巴之雷(建议)", "", "你说 3043 是三阶段的打雷招式"),
    ("711000", "Kengeki32"): ("巴之雷(建议)", "拼刀后", "以 3043 结尾;你说 3043 是三阶段的打雷招式"),
}

# Product moves (semantic/wiki_mapping/genichiro-ashina.json) that an entry may correspond to, with the basis.
WIKI = {
    ("710000", "Act09"): ("floating-passage", "你确认的飞渡浮舟第一套"),
    ("711000", "Act09"): ("floating-passage-phase-3", "你确认的飞渡浮舟第一套,三阶段"),
    ("710000", "Kengeki31"): ("floating-passage", "你确认的飞渡浮舟第二套"),
    ("711000", "Kengeki31"): ("floating-passage-phase-3", "你确认的飞渡浮舟第二套,三阶段"),
    ("710000", "Interrupt:3092"): ("floating-passage", "你确认的飞渡浮舟第二套"),
    ("711000", "Interrupt:3092"): ("floating-passage-phase-3", "你确认的飞渡浮舟第二套,三阶段"),
    ("710000", "Kengeki40"): ("floating-passage", "你确认的飞渡浮舟第三套"),
    ("711000", "Kengeki40"): ("floating-passage-phase-3", "你确认的飞渡浮舟第三套,三阶段"),
    ("710000", "Interrupt:3017"): ("Fextralife 的 Floating Passage Cancel", "触发条件和射箭取消一致;你确认它是飞渡浮舟的衍生 floating-passage-cancel(2026-10-15)"),
    ("710000", "Kengeki30"): ("floating-passage", "你确认的飞渡浮舟第二套起手"),
    ("711000", "Kengeki30"): ("floating-passage-phase-3", "你确认的飞渡浮舟第二套起手,三阶段"),
    ("710000", "Kengeki38"): ("perilous-attack-follow-up、perilous-attack-follow-up-phase-2", "按阶段换结尾,和 wiki 一致"),
    ("711000", "Kengeki38"): ("perilous-attack-follow-up-phase-3", "三种结尾,和 Fandom 一致"),
    ("711000", "Interrupt:3080"): ("floating-passage-phase-3、perilous-attack-follow-up-phase-3",
                                   "你确认:完美弹开飞渡浮舟的最后一下或 3032(危攻击后续追击的第三种结尾)之后都接 3080(2026-10-15)"),
    ("710000", "Interrupt:3023"): ("guard-breaking-shot", "wiki:用来惩罚喝药;这里由你使用道具触发,3023 是飞行物"),
    ("711000", "Interrupt:3008"): ("deaths-thrust", "wiki:用来惩罚喝药/用道具;这里由你使用道具触发"),
    ("711000", "Act20"): ("deaths-thrust", "和用道具时触发的是同一个动画 3008"),
    ("710000", "Act11"): ("perilous-grab", "3020 你标为危·抓投"),
    ("710000", "Act31"): ("two-hit-combo", "你确认(2026-10-15):3003 → 3045 就是横砍踢击 / Slash into Back Kick"),
    ("710000", "Kengeki43"): ("perilous-thrust", "3062 你标为危·突刺;但 3025 也是危·突刺,需要你区分"),
    ("711000", "Act18"): ("lightning-of-tomoe-slash / -smash / -shot", "3043 是打雷招式,具体是哪一个待你确认"),
}

# Owner labels (2026-10-10 perilous labels for c7100; 2026-10-12 confirmations).
OWNER = {
    ("c7100", 3007): "危·下段", ("c7100", 3020): "危·抓投", ("c7100", 3021): "危·下段",
    ("c7100", 3022): "危·突刺(你倒地时出,很难识破,只能侧闪)", ("c7100", 3025): "危·突刺", ("c7100", 3027): "不确定",
    ("c7100", 3032): "下段(非危)", ("c7100", 3048): "下段(非危)", ("c7100", 3062): "危·突刺",
    ("c7100", 3067): "危·下段", ("c7100", 3080): "危·突刺",
}
for c in ("c7100", "c7110"):
    for a, lab in ((3040, "飞渡浮舟·第一套"), (3041, "飞渡浮舟·第一套"), (3068, "飞渡浮舟·第二套"),
                   (3092, "飞渡浮舟·第二套"), (3028, "飞渡浮舟·第三套")):
        OWNER[(c, a)] = "；".join(x for x in (OWNER.get((c, a)), lab) if x)
OWNER[("c7110", 3080)] = "飞渡浮舟或 3032 被完美弹开后的突刺(三阶段;2026-10-15 加上 3032)"
OWNER.update({("c7110", 3009): "危·投技", ("c7110", 3039): "危·雷电", ("c7110", 3042): "危·雷电",
              ("c7110", 3062): "危·突刺"})  # owner, 2026-10-13
OWNER[("c7100", 3045)] = "踢一脚(横砍踢击 3003 → 3045 的第二段;2026-10-15)"
OWNER[("c7110", 3007)] = "危·下段"  # owner, 2026-10-15; c7100 3007 was 下段(非危) until the owner corrected it the same day

# Notes the owner asked for while reviewing (2026-10-13), with the evidence checked in the decompiled AI.
NOTES = {
    ("710000", "Act01"): "两条分支都在天守阁 AI 710000 里(心中的弦一郎 710300 完全相同),一、二阶段 30% 走 3002 → 3003,70% 走 3010 → 3025。"
                         "每一段都要你还在距离内才接下一段:走 3002 那条,3001 和 3002 都要约 3.4 米内;走 3010 那条,3001 要 3.5 米内,3010 要 5 米内。3010 从没录到;你决定按 AI 文件收录(2026-10-13)。",
    ("711000", "Act01"): "两条分支都在天守阁 AI 711000 里(心中的弦一郎 711300 相同,只多一个计数),三阶段 70% 走 3002 → 3003,30% 走 3010 → 3025。"
                         "每一段都要你还在距离内才接下一段:走 3002 那条,3001 和 3002 都要约 3.4 米内;走 3010 那条,3001 要 3.5 米内,3010 要 5 米内。3002、3003、3010 都没录到;你决定按 AI 文件收录(2026-10-13)。",
    ("710000", "Act34"): "在天守阁 AI 710000 里:注册为第 34 个选项,5–7 米时权重 100,只有序章(带 200051)会清零;心中的弦一郎 710300 里也有同样的 Act34。"
                         "15 秒内出过 3007 时权重降为 1。你确认原版有这招(2026-10-13),但还没录到。",
}
# Confirmed by the owner on 2026-10-15, from the recording check (observations/vanilla/genichiro/chain_check.md).
NOTES.update({
    ("711000", "Kengeki38"): "3032 被你完美弹开时,他放 8604 或 8704,随后出突刺 3080(P3-30);不完美弹开不会(你确认,2026-10-15)。"
                             "第二次录像里有两次(3:38.6、5:11.8)。和 Fandom 写的第三种结尾“上挑,被弹开后接延迟危·突刺”一致。",
    ("711000", "Interrupt:3080"): "三阶段 AI 在他身上出现特效 5030 时出 3080;TAE 里只有 8604 加 5030,8704 完全借用 8604。"
                                  "3032 和飞渡浮舟三套的最后一下(3028、3041、3092)带同一个攻击判定 292。"
                                  "录到的两次 3080 都在完美弹开 3032 之后;完美弹开飞渡浮舟之后的 3080 还没录到。",
    ("710000", "Act34"): NOTES[("710000", "Act34")] + "3007 是危·下段(你确认,2026-10-15;之前标的“下段(非危)”是看漏了):"
                         "TAE 里 3007 在 0.6 秒调用飞行物行为 980,和其他危字招式一样,三阶段录像里在这个时间看得到危字;0–2.23 秒带特效 400200,跳踩的体干伤害 ×8。",
    ("711000", "Kengeki20"): "3007 是危·下段(你确认,2026-10-15):0.6 秒出危字(录像 4:05.8、6:32.1 截图可见),0–2.23 秒跳踩的体干伤害 ×8(特效 400200)。",
    ("710000", "Interrupt:3023"): "两次录像里的 3 次 3023 都是你喝药或使用道具时出的(你确认,2026-10-15:第一次录像 1:02.9、1:59.9,第二次 2:05.3)。",
    ("711000", "Interrupt:3008"): "喝药也会触发;你确认录像里三阶段有一次 3008 是你喝药时出的(2026-10-15)。",
})

CASTLE_FACTS = [  # applied to the chain text: castle Genichiro has 200050 and never 3711500
    (re.compile(r"\[Boss有特效3711500(?: 且 计时器8已到)?: \d+ ｜ 否则: ([^\[\]]+)\]"), r"\1"),
    (re.compile(r" 且 非 Boss有特效3711500"), ""),
    (re.compile(r" 且 Boss有特效200050"), ""),
]

# ---------------------------------------------------------------- inputs
reach = list(csv.DictReader(open(GT / "engine/genichiro_castle_ai_reachability.csv", encoding="utf-8")))
info = {(r["character"], int(r["anim"][5:])): r for r in reach}
options = defaultdict(set)        # (ai, option) -> animation IDs it requests at the castle
for r in reach:
    for p in filter(None, r["castle_ai_paths"].split("; ")):
        ai, fn = p.split(":")
        anim = int(r["anim"][5:])
        options[(ai, f"Interrupt:{anim}" if fn == "Interrupt" else fn)].add(anim)

counts = defaultdict(int)          # (character, animation) -> occurrences over all castle recordings
first_seen = {}                    # (character, animation) -> (recording date, start time) of the earliest occurrence
for rec_dir in RECS:
    for r in csv.DictReader(open(rec_dir / "occurrences.csv", encoding="utf-8")):
        key = (r["character"][:5], int(r["anim"][5:]))
        counts[key] += 1
        if key not in first_seen:  # recordings in date order, occurrences in time order
            first_seen[key] = (rec_dir.name[:10], float(r["start_time"]))

hits = {}
for c in ("c7100", "c7110"):
    tae = json.load(open(f"{tae_dir}/{c}_tae.json", encoding="utf-8"))["animations"]
    by = {a["id"]: a for a in tae}
    for a in tae:
        src = a
        while src["kind"] == "import_other_anim":
            src = by[src["imports_from"]]
        # distinct attack windows: overlapping or touching windows are one hit; judge -1 is an empty event
        wins = sorted((e["start_frame_30"], e["end_frame_30"]) for e in src["events"]
                      if e["type"] == 1 and e["params"].get("BehaviorJudgeID", 0) >= 0)
        n, end = 0, None
        for st, en in wins:
            if end is None or st > end:
                n += 1
                end = en
            else:
                end = max(end, en)
        hits[(c, a["id_int"])] = n

# ---------------------------------------------------------------- entries
entries = {}
for ai, (char, phases) in CASTLE.items():
    funcs = af.split_functions(open(f"{ai_dir}/{ai}_battle.txt", encoding="utf-8").read())
    for (a, opt), anims in sorted(options.items()):
        if a != ai:
            continue
        if opt.startswith("Interrupt:"):
            chain = opt.split(":")[1]
        else:
            lines = funcs["Goal." + opt]
            chain = af.inline(af.parse_function(lines), af.reg_names(lines), af.num_regs(lines))
            for pat, rep in CASTLE_FACTS:
                chain = pat.sub(rep, chain)
        e = entries.setdefault((char, chain), {"character": char, "ai": ai, "chain": chain, "options": [], "anims": set()})
        e["options"].append(opt)
        e["anims"] |= anims


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


rows = []
for (char, chain), e in entries.items():
    ai = e["ai"]
    anims = sorted(e["anims"])
    cats = {a: info[(char, a)]["category"] for a in anims}
    combat = [a for a in anims if cats[a] in ("attack", "bullet")]
    phase_cols = ("1", "2") if char == "c7100" else ("3",)
    rec = {a: counts[(char, a)] for a in anims}
    seen = [a for a in combat if rec[a]]
    if not combat:
        evidence = ""
    elif len(seen) == len(combat):
        evidence = "已运行观察"
    elif seen:
        evidence = "部分运行观察"
    else:
        evidence = "仅静态证据"
    if char == "c7100":
        only2 = [a for a in anims if info[(char, a)]["castle_ai_phase1"] == "no"]
        ph = "2" if len(only2) == len(anims) else "1、2"
        note = f"{'、'.join(map(str, only2))} 仅二阶段" if only2 and ph != "2" else ""
    else:
        ph, note = "3", ""
    keys = [(ai, o) for o in e["options"]]
    fam = next((FAMILY[k] for k in keys if k in FAMILY), ("", "", ""))
    wiki = next((WIKI[k] for k in keys if k in WIKI), ("", ""))
    rows.append({
        "character": char, "phases": ph, "kind": "move" if combat else "not_move",
        "ai_options": "、".join(f"{ai}:{o}" for o in e["options"]),
        "chain": chain,
        "trigger": "；".join(dict.fromkeys(TRIGGERS.get(k, "") for k in keys if TRIGGERS.get(k))),
        "attack_anims": " ".join(f"{a}({hits[(char, a)]}击)" for a in anims if cats[a] == "attack"),
        "bullet_anims": " ".join(str(a) for a in anims if cats[a] == "bullet"),
        "other_anims": " ".join(str(a) for a in anims if cats[a] == "other"),
        "recorded": " ".join(f"{a}:{rec[a]}" for a in combat),
        "first_seen": " ".join(f"{a}@{first_seen[(char, a)][0][5:]} {mmss(first_seen[(char, a)][1])}" for a in combat
                              if rec[a] and (char, a) in first_seen),
        "evidence": evidence,
        "family_proposed": fam[0], "variant_proposed": fam[1], "family_basis": fam[2],
        "wiki_candidate": wiki[0], "wiki_basis": wiki[1],
        "owner_labels": "；".join(f"{a} {OWNER[(char, a)]}" for a in anims if (char, a) in OWNER),
        "notes": "；".join(x for x in [note] + [NOTES[k] for k in keys if k in NOTES] if x),
    })

rows.sort(key=lambda r: (r["character"], r["kind"], min(int(x.split("(")[0]) for x in (r["attack_anims"] + " " + r["bullet_anims"] + " " + r["other_anims"]).split())))
counter = defaultdict(int)
for r in rows:
    pre = "P12" if r["character"] == "c7100" else "P3"
    if r["kind"] == "not_move":
        pre += "-N"
    counter[pre] += 1
    r["entry"] = f"{pre}-{counter[pre]:02d}"

shared = defaultdict(list)    # attack/bullet animation -> entries that contain it
for r in rows:
    for a in (r["attack_anims"] + " " + r["bullet_anims"]).split():
        shared[(r["character"], a.split("(")[0])].append(r["entry"])
for r in rows:
    others = sorted({x for a in (r["attack_anims"] + " " + r["bullet_anims"]).split()
                     for x in shared[(r["character"], a.split("(")[0])] if x != r["entry"]})
    r["shares_animations_with"] = " ".join(others)

# ---------------------------------------------------------------- the owner's review
# The owner reviews in the .md: the 审核 cell holds ☐ (not reviewed), ✅ (approved) or ❌ (rejected), and 理由 the reason.
# On regeneration those cells are read back and kept. They are matched through the previous CSV by
# (character, ai_options), not by entry number, so they stay with the right entry if entries are added or removed.
REVIEW_HEAD = "| 条目 | 审核 | 理由 |"


def review_status(mark):
    if "❌" in mark or "不通过" in mark:
        return "不通过"
    if "✅" in mark or "通过" in mark:
        return "通过"
    return "待审核"


def previous_reviews():
    if not (Path(out_csv).exists() and Path(out_md).exists()):
        return {}
    text = open(out_md, encoding="utf-8").read()
    if REVIEW_HEAD not in text:
        return {}
    key = {r["entry"]: (r["character"], r["ai_options"]) for r in csv.DictReader(open(out_csv, encoding="utf-8"))}
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\| (P\d+(?:-N)?-\d+) \|([^|]*)\|([^|]*)\|", line)
        if m and m.group(1) in key:
            mark, reason = m.group(2).strip(), m.group(3).strip()
            out[key[m.group(1)]] = (mark or "☐", "" if reason in ("", "—") else reason)
    return out


reviews = previous_reviews()
for r in rows:
    mark, reason = reviews.get((r["character"], r["ai_options"]), ("☐", ""))
    r["review_mark"] = mark
    r["owner_review"] = review_status(mark)
    r["owner_reason"] = reason

FIELDS = ["entry", "character", "phases", "kind", "ai_options", "chain", "trigger", "attack_anims", "bullet_anims",
          "other_anims", "recorded", "first_seen", "evidence", "family_proposed", "variant_proposed", "family_basis",
          "wiki_candidate", "wiki_basis", "owner_labels", "shares_animations_with", "notes", "owner_review", "owner_reason"]
with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in FIELDS})

# ---------------------------------------------------------------- review sheet
moves = [r for r in rows if r["kind"] == "move"]
md = ["# 天守阁弦一郎招式目录(草稿,待你审核)", "",
      "由 `scripts/ai/catalog.py` 从天守阁战斗 AI、TAE 和天守阁录像(" + "、".join(p.name[:10] for p in RECS) + ")生成,数据在 `genichiro_catalog.csv`。",
      "",
      "- \"录到次数\"是所有录像的合计;\"最早录到\"是第一次录到它的录像日期和录像内时间。",
      "",
      "- 一行是 AI 能请求的一整串动画(一个或几个 AI 选项),通常就是玩家眼中的一招。"
      "同一个动画可能出现在几行里,比如 3067 既是飞渡浮舟第一套在三阶段的结尾,也能单独出,见\"共用动画\"。",
      "- 招式族、变体、wiki 候选和触发条件都是建议,依据写在后面。标\"已确认\"的是你确认过的,其余等你审核。",
      "- 动画链里的条件按天守阁的情况化简过:天守阁的弦一郎带特效 200050,没有 3711500(剑圣战巴流的不死斩标记)。",
      "- 括号里的\"击\"是 TAE 里独立的攻击窗口个数:重叠或相连的攻击判定算一击,判定 ID 为 -1 的空事件不算。"
      "权重和条件的细节见 `engine/genichiro_castle_ai.md`。",
      "- 主动选招还有一个冷却:同一招 15 秒内出过,它的权重降为 1(公用 AI 函数 SetCoolTime)。",
      "",
      "## 怎么审核", "",
      "用鼠标审核:在终端运行 `python -I research/ground_truth/scripts/ai/catalog_review.py`,"
      "然后在 VS Code 里 Ctrl+Shift+P → Simple Browser: Show,打开 http://127.0.0.1:8765。"
      "每条有 ✅ / ❌ 按钮和理由框,点击就直接写进这个文件。",
      "",
      "也可以直接改这个文件:每张表的第 2、3 列是审核栏。",
      "",
      "1. 把\"审核\"栏的 ☐ 改成 ✅(通过)或 ❌(不通过)。",
      "2. 不通过时,在\"理由\"栏写具体理由。部分同意(比如名称对、分组不对)也标 ❌,把哪里不对写在理由里。",
      "3. 理由里不要用竖线 `|`,它会打断表格。",
      "",
      "改完保存,告诉 Claude 就行。以后重新生成这份目录时,你的审核结果会保留下来,也会写进 `genichiro_catalog.csv` "
      "的 `owner_review` 和 `owner_reason` 两列。",
      "",
      "## 证据等级", "",
      "| 等级 | 含义 |", "|---|---|",
      "| 已运行观察 | 这串里所有攻击和飞行物动画,都在录像的对应阶段出现过 |",
      "| 部分运行观察 | 只录到其中一部分 |",
      "| 仅静态证据 | 一个都没录到,只有 AI 和 TAE 的证据 |",
      "",
      "证据按动画计算:一个动画在对应阶段录到过就算,不区分是哪个 AI 选项请求的。"
      "比如三阶段录到的那次 3067 来自危攻击后续追击,飞渡浮舟第一套本身还没录到。",
      "",
      "## 统计", "",
      "| | 一、二阶段 c7100 | 三阶段 c7110 |", "|---|---|---|"]
for ev in ("已运行观察", "部分运行观察", "仅静态证据"):
    md.append(f"| {ev} | {sum(1 for r in moves if r['character'] == 'c7100' and r['evidence'] == ev)} "
              f"| {sum(1 for r in moves if r['character'] == 'c7110' and r['evidence'] == ev)} |")
md.append(f"| 招式候选合计 | {sum(1 for r in moves if r['character'] == 'c7100')} | {sum(1 for r in moves if r['character'] == 'c7110')} |")
md.append(f"| 不算招式 | {sum(1 for r in rows if r['character'] == 'c7100' and r['kind'] == 'not_move')} "
          f"| {sum(1 for r in rows if r['character'] == 'c7110' and r['kind'] == 'not_move')} |")
for st, mark in (("通过", "✅"), ("不通过", "❌"), ("待审核", "☐")):
    md.append(f"| 审核 {mark} {st} | {sum(1 for r in rows if r['character'] == 'c7100' and r['owner_review'] == st)} "
              f"| {sum(1 for r in rows if r['character'] == 'c7110' and r['owner_review'] == st)} |")
md.append("")


def cell(x):
    return (x or "—").replace("|", "｜")


def table(rs):
    out = [REVIEW_HEAD + " 阶段 | 动画链 | 触发 | 攻击(击数) / 飞行物 | 录到次数 | 最早录到 | 证据 | 建议的招式族 / 变体 | wiki 候选 | 你的标注 | 共用动画 | 说明 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rs:
        fam = " / ".join(x for x in (r["family_proposed"], r["variant_proposed"]) if x)
        if r["family_basis"]:
            fam += f"(依据:{r['family_basis']})"
        wiki = r["wiki_candidate"] + (f"(依据:{r['wiki_basis']})" if r["wiki_basis"] else "")
        ab = " ".join(x for x in (r["attack_anims"], ("飞行物 " + r["bullet_anims"]) if r["bullet_anims"] else "") if x)
        chain = r["chain"]
        out.append(f"| {r['entry']} | {r['review_mark']} | {r['owner_reason']} | {r['phases']} | {cell(chain)} | {cell(r['trigger'])} | {cell(ab)} | {cell(r['recorded'])} "
                   f"| {cell(r['first_seen'])} | {cell(r['evidence'])} | {cell(fam)} | {cell(wiki)} | {cell(r['owner_labels'])} "
                   f"| {cell(r['shares_animations_with'])} | {cell(r['notes'])} |")
    return out


fp = [r for r in moves if r["family_proposed"].startswith("飞渡浮舟")]
md += ["## 飞渡浮舟一族", "", "你确认了三套:3040 + 3041、3068 + 3092、3028。下面还包括建议归入这一族的分支。", ""]
md += table(fp) + [""]
for char, title in (("c7100", "一、二阶段(c7100,AI 710000)"), ("c7110", "三阶段(c7110,AI 711000)")):
    md += [f"## 其他招式候选:{title}", ""]
    md += table([r for r in moves if r["character"] == char and r not in fp]) + [""]
md += ["## 不算招式(建议)", "",
       "这些选项请求的动画里没有攻击判定或飞行物,比如他弹开你、后跳、侧移。全集里其余的编号(受击、忍杀、移动、过场等)在 M5 分类。", "",
       REVIEW_HEAD + " 阶段 | AI 选项 | 动画 | 触发 |", "|---|---|---|---|---|---|---|"]
for r in rows:
    if r["kind"] == "not_move":
        md.append(f"| {r['entry']} | {r['review_mark']} | {r['owner_reason']} | {r['phases']} | {cell(r['ai_options'])} "
                  f"| {cell(r['other_anims'])} | {cell(r['trigger'])} |")
md.append("")
open(out_md, "w", encoding="utf-8").write("\n".join(md))

sys.stdout.reconfigure(encoding="utf-8")
print(len(rows), "entries:", len(moves), "move candidates,", len(rows) - len(moves), "not moves")
for r in rows:
    print(r["entry"], r["phases"], r["evidence"] or "-", r["ai_options"], "|", r["chain"][:70], "|", r["family_proposed"])
