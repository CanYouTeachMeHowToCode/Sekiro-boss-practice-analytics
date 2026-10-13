# 暂存:还没审核的分类草稿

这里放的是暂时不审核、但要留着备查的结果。

## 为什么暂存

2026-10-13 你决定：第 7 步（全集分类，V4 M5）只审核**天守阁 AI 会出、带攻击判定或飞行物**的 TAE 编号，审核表是 `semantic/genichiro_classification.md`。其余编号的分类只作为草稿留在这里。以后实际测试或新录像里出现招式目录里没有的攻击动画时，再回来查它的分类和依据，补进招式目录。

## 文件

| 文件 | 内容 |
|---|---|
| `genichiro_castle_tae_deferred.csv` | 270 个 TAE 编号（c7100、c7110）的分类草稿：分类、置信度、依据、天守阁 AI 会不会出、两次录像里出现几次、在哪些目录条目里。 |
| `genichiro_castle_tae_deferred.md` | 同一份内容的中文表格，按分类分组。 |

包括：

- 天守阁 AI 不会出的攻击和飞行物（39 个），每个都写了原因：只有心中的弦一郎、剑圣战巴流或另一个角色的 AI 才用，或者没有任何 AI 请求；
- 被借用的源动画（2 个，8603 的动画和事件被 3092 完全借用）；
- 所有没有攻击判定和飞行物的动画（229 个）：受击和拼刀反应、移动、忍杀和死亡、演出、待机等。它们不会伤到玩家。

## 重新生成

和审核表一起由 `scripts/ai/classify.py` 生成：

```text
python -I research/ground_truth/scripts/ai/classify.py <work> research/ground_truth/engine/genichiro_castle_tae_classes.csv research/ground_truth/semantic/genichiro_classification.md research/ground_truth/semantic/genichiro_gap_report.md research/ground_truth/deferred
```
