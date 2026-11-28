"""Throws: the catch the AI requests, and the follow-up the game plays when the catch connects.

A throw's damage is the TAE event Throw Atk (type 304), not an attack window (InvokeAttackBehavior). The AI requests
only the catch. When the catch connects, the game plays the follow-up, which none of the four decompiled Genichiro AIs
(710000, 711000, 710300, 711300) requests. V3.1 counted neither the event nor the follow-ups, so its completeness
review left 4100 and 4110 as unknown. Each pair below was seen in a dev-menu recording and confirmed by the owner
(research/failure_attribution/plan_v5.md, 2026-11-27):

    c7100 3020 -> 4100   phases 1-2 perilous grab: the catch hits (judge 160); 4100 is the punch (Throw Atk, judge 161)
    c7110 3009 -> 4110   phase 3 perilous grab: the catch does no damage (judge 170); 4110 is the slam (Throw Atk,
                         judge 171)

c7100 4110 has Throw Atk too (judge 171). Its catch would be an animation with judge 170 (c7100 3021 or 3027), which
the castle AI never requests. That pairing is inferred from the judge numbers; the game files do not state it.
"""
THROW_ATK = 304
CONDITION = "抓中"                                    # the chain condition: the catch connected
FOLLOW_UPS = {("c7100", 3020): 4100, ("c7110", 3009): 4110}
CATCH_OF = {(c, follow): catch for (c, catch), follow in FOLLOW_UPS.items()}
CONFIRMED = "你看叠加层录像确认(2026-11-27)"
# Throw follow-ups that no castle catch leads to, with the inferred catches: (character, animation) -> reason
UNPAIRED = {("c7100", 4110): "投技伤害(Throw Atk,判定 171),由游戏在抓中后播放,不由 AI 请求;按判定编号成对推断,"
                             "抓取是判定 170 的 3021 或 3027,天守阁 AI 都不请求(推断,游戏文件里没有写明)"}


def throws(events):
    """The Throw Atk events of an animation (judge -1 is an empty event)."""
    return [e for e in events if e["type"] == THROW_ATK and e["params"].get("BehaviorJudgeID", 0) >= 0]
