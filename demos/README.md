# Demos · 可运行 mock 演示（v3.46，critic 轮 1–55 修复 + 记忆剪枝 + schema 校验与运行时防御 + 可视化 + 居民记忆流查看器 + 分布式复刻 + 千人 30 夜浸泡/全注入三种子/TTL/零失败反事实实测；R26 整体验收原始目标达成，R44 冷读者审计确认，R55 证据层全逐字节可复现）

零依赖（Python 3.10+ 标准库）、零网络、零真实 LLM、零 API key。
所有失败注入都是**种子确定**的：同配置双跑，哈希逐位一致。
价格口径是真实平台时价（2026-11-11 核验，见 [../sources.md](../sources.md) S13/S14），
但模型是确定性假模型——**演示的是架构与工程模式，不是模型能力**。

## 文件

| 文件 | 作用 |
| --- | --- |
| `overnight_town.py` | 主演示：1000 居民 x N 夜通宵模拟（分层认知/记忆/网关/看门狗/检查点/审计/早晨报告） |
| `test_overnight_town.py` | **55 个测试**：确定性、真实崩溃重放等价、检查点隔离与存档相位（两个 BLOCKER 回归）、干预审计崩溃窗口、污染回滚、计划违例实弹、分散注入、抽样互质、resume 五连、**深层语义损坏 73 形态（schema 校验覆盖已知消费字段：llm 全键含有限数/超 float 大整数/bool 守卫（含 p_*）/tokens 对/residents 全字段含夜班 id ASCII 数字+前缀一致/memories 全字段含 keywords 非空字符串列表与有限 importance/audit 内部 type/plans 键完整性与段结构；另有 retrieve/audit_summary/build_day 消费点运行时防御纵深——两层用不同机制（校验 ASCII 谓词 / build_day try-int），不声称穷尽任意篡改，未知形态由看门狗与体面停机兜底）**、**夜班 id 独立回归 + build_day/retrieve 防御单元守卫 + 看门狗 I3/存档闸门/Config 大整数回归 + 深嵌套 JSON RecursionError 拒绝 + main 大整数 counter 活兜底 + agents/nights/corrupt_times 量级上限（R11/R12/R13/R14：杀 M3/M4/M5/M35/N2/N5/N6/N10/X_recursion/X_cost_bool/X_main_exc/X_p_bool/X_corrupt_cap，基线对照实证）**、跨版本计数补齐/内存篡改单点校验/OSError 路径、schema_version 契约、events-out 导出契约、NaN/inf/大整数/深嵌套/CLI 拒绝、记忆剪枝 TTL×3（含 age==ttl 边界断言）、预算封顶、全坏输出、全限流、退避+半开探针、体面停机、Batch 折扣、名册爆炸半径教训复刻、参数校验（seed/budget/frac/p_*/batch/storm/resume 类型与量级）等 |
| `distributed_replica.py` | **分布式规模化路线最小复刻（R35，零依赖 multiprocessing）**：演示 AgentSociety 2 [S08] 无状态 worker + 确定性世界 + 焦点激活——worker 是纯函数 (seed,tick,resident,focal)→补丁、RNG 命名空间派生（FNV-1a+mulberry32 同 overnight_town）、补丁按 id 排序施加 → **并行==串行**（`--mode both` 实证哈希一致）+ 检查点续跑==全程（记录并校验 focal_period、schema_version=1、字段值类型：seed/n/tick/focal_period/schema_version 须严格整数且 bool/float 不算整数、residents 须列表且数量与 n 一致、tick 须 >= 0；snap/world 未知键拒绝；深嵌套 JSON 解析层干净拒绝，计算/序列化点超递归上限由顶层四家族兜底（ValueError/OSError/OverflowError/RecursionError，对齐主 demo）干净拒绝，孤立代理对等编码类错误同被捕获；写路径 OSError 干净拒绝。residents 元素内部结构不深校验——域外，未超递归上限的深嵌套原样携带，元素垃圾 TypeError/KeyError 保持 rc=1）。剥离 overnight_town 的可并行计算内核，证明路线 B 的确定性基础 |
| `test_distributed_replica.py` | **20 个测试**：并行==串行、确定性双跑、worker 纯函数无状态（不修改输入）、RNG 命名空间、焦点选择确定性旋转、补丁顺序无关、检查点续跑==全程、CLI 校验、**续跑 focal_period 不匹配/bool/float 拒绝、损坏检查点拒绝、量级上限、值类型损坏拒绝（7 形态含 bool 陷阱）、schema_version 读取校验（999/缺失/True/1.0/"1" 拒绝）、深嵌套合法 JSON RecursionError 拒绝、负 tick 拒绝（含 -(10^400) 防挂死）、residents 数量交叉校验、写路径 OSError 拒绝、snap/world 未知键拒绝（含额外键深 800 both 崩溃窗）、元素内深 1500 顶层兜底（both/sequential）、孤立代理对四家族兜底（3 模式）**。运行：`python -m unittest test_distributed_replica` |
| `vis_smoke.js` | **visualize.html 冒烟守卫（38 项，node 运行）**：XSS 四向量、合成/真实来源三态标注、只载 report/只载 events 场景、null token、null/标量/畸形行容错、全无效拒绝、sample_events null 渲染安全、**tab 处理器 render 守卫（结构守卫为有效 M6 守卫；行为点击仅辅助验证接线，render 容错无法区分 try/catch 有无——R11 MINOR-2 校准）**、dayLabel null、nights 上限、BOM 路由、CSS 暗色覆盖源顺序、**居民记忆流查看器（R30：检查点载入/居民选择器/记忆流+计划渲染/居民字段 XSS 四向量/null 记忆容错/检查点独立于报告/空检查点提示；R31：居民 option 上限 2000/计划行上限 300/记忆精确计数；R32：数组记忆排除/分数索引归整）**。运行：`node vis_smoke.js .` |
| `contrast_check.py` | 暗色/亮色徽章（GREEN+RED）与 tabs 对比度**真实 Chromium 实测**（需 playwright，路径相对脚本自身）：`python contrast_check.py`，AA ≥4.5 判定。v3.46 实测 6/6 全过（dark 10.25/6.45/7.02，light 5.02/6.47/6.70） |
| `roi_calculator.py` | ROI 估算器：OASIS 实测 token 基线 x 平台时价 x 缓存/Batch 杠杆 + Claude/DeepSeek 谷时/**Qwen 现价（北京区 6 模型，缓存/Batch 不叠加）**场景（双层参数校验，对齐 04 §1.3–1.5） |
| `visualize.html` | **早晨报告可视化**：零依赖单文件，双击离线打开；拖入 report JSON + events JSONL + **ckpt.json（检查点）** → 状态徽章/成本与覆盖率卡片/每夜 24h 事件时间轴（社交窗口+9 锚点+干预标记）/token 分布/审计流/双哈希/**居民记忆流查看器（R30：居民选择器+记忆流+当日计划，演示记忆检索架构）**；内置合成示例（明确标注），事件与居民字段 XSS 转义 |
| `out/` | 运行产物（早晨报告 / 对照报告 / 增长报告 / events.jsonl 事件流） |

## 运行

```bash
cd <repo>/demos   # <repo> = 本仓库 clone 的根目录

# 标准通宵：3 夜 x 1000 人，崩溃注入(40%) + 名册污染注入(70%) + 限流/坏JSON风暴 + 事件流导出
python -I overnight_town.py --seed 20260818 --nights 3 --agents 1000 \
    --budget 2.0 --crash-frac 0.4 --corrupt-frac 0.7 \
    --events-out out/events.jsonl --out out/morning_report.json
# 然后双击 visualize.html，拖入上面两个文件看时间轴

# 对照跑：保留风暴（风暴是种子历史的一部分），只去掉崩溃/污染
python -I overnight_town.py --seed 20260818 --nights 3 --agents 1000 \
    --budget 2.0 --no-crash --out out/control_report.json

# 测试（注意：unittest 需要 cwd 在 sys.path，不要加 -I）
python -m unittest test_overnight_town -v

# ROI 估算
python -I roi_calculator.py --agents 1000 --steps 48 --activation 0.1 --nights 1

# 分布式规模化路线最小复刻（AgentSociety 2 [S08]）：并行==串行实证 + 检查点续跑
python -I distributed_replica.py --seed 20260818 --agents 1000 --ticks 144 --workers 4 --mode both
python -I distributed_replica.py --checkpoint-dir out/dist --ticks 144            # 落检查点
python -I distributed_replica.py --checkpoint-dir out/dist --resume --ticks 288   # 续跑==全程
python -m unittest test_distributed_replica -v

# 更多演练（完整清单见 ../05-overnight-runbook.md §5）
python -I overnight_town.py --nights 1 --agents 200 --budget 0.05            # 预算耗尽
python -I overnight_town.py --nights 1 --agents 200 --batch                  # Batch 5折
python -I overnight_town.py --nights 1 --agents 200 --checkpoint-dir out/ckpt # 磁盘检查点
python -I overnight_town.py --nights 1 --agents 200 --checkpoint-dir out/ckpt --resume  # 冷重启续跑
python -I overnight_town.py --nights 30 --agents 200 --budget 20 --no-crash --memory-ttl 7  # 记忆剪枝（GA 30天过期移植，opt-in）
python -I overnight_town.py --nights 2 --agents 200 --corrupt-plan-frac 0.5  # I2/I4 实弹
python -I overnight_town.py --nights 2 --agents 200 --corrupt-frac 0.2 --corrupt-times 4  # 体面停机
python -I overnight_town.py --nights 2 --agents 200 --crash-frac 0.5 --corrupt-frac 0.5   # BLOCKER 回归
```

## 两种哈希（验收口径，对应军规 2/5/8/12）

- `final_hash`：全量状态（世界+审计+计费+RNG+meta）。**同配置**双跑必须逐位一致；崩溃恢复不改变它。
- `world_hash`：世界本体（居民/计划/事件，不含审计与计费）。**跨干预**不变量：
  污染回滚后它必须与对照跑一致，而审计流会多出 `rollback` 条目（干预必须留痕）；
  Batch 计价模式只改成本，不改它。
- `llm_calls` 定义：**总尝试次数**（含限流/坏输出失败），不是成功数。
- `resumed_from_tick` 语义：本进程**最后一次**检查点续跑点（冷重启起点或内部崩溃恢复点）；>0 证明发生过续跑，但不区分冷/热（R4 critic 语义声明）。
- **跨 nights 扩展续跑的边界**：注入/风暴窗口按 total 比例调度，nights 改变会移动窗口位置 → 首段历史不同。逐位等价在**首段无风暴/污染历史差异**时成立（崩溃注入被重放吸收，不影响 final_hash）；resume 测试特意用 storm=False 构造中间续跑。
- v3.2 快照新增 `memories_pruned` 计数、v3.3 新增 `schema_version=2` → **final_hash 随之变化**（world_hash、成本、调用数逐位不变）。旧版快照续跑时缺失计数键自动补齐；`memory_ttl` 是运行配置不入快照，续跑可变（行为自洽，critic 轮 5 已验证）。

## 实测记录（2026-11-11，本机 Python 3.13，v3.46；world_hash/成本/调用数与 v2 起逐位一致）

标准通宵跑（1000 人 x 3 夜，432 ticks，含全部注入）：

| 指标 | 值 |
| --- | --- |
| 状态 | GREEN（~2 秒跑完） |
| 崩溃恢复 / 自动回滚 | 1 / 1，全部吸收，未解决违例 0；崩溃回退最近周期检查点重放 ≤6 tick |
| 对话 | 252（LLM 235 / 规则兜底 17） |
| 反思 | 120（采纳 79 / 拒绝 1 / 降级 40） |
| 限流吸收 | 限流命中 9、退避跳过 45、熔断开 0（退避在风暴期即吸收，未需熔断） |
| LLM 调用覆盖率 | 335 次尝试 / 432,000 代理-tick = **0.0775%** |
| Token | T1: 149,804 in / 19,538 out；T2: 76,194 in / 17,573 out |
| 成本 | **$0.2050** / 封顶 $2.00（10.25%）；每事件 $0.000551 / 每 LLM 有效事件 $0.000653 |
| world_hash（与对照跑一致） | `2fe29e0a8fe988bd34c15d56f93a64521288185501d37828684c785a9ddce260` |

长夜增长跑（30 夜 x 200 人，70 秒，GREEN）：记忆 6,804 条（人均 34，约 +1/人/夜；计数从 ckpt.json 的 residents[].memories 读取，morning_report 无 memories_total 键）、
检查点 2.09 MB、对话 2,520（另有反思 1,200）、审计 1,131、成本 $2.90、熔断开 4 关 1（半开探针长跑实证）。
千人 30 夜浸泡实测（v3.37，GREEN，`out/growth_1000x30_report.json`）：检查点 **3.04 MB**、记忆 **9,204**（人均 9.2）、成本 **$2.8983** ≈ 200 人跑——焦点激活固定事件配额下成本/存储由夜数驱动，人口只加线性基座（**原「外推 ≈10 MB」被实测证伪**，机理与口径告诫见 ../04-roi.md §3.1）。剪枝策略见军规 10。

**记忆剪枝实测（--memory-ttl，v3.2）**：ttl=7 × 30 夜 → 剪枝 4,548 条、存留 2,256 条（**-67%**）、
检查点 1.22 MB（**-42%**）、成本 $2.9013（与不过期 $2.8979 几乎相同，GREEN）。
ttl=30 × 30 夜 → 剪枝 0（正确：记忆年龄未超 30 天；GA 式过期只在超长运行生效）。
人格记忆（identity 2 条 + habit 1 条）永驻，不参与剪枝。

**千人 30 夜规模锚点（v3.38）**：全注入跑（崩溃 0.4 / 污染 0.7 / 风暴）GREEN，4320/4320 ticks、人口 1000/1000，崩溃恢复 1（resumed_from 1728）+ 回滚 1 全吸收，**world_hash/成本/调用数与干净浸泡跑逐位一致**（`growth_1000x30`，--no-crash 保留风暴；**非 `clean_*` 零失败跑**——去风暴改变失败历史故 world_hash 不同，重放不膨胀计费，干预只留审计痕，`out/inject_1000x30_report.json`）；TTL=7 剪枝 **4,548（与 200 人跑逐位相同，夜数驱动）**、存留 4,656、检查点 **2.18 MB（-28.5%**，降幅随人口增长收窄——人格基座变大，`out/ttl_1000x30_report.json`）。**多种子稳健性（v3.39）**：seed 42/20261111 同配置全注入亦 GREEN（成本 $2.9032/$2.9055，`out/inject_1000x30_s42_report.json` / `_s20261111_report.json`）。机理与口径告诫见 ../04-roi.md §3.1。

测试套件：`Ran 55 tests ... OK`（~25 秒）+ `node vis_smoke.js .` 38/38 + `python contrast_check.py` 6/6 AA（Chromium 实测，含 RED 徽章）。R10 三根因 + R11 夜班 id Unicode 洞（`nurse-²`/`nurse-①`）/前缀不一致/NaN + R12 超 float 大整数（`10**400`，8 字段入口）+ R13 深嵌套合法 JSON（5000 层 meta.unresolved/world.events）/大整数 counter + R14 corrupt_times 量级（`10**9` 不再挂起）攻击形态端到端复现：全部 rc=2 干净拒绝（无 OverflowError/RecursionError 裸 traceback）；消费点运行时防御单元守卫入库；**变异击杀基线对照实证**（M3/M4/M5/M35/N2/N5/N6/N10/X_recursion/X_cost_bool/X_main_exc/X_p_bool/X_corrupt_cap 各被对应测试精确杀死，未变异基线全绿）。

## mock 口径的已知偏差（引用数字前必读）

1. **缓存**：首写后 100% 命中、无 TTL 过期模型——对稀疏调用乐观（真实 Batch 命中 30–98% [S14]）。
2. **中文 token**：CJK≈1 token/字 估算（v2 修复旧版 len//3 低估），仍非真 tokenizer。
3. **检索/反思**：与 Generative Agents 原文/官方代码的逐项偏差见 ../02-architecture.md §6 偏差清单。
4. **内容审核未实现**：只有结构校验（军规 7）；军规 13 的内容闸门在真实接入时必须补。
5. **崩溃是进程内异常**（热重启）；冷重启用 `--checkpoint-dir` + `--resume`（v3 实装：meta 入快照 + fsync + 从 ckpt.json 续跑）。注入触发集合不跨进程持久化，冷重启后未来调度注入点可能再触发（演练语义）。

## 每个演示点对应的研究证据

| 演示点 | 军规 | 证据 |
| --- | --- | --- |
| T0 纯函数作息覆盖 >99.9% | 1/2 | 千人小镇 dayRng [S16]；OASIS 分层激活 [S05][S06]；AI Town 社区规则工作层提案 PR #313（未合并）[S21] |
| 命名空间 ID + 爆炸半径测试 | 3 | resident.js:291 反事实设计注释（旧方案本会重掷 ~760 人；测试复刻教训机制：加 40 人）[S16] |
| 检查点含 RNG+meta + 真实崩溃重放 + 深拷贝隔离 | 4/5 | generative_agents fork/fin [S02]；last_accessed 事故 PR #211 [S22]；AgentSociety2 无状态 [S08] |
| 限流风暴 → 指数退避 → 熔断 → 半开探针 | 6 | 官方限流挂起教训 [S02]；对话循环事故 PR #203 [S22] |
| 坏 JSON / 越界 focus → 拒绝 + 审计 | 7 | PRD §7.5 [S15]；Concordia GM [S10]；Sid 幻觉级联 [S04]；gpt-4o 解析事故 PR #208 [S22] |
| 名册/计划/记忆污染 → 看门狗 → 回滚 → 体面停机 | 8 | PRD F-06 [S15]；AI Town input 校验 [S18] |
| 记忆检索 + 重要性触发反思 | 10 | Generative Agents [S01][S19] |
| 预算封顶 → 降档 → 全规则 | 11 | Batch spend limit 警告 [S14] |
| 前缀缓存计价 + Batch 5折 | 10/11 | [S13][S14] |
| 只追加审计（模拟时间戳） | 12 | PRD §7.4 [S15]；JSONL replay [S08] |
