# 招式归类第 1 版（M1、M2 用的版本，存档）

这里存的是失败归因第 1 版用的天守阁弦一郎产品招式表，你在 2026-11-11 要求存档保留。第 2 版生效以后，上一层的 `genichiro_product_moveset.csv` 会改，这里的两份不再改动。

| 文件 | 内容 |
|---|---|
| `genichiro_product_moveset.csv` | 26 个产品招式：slug、中英文名字、阶段、对应的目录条目（AI 链），以及证据状态 |
| `genichiro_product_moveset.md` | 同一张表的可读版本 |

两份都是 2026-11-11 从上一层复制过来的，对应提交 371d814，已经包含 2026-10-25 你改的两个名字：退潮（射箭+居合斩/射两箭）和连斩（肘击横砍收尾 / 危·突刺收尾 / 变招）。

## 第 1 版怎么归类

一次失败算 Boss 当时在放的那一招：先看他走的是哪条 AI 链（目录条目），再按这张表对到产品招式。被一招里的哪一下打中都一样，比如被巴之雷·砸击开头的箭射中，也算巴之雷·砸击。

## 用这一版做过什么

- M1 的答案和结果（`research/failure_attribution/results.md`）。
- M2 的测试（`research/failure_attribution/results_m2.md`）：冻结版本 a9030dc，失败精确率 97%、召回率 100%，有把握时招式答对 52/56。
- 你在 M1、M2 核对和盲审标的招式（`research/ground_truth/annotations/vanilla/genichiro/*/failure_moves.csv`、`failure_truth.csv`），都是按这一版标的。

## 第 2 版改了什么

见 `../../genichiro_v2_actions.md`（你在 2026-11-11 全部批准）。第 2 版仍然用这 26 个招式和名字，被一招的主要内容打中就算这一招，只有应对不同的动作单独算：

- 招式前后附带的普通的箭，算新的一招"普通射箭攻击 / Arrow Shot"；
- 别的招式里需要识破的突刺（3025、3080），算危·突刺；
- 跳起突刺改名为"跃起后危·突刺 / Leaping Perilous Thrust"。

那张表的"现在算"一栏，就是每个动画在第 1 版里算的招式。
