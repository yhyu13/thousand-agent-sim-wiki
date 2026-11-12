# bw-town 研究知识库（LLM Wiki）

> 主题：**千人级 AI 模拟，如何通宵无人值守运行、世界不崩溃、且 ROI 为正。**
> 服务对象：`bw-town` 千人小镇项目（PRD 见 `../PRD-千人小镇Web引擎.md`），以及未来任何想读这份资料的 LLM agent。
> 建立日期：2026-11-11 · 状态：v3.84（Prisma ORM 7 生产用 migrate deploy，不检测 drift，也不用影子库。换班 14 项，合计 104。**R26 整体验收原始目标达成**，R44 冷读者审计确认立项目标达成，R55 证据层 13 产物全逐字节可复现，R58 跨文档完整性终审全绿，进度见 [STATUS.md](STATUS.md)）

## TL;DR（六条快结论）

1. **千人不等于千个 LLM。** 已验证的千级系统全部靠「焦点激活」省钱：OASIS 用激活概率（100 万代理只有小部分每步调用 LLM）[S06]；千人小镇源码用统计代理（1000 居民、街上最多 360 个行走代理）[S16]。给每个居民每个时刻都跑一次 LLM 是成本崩溃的第一原因。
2. **不崩溃 = 确定性世界层 + 可回滚认知层。** 世界状态由种子派生、纯函数生成（千人小镇的 XOR/FNV-1a 链 [S16]）；LLM 只产出**经过校验的对象级补丁**，写坏就回滚（PRD §7.5 [S15]；Concordia 的 GM 校验动作物理合理性 [S10]）。demo **千人 × 30 夜全注入实测 GREEN**（崩溃恢复 + 污染回滚全吸收，world_hash 与干净浸泡跑逐位一致，见 04 §3.1）。
3. **通宵运行的头号杀手是限流与空闲暂停，不是模型变笨。** Generative Agents 官方 README 明说 API 到小时限流会挂起、建议勤存档 [S02]；AI Town 默认「窗口空闲 5 分钟暂停模拟」，通宵必须注释掉该 cron [S03]。
4. **崩溃恢复靠「无状态代理 + 外部化状态 + 检查点」。** AgentSociety 2 的代理是 workspace 绑定的无状态记录，由 Ray Tasks 驱动，JSONL 可重放 [S08]；Generative Agents 用 fork/fin 存档续跑 [S02]；本项目 demo 演示了 crash→checkpoint→resume 后终态哈希逐位一致。
5. **ROI 有实测锚点。** OASIS 给出实测 token 表（100 代理×1 步 = 335,600 输入 + 16,750 输出）与人民币成本表 [S06]；Anthropic 缓存读 0.1×（Sonnet 5.5 为 0.05×）、Batch API 全单 5 折、两者可叠加 [S13][S14]。千人一夜（48 步、激活率 0.1）用 Haiku 级模型约 $2，叠加缓存+批处理可压到 ~$0.5（估算，公式见 [04-roi.md](04-roi.md)）。
6. **底座不是一千个智能体进程。** 游戏早就有千人，差在决策从手写规则变成会出错的语言模型。MCP 接窄工具，技能并列、只引用一层，检查已经通过就不要再加评判角色。编码实验里三角色 harness 曾花 $200 / 6 小时，那不是千人一夜的推理账单 [S35]。详见 [08-substrate.md](08-substrate.md)。

## 导航

