# 勾选规则

模拟已经结束才勾选。命令形如：

```bash
python -I overnight_town.py --seed 20260818 --nights 3 --agents 1000 \
    --budget 2.0 --crash-frac 0.4 --corrupt-frac 0.7 \
    --out morning.json --events-out events.jsonl \
    --feature-list features.json
```

不加 `--feature-list` 时，模拟与已入库的早晨报告哈希一致（world_hash `2fe29e0a8fe988bd…`，final_hash `ff7c76832d6e1145…`，成本 0.205012，调用 335）。这是 2026-11-12 对 v3.62 默认路径的核对，不是这个技能文件自己跑出来的。

一份报告能勾的只有四条：`ticks`、`structure`、`budget`、`society`。

`repro` 还要 `--control-report` 的 `world_hash` 相同，以及 `--rerun-report` 的 `final_hash` 相同。

`audit` 只统计事件流里 `_stream` 为 `audit` 的行。每行要有整数 `day` 和 `minute`。回滚、降级、熔断开、拒绝的行数不能少于报告里的计数。

这个文件到此为止，不再指向下一层。
