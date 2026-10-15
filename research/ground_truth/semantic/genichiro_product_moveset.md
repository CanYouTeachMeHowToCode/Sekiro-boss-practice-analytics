# 第 8 步:产品里的弦一郎招式清单(按你的决定整理)

由 `scripts/ai/moveset.py` 从你审完的决策表 `genichiro_product_decisions.md` 生成,数据在 `genichiro_product_moveset.csv`。这是改种子数据(`backend/seed/bosses.json`)的依据;产品现在还没有改。

- 现有 22 个招式 → 改完后 26 个:删掉 1 个,新增 5 个。
- 目录里的 63 个招式全部对上了产品招式;P3-30(完美弹开后的突刺 3080)同时属于两个招式。
- 新增招式的 slug 是我起的,你可以改。新增招式和改了含义的招式,描述、预兆、应对方法要另外定(wiki 没有的不编)。

## 招式

| slug | 中文名 | 英文名 | 阶段 | 改动 | 目录条目 | 决策表行 | 证据 | 备注 |
|---|---|---|---|---|---|---|---|---|
| `perilous-attack-follow-up` | 一阶段跳劈后续危（只有突刺） | Phase 1 Perilous Attack Follow Up (Only Thrust) | 1 | 改名 | P12-20 | A01 | 已运行观察 | — |
| `perilous-attack-follow-up-phase-2` | 二阶段跳劈后续危（突刺/下段） | Phase 2 Perilous Attack Follow Up (Thrust/Sweep) | 2 | 改名 | P12-20 | A02 | 已运行观察 | — |
| `perilous-attack-follow-up-phase-3` | 三阶段跳劈后续（突刺危/下段危/上挑） | Phase 3 Perilous Attack Follow Up (Thrust/Sweep/Upward Slash) | 3 | 改名 | P3-17 P3-30 | A03 | 已运行观察 | 第三种结尾 3032 被完美弹开后接突刺 3080(P3-30,和三阶段飞渡浮舟共用) |
| `perilous-grab` | 危·投技 | Perilous Grab | 1、2 | 不变 | P12-17 | A04 | 已运行观察 | 加上应对方法:1. 完美弹反 2. 向后垫步躲开(你在 A04 写的) |
| `closing-tide` | 涨潮（射箭+前滚劈砍） | Closing Tide (Bow into Rolling Slash) | 1、2、3 | 改名；加阶段 3 | P12-10 P12-09 P12-11 P12-12 P3-09 P3-10 P3-11 | A05 B09 B10 B11 | 部分运行观察 | — |
| `floating-passage` | 绝技·飞渡浮舟 | Floating Passage | 1、2 | 不变 | P12-21 P12-22 P12-27 P12-29 P12-32 P12-14 | A06 B13 | 部分运行观察 | 描述里写明:二阶段打到一半、你在 4.1 米外时改射一箭(射箭取消 3017) |
| `guard-breaking-shot` | 破防射击 | Guard Breaking Shot | 1、2 | 不变 | P12-19 | A07 | 已运行观察 | — |
| `hawk-shot` | 鹰射（后撤/四连射击） | Hawk Shot (Step-back/4 Arrow Shot) | 1、2 | 改名 | P12-23 | A08 | 已运行观察 | — |
| `two-hit-combo` | 横砍踢击 | Slash into Back Kick | 1、2 | 改名 | P12-02 | A09 | 已运行观察 | — |
| `deaths-thrust` | 跳起突刺 | Sword Dive Thrust Attack | 3 | 改名 | P3-06 | A10 | 已运行观察 | — |
| `perilous-grab-phase-3` | 危·投技（第三阶段） | Perilous Grab (Phase 3) | 3 | 不变 | P3-07 | A11 | 已运行观察 | — |
| `lightning-of-tomoe-slash` | 巴之雷·斩击 | Lightning of Tomoe Slash | 3 | 不变 | P3-21 | A12 | 已运行观察 | — |
| `lightning-of-tomoe-smash` | 巴之雷·砸击 | Lightning of Tomoe Smash | 3 | 不变 | P3-22 P3-14 | A13 | 已运行观察 | — |
| `perilous-attack` | 倒地后跳刺危攻击 | Perilous recovery jump-back thrust attack | 1、2 | 改名 | P12-18 | A14 B17 | 已运行观察 | — |
| `perilous-thrust` | 危·突刺 | Perilous Thrust | 1、2、3 | 加阶段 3 | P12-26 P3-25 | A15 B20 | 部分运行观察 | — |
| `perilous-sweep` | 危·下段横扫（后可接射击） | Perilous Sweep (Follow-up Shot Available) | 1、2、3 | 改名；加阶段 3 | P12-06 P3-05 P3-27 | A16 B06 B22 | 部分运行观察 | — |
| `advance` | 二连横砍 | Two-Hit Slash | 1、2、3 | 改名；加阶段 3 | P12-03 P3-02 | A17 B03 | 已运行观察 | — |
| `chasing-slice` | 追击二连横砍 | Chasing Two-Hit Slash | 1、2、3 | 改名；加阶段 3 | P12-05 P3-04 | A18 B05 | 已运行观察 | — |
| `receding-tide` | 退潮（射箭+居合斩） | Receding Tide (Bow into Iaijutsu) | 1、2、3 | 改名；加阶段 3；并入 iaijutsu | P12-15 P12-16 P3-15 P3-16 | A20 A19 B15 B16 | 部分运行观察 | — |
| `floating-passage-phase-3` | 绝技·飞渡浮舟（第三阶段） | Floating Passage (Phase 3) | 3 | 不变 | P3-18 P3-20 P3-26 P3-28 P3-30 P3-31 P3-13 | A21 B14 | 部分运行观察 | 描述里写明:3040 打完第 4 刀时你在 11 米外改射两箭(3018);5.5–11 米时改出死亡突刺(见 deaths-thrust) |
| `lightning-of-tomoe-shot` | 巴之雷·射击 | Lightning of Tomoe Shot | 3 | 不变 | P3-19 P3-08 | A22 | 已运行观察 | — |
| `slash-combo` | 连斩（肘击横砍收尾 / 危·突刺收尾） | Slash Combo (Elbow and Slash Finish / Perilous Thrust Finish) | 1、2、3 | 新增 | P12-01 P3-01 | B01 | 部分运行观察 | — |
| `horizontal-slash` | 横砍 | Horizontal Slash | 1、2、3 | 新增 | P12-04 P3-03 P12-13 P3-12 | B04 B12 | 已运行观察 | — |
| `backstep-shot` | 后撤射击 | Backstep Shot | 1、2 | 新增 | P12-07 P12-08 | B08 | 已运行观察 | — |
| `counter-slash` | 拼刀反斩 | Counter Slash | 1、2、3 | 新增 | P12-24 P3-23 P12-25 P3-24 P12-31 P3-29 | B18 B19 B24 | 部分运行观察 | — |
| `deflect-counter-slash` | 强弹反斩 | Deflect Counter Slash | 1、2 | 新增 | P12-28 P12-30 | B21 B23 | 已运行观察 | — |

