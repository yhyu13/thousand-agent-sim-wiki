#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""overnight_town 测试套件 v3.42（55 项）：python -m unittest test_overnight_town -v
v2：别名污染回归、检查点隔离、from_dict 等价、边界、计划违例实弹、半开探针、审计顺序、
体面停机、meta 崩溃安全；v3：存档相位 BLOCKER、回滚后崩溃窗口、分散注入、抽样互质、
resume 五连、Config 校验；v3.2：语义损坏 ckpt、NaN/CLI 拒绝、记忆剪枝 TTL×3；
v3.3：深层语义损坏、跨版本计数补齐、内存篡改单点校验、ttl 边界断言、ttl 类型；
v3.4：叶子层校验、OSError 路径、schema_version 契约、nights/agents 类型；
v3.5：叶子层残留、events-out 导出契约、seed/budget/frac/p_* 类型（bool 陷阱）；
v3.6：llm 兄弟字段/tokens 对/residents.id/memories 叶子/plans 段、frac/p_* 拒 str；
v3.7：schema 驱动校验（44 形态：memories 全字段/非空 keywords/plans 键完整性/
段 state/location/residents 全字段/llm 档位齐全/meta.unresolved/events 元素）、batch/storm/resume bool；
v3.8：R10 三根因（keywords 元素 str/audit 内部 type/夜班 id 格式，49 形态）+ 消费点运行时防御。
v3.9：R11 夜班 id 双层独立机制（校验 ASCII 谓词+前缀一致 / build_day try-int）+ NaN/inf 有限校验
+ 夜班独立回归与消费点防御单元守卫（62 形态，杀 M3/M4/M5/M35）。
v3.10：R12 _finite 安全版（拒超 float 范围大整数 10**400，封 OverflowError 裸 traceback）+ 前缀形态
改不重名 id 破遮蔽（杀 N2）+ 看门狗 I3/存档闸门/Config 大整数回归（杀 N5/N6，66 形态）。
v3.11：R13 深嵌套合法 JSON RecursionError 捕获转 ValueError（load 解析/深拷贝两处+main 兜底）
+ 数值字段 bool deep 形态 + main 大整数 counter 活兜底回归 + agents/nights 量级上限（70 形态，杀 X_recursion/X_cost_bool/X_main_exc）。
v3.12：R14（ACCEPT 后硬化）corrupt_times 量级上限闭合近无限循环同族残留 + p_* bool deep 形态（杀 X_p_bool/X_corrupt_cap，73 形态）
+ 深拷贝/main RecursionError 冗余兜底诚实标注。
v3.13：R15（ACCEPT）观察项硬化——量级测试超界改精确 +1 边界（agents/nights/corrupt_times）+ STATUS 错别字修正（编辑性，无行为变更）。
v3.14：R16（ACCEPT）O-1 历史引文改写（清除错别字字面 grep 命中，编辑性，无代码/测试行为变更）。
v3.15：R18（wiki 研究正文首次深审 ACCEPT）grounding 校准——04 头条 ±20% 改为公式化估算（偏差界须校准）/缓存乘数理想化披露挂钩 §3.1/10.2%→10.25%、03 军规 11「精确」→「公式化」、07 契约草图可解析、sources S02 n3 底本名澄清。**demo 代码无变更、哈希不变**。
v3.16：R19（ACCEPT）O-2 根因修复——控制台预算百分比 %.1f→%.2f（与 JSON budget_used_pct=10.25 对齐，纯打印变更、哈希不变）+ demos README 轮号口径澄清。
v3.17：轮 21 研究迭代——GA bootstrap scratch.json 直抓关闭 sources §E 开放项（初始发现：覆盖机制 + Isabella 底本 recency_decay=0.995）。**demo 代码无变更、哈希不变**。
v3.18：R21 穷尽纠正（单点→全称被证伪）——分底本口径（n25 25/25=0.995=论文 / n3 混合 Isabella 0.995、Klaus/Maria 0.99），n25 trigger 250≠论文 150 第二处偏差；02 §6/sources §E/S19 分底本；R22 编辑性收尾（版本标签对齐/§6 标签/清已结 TODO）。**demo 代码无变更、哈希不变**。
v3.19：轮 24 研究迭代——直抓关闭 Qwen 现价 ⏳ 项并纠正 S27「无单价」误判（公开定价页 model-pricing 可得）；04 §1.5 现价表 + 千人一夜重算算例 + 口径告诫。**demo 代码无变更、哈希不变**。
v3.20：R24（ACCEPT）收尾——04:27 过期指针→§1.5、§1.5 Batch 依据补登记 + 思考模式细化（3.x 同单价思考 token 计入输出/Batch 默认开启思考）、S27 补 Batch API 页。**demo 代码无变更、哈希不变**。
v3.21：R26（整体验收 ACCEPT，原始目标达成）——roi_calculator 修过期指针 + 补 Qwen 现价 5 场景（北京区 USD，no_stack 缓存/Batch 不叠加，实跑对齐 04 §1.5）；S27 作用域精化。**overnight_town.py 无变更、哈希不变**。
v3.22：R27（ACCEPT 零缺陷）——roi_calculator 补 qwen-plus legacy 现价行（覆盖 §1.5 全部 distinct 价格，6 场景）。**overnight_town.py 无变更、哈希不变**。
v3.23：R28（ACCEPT）同步收尾——README 计数 5→6、roi docstring 含 legacy、04 §1.5 算例表补 qwen-plus 行。**overnight_town.py 无变更、哈希不变**。
v3.24：R29（ACCEPT 零发现）后可选深化——visualize.html 居民记忆流查看器（ckpt.json 载入/居民选择器/记忆流+计划，XSS 转义+null 容错，vis_smoke 24→33 项，真实 Chromium 验证）；S27 补全七单价。**overnight_town.py 无变更、哈希不变**。
v3.25：R30（ACCEPT）居民查看器硬化——start/end Number 强制（与 minute 同口径）、记忆精确计数（排除 null/畸形）、居民 option 上限 2000 + 计划行上限 300（仿 nights 366，防恶意检查点挂死）；vis_smoke 33→36 项，真实 Chromium 复验。**overnight_town.py 无变更、哈希不变**。
v3.26：R31（ACCEPT）微硬化——selectedResident Math.trunc 整数索引（INFO-1）、记忆 filter 排除数组（INFO-2 严格对象）；vis_smoke 36→38 项，真实 Chromium 复验。**overnight_town.py 无变更、哈希不变**。
v3.27：R33（操作文档深审 REQUEST_CHANGES）修复——05 预算演练预期准确化（@0.05 降档对话仍 T1 + @0.001 近全规则行，实测核验）、标准命令补 --events-out、风暴 caveat、meta 措辞、07 output_format 区分；overnight_town.py 仅 events 注释修正（反思不入 events），**哈希不变**。
v3.28：R34（ACCEPT）O-1 落实——sources S24 补废弃参数区分细节（原始 output_format 废弃 vs messages.parse 现行 vs output_config.format 无需 header，官方页直抓核验）。sources only，**demo 无变更、哈希不变**。
v3.29：R35（ACCEPT）可选深化——S24 补 Python 限定；新增分布式规模化路线最小复刻 distributed_replica.py + test_distributed_replica.py（8 测试，并行==串行实证 [S08]）。**overnight_town.py 无变更、哈希不变**。
v3.30：R36（ACCEPT）分布式复刻硬化——检查点记录并校验 focal_period、resume schema 校验、量级上限、唯一 id/段统计语义注、README 签名对齐；test_distributed_replica 8→11。**overnight_town.py 无变更、哈希不变**。
v3.31：R37（ACCEPT 硬化复核，52 断言全过）分布式复刻值类型硬化——resume 值类型校验（seed/n/tick 须 int 排除 bool、residents 须 list，键齐全但值损坏干净 rc=2）+ schema_version 读取校验（仅支持整数 1）+ focal_period 严格整数化（封 True==1/10.0==10 等值陷阱）；test_distributed_replica 11→13。**overnight_town.py 无变更、哈希不变**。
v3.32：R38（ACCEPT，106 探针域内零穿透）四项闭合——深嵌套合法 JSON RecursionError 捕获（与 R13 同型）+ 负 tick 拒绝（防 -(10^400) 挂死绕过上限）+ residents 数量与 n 交叉校验 + 检查点/报告写路径 OSError 干净拒绝；test_distributed_replica 13→17。**overnight_town.py 无变更、哈希不变**。
v3.33：R39（REQUEST_CHANGES MINOR，域内反例：world 额外键深嵌套 W1 deepcopy/W2 写盘裸崩，三递归上限不对称 load~2996/dump~994/deepcopy~497）——snap/world 双层未知键闸门 + main() 顶层 RecursionError 兜底（与本 demo R13 同模式）+ 措辞三层限定；test_distributed_replica 17→19。**overnight_town.py 无变更、哈希不变**。
v3.34：R40（ACCEPT，234 探针域内零反例）O-1/O-2 落实——分布式复刻顶层兜底扩四家族（ValueError/OSError/OverflowError/RecursionError，与本 demo main() 对齐；孤立代理对 UnicodeEncodeError ⊂ ValueError 干净拒绝，域外元素垃圾 TypeError/KeyError 保持 rc=1）；test_distributed_replica 19→20。**overnight_town.py 无变更、哈希不变**。
v3.35：R42（发布产物 fresh clone 端到端审计 ACCEPT）2 MINOR 编辑性修复——01 页分布式复刻「8 测试」→20、README 回归覆盖轮范围 1–28→1–41 并补 75 测试口径；README 补本地底稿不随公开 repo 分发说明、STATUS 初始快照行加轮号注记。**代码无变更、哈希不变**。
v3.36：R44（冷读者任务式可用性审计 ACCEPT，30+ 指标零失配 + 8 grounding 直抓全属实 + 独立产出通宵运行计划）3 MINOR + 3 观察项编辑性落实——三处快速开始 cd 改 <repo>/demos、demos README 运行节补分布式复刻命令、STATUS 过期可选深化 TODO 更正（查看器/stdlib 复刻已落地）；02 §7 加「Ray 版」限定、S16 补公开 URL + 行号漂移注、增长记忆计数注明 ckpt 读取位置。**代码无变更、哈希不变**。
v3.37：R45（ACCEPT 零缺陷）观察项落实 + 主动研究迭代——.gitignore 补 out/ckpt/ 与 out/dist/（对齐 growth_*_ckpt 模式）；**千人 30 夜浸泡实测证伪 10MB 线性外推**（实测 3.04MB/9204 记忆/$2.8983；事件派生记忆 6204 与 200 人跑恰相等→固定配额下夜数驱动），04 §3.1/03 军规 10/demos README 三处纠正 + 口径告诫，报告入库 out/growth_1000x30_report.json。**代码无变更、哈希不变**。
v3.38：R46（ACCEPT，独立复跑逐值命中+机理加固：6204 精确分解/配额硬常数/拒绝不写记忆）后主动研究迭代续——**千人 30 夜全注入跑 GREEN**（崩溃恢复1+回滚1 全吸收，world_hash/成本/调用数与干净跑逐位一致，重放不膨胀计费）+ **千人 TTL=7 剪枝跑**（剪枝 4548 与 200 人跑逐位相同，检查点 -28.5%）；07:57 交叉注记（112/夜 3 夜口径 vs 浸泡 122/夜）；README TL;DR#2 补实测锚点；两报告入库。**代码无变更、哈希不变**。
v3.39：R47（ACCEPT，三不变量证伪失败+机理代码逐行吻合+字节分解）后——04 §3.1 基座措辞精化（~1190B/人总增量分解人格422+计划628+字段131）；**多种子稳健性实证：seed 42/20261111 × 1000×30 全注入亦 GREEN**（三种子全 GREEN，记忆公式 3N+2×对话+(反思−拒绝) 跨种子闭合，注入点 frac 定位），两报告入库。**代码无变更、哈希不变**。
v3.40：R48（ACCEPT，13 复跑+177 断言，记忆公式边界定位 TTL）MINOR-1 修正——04 §3.1 成本归因改「prompt token 差与失败/重试叠加」（零失败反事实证伪单独归因：纯 prompt −0.013417 量级大于净差 +0.004870 且反号），作者独立复跑核实，两 clean 报告入库；STATUS 记忆公式行补 TTL 边界注。**代码无变更、哈希不变**。
v3.41：R49（ACCEPT，反事实逐值命中+独立成本重算+调用核算 3720−降级+重试 三种子精确）MINOR-1 修正——归因标签精化：零失败种子差主导项是 **output 响应长度采样**（−0.013901，out=OUT_BASE+rng.randint(40) 纯种子派生 :276/:727），prompt 输入差仅 +0.000484 微小反号（R49 分解、作者独立复核）；「失败/重试」改「失败总效应差」（含跳过/降级，两跑均净降本）。数字与分解算式不变。**代码无变更、哈希不变**。
v3.42：R50（ACCEPT，seed-only 重放探针证实 output 零 prompt 信息+唯一整数解成本重解）MINOR-1 修正——核算式内联定义（llm_calls=3720−降级事件+限流尝试+坏JSON尝试，三种子算例；坏JSON不重试仍计费须入式，「重试」仅指限流）；「重试加价」改「限流不计费、坏JSON仍计费」；三联数注种子顺序；STATUS 96.6% 补绝对贡献和口径。**代码无变更、哈希不变**。
可视化冒烟另见 vis_smoke.js（node vis_smoke.js .，38 项）；对比度实测 contrast_check.py（6 项含 RED）。"""
import copy
import json
import os
import tempfile
import unittest

from overnight_town import (CheckpointStore, Config, MockLLM, Rng, Supervisor,
                            World, build_day, canonical_hash, do_reflections,
                            fnv1a, gateway, make_snapshot, new_counters,
                            retrieve, run_overnight, sample_indices,
                            validate_patch)

BASE = dict(seed=20260818, nights=2, agents=200, budget=2.0,
            crash_frac=None, corrupt_frac=None, storm=False)


def cfg(**kw):
    d = dict(BASE)
    d.update(kw)
    return Config(**d)


def _nurse_id(s, new_id):
    """R11 MAJOR-2：把 residents[0] 改成夜班并**同步重命名 plans 键**，
    使 plans 键完整性检查放行——只有夜班 id 格式检查能拒绝（杀 M3/M35 的独立形态）。"""
    r = s["world"]["residents"][0]
    old = r["id"]
    r["role"] = "nurse"
    r["id"] = new_id
    s["world"]["plans"][new_id] = s["world"]["plans"].pop(old)


class TestDeterminism(unittest.TestCase):
    def test_determinism_clean(self):
        """军规2：同种子双跑终态哈希逐位一致。"""
        r1, r2 = run_overnight(cfg()), run_overnight(cfg())
        self.assertEqual(r1["status"], "GREEN")
        self.assertEqual(r1["final_hash"], r2["final_hash"])

    def test_crash_resume_equivalence(self):
        """军规4/5：真实崩溃（不存新检查点）→回退最近周期检查点→重放，终态一致。"""
        base = run_overnight(cfg(storm=True))
        crashed = run_overnight(cfg(storm=True, crash_frac=0.4))
        self.assertEqual(crashed["crashes_recovered"], 1)
        self.assertEqual(crashed["status"], "GREEN")
        self.assertEqual(base["final_hash"], crashed["final_hash"])

    def test_corrupt_rollback_absorbed(self):
        """军规8：名册污染被看门狗检出并回滚，世界本体不变、人口恢复、审计留痕。"""
        base = run_overnight(cfg(storm=True))
        corrupted = run_overnight(cfg(storm=True, corrupt_frac=0.5))
        self.assertGreaterEqual(corrupted["interventions_rollbacks"], 1)
        self.assertEqual(corrupted["population_final"], 200)
        self.assertEqual(corrupted["status"], "GREEN")
        self.assertEqual(base["world_hash"], corrupted["world_hash"])
        self.assertGreaterEqual(corrupted["audit_summary"].get("rollback", 0), 1)

    def test_full_injection_absorbed(self):
        """崩溃+污染同时注入，世界本体仍与仅风暴运行一致。"""
        base = run_overnight(cfg(storm=True))
        full = run_overnight(cfg(storm=True, crash_frac=0.37, corrupt_frac=0.61))
        self.assertEqual(full["status"], "GREEN")
        self.assertEqual(base["world_hash"], full["world_hash"])

    def test_census_blast_radius(self):
        """军规3：复刻 resident.js:291 的反事实教训——名册加 40 人，老居民计划逐位不变。
        注：~760 人是旧全局计数器方案下『本会』受影响的规模（源码注释 would have），
        本测试复刻的是教训机制（加 40 岗位），不是事故规模。"""
        w1, w2 = World(20260818, 1000), World(20260818, 1040)
        for i in range(0, 1000, 50):
            rid = w1.residents[i]["id"]
            self.assertEqual(w1.plans[rid], w2.plans[rid], rid)
        self.assertEqual(len(w2.residents), 1040)


class TestCheckpointIntegrity(unittest.TestCase):
    """BLOCKER 回归：恢复路径的检查点别名污染（demo critic round 1）。"""

    def test_crash_corrupt_same_tick(self):
        """崩溃恢复后同一 tick 注入污染：回滚必须加载干净检查点。"""
        base = run_overnight(cfg(storm=True))
        r = run_overnight(cfg(storm=True, crash_frac=0.5, corrupt_frac=0.5))
        self.assertEqual(r["status"], "GREEN")
        self.assertEqual(r["population_final"], 200)
        self.assertEqual(base["world_hash"], r["world_hash"])

    def test_crash_corrupt_adjacent(self):
        """崩溃恢复后、下一次周期存档前注入污染（原失效窗口 gap=1）。"""
        base = run_overnight(cfg(storm=True))
        total = 2 * 144
        r = run_overnight(cfg(storm=True, crash_frac=0.5,
                              corrupt_frac=(0.5 * total + 1) / total))
        self.assertEqual(r["status"], "GREEN")
        self.assertEqual(base["world_hash"], r["world_hash"])

    def test_crash_corrupt_disk_backend(self):
        """磁盘检查点后端：与内存后端行为一致（原后端依赖 bug）。"""
        base = run_overnight(cfg(storm=True))
        with tempfile.TemporaryDirectory() as d:
            r = run_overnight(cfg(storm=True, crash_frac=0.5, corrupt_frac=0.5,
                                  checkpoint_dir=d))
            self.assertTrue(os.path.exists(os.path.join(d, "ckpt.json")))
        self.assertEqual(r["status"], "GREEN")
        self.assertEqual(base["world_hash"], r["world_hash"])

    def test_checkpoint_isolation(self):
        """load() 返回深拷贝：修改恢复体不得污染检查点。"""
        store = CheckpointStore()
        w = World(7, 50)
        llm = MockLLM(Rng(11))
        meta = {"rollbacks": 0, "violations_detected": 0, "unresolved": []}
        store.save(make_snapshot(6, w, llm, Rng(33), new_counters(), meta))
        loaded = store.load()
        loaded["world"]["residents"].pop()
        loaded["counters"]["conversations_llm"] = 999
        loaded["llm"]["tokens"]["T1"][0] = 12345
        self.assertEqual(len(store.latest["world"]["residents"]), 50)
        self.assertEqual(store.latest["counters"]["conversations_llm"], 0)
        self.assertEqual(store.latest["llm"]["tokens"]["T1"][0], 0)

    def test_from_dict_restore_equivalence(self):
        """World.from_dict 恢复后哈希等价（防回归）。"""
        w = World(7, 60)
        d = json.loads(json.dumps(w.to_dict(), ensure_ascii=False))
        w2 = World.from_dict(d)
        self.assertEqual(canonical_hash(w.to_dict()), canonical_hash(w2.to_dict()))

    def test_meta_crash_safe(self):
        """干预计数入检查点：崩溃恢复后 violations_detected 不丢失。"""
        r = run_overnight(cfg(corrupt_frac=0.2, crash_frac=0.5))
        self.assertEqual(r["crashes_recovered"], 1)
        self.assertGreaterEqual(r["violations_detected"], 1)
        self.assertEqual(r["status"], "GREEN")


class TestResilience(unittest.TestCase):
    def test_budget_cap(self):
        """军规11：预算耗尽是降级事件不是崩溃事件。"""
        r = run_overnight(cfg(budget=0.05))
        self.assertEqual(r["status"], "GREEN")
        self.assertLessEqual(r["cost_usd"], 0.05 + 1e-9)
        self.assertEqual(r["ticks_completed"], r["ticks_planned"])
        c = r["counters"]
        self.assertGreater(c["budget_degradations"] + c["budget_refusals"], 0)

    def test_all_malformed(self):
        """军规7：100% 坏输出 → 全兜底，世界照常跑完。"""
        r = run_overnight(cfg(p_bad=1.0, p_rate=0.0))
        self.assertEqual(r["status"], "GREEN")
        c = r["counters"]
        self.assertGreater(c["conversations_degraded"], 0)
        self.assertGreater(c["reflections_degraded"], 0)
        self.assertEqual(c["conversations_llm"], 0)

    def test_all_rate_limited(self):
        """军规6：100% 限流 → 退避+熔断+规则兜底，零计费，世界不停。"""
        r = run_overnight(cfg(p_rate=1.0, p_bad=0.0))
        self.assertEqual(r["status"], "GREEN")
        self.assertEqual(r["cost_usd"], 0.0)
        c = r["counters"]
        self.assertGreater(c["breaker_opens"], 0)
        self.assertGreater(c["backoff_skips"], 0)
        self.assertGreater(c["conversations_degraded"], 0)

    def test_batch_discount(self):
        """[S14]：Batch 模式成本约为标准模式一半（世界本体不受计价影响）。"""
        std = run_overnight(cfg())
        bat = run_overnight(cfg(batch=True))
        self.assertEqual(std["world_hash"], bat["world_hash"])
        self.assertAlmostEqual(bat["cost_usd"], std["cost_usd"] * 0.5, places=5)

    def test_plan_corruption_detected(self):
        """军规8 实弹：计划/记忆违例（I2/I4）被抽样看门狗检出并回滚。"""
        base = run_overnight(cfg(storm=True))
        r = run_overnight(cfg(storm=True, corrupt_plan_frac=0.5))
        self.assertGreaterEqual(r["interventions_rollbacks"], 1)
        self.assertGreaterEqual(r["violations_detected"], 2)  # I2 + I4
        self.assertEqual(r["status"], "GREEN")
        self.assertEqual(r["population_final"], 200)
        self.assertEqual(base["world_hash"], r["world_hash"])

    def test_p_invalid_no_pollution(self):
        """军规7：100% 越界 focus → 全拒绝，零采纳，审计留痕。"""
        r = run_overnight(cfg(p_invalid=1.0, p_rate=0.0, p_bad=0.0))
        c = r["counters"]
        self.assertEqual(c["reflections_accepted"], 0)
        self.assertGreater(c["reflections_rejected"], 0)
        self.assertGreaterEqual(r["audit_summary"].get("patch_rejected", 0), 1)

    def test_graceful_stop(self):
        """军规8：连续回滚超限 → 体面停机 RED，不带病运行。"""
        r = run_overnight(cfg(corrupt_frac=0.2, corrupt_times=4))
        self.assertEqual(r["status"], "RED")
        self.assertGreaterEqual(r["interventions_rollbacks"], 3)
        self.assertLess(r["ticks_completed"], r["ticks_planned"])
        self.assertGreater(len(r["violations_unresolved"]), 0)


class TestUnits(unittest.TestCase):
    def test_backoff_and_half_open(self):
        """军规6：调用间指数退避 + 熔断开→半开探针→关闭，全链路单元测试。"""
        llm = MockLLM(Rng(5), p_rate=1.0, p_bad=0.0)
        counters, audit = new_counters(), []
        s, _, _ = gateway(llm, "T1", "p", 0, 2.0, counters, audit, 0, 0)
        self.assertEqual(s, "rate_limit")
        self.assertGreater(llm.backoff_until, 0)          # 指数退避已设置
        s, _, _ = gateway(llm, "T1", "p", 1, 2.0, counters, audit, 0, 10)
        self.assertEqual(s, "backoff")                    # 退避期跳过
        self.assertEqual(counters["backoff_skips"], 1)
        gateway(llm, "T1", "p", 20, 2.0, counters, audit, 0, 200)
        self.assertGreaterEqual(counters["breaker_opens"], 1)  # 连续失败→熔断
        self.assertTrue(llm.breaker_half_open)
        s, _, _ = gateway(llm, "T1", "p", 21, 2.0, counters, audit, 0, 210)
        self.assertEqual(s, "breaker")                    # 熔断期跳过
        llm.p_rate = 0.0
        s, _, _ = gateway(llm, "T1", "p", 40, 2.0, counters, audit, 0, 400)
        self.assertEqual(s, "ok")                         # 到期后第一调用=探针
        self.assertEqual(counters["breaker_closes"], 1)   # 探针成功→关闭
        self.assertFalse(llm.breaker_half_open)

    def test_budget_audit_order(self):
        """熔断期不得记录根本没执行的预算降级（审计保真）。"""
        llm = MockLLM(Rng(5))
        llm.breaker_until = 100
        counters, audit = new_counters(), []
        s, _, _ = gateway(llm, "T2", "p", 0, 0.0001, counters, audit, 0, 0)
        self.assertEqual(s, "breaker")
        self.assertEqual(counters["budget_degradations"], 0)
        self.assertEqual(audit, [])

    def test_agents_zero_no_crash(self):
        """边界：agents=0 不得 IndexError；无事件 → RED 但跑完。"""
        r = run_overnight(cfg(agents=0, nights=1))
        self.assertEqual(r["ticks_completed"], r["ticks_planned"])
        self.assertEqual(r["population_final"], 0)
        self.assertEqual(r["status"], "RED")

    def test_nights_zero_no_false_violation(self):
        """边界：nights=0 空跑不得误报 I5 时钟不一致。"""
        r = run_overnight(cfg(nights=0))
        self.assertEqual(r["ticks_completed"], 0)
        self.assertFalse(any("I5" in v for v in r["violations_unresolved"]))

    def test_retrieval_ranking(self):
        """[S01] 简化三因子：新+重要+相关的记忆排最前。"""
        mems = [
            {"day": 0, "minute": 0, "text": "旧闻", "importance": 1.0,
             "kind": "x", "keywords": ["无关"]},
            {"day": 1, "minute": 700, "text": "新且相关", "importance": 9.0,
             "kind": "x", "keywords": ["plaza", "nurse"]},
        ]
        top = retrieve(mems, ["plaza", "nurse"], 1 * 1440 + 720, k=1)
        self.assertEqual(top[0]["text"], "新且相关")

    def test_patch_validation(self):
        """军规7：ID 白名单 + 值域校验。"""
        ids = {"nurse-001"}
        ok, _ = validate_patch(ids, {"target": "nurse-001", "tomorrow_focus": "health"})
        self.assertTrue(ok)
        ok, _ = validate_patch(ids, {"target": "ghost-999", "tomorrow_focus": "health"})
        self.assertFalse(ok)
        ok, _ = validate_patch(ids, {"target": "nurse-001", "tomorrow_focus": "征服世界"})
        self.assertFalse(ok)

    def test_checkpoint_json_roundtrip(self):
        """军规5：检查点 JSON 安全 + from_dict 恢复等价 + RNG 状态在快照内。"""
        w = World(7, 50)
        llm = MockLLM(Rng(11))
        meta = {"rollbacks": 0, "violations_detected": 0, "unresolved": []}
        snap = make_snapshot(6, w, llm, Rng(33), new_counters(), meta)
        rt = json.loads(json.dumps(snap, ensure_ascii=False))
        self.assertEqual(canonical_hash(snap), canonical_hash(rt))
        self.assertEqual(snap["rng"]["event"], 33)
        self.assertEqual(snap["schema_version"], 2)  # 钉住 v3.3 契约（杀 R6 M6 变异）
        self.assertIn("meta", snap)
        w2 = World.from_dict(rt["world"])
        self.assertEqual(canonical_hash(w2.to_dict()), canonical_hash(w.to_dict()))

    def test_reflection_threshold(self):
        """[S01]：重要性累计超阈才反思；反思后清零。"""
        w = World(7, 100)
        w.abs_minute, w.day = 1320, 0
        for r in w.residents[:3]:
            r["imp_sum"] = 10.0
        llm = MockLLM(Rng(5), p_rate=0.0, p_bad=0.0, p_invalid=0.0)
        counters = new_counters()
        do_reflections(w, llm, Rng(9), 132, 2.0, counters)
        total = (counters["reflections_accepted"] + counters["reflections_rejected"]
                 + counters["reflections_degraded"])
        self.assertEqual(total, 3)
        for r in w.residents[:3]:
            self.assertEqual(r["imp_sum"], 0.0)
            self.assertEqual(r["last_ref_day"], 0)

    def test_supervisor_detects_population_loss(self):
        """军规8：人口不守恒必须被检出（全员检查，非抽样）。"""
        w = World(7, 50)
        w.abs_minute = 0
        sup = Supervisor(50, 2.0)
        self.assertEqual(sup.check(w, MockLLM(Rng(1)), 1, full=True), [])
        w.residents.pop()
        self.assertTrue(any("I1" in v for v in sup.check(w, MockLLM(Rng(1)), 1, full=True)))


class TestRound2Regressions(unittest.TestCase):
    """critic 轮 2 新发现的回归：检查点相位 / 干预审计窗口 / 分散注入 / 抽样退化 / 冷重启。"""

    def test_roster_corrupt_checkpoint_phase(self):
        """BLOCKER 回归：污染相位 (X+1)%6==0 时脏状态不得进入检查点。
        注意浮点陷阱：用 (t+0.5)/total 精确命中目标 tick。"""
        base = run_overnight(cfg(storm=True))
        total = 2 * 144
        r = run_overnight(cfg(storm=True, corrupt_frac=59.5 / total))  # X=59, 60%6==0
        self.assertEqual(r["status"], "GREEN")
        self.assertEqual(r["population_final"], 200)
        self.assertEqual(base["world_hash"], r["world_hash"])

    def test_crash_after_rollback_window(self):
        """MAJOR 回归：回滚后、下次存档前崩溃 → 干预审计与计数不得被抹除。"""
        total = 2 * 144
        no_crash = run_overnight(cfg(storm=True, corrupt_frac=57.5 / total))
        crashed = run_overnight(cfg(storm=True, corrupt_frac=57.5 / total,
                                    crash_frac=58.5 / total))
        self.assertGreaterEqual(no_crash["interventions_rollbacks"], 1)
        self.assertEqual(crashed["status"], "GREEN")
        self.assertGreaterEqual(crashed["interventions_rollbacks"], 1)
        self.assertGreaterEqual(crashed["violations_detected"], 1)
        self.assertGreaterEqual(crashed["audit_summary"].get("rollback", 0), 1)
        self.assertEqual(no_crash["world_hash"], crashed["world_hash"])

    def test_corrupt_times_distributed(self):
        """MINOR 回归：多次注入分散在不同 tick（fired 集合防回滚重放重复触发）。"""
        r = run_overnight(cfg(corrupt_frac=0.2, corrupt_times=3))
        self.assertEqual(r["status"], "GREEN")
        self.assertEqual(r["interventions_rollbacks"], 3)

    def test_sampling_coprime(self):
        """MINOR 回归：101|n 时抽样不得退化为单点。"""
        idx = sample_indices(1, 101)
        self.assertEqual(len(set(idx)), 40)
        w = World(7, 101)
        w.abs_minute = 0
        victim = idx[0]
        w.plans[w.residents[victim]["id"]][0]["end"] = 1500
        sup = Supervisor(101, 2.0)
        self.assertTrue(any("I2" in v for v in sup.check(w, MockLLM(Rng(1)), 1)))

    def test_resume_midrun_equivalence(self):
        """R3 MINOR-1 回归：从中间检查点（144/288）续跑，真实执行续跑 tick，
        终态与完整跑逐位一致；resumed_from_tick 证明不是静默重跑。"""
        fresh = run_overnight(cfg(nights=2))
        with tempfile.TemporaryDirectory() as d:
            run_overnight(cfg(nights=1, checkpoint_dir=d))
            resumed = run_overnight(cfg(nights=2, checkpoint_dir=d, resume=True))
        self.assertEqual(resumed["resumed_from_tick"], 144)
        self.assertEqual(resumed["ticks_completed"], 288)
        self.assertEqual(fresh["final_hash"], resumed["final_hash"])

    def test_resume_restores_meta(self):
        """R3 MINOR-1 回归：带干预冷重启后，回滚/违例计数从快照恢复。"""
        with tempfile.TemporaryDirectory() as d:
            first = run_overnight(cfg(nights=1, corrupt_frac=0.2, checkpoint_dir=d))
            self.assertGreaterEqual(first["interventions_rollbacks"], 1)
            second = run_overnight(cfg(nights=2, corrupt_frac=0.2, checkpoint_dir=d, resume=True))
        self.assertEqual(second["resumed_from_tick"], 144)
        self.assertGreaterEqual(second["interventions_rollbacks"], first["interventions_rollbacks"])
        self.assertGreaterEqual(second["violations_detected"], 1)
        self.assertEqual(second["status"], "GREEN")

    def test_resume_config_mismatch(self):
        """R3 MINOR-3 回归：seed/agents 不匹配必须报错，不得静默按错误配置续跑。"""
        with tempfile.TemporaryDirectory() as d:
            run_overnight(cfg(nights=1, checkpoint_dir=d))
            with self.assertRaises(ValueError):
                run_overnight(cfg(nights=1, checkpoint_dir=d, resume=True, seed=999))
            with self.assertRaises(ValueError):
                run_overnight(cfg(nights=1, checkpoint_dir=d, resume=True, agents=100))

    def test_resume_no_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                run_overnight(cfg(nights=1, checkpoint_dir=d, resume=True))

    def test_resume_corrupt_checkpoint(self):
        """R3 MINOR-2 回归：损坏 ckpt.json → 干净 ValueError（CLI 转 p.error）。"""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "ckpt.json"), "w", encoding="utf-8") as f:
                f.write("{corrupted")
            with self.assertRaises(ValueError):
                run_overnight(cfg(nights=1, checkpoint_dir=d, resume=True))

    def test_config_validation(self):
        """MINOR 回归：非法参数在 Config 层即拒绝（库调用不可绕过）。"""
        for kw in ({"budget": -1}, {"agents": -5}, {"nights": -1},
                   {"corrupt_times": 0}, {"crash_frac": 1.0}, {"corrupt_frac": -0.1},
                   {"p_rate": 1.5}, {"p_bad": -0.1}, {"p_invalid": 2.0},
                   {"budget": float("nan")}, {"budget": float("inf")},
                   {"memory_ttl": 0}, {"memory_ttl": 2.5}, {"memory_ttl": True},
                   {"memory_ttl": float("nan")},
                   {"nights": 2.5}, {"agents": True}, {"corrupt_times": 2.5},
                   {"seed": 2.5}, {"seed": True}, {"budget": True},
                   {"crash_frac": False}, {"p_rate": True},
                   {"crash_frac": "x"}, {"p_rate": "x"}, {"corrupt_frac": "x"},
                   {"batch": "x"}, {"storm": []}, {"resume": 1}):
            with self.assertRaises(ValueError):
                cfg(**kw)

    def test_events_out_export(self):
        """R7 MINOR-1 回归：事件流导出行数/标记/直方图与报告一致；导出不改快照；非法路径干净报错。"""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "events.jsonl")
            r1 = run_overnight(cfg(nights=1, events_out=p))
            with open(p, encoding="utf-8") as f:
                lines = [json.loads(l) for l in f if l.strip()]
            self.assertEqual(len(lines), r1["conversations_total"] + r1["audit_entries"])
            audits = [e for e in lines if e.get("_stream") == "audit"]
            self.assertEqual(len(audits), r1["audit_entries"])
            hist = {}
            for a in audits:
                hist[a["type"]] = hist.get(a["type"], 0) + 1
            self.assertEqual(hist, r1["audit_summary"])
            r2 = run_overnight(cfg(nights=1))  # 不带导出
            self.assertEqual(r1["final_hash"], r2["final_hash"])
            with self.assertRaises((OSError, ValueError)):
                run_overnight(cfg(nights=1, events_out=d))  # 指向目录

    def test_checkpoint_oserror_paths(self):
        """R6 NEW-2 回归：ckpt.json 是目录 / checkpoint-dir 是文件 → 干净异常，无裸 traceback。"""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ckpt.json"))  # 检查点路径被目录占据
            with self.assertRaises(ValueError):
                run_overnight(cfg(nights=1, checkpoint_dir=d, resume=True))
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "afile")
            with open(f, "w", encoding="utf-8") as fh:
                fh.write("x")
            with self.assertRaises(OSError):  # makedirs FileExistsError；CLI 层转 p.error
                run_overnight(cfg(nights=1, checkpoint_dir=f))

    def test_cli_rejects_invalid_args(self):
        """R4 MINOR-2/3 回归：CLI 层拒绝非法参数（rc=2，无 traceback）。"""
        from overnight_town import main
        for argv in (["--p-rate", "1.5"], ["--budget", "nan"],
                     ["--crash-frac", "1.0"], ["--memory-ttl", "0"]):
            with self.assertRaises(SystemExit) as cm:
                main(argv)
            self.assertEqual(cm.exception.code, 2)

    def test_resume_semantic_corrupt_checkpoint(self):
        """R4 MINOR-1 回归：合法 JSON 但缺字段/错类型 → 干净 ValueError。"""
        with tempfile.TemporaryDirectory() as d:
            for payload in ('{"foo": 1}', '[]', '{"tick": 5}'):
                with open(os.path.join(d, "ckpt.json"), "w", encoding="utf-8") as f:
                    f.write(payload)
                with self.assertRaises(ValueError):
                    run_overnight(cfg(nights=1, checkpoint_dir=d, resume=True))

    def test_resume_semantic_corrupt_deep(self):
        """R5 MINOR-1 回归：真实快照的深层语义损坏（缺 day/bool tick/负 tick/空 rng/
        错类型 residents/错类型 meta/空 llm）全部干净拒绝。"""
        with tempfile.TemporaryDirectory() as d:
            run_overnight(cfg(nights=1, checkpoint_dir=d))
            p = os.path.join(d, "ckpt.json")
            with open(p, encoding="utf-8") as f:
                base = json.load(f)
            muts = [
                lambda s: s["world"].pop("day"),
                lambda s: s.update(tick=True),
                lambda s: s.update(tick=-5),
                lambda s: s.update(rng={}),
                lambda s: s["world"].update(residents="x"),
                lambda s: s.update(meta=[]),
                lambda s: s["llm"].clear(),
                # R6 NEW-1 叶子层形态
                lambda s: s["world"].update(day="x"),
                lambda s: s.update(llm={"rng": 123}),
                lambda s: s["rng"].update(event="x"),
                lambda s: s["meta"].update(rollbacks="x"),
                lambda s: s["counters"].update(conversations_llm="x"),
                lambda s: s["world"].update(residents=[{}]),
                # R7 MINOR-2 叶子层残留形态
                lambda s: s["llm"].update(calls="x"),
                lambda s: s["llm"].update(cost="x"),
                lambda s: s["llm"].update(tokens="x"),
                lambda s: s["world"]["plans"].update({s["world"]["residents"][0]["id"]: "y"}),
                lambda s: s["world"]["residents"][0].update(memories=[None]),
                # R8 MINOR-2 兄弟字段形态
                lambda s: s["llm"].update(batch="x"),
                lambda s: s["llm"].update(p_invalid="x"),
                lambda s: s["llm"].update(prefix_written="x"),
                lambda s: s["llm"].update(backoff_until="x"),
                lambda s: s["llm"].update(breaker_half_open="x"),
                lambda s: s["llm"]["tokens"].update(T1="x"),
                lambda s: s["llm"]["tokens"].update(T1=[1, "a"]),
                lambda s: s["world"]["residents"][0].update(id=5),
                lambda s: s["world"]["residents"][0]["memories"][0].update(importance="x"),
                lambda s: s["world"]["residents"][0]["memories"][0].update(keywords="x"),
                lambda s: s["world"]["plans"][s["world"]["residents"][0]["id"]][0].update(start="x"),
                # R9 NEW-1 家族代表形态（15 崩溃形态代表集，非穷尽——见上层 docstring）
                lambda s: s["world"]["residents"][0]["memories"][0].update(day="x"),
                lambda s: s["world"]["residents"][0]["memories"][0].pop("text"),
                lambda s: s["world"]["residents"][0]["memories"][0].update(keywords=[]),
                lambda s: s["world"]["plans"][s["world"]["residents"][0]["id"]][0].pop("state"),
                lambda s: s["world"]["plans"][s["world"]["residents"][0]["id"]][0].update(state=[]),
                lambda s: s["world"]["plans"][s["world"]["residents"][0]["id"]][0].pop("location"),
                lambda s: s["world"]["plans"].pop(s["world"]["residents"][0]["id"]),
                lambda s: s["world"]["residents"][0].pop("role"),
                lambda s: s["world"]["residents"][0].update(imp_sum="x"),
                lambda s: s["world"]["residents"][0].pop("last_ref_day"),
                lambda s: s["llm"].update(prefix_written={}),
                lambda s: s["llm"]["tokens"].pop("T2"),
                lambda s: s["meta"].update(unresolved=42),
                lambda s: s["world"]["residents"][0].update(focus=42),
                lambda s: s["world"].update(events=[None]),
                # R10 三根因形态（keywords 元素/audit 内部 type/夜班 id 格式）
                lambda s: s["world"]["residents"][0]["memories"][0].update(keywords=[["x"]]),
                lambda s: s["world"]["residents"][0]["memories"][0].update(keywords=[{"a": 1}]),
                lambda s: s["world"].update(audit=[{}]),
                lambda s: s["world"].update(audit=[{"type": []}]),
                lambda s: s["world"]["residents"][0].update(role="nurse", id="nurse"),
                # R11 MAJOR-2：夜班 id 独立回归（plans 同步改名，仅 id 格式检查能拒；杀 M3/M35）
                lambda s: _nurse_id(s, "nurse"),          # 无 dash
                lambda s: _nurse_id(s, "nurse-²"),        # isdigit 但 int() 抛（MAJOR-1 洞）
                lambda s: _nurse_id(s, "nurse-①"),        # 圈号同上
                lambda s: _nurse_id(s, "nurse-٣"),        # 非 ASCII 十进制（MINOR-3 收紧）
                lambda s: _nurse_id(s, "nurse-１"),       # 全角同上
                lambda s: _nurse_id(s, "guard-999"),      # 前缀与 role 不一致（MINOR-3；R12 NEW-2 用不重名 id 破除重复 id 遮蔽，杀 N2）
                lambda s: _nurse_id(s, "nurse-"),         # 空后缀
                # R11 MINOR-1：NaN/inf 数值字段（校验须拒，不再靠存档闸门中途崩）
                lambda s: s["llm"].update(cost=float("nan")),
                lambda s: s["llm"].update(cost=float("inf")),
                lambda s: s["llm"].update(p_rate=float("nan")),
                lambda s: s["llm"]["tokens"].update(T1=[float("nan"), 1]),
                lambda s: s["world"]["residents"][0].update(imp_sum=float("nan")),
                lambda s: s["world"]["residents"][0]["memories"][0].update(importance=float("nan")),
                # R12 NEW-1：有限但超 float 范围的大整数（_finite 须干净 ValueError，不得 OverflowError）
                lambda s: s["llm"].update(cost=10**400),
                lambda s: s["llm"]["tokens"].update(T1=[10**400, 1]),
                lambda s: s["world"]["residents"][0].update(imp_sum=10**400),
                lambda s: s["world"]["residents"][0]["memories"][0].update(importance=10**400),
                # R13 NEW-R13-2：快照数值字段 bool 守卫（代码已拒，补 deep 形态钉死，杀 X_cost_bool_del）
                lambda s: s["llm"].update(cost=True),
                lambda s: s["world"]["residents"][0].update(imp_sum=True),
                lambda s: s["world"]["residents"][0]["memories"][0].update(importance=True),
                lambda s: s["llm"]["tokens"].update(T1=[True, 1]),
                # R14 NEW-R14-2：p_* 快照 bool 守卫独立形态（杀 X_p_bool）
                lambda s: s["llm"].update(p_rate=True),
                lambda s: s["llm"].update(p_bad=True),
                lambda s: s["llm"].update(p_invalid=True),
            ]
            for mut in muts:
                s = copy.deepcopy(base)
                mut(s)
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(s, f)
                with self.assertRaises(ValueError):
                    run_overnight(cfg(nights=1, checkpoint_dir=d, resume=True))

    def test_build_day_shift_defense(self):
        """R11 MAJOR-1/MINOR-4：build_day 防御解析单元守卫（直接库调用，杀 M5/M35）。
        防御用 try-int，独立于校验层 ASCII 谓词：isdigit 但 int() 抛的 ²/① 必须落默认班而非崩。"""
        work_starts = {0: [480, 840], 1: [1020, 1200], 2: [0, 1320]}
        cases = {
            "nurse-1": 0, "nurse-2": 1, "nurse-3": 2, "nurse-4": 0,
            "nurse-0": 2, "nurse-007": 0, "nurse-1-2": 1,
            "nurse": 0, "nurse-": 0, "nurse-abc": 0, "": 0,
            "nurse-²": 0, "nurse-①": 0,        # MAJOR-1：不得抛 ValueError
            "nurse-٣": 2, "nurse-１": 0,        # int() 可解析的 Unicode 十进制：行为安全
        }
        for rid, want in cases.items():
            plan = build_day(7, rid, 0, "nurse", "home", "hospital")
            got = sorted(s["start"] for s in plan if s["state"] == "work")
            self.assertEqual(got, work_starts[want], f"rid={rid!r}")
        # 非夜班角色忽略 id 形态；guard 同属夜班
        self.assertEqual(sorted(s["start"] for s in build_day(7, "²", 0, "baker", "h", "w")
                                if s["state"] == "work"), work_starts[0])
        self.assertEqual(sorted(s["start"] for s in build_day(7, "guard-2", 0, "guard", "h", "w")
                                if s["state"] == "work"), work_starts[1])

    def test_retrieve_filters_non_str_keywords(self):
        """R11 MINOR-4：retrieve 运行时防御单元守卫（绕过校验直接库调用，杀 M4）。
        非 str 关键词元素不得入 set（否则 unhashable TypeError）。"""
        mem = [{"day": 0, "minute": 0, "text": "t", "importance": 5.0,
                "keywords": ["ok", ["x"], 5, {"a": 1}, None]}]
        self.assertEqual(len(retrieve(mem, ["ok"], 60)), 1)
        self.assertEqual(len(retrieve(mem, ["missing"], 60)), 1)  # rel=0 不崩
        self.assertEqual(retrieve(mem, ["ok"], 60)[0]["text"], "t")

    def test_watchdog_i3_detects_nan_cost(self):
        """R12 NEW-3：看门狗 I3 显式查 _finite——运行中 NaN/inf/大整数 cost 必须检出
        （直接构造运行世界，绕过 load 校验；杀 N5）。"""
        w = World(7, 20)
        llm = MockLLM(Rng(11))
        sup = Supervisor(20, 2.0)
        for bad in (float("nan"), float("inf"), 10**400):
            llm.cost = bad
            v = sup.check(w, llm, 1, full=True)
            self.assertTrue(any(x.startswith("I3") for x in v), f"cost={bad!r} 未检出 I3")

    def test_save_rejects_nan(self):
        """R12 NEW-4：存档 allow_nan=False 最终闸门——存 NaN cost 必须 ValueError（杀 N6）。"""
        with tempfile.TemporaryDirectory() as d:
            store = CheckpointStore(d)
            w = World(7, 20)
            llm = MockLLM(Rng(11))
            llm.cost = float("nan")
            meta = {"rollbacks": 0, "violations_detected": 0, "unresolved": []}
            with self.assertRaises(ValueError):
                store.save(make_snapshot(6, w, llm, Rng(33), new_counters(), meta))

    def test_config_rejects_huge_int_budget(self):
        """R12 NEW-1：Config(budget=10**400) 须干净 ValueError，不得 OverflowError。"""
        with self.assertRaises(ValueError):
            cfg(budget=10**400)

    def test_resume_rejects_deep_nesting(self):
        """R13 NEW-R13-1：合法深嵌套 JSON（5000 层）须干净 ValueError，不得 RecursionError 裸 traceback。
        攻击文件用字符串注入构造（json.dump 编码自身会递归崩）；杀「移除 RecursionError 捕获」变异。"""
        from overnight_town import main
        with tempfile.TemporaryDirectory() as d:
            run_overnight(cfg(nights=1, checkpoint_dir=d))
            p = os.path.join(d, "ckpt.json")
            with open(p, encoding="utf-8") as f:
                base_text = f.read()
            anchor = '"unresolved": []'
            self.assertIn(anchor, base_text)
            atk = base_text.replace(anchor, '"unresolved": ' + "[" * 5000 + "]" * 5000, 1)
            with open(p, "w", encoding="utf-8") as f:
                f.write(atk)
            with self.assertRaises(ValueError):
                run_overnight(cfg(nights=1, checkpoint_dir=d, resume=True))
            with self.assertRaises(SystemExit) as cm:
                main(["--seed", str(BASE["seed"]), "--agents", "200", "--nights", "1",
                      "--checkpoint-dir", d, "--resume", "--out", os.path.join(d, "r.json")])
            self.assertEqual(cm.exception.code, 2)

    def test_main_huge_int_counter_backstop(self):
        """R13 NEW-R13-3：大整数 counter（type int 过校验）→ 报告格式化 OverflowError →
        main except 干净捕获 rc=2（钉死活兜底，杀 X_main_exc_del）。"""
        from overnight_town import main
        with tempfile.TemporaryDirectory() as d:
            run_overnight(cfg(nights=1, checkpoint_dir=d))
            p = os.path.join(d, "ckpt.json")
            with open(p, encoding="utf-8") as f:
                s = json.load(f)
            s["counters"]["conversations_llm"] = 10**400
            with open(p, "w", encoding="utf-8") as f:
                json.dump(s, f)
            with self.assertRaises(SystemExit) as cm:
                main(["--seed", str(BASE["seed"]), "--agents", "200", "--nights", "1",
                      "--checkpoint-dir", d, "--resume", "--out", os.path.join(d, "r.json")])
            self.assertEqual(cm.exception.code, 2)

    def test_config_magnitude_caps(self):
        """R13 NEW-R13-4 / R14 NEW-R14-1：agents/nights/corrupt_times 量级上限防无界构造/近无限循环；
        超界用精确 +1 边界（R15 观察项 2），边界值接受。"""
        with self.assertRaises(ValueError):
            cfg(agents=10**6 + 1)
        with self.assertRaises(ValueError):
            cfg(nights=10**5 + 1)
        with self.assertRaises(ValueError):
            cfg(corrupt_times=10**4 + 1)
        cfg(agents=10**6)  # 边界接受（仅构造，不运行）
        cfg(nights=10**5)
        cfg(corrupt_times=10**4)

    def test_resume_backfills_old_counters(self):
        """R5 MINOR-3 回归：跨版本快照（缺 memories_pruned/schema_version）续跑不崩，计数补齐。"""
        with tempfile.TemporaryDirectory() as d:
            run_overnight(cfg(nights=1, checkpoint_dir=d))
            p = os.path.join(d, "ckpt.json")
            with open(p, encoding="utf-8") as f:
                s = json.load(f)
            s["counters"].pop("memories_pruned")  # 模拟 v3.1 快照
            s.pop("schema_version", None)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(s, f)
            r = run_overnight(cfg(nights=2, checkpoint_dir=d, resume=True))
        self.assertEqual(r["status"], "GREEN")
        self.assertEqual(r["counters"]["memories_pruned"], 0)

    def test_load_validates_tampered_memory_checkpoint(self):
        """R5 MINOR-2 回归：load() 单点校验——内存检查点被篡改后，热恢复/回滚路径同样拒绝。"""
        store = CheckpointStore()
        w = World(7, 20)
        llm = MockLLM(Rng(11))
        meta = {"rollbacks": 0, "violations_detected": 0, "unresolved": []}
        store.save(make_snapshot(6, w, llm, Rng(33), new_counters(), meta))
        store.latest["world"].pop("day")
        with self.assertRaises(ValueError):
            store.load()

    def test_memory_ttl_bounded(self):
        """轮5：记忆剪枝（GA 30 天过期移植 [S19]）——非身份记忆年龄 <= ttl，身份永驻。"""
        with tempfile.TemporaryDirectory() as d:
            r = run_overnight(cfg(nights=6, memory_ttl=2, checkpoint_dir=d))
            self.assertEqual(r["status"], "GREEN")
            self.assertGreater(r["counters"]["memories_pruned"], 0)
            with open(os.path.join(d, "ckpt.json"), encoding="utf-8") as f:
                snap = json.load(f)
        day = snap["world"]["day"]
        for res in snap["world"]["residents"]:
            persona = [m for m in res["memories"] if m["kind"] in ("identity", "habit")]
            self.assertEqual(len(persona), 3)  # 人格记忆（身份2+习惯1）永驻
            for m in res["memories"]:
                if m["kind"] not in ("identity", "habit"):
                    self.assertLessEqual(day - m["day"], 2)
        ages = [day - m["day"] for res in snap["world"]["residents"]
                for m in res["memories"] if m["kind"] not in ("identity", "habit")]
        self.assertIn(2, ages)  # age==ttl 边界记忆必须保留（杀 M4 变异，R5 MINOR-6）

    def test_memory_ttl_determinism(self):
        a = run_overnight(cfg(nights=3, memory_ttl=2))
        b = run_overnight(cfg(nights=3, memory_ttl=2))
        self.assertEqual(a["final_hash"], b["final_hash"])
        self.assertEqual(a["status"], "GREEN")

    def test_memory_ttl_off_by_default(self):
        """默认不过期：历史行为不变（剪枝计数 0）。"""
        r = run_overnight(cfg(nights=2))
        self.assertIsNone(r["memory_ttl"])
        self.assertEqual(r["counters"]["memories_pruned"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
