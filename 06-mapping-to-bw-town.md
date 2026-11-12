# 06 · 映射到 bw-town：研究结论 ↔ PRD 条款 ↔ 源码锚点 ↔ demo

> 用途：把本 wiki 的每条研究结论落到千人小镇项目的具体位置。PRD 指 `../PRD-千人小镇Web引擎.md` [S15]；源码指 `../source/`（thousand-town 克隆）[S16]。

## §1 已经有的（千人小镇原生优势，直接继承）

| 能力 | 源码/PRD 锚点 | 对应研究结论 |
| --- | --- | --- |
| 确定性世界层 | `resident-plan.js:50-60` FNV-1a `hash32(seed:id:day)`；`city-layout.js:46` XOR 派生；PRD C-05/F-01 | 军规 2；路线 B 的骨架（01 页 §2） |
| 命名空间稳定 ID | `resident.js:291-297`（旧方案本会重掷 ~760 人作息的反事实设计注释→`role-001`） | 军规 3；**源码注释已明言这是 LLM-authored Plan 的寻址前提** |
| 焦点激活雏形 | `sketch.js:217` `maxPeople:360`；其余居民「在楼里」 | 军规 1；OASIS 激活概率同构 [S06] |
| 纯 JSON 快照 | `plan-snapshot.js capture()` → `{version,seed,day,plans}`；PRD F-09 | 军规 5 的检查点格式基础 |
| 审计与回滚设计 | PRD §7.4 只追加、§7.5 校验失败拒绝/渲染异常回滚、F-06 | 军规 7/8/12；Concordia GM 同构 [S10] |
| 零网络零构建 | PRD F-07/C-01/C-02 | 世界层离线可跑；认知层需另立版本决策（Q-01） |
| 花名册 grounding 载体 | PRD §7.2 契约字段；`resident-character-admin` | [S12]：档案越厚扮演越像（83–86% vs 74%） |

## §2 还缺的（通宵 AI 模拟需要新增，按优先级）

| 缺口 | 研究依据 | 建议落点 | demo 参照 |
| --- | --- | --- | --- |
| LLM 网关（预算/重试/熔断/校验） | 军规 6/7/11；[S02][S13][S14] | PRD Q-01 决策后新增模块；离线版=本地规则+Ollama [S03] | `MockLLM` + `gateway` |
| 不变量看门狗 | 军规 8；[S16] 760 人反事实教训 | M0 契约测试扩展为运行时体检 | `Supervisor.check` |
| 检查点含 RNG 状态 | 军规 5；[S02] | `plan-snapshot` 扩展 version 2：+rng+audit 长度 | `CheckpointStore` |
| 认知分层 T0/T1/T2 | 军规 1；[S06][S08] | 社交相遇/反思才调 LLM；作息永远 T0 | `step_tick` |
| 记忆流+反思 | [S01]；军规 10 | 花名册备注（PRD F-10）升级为记忆记录 | `residents[].memories` + `retrieve()` |
| 早晨报告 | 03 页 §13；[S04] 文明基准 | M2 验收物 | `_run()` 报告 dict → out/morning_report.json |

## §3 PRD 条款逐条对照

| PRD 条款 | 本研究库的支撑/挑战 |
| --- | --- |
| F-01 同种子逐位相等 | 军规 2/5：demo 双跑+崩溃恢复哈希一致已验证该模式可行 |
| F-02 昼夜作息 | 世界层 T0 永远纯函数；LLM 补丁只改 `tomorrow_focus` 这类枚举，不碰锚点常量（`daily-clock.js:13-27`） |
| F-05 点名改动、其余 999 人不变 | 军规 3：`test_census_blast_radius` 直接复刻验收；补丁必须带显式 ID（R-01） |
| F-06 审计可回滚 | 军规 8/12：回滚后重新断言 F-01；审计用模拟时间戳 |
| F-07 离线可用 | **冲突点**：云 LLM 必然破坏 F-07。两条出路：(a) Ollama 本地推理 [S03]；(b) 认知层作为可选联网版本另立决策（Q-01/Q-05）。demo 用 mock LLM 演示架构而不站队 |
| SEC-2 ≤360 行走代理 | 军规 1 的渲染侧表达；认知侧激活率独立配置（街上 360 ≠ 每步 360 次 LLM） |
| C-05 禁 Math.random | demo 全程种子 RNG；真实接入时 LLM 采样温度>0 的输出只能进补丁通道，不进派生链 |
| Q-01 本地规则 vs 外部 LLM | 04 页 §4：本地 T1 + 云 T2 混合是 ROI 最优（假设，待验证）；纯本地=AI Town 默认形态 [S03]；**决策表与接入细节见 [07-integration.md](07-integration.md) §10** |
| W-05 不做一句话生成整座城 | 与 [S04] 一致：文明级涌现需要长时间多代理交互，不是一次生成；对象级补丁才是可验收粒度 |

## §4 视频作者方法论的印证

作者原话「技术的问题让 AI 去解决落地，最后我们再把结果一项项检查清楚」[S17]——这正是军规 8（看门狗）+ 军规 12（审计）+ 05 页早晨验收的人肉版本。本 wiki 把它机器化：**AI 负责跑，不变量负责查，审计负责记住，哈希负责证明**。

## §5 技术底座落到哪（08 的结论，不新开一条模拟）

| 结论 | 依据 | 落点 |
| --- | --- | --- |
| 千人不是新的，会出错的语言模型才是 | 游戏用状态机和行为树拼 NPC，写不进脚本的行为做不到 [S01][S33] | 作息留在 `resident-plan.js` 的纯函数；LLM 只走补丁通道（§3 C-05） |
| 不要给每个居民一个 MCP 服务器 | 服务器应窄、互相看不见对话；手的形状是一次调用返回字符串 [S28][S32] | 若接工具，只接检查点、账本、内容闸门。居民状态仍在快照里 |
| 技能不是父子嵌套 | 规范没有父技能类型，引用只宜一层 [S29] | `demos/skills/overnight-operator` 只读自己的 `references/grade.md`；`demos/skills/hash-guard` 没有下一层。两份正文互不读文件 |
| 换班靠外置清单，不靠会话记忆 | 新会话失忆；功能先标失败；每班一条 [S34] | [05-overnight-runbook.md](05-overnight-runbook.md) §7。`--feature-list` 可选，默认不写 |
| 默认通宵哈希仍是入库值 | 2026-11-12 再跑：world_hash `2fe29e0a8fe988bd…`，final_hash `ff7c76832d6e1145…`，成本 0.205012，调用 335 | `hash-guard` 只核对这组，对不上就停 |
| 库表迁移器不是专家团 | Flyway、Liquibase、Alembic 都是版本化脚本加历史表，已跑过的不再重跑；这三页都没有 MCP、skill 或 AI agent [S31][S37][S38]。Django 6.1 也不是专家团，但不能并进上一句：DDL 事务默认只包 SQLite 和 PostgreSQL，MySQL 与 Oracle 不包，MySQL 失败不能自动退回 [S39] | 模拟侧的迁移是 `demos/overnight_town.py` 快照里的 `schema_version`（约第 734 行），不是再包一层委员会 |
| 三个角色会过期 | 规划/生成/评判能抬质量，也会又贵又慢；模型变强后应拆掉不再承重的架子 [S35] | 千人模拟不默认上三角色。评判只留给哈希和回归测试对不上的时候 |