| 页面 | 回答什么问题 |
| --- | --- |
| [01-landscape.md](01-landscape.md) | 业界有哪些千人级 AI 模拟系统？各自规模、架构、成本证据？ |
| [02-architecture.md](02-architecture.md) | 参考架构：世界层 / 认知分层 / 记忆 / LLM 网关 / 监督者 / 审计，怎么拼？ |
| [03-stability.md](03-stability.md) | **核心页**：13 条「不崩溃秘密」+ 8 个真实事故复盘，每条 结论→证据→防再犯 |
| [04-roi.md](04-roi.md) | **核心页**：成本公式、实测锚点、省钱杠杆、ROI 怎么算 |
| [05-overnight-runbook.md](05-overnight-runbook.md) | 通宵运行手册：起飞前检查单、监控、故障演练、早晨验收 |
| [06-mapping-to-bw-town.md](06-mapping-to-bw-town.md) | 每条研究结论映射到千人小镇 PRD 条款与源码 file:line |
| [07-integration.md](07-integration.md) | 真实 LLM 接入：Ollama/Batch 双路线、限流档位、结构化输出、中文 token 校准、内容闸门、Q-01 决策表 |
| [08-substrate.md](08-substrate.md) | 技术底座：游戏人群 vs 语言模型、MCP/技能、父技能不是规范类型、迁移工具有没有专家团 |
| [sources.md](sources.md) | 全部参考来源登记册（论文 / 代码仓 / 官方文档 / 本地底稿），含核验状态 |
| [STATUS.md](STATUS.md) | 建设进度、核验日志、下一步 |
| [demos/](demos/README.md) | 可运行 mock 演示（零依赖、零网络、mock LLM） |

## Demo（动手验证，不是纸上谈兵）

```bash
cd <repo>/demos   # <repo> = 本仓库 clone 的根目录
python -I overnight_town.py --seed 20260818 --nights 3 --agents 1000 --budget 2.0 --crash-frac 0.4
python -m unittest test_overnight_town test_distributed_replica test_shift_handoff -v
python -I roi_calculator.py --agents 1000 --steps 48 --activation 0.1
```

`overnight_town.py` 用纯 Python 标准库模拟 1000 名居民连续 3 夜：分层认知（T0 规则 / T1 廉价模型 / T2 贵模型）、记忆流+检索+反思+**opt-in 记忆剪枝（--memory-ttl，GA 30 天过期移植）**、限流指数退避+熔断+半开探针、预算封顶降级、真实崩溃→检查点重放、不变量看门狗+自动回滚+体面停机、`--resume` 冷重启（检查点语义校验单点覆盖冷/热/回滚），最后产出「早晨报告」+ 事件流（`--events-out`）。全部失败注入都是种子确定的，**同种子两次运行终态哈希逐位一致**；104 个测试（主演示 64 + 分布式复刻 26 + 换班 14）+ 38 项可视化冒烟 + Chromium 对比度实测（6/6 AA）覆盖 critic 轮 1–66 发现的全部回归点（含检查点别名污染与存档相位两个 BLOCKER、可视化 XSS 四向量、schema 校验 73 形态 + 消费点运行时防御纵深，夜班 id 双层独立机制 + NaN/inf/超 float 大整数有限校验（_finite 安全版）+ 深嵌套 JSON RecursionError 干净拒绝 + agents/nights/corrupt_times 量级上限 + 变异击杀基线对照实证）。**`visualize.html` 双击离线打开，拖入报告/事件流/检查点即可看每夜 24h 时间轴与居民记忆流**。真实 LLM 接入见 [07-integration.md](07-integration.md)。

## 给 LLM 读者的使用约定

- 引用键 `[Sxx]` 一律指向 [sources.md](sources.md) 的登记条目；每条事实性陈述都应能落到一个 `[Sxx]` 或本地 `file:line`。
- 标注「**假设，待验证**」的内容不是事实，是工程估算或待办（沿用 PRD 写作约定 [S15]）。
- 页面 ID 稳定（`01`–`08`），小节用 `§` 编号；改内容不改 ID，方便交叉引用。
- **本地底稿锚点**（`../PRD-千人小镇Web引擎.md`、`../source/`、`../meta.json`）指向作者 bw-town 工作布局，**不随公开 repo 分发**；外部研究声称均可经 `[Sxx]` 外源核验（如 S17 视频 BV1ArJ96CE3P 为公开外源），demos 完全自包含（零依赖/零网络）。
- 本地底稿优先级：`../source/`（thousand-town 克隆）> `../PRD-千人小镇Web引擎.md` > 外部网页。外部网页核验日期见 sources.md。
- demo 代码是**教学 mock**：LLM 是确定性假模型，价格表是真的（[S13]），行为模式对齐论文，但不要把 mock 输出当成真实模型能力证据。