---
name: hash-guard
description: 核对默认同种子通宵有没有漂。用户问 world_hash、final_hash、成本或调用数是否仍与入库早晨报告一致时使用。不用于换班勾选，也不改模拟。
---

# 哈希门

只做这一件事：默认同种子通宵（seed 20260818，3 夜，1000 人，budget 2.0，crash-frac 0.4，corrupt-frac 0.7）不传 `--feature-list`。

对上才算没漂：world_hash `2fe29e0a8fe988bd34c15d56f93a64521288185501d37828684c785a9ddce260`，final_hash `ff7c76832d6e11451c9780b709346e1c31b5c73562a16964a98bdc41cfd07818`，成本 0.205012，调用 335，状态 GREEN。这是 2026-11-12 对 v3.62 默认路径的核对。

对不上就停，不要勾选，也不要改模拟去凑哈希。

这个技能没有下一层文件。换班勾选是另一份技能的事，这里不读它的文件。