## 删掉的招式

| slug | 并入 | 原因 |
|---|---|---|
| `iaijutsu` | `receding-tide` | A19 你判为和 A20 重复:居合斩是退潮的后半段,并入退潮 |

已有练习记录指向这些招式的,迁移到并入的招式(CLAUDE.md 第 45 节)。数据库对招式删除有约束,有记录指向时删不掉,所以迁移必须在删除之前。

## 名字里的笔误(待你确认)

上面的表已经按建议改了;你不同意的话告诉我。

| slug | 你写的 | 建议改成 | 原因 |
|---|---|---|---|
| `perilous-attack-follow-up-phase-2` | 二阶段跳劈后续危（突刺/下段）/ Phase 1 Perilous Attack Follow Up (Thrust/Sweep)) | 二阶段跳劈后续危（突刺/下段） / Phase 2 Perilous Attack Follow Up (Thrust/Sweep) | 英文写成了 Phase 1,末尾多一个括号 |
| `perilous-attack-follow-up-phase-3` | 三阶段跳劈后续 （突刺危/下段危/上挑） / Phase 3 Perilous Attack Follow Up (Thrust/Sweep/Leaping Slam)) | 三阶段跳劈后续（突刺危/下段危/上挑） / Phase 3 Perilous Attack Follow Up (Thrust/Sweep/Upward Slash) | 中文多一个空格;英文末尾多一个括号,而且第三种结尾中文是“上挑”,英文却是 Leaping Slam |
| `hawk-shot` | 鹰射（后撤/四连射击）/ Hawk Shot （Step-back/4 Arrow Shot) | 鹰射（后撤/四连射击） / Hawk Shot (Step-back/4 Arrow Shot) | 英文用了全角括号 |
| `perilous-sweep` | 危·下段横扫（后可接射击）/ Perilous Sweep (Follow-up shot available)) | 危·下段横扫（后可接射击） / Perilous Sweep (Follow-up Shot Available) | 英文末尾多一个括号 |
| `receding-tide` | 退潮（射箭+居合斩）/ Receding Tide (Bow into Laijutsu) | 退潮（射箭+居合斩） / Receding Tide (Bow into Iaijutsu) | Laijutsu 应为 Iaijutsu |
