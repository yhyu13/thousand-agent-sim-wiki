---
name: overnight-operator
description: 通宵模拟跑完后的换班勾选。用户要写 feature-list、或问一份报告能勾哪几条时使用。不用于核对入库哈希，也不改模拟规则或居民人设。
---

# 通宵操作员

这是路由，不是父技能类型。规范里没有父技能对象，引用只走一层。

先读 [references/grade.md](references/grade.md)，再决定要不要给 `overnight_town.py` 加 `--feature-list`。

不要做的事：

- 不要给每个居民各写一份技能。居民差异在世界状态里。
- 不要在没有对照报告和同配置重跑时，把 `repro` 改成通过。
- 不要为了勾选去改模拟循环。默认运行不写清单。
- 入库哈希对不对，是另一份并列技能的事。不要去读那份技能的文件。
