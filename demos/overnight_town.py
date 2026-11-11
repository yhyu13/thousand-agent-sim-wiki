#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
overnight_town.py — 千人小镇「通宵无人值守 AI 模拟」mock 演示
=============================================================
零依赖（Python 3.10+ 标准库）、零网络、零真实 LLM。
架构与军规映射见 ../02-architecture.md 与 ../03-stability.md。

演示的技能（全部有研究先例，见 wiki/sources.md）：
  * 确定性世界层：FNV-1a + mulberry32 派生链，build_day 纯函数（军规2/3，[S16]）
  * 焦点激活 + 认知分层 T0/T1/T2（军规1，[S06][S08]）
  * 记忆流 + 检索 + 重要性触发反思（军规10，[S01]）
  * LLM 网关：预算封顶降级 / 前缀缓存计价 / 退避重试 / 熔断 / schema 校验
    （军规6/7/11，[S02][S13][S14]）
  * 检查点 + 崩溃恢复（含 RNG 状态），终态哈希逐位一致（军规4/5，[S02][S08]）
  * 不变量看门狗 + 自动回滚（军规8，[S15][S16]）
  * 只追加审计（模拟时间戳）+ 早晨报告（军规12，[S15][S08]）

价格口径为真实平台时价（2026-11-11 核验 [S13]）：
  T1 = Haiku 5.5 档 ($0.10/$0.50 per MTok)，T2 = Sonnet 5.5 档 ($2/$10 per MTok)。
  缓存：静态前缀首调用 1.25x 写，后续读 T1 0.1x / T2 0.05x。Batch 全单 x0.5 [S14]。

用法：
  python -I overnight_town.py --seed 20260818 --nights 3 --agents 1000 \
      --budget 2.0 --crash-frac 0.4 --corrupt-frac 0.7 --out out/morning_report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass


def _retry_on_lock(fn, attempts: int = 5):
    """对瞬时 Windows 文件锁（PermissionError/WinError 5，杀软/索引器短暂持有被写文件）
    有界退避重试（R59/R61 硬化，军规 4/5）。仅捕 PermissionError 退避重试，永久失败
    （最后一次）仍抛出；非 PermissionError（如 NaN 的 ValueError、其他 OSError）立即
    传播不重试。无锁时首次即成功。attempts<1 守卫防静默跳过。"""
    if attempts < 1:
        raise ValueError("attempts 须 >= 1（防静默丢检查点，军规 4/5）")
    for i in range(attempts):
        try:
            return fn()
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.05 * (i + 1))


def _atomic_replace(tmp: str, target: str, attempts: int = 5):
    """原子替换 + 瞬时文件锁短重试（R59 硬化，军规 4/5）。
    掉电安全语义不变（调用前已 fsync 落盘）；委托 _retry_on_lock，无锁时行为同 os.replace。"""
    _retry_on_lock(lambda: os.replace(tmp, target), attempts)

# ---------------------------------------------------------------------------
# 确定性随机（对齐 thousand-town 源码约定：FNV-1a hash32 + 派生流隔离 [S16]）
# ---------------------------------------------------------------------------

def fnv1a(text: str) -> int:
    """FNV-1a 32bit，与 source/city-life-ext/resident-plan.js:50 同常量。"""
    h = 0x811C9DC5
    for ch in text:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


class Rng:
    """mulberry32：状态为单个 uint32，可序列化进检查点（军规5）。"""

    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFF

    def next_u32(self) -> int:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ ((t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return (t ^ (t >> 14)) & 0xFFFFFFFF

    def random(self) -> float:
        return self.next_u32() / 4294967296.0

    def randint(self, n: int) -> int:
        return self.next_u32() % n

    def choice(self, seq):
        return seq[self.randint(len(seq))]


# ---------------------------------------------------------------------------
# 世界层常量（对齐 source/city-life-ext/daily-clock.js:13-27 [S16]）
# ---------------------------------------------------------------------------

MINUTES_PER_DAY = 1440
TICK_MINUTES = 10
TICKS_PER_NIGHT = MINUTES_PER_DAY // TICK_MINUTES  # 144
ANCHORS = {"dawn": 300, "wake": 360, "commute": 420, "workStart": 480,
           "lunch": 720, "afternoon": 840, "offWork": 1020,
           "dinner": 1140, "sleep": 1320}
STATES = {"sleep", "morning", "commute", "work", "lunch", "free", "dinner"}
SOCIAL_LOCS = ("park", "plaza", "restaurant")
ROLES = ["farmer", "teacher", "nurse", "engineer", "cook", "driver", "clerk",
         "artist", "doctor", "builder", "merchant", "guard", "baker", "weaver",
         "fisher", "miner", "student", "elder", "child", "vet"]  # 20 职业 x 50 = 1000
NIGHT_SHIFT_ROLES = {"nurse", "guard"}  # 三班制（PRD F-02 [S15]）
FOCUS_SET = {"work", "family", "health", "social", "study", None}
REFLECT_THRESHOLD = 5.0   # 重要性累计阈值（demo 焦点激活口径；原文阈值 150 已核验 [S01][S19]，偏差见 02 页 §6）
MAX_REFLECTIONS = 40      # 每夜反思上限 = 焦点激活（军规1）
MAX_PAIRS_PER_SLOT = 6    # 每社交时段对话上限（军规1）


def _finite(v):
    """math.isfinite 的安全版（R12 NEW-1）：超 float 范围的有限大整数（如 10**400）
    会使 math.isfinite 抛 OverflowError——此处捕获并视为非法（返回 False），
    使校验/看门狗/Config 按契约走干净 ValueError/违例路径，而非裸 traceback。
    正常有限数返回 True，NaN/inf 返回 False（与 math.isfinite 一致）。"""
    try:
        return math.isfinite(v)
    except OverflowError:
        return False


def seg(start, end, state, location):
    return {"start": start, "end": end, "state": state, "location": location}


def build_day(seed: int, rid: str, day: int, role: str, home: str, work: str):
    """纯函数：只依赖 (seed, id, day) + 静态档案。名册增删不影响他人（军规3）。

    复刻 resident-plan.js 的 dayRng(seed:id:day) 局部抖动 [S16]。
    """
    r = Rng(fnv1a(f"{seed}:{rid}:{day}"))
    free_loc = "park" if r.random() < 0.5 else "plaza"
    dinner_loc = "restaurant" if r.random() < 0.4 else home
    shift = 0
    if role in NIGHT_SHIFT_ROLES:
        # 防御解析（R11 MAJOR-1）：try-int 独立于校验层的 ASCII 谓词——
        # 无 dash→IndexError、非 int 后缀（含 ²/① 等 isdigit 但 int() 抛的 Unicode）→ValueError，均落默认班。
        parts = rid.rsplit("-", 1)
        try:
            shift = (int(parts[1]) - 1) % 3
        except (ValueError, IndexError):
            shift = 0
    if shift == 1:  # 中班 16-24
        return [seg(0, 360, "sleep", home), seg(360, 480, "morning", home),
                seg(480, 960, "free", free_loc), seg(960, 1020, "commute", "street"),
                seg(1020, 1140, "work", work), seg(1140, 1200, "dinner", dinner_loc),
                seg(1200, 1440, "work", work)]
    if shift == 2:  # 夜班 0-8
        return [seg(0, 480, "work", work), seg(480, 540, "commute", "street"),
                seg(540, 600, "morning", home), seg(600, 1020, "sleep", home),
                seg(1020, 1140, "free", free_loc), seg(1140, 1320, "dinner", dinner_loc),
                seg(1320, 1440, "work", work)]
    return [seg(0, 360, "sleep", home), seg(360, 420, "morning", home),
            seg(420, 480, "commute", "street"), seg(480, 720, "work", work),
            seg(720, 840, "lunch", "plaza"), seg(840, 1020, "work", work),
            seg(1020, 1140, "free", free_loc), seg(1140, 1320, "dinner", dinner_loc),
            seg(1320, 1440, "sleep", home)]


class World:
    """全量可序列化的世界状态（军规4：无状态执行体 + 外部化状态 [S08]）。"""

    def __init__(self, seed: int, n: int):
        self.seed = seed
        self.n = n
        self.day = 0
        self.abs_minute = 0
        self.residents = []
        self.plans = {}
        self.events = []   # 世界事件（对话），JSONL 可导出（军规12；反思计入报告 reflections_total，不入 events）
        self.audit = []    # 只追加审计：补丁/拒绝/回滚/熔断/降级（军规12 [S15]）
        for i in range(n):
            role = ROLES[i % len(ROLES)]
            rid = f"{role}-{i // len(ROLES) + 1:03d}"  # 命名空间 ID（军规3 [S16]）
            home = f"home:{fnv1a(f'{seed}:home:{rid}') % 24}"   # 24 地块 [S16]
            work = f"work:{fnv1a(f'{seed}:work:{rid}') % 24}"
            r = Rng(fnv1a(f"{seed}:init:{rid}"))
            memories = [
                {"day": 0, "minute": 0, "text": f"我是{rid}，职业是{role}",
                 "importance": 4.0, "kind": "identity", "keywords": [role, "identity"]},
                {"day": 0, "minute": 0, "text": f"我住在{home}，在{work}工作",
                 "importance": 3.0, "kind": "identity", "keywords": [home, work]},
                {"day": 0, "minute": 0, "text": "我习惯晚饭后散步",
                 "importance": 3.0, "kind": "habit", "keywords": ["散步", "dinner"]},
            ]
            self.residents.append({"id": rid, "role": role, "home": home, "work": work,
                                   "memories": memories, "focus": None,
                                   "imp_sum": 0.0, "last_ref_day": -1})
        self.rebuild_plans()

    def rebuild_plans(self):
        for r in self.residents:
            self.plans[r["id"]] = build_day(self.seed, r["id"], self.day,
                                            r["role"], r["home"], r["work"])

    def resident(self, rid):
        for r in self.residents:
            if r["id"] == rid:
                return r
        return None

    def location_at(self, r, minute):
        for s in self.plans[r["id"]]:
            if s["start"] <= minute < s["end"]:
                return s["location"]
        return r["home"]

    def to_dict(self):
        return {"seed": self.seed, "n": self.n, "day": self.day,
                "abs_minute": self.abs_minute, "residents": self.residents,
                "plans": self.plans, "events": self.events, "audit": self.audit}

    @classmethod
    def from_dict(cls, d):
        w = cls.__new__(cls)
        w.seed, w.n, w.day = d["seed"], d["n"], d["day"]
        w.abs_minute = d["abs_minute"]
        w.residents, w.plans = d["residents"], d["plans"]
        w.events, w.audit = d["events"], d["audit"]
        return w


# ---------------------------------------------------------------------------
# 记忆检索（Generative Agents 三因子打分的简化版 [S01][S19]；与原文/代码差异见 02 页 §6 偏差清单）
# ---------------------------------------------------------------------------

def retrieve(memories, query_kw, abs_minute, k=3):
    q = set(query_kw)
    scored = []
    for m in memories:
        hours = max(0, abs_minute - (m["day"] * 1440 + m["minute"])) / 60.0
        recency = 0.995 ** hours
        imp = m["importance"] / 10.0
        kw = set(x for x in m["keywords"] if isinstance(x, str))  # 运行时防御：非 str 元素不入 set（R10 MINOR-1）
        rel = len(q & kw) / len(q | kw) if (q | kw) else 0.0
        scored.append((recency + imp + rel, m))
    scored.sort(key=lambda x: (-x[0], x[1]["text"]))
    return [m for _, m in scored[:k]]


# ---------------------------------------------------------------------------
# MockLLM：确定性假模型 + 真实价格口径（[S13][S14]）+ 可注入失败
# ---------------------------------------------------------------------------

T1_TEMPLATES = [
    "「{topic}的事，我觉得挺好。」", "「说起{topic}，我昨天也遇到了。」",
    "「{topic}吗？下班再聊！」", "「我对{topic}有点新想法。」",
    "「{topic}这事，得问问家里人。」", "「哈哈，{topic}总是这样。」",
    "「{topic}……让我想想。」", "「关于{topic}，我同意一半。」",
]
T2_INSIGHTS = [
    "最近社交让我更重视邻里关系", "规律作息比什么都重要",
    "工作和家庭需要更好的平衡", "我应该多学点新东西",
    "帮助他人让日子更有意义",
]


def estimate_tokens(text: str) -> int:
    """mock token 估算：CJK 字符约 1 token/字，其余约 4 字符/token。
    旧版 len//3 对中文低估 2–3 倍（wiki critic MAJOR-6）；仍是估算，真实系统须用真 tokenizer。"""
    n = 0.0
    for ch in text:
        n += 1.0 if ord(ch) >= 0x2E80 else 0.25
    return max(1, int(n))


class MockLLM:
    PRICES = {"T1": (0.10, 0.50), "T2": (2.0, 10.0)}      # $/MTok [S13]
    PREFIX = {"T1": 600, "T2": 900}                       # 静态前缀 >=512 [S13]
    READ_MULT = {"T1": 0.1, "T2": 0.05}                   # 缓存读倍率 [S13]
    OUT_BASE = {"T1": 60, "T2": 200}

    def __init__(self, rng: Rng, batch=False, p_rate=0.02, p_bad=0.02, p_invalid=0.03):
        self.rng = rng
        self.batch = batch
        self.p_rate, self.p_bad, self.p_invalid = p_rate, p_bad, p_invalid
        self.calls = 0
        self.cost = 0.0
        self.tokens = {"T1": [0, 0], "T2": [0, 0]}
        self.prefix_written = {"T1": False, "T2": False}
        self.consec_fail = 0
        self.breaker_until = -1
        self.backoff_until = -1
        self.breaker_half_open = False

    def call(self, tier: str, prompt: str):
        """返回 (status, payload)。rate_limit 不计费；malformed 计费（token 已生成）。"""
        self.calls += 1
        if self.rng.random() < self.p_rate:
            return ("rate_limit", None)
        var_in = estimate_tokens(prompt)
        out = self.OUT_BASE[tier] + self.rng.randint(40)
        prefix = self.PREFIX[tier]
        if not self.prefix_written[tier]:
            in_cost = prefix * 1.25 + var_in
            self.prefix_written[tier] = True
        else:
            in_cost = prefix * self.READ_MULT[tier] + var_in
        pin, pout = self.PRICES[tier]
        c = (in_cost * pin + out * pout) / 1e6
        if self.batch:
            c *= 0.5
        self.cost += c
        self.tokens[tier][0] += prefix + var_in
        self.tokens[tier][1] += out
        if self.rng.random() < self.p_bad:
            return ("malformed", "这不是JSON{{")
        h = fnv1a(prompt + str(self.calls))
        if tier == "T1":
            topic = prompt.split("|")[-1][:12] or "日常"
            return ("ok", T1_TEMPLATES[h % len(T1_TEMPLATES)].format(topic=topic))
        focus = sorted(FOCUS_SET - {None})[h % 5]
        if self.rng.random() < self.p_invalid:
            focus = "征服世界"  # 越界值：校验层必须拒绝（军规7）
        payload = json.dumps({"insight": T2_INSIGHTS[h % len(T2_INSIGHTS)],
                              "tomorrow_focus": focus}, ensure_ascii=False)
        return ("ok", payload)

    def to_dict(self):
        return {"rng": self.rng.state, "batch": self.batch, "p_rate": self.p_rate,
                "p_bad": self.p_bad, "p_invalid": self.p_invalid, "calls": self.calls,
                "cost": self.cost, "tokens": self.tokens,
                "prefix_written": self.prefix_written,
                "consec_fail": self.consec_fail, "breaker_until": self.breaker_until,
                "backoff_until": self.backoff_until,
                "breaker_half_open": self.breaker_half_open}

    @classmethod
    def from_dict(cls, d):
        m = cls(Rng(d["rng"]), d["batch"], d["p_rate"], d["p_bad"], d["p_invalid"])
        m.calls, m.cost, m.tokens = d["calls"], d["cost"], d["tokens"]
        m.prefix_written = d["prefix_written"]
        m.consec_fail, m.breaker_until = d["consec_fail"], d["breaker_until"]
        m.backoff_until = d.get("backoff_until", -1)
        m.breaker_half_open = d.get("breaker_half_open", False)
        return m


# ---------------------------------------------------------------------------
# LLM 网关：预算 governor + 熔断 + 重试（军规6/11 [S02][S14]）
# ---------------------------------------------------------------------------

WORST_EST = {"T1": 0.001, "T2": 0.01}  # 前置最坏估价（军规11：不能事后追认）


def gateway(llm: MockLLM, tier: str, prompt: str, tick: int, cap: float,
            counters: dict, audit: list, day: int, minute: int):
    # 1) 熔断/退避检查在前：熔断期不记录根本没执行的预算降级（审计保真）
    if tick < llm.breaker_until:
        counters["breaker_skips"] += 1
        return ("breaker", None, tier)
    if tick < llm.backoff_until:
        counters["backoff_skips"] += 1
        return ("backoff", None, tier)
    # 2) 预算 governor：前置最坏估价（军规11）
    est = WORST_EST[tier]
    if llm.cost + est > cap:
        if tier == "T2":
            tier = "T1"
            est = WORST_EST["T1"]
            counters["budget_degradations"] += 1
            audit.append({"day": day, "minute": minute, "type": "budget_downgrade",
                          "detail": "T2->T1"})
        if llm.cost + est > cap:
            counters["budget_refusals"] += 1
            return ("budget", None, tier)
    # 3) 半开探测：熔断到期后的第一次调用是探针
    probing = llm.breaker_half_open
    status, payload = "rate_limit", None
    for _ in range(3):  # 调用内立即重试 x3（不 sleep）；调用间退避见下
        status, payload = llm.call(tier, prompt)
        if status != "rate_limit":
            break
        counters["rate_limit_hits"] += 1
        llm.consec_fail += 1
        if llm.consec_fail >= 5:
            llm.breaker_until = tick + 12
            llm.breaker_half_open = True
            llm.consec_fail = 0
            counters["breaker_opens"] += 1
            audit.append({"day": day, "minute": minute, "type": "breaker_open",
                          "detail": "连续5次失败，熔断12tick，世界走规则层"})
            break
    if status == "rate_limit":
        # 调用间指数退避：2^n tick（封顶8），退避期世界走规则层不停摆
        llm.backoff_until = tick + min(2 ** max(1, llm.consec_fail), 8)
        if probing:
            llm.breaker_until = tick + 12
            counters["breaker_opens"] += 1
            audit.append({"day": day, "minute": minute, "type": "breaker_reopen",
                          "detail": "半开探针失败，重新熔断12tick"})
        return ("rate_limit", None, tier)
    llm.consec_fail = 0
    if probing:
        llm.breaker_half_open = False
        counters["breaker_closes"] += 1
        audit.append({"day": day, "minute": minute, "type": "breaker_close",
                      "detail": "半开探针成功，熔断关闭"})
    if status == "malformed":
        counters["malformed_hits"] += 1
    return (status, payload, tier)


def validate_patch(resident_ids, patch: dict):
    """对象级补丁校验：ID 白名单 + 值域（军规7 [S15] §7.5 / [S10] GM）。"""
    if not isinstance(patch, dict):
        return False, "patch 不是对象"
    if patch.get("target") not in resident_ids:
        return False, "target 不在花名册白名单"
    if patch.get("tomorrow_focus") not in FOCUS_SET:
        return False, "tomorrow_focus 越界"
    return True, ""


# ---------------------------------------------------------------------------
# 监督者：不变量看门狗（军规8 [S15][S16]）
# ---------------------------------------------------------------------------

def sample_indices(tick: int, n: int, k: int = 40):
    """看门狗抽样索引。步长与 n 互质，避免 101|n 时抽样退化为单点（v2 MINOR）。
    n<=k 时全员检查。确定性：只依赖 (tick, n)。"""
    if n <= k:
        return list(range(n))
    step = 101
    while math.gcd(step, n) != 1:
        step += 1
    return [(tick * 37 + j * step) % n for j in range(k)]


class Supervisor:
    def __init__(self, expected_n: int, cap: float):
        self.expected_n = expected_n
        self.cap = cap

    def check_plan(self, plan):
        if not plan or plan[0]["start"] != 0 or plan[-1]["end"] != 1440:
            return False
        prev_end = 0
        for s in plan:
            if s["start"] != prev_end or s["end"] <= s["start"]:
                return False
            if s["state"] not in STATES:
                return False
            prev_end = s["end"]
        return True

    def check(self, world: World, llm: MockLLM, tick: int, full=False):
        v = []
        ids = [r["id"] for r in world.residents]
        if len(ids) != self.expected_n:
            v.append("I1:人口不守恒")
        if len(set(ids)) != len(ids):
            v.append("I1:ID重复")
        if not ids:
            return v  # 空人口：I1 已记录（若期望>0），抽样无意义
        sample = range(len(ids)) if full else sample_indices(tick, len(ids))
        for i in sample:
            r = world.residents[i]
            if not self.check_plan(world.plans.get(r["id"])):
                v.append(f"I2:计划非法:{r['id']}")
                break
        for i in sample:
            for m in world.residents[i]["memories"][-3:]:
                imp = m["importance"]
                if not _finite(imp) or not (0.0 <= imp <= 10.0):
                    v.append("I4:记忆重要性越界")
                    break
        if not _finite(llm.cost) or llm.cost > self.cap + 1e-9:
            v.append("I3:成本超封顶")
        # tick 语义 = 下一个待执行 tick；世界时钟停在 (tick-1)*10；tick0 未执行任何 tick
        expected_min = (tick - 1) * TICK_MINUTES if tick > 0 else 0
        if world.abs_minute != expected_min:
            v.append("I5:时钟不一致")
        return v


class CheckpointStore:
    """检查点：内存必选，磁盘可选（军规5 [S02]）。"""

    def __init__(self, directory=None):
        self.directory = directory
        self.latest = None
        if directory:
            os.makedirs(directory, exist_ok=True)

    def save(self, snap: dict):
        self.latest = json.loads(json.dumps(snap, ensure_ascii=False))  # 深拷贝
        if self.directory:
            tmp = os.path.join(self.directory, "ckpt.tmp.json")

            def _write_tmp():
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(snap, f, ensure_ascii=False, allow_nan=False)
                    f.flush()
                    os.fsync(f.fileno())  # 掉电安全：先落盘再原子替换
            _retry_on_lock(_write_tmp)  # R61：tmp 写段瞬时锁重试（与 replace 对称，军规 4/5）
            _atomic_replace(tmp, os.path.join(self.directory, "ckpt.json"))

    def load(self):
        # 单点语义校验：冷重启/热恢复/回滚三条路径共用（R5 MINOR-2）
        snap = None
        if self.directory:
            p = os.path.join(self.directory, "ckpt.json")
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f:
                        snap = json.load(f)
                except (OSError, ValueError, RecursionError) as e:
                    # JSONDecodeError/UnicodeDecodeError ⊂ ValueError；目录/权限 ⊂ OSError（R6 NEW-2）；
                    # 深嵌套合法 JSON 触发 RecursionError ⊂ RuntimeError（R13 NEW-R13-1），统一转干净 ValueError
                    raise ValueError(f"检查点文件读取失败（{p}）：{e}") from e
        else:
            snap = self.latest
        if snap is None:
            return None
        _validate_snapshot(snap)
        # 深拷贝：恢复出的执行体与检查点零共享（修复别名污染 BLOCKER，
        # 否则崩溃恢复后的原地修改会连检查点一起改脏，回滚永远加载脏快照）
        try:
            return json.loads(json.dumps(snap, ensure_ascii=False))
        except RecursionError as e:  # 冗余兜底：CPython 3.13 下解析捕获恒先触发，此 catch 不可达（R14 NEW-R14-3）
            raise ValueError(f"检查点深拷贝失败（嵌套过深）：{e}") from e


class SimCrash(Exception):
    """注入的进程崩溃。"""


def canonical_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 认知层：T0 规则（implicit）/ T1 社交对话 / T2 反思与计划补丁
# ---------------------------------------------------------------------------

def social_slot(minute: int) -> bool:
    return (720 <= minute < 840 or 1020 <= minute < 1320) and minute % 30 == 0


def do_conversations(w, llm, event_rng, tick, cap, counters):
    minute = w.abs_minute % 1440
    day = w.day
    groups = {}
    for r in w.residents:
        loc = w.location_at(r, minute)
        if loc in SOCIAL_LOCS:
            groups.setdefault(loc, []).append(r)
    budget = MAX_PAIRS_PER_SLOT
    for loc in sorted(groups):
        group = groups[loc]
        while budget > 0 and len(group) >= 2:
            i1 = event_rng.randint(len(group))
            i2 = event_rng.randint(len(group) - 1)
            if i2 >= i1:
                i2 += 1
            a, b = group[i1], group[i2]
            budget -= 1
            mems = retrieve(a["memories"], [loc, b["role"]], w.abs_minute, k=1)
            topic = mems[0]["keywords"][0] if mems and mems[0]["keywords"] else "日常"
            prompt = f"T1|{a['id']}|{b['id']}|{loc}|{topic}"
            status, payload, _tier = gateway(llm, "T1", prompt, tick, cap,
                                             counters, w.audit, day, minute)
            if status == "ok":
                text = f"{a['id']} 对 {b['id']} 说：{payload}"
                imp = round(2 + event_rng.random() * 6, 2)
                counters["conversations_llm"] += 1
                mode = "llm"
            else:
                text = f"（规则兜底）{a['id']} 和 {b['id']} 在{loc}聊了聊日常"
                imp = 2.0
                counters["conversations_degraded"] += 1
                mode = "rule"
            for r, other in ((a, b), (b, a)):
                r["memories"].append({"day": day, "minute": minute, "text": text,
                                      "importance": imp, "kind": "conversation",
                                      "keywords": [loc, other["role"], topic]})
                r["imp_sum"] += imp
            w.events.append({"type": "conversation", "day": day, "minute": minute,
                             "a": a["id"], "b": b["id"], "loc": loc,
                             "mode": mode, "text": text})


def do_reflections(w, llm, event_rng, tick, cap, counters):
    minute = w.abs_minute % 1440
    day = w.day
    cands = [r for r in w.residents
             if r["imp_sum"] >= REFLECT_THRESHOLD and r["last_ref_day"] != day]
    cands.sort(key=lambda r: (-r["imp_sum"], r["id"]))
    ids = {r["id"] for r in w.residents}
    for r in cands[:MAX_REFLECTIONS]:
        mems = retrieve(r["memories"], [r["role"], "dinner"], w.abs_minute, k=3)
        prompt = f"T2|{r['id']}|imp={r['imp_sum']:.1f}|" + ";".join(m["text"] for m in mems)
        status, payload, _tier = gateway(llm, "T2", prompt, tick, cap,
                                         counters, w.audit, day, minute)
        outcome = "degraded"
        if status == "ok":
            try:
                obj = json.loads(payload)
            except (ValueError, TypeError):
                obj = None
            if isinstance(obj, dict):
                patch = {"target": r["id"], "tomorrow_focus": obj.get("tomorrow_focus")}
                ok, reason = validate_patch(ids, patch)
                if ok:
                    r["focus"] = obj.get("tomorrow_focus")
                    r["memories"].append({"day": day, "minute": minute,
                                          "text": f"反思：{obj.get('insight', '')}",
                                          "importance": 8.0, "kind": "reflection",
                                          "keywords": [r["role"], "reflection"]})
                    w.audit.append({"day": day, "minute": minute, "type": "plan_patch",
                                    "target": r["id"], "scope": "behavior",
                                    "patch": {"tomorrow_focus": r["focus"]}})
                    outcome = "accepted"
                else:
                    w.audit.append({"day": day, "minute": minute, "type": "patch_rejected",
                                    "target": r["id"], "reason": reason,
                                    "raw": str(obj.get("tomorrow_focus"))})
                    outcome = "rejected"
        if outcome == "degraded":
            r["memories"].append({"day": day, "minute": minute,
                                  "text": "（规则反思）今天过得平稳，明天继续",
                                  "importance": 5.0, "kind": "reflection",
                                  "keywords": [r["role"], "reflection"]})
        counters["reflections_" + outcome] += 1
        r["imp_sum"] = 0.0
        r["last_ref_day"] = day


def step_tick(w, llm, event_rng, tick, cap, counters, cfg):
    minute = (tick * TICK_MINUTES) % 1440
    day = tick // TICKS_PER_NIGHT
    if minute == 0:
        w.day = day
        w.rebuild_plans()  # T0：纯函数重建当日计划，零 LLM（军规1/2）
        if cfg.memory_ttl is not None and day > 0:
            # 记忆剪枝（opt-in）：过期对话/反思清除，身份记忆永驻
            # 移植 GA 官方代码反思记忆 30 天过期机制 [S19]；军规10 存储侧剪枝
            pruned = 0
            for r in w.residents:
                keep = [m for m in r["memories"]
                        if m["kind"] in ("identity", "habit") or (day - m["day"]) <= cfg.memory_ttl]
                pruned += len(r["memories"]) - len(keep)
                r["memories"] = keep
            counters["memories_pruned"] += pruned
    w.abs_minute = tick * TICK_MINUTES
    total = cfg.nights * TICKS_PER_NIGHT
    if cfg.storm:
        llm.p_rate = 0.8 if int(0.30 * total) <= tick < int(0.34 * total) else cfg.p_rate
        llm.p_bad = 0.6 if int(0.55 * total) <= tick < int(0.58 * total) else cfg.p_bad
    else:
        llm.p_rate, llm.p_bad = cfg.p_rate, cfg.p_bad
    if social_slot(minute):
        do_conversations(w, llm, event_rng, tick, cap, counters)
    if minute == ANCHORS["sleep"]:
        do_reflections(w, llm, event_rng, tick, cap, counters)


# ---------------------------------------------------------------------------
# 运行器：检查点 / 崩溃恢复 / 回滚 / 早晨报告
# ---------------------------------------------------------------------------

@dataclass
class Config:
    seed: int = 20260818
    nights: int = 3
    agents: int = 1000
    budget: float = 2.0
    crash_frac: float | None = 0.4     # 进程崩溃注入点（进度比例）
    corrupt_frac: float | None = None  # 名册污染注入点（军规8演练）
    corrupt_times: int = 1             # 污染注入次数（间隔0.05进度；>=4 可演练体面停机）
    corrupt_plan_frac: float | None = None  # 计划/记忆违例注入点（I2/I4 实弹演练）
    storm: bool = True                 # 限流/坏JSON风暴窗口
    p_rate: float = 0.02
    p_bad: float = 0.02
    p_invalid: float = 0.03            # T2 输出越界 focus 的概率（军规7演练）
    batch: bool = False                # Batch API 5折模式 [S14]
    checkpoint_dir: str | None = None
    resume: bool = False               # 冷重启：从 checkpoint_dir/ckpt.json 续跑
    memory_ttl: int | None = None      # 记忆过期天数（opt-in，移植 GA 30 天过期 [S19]）；None=不过期（默认，历史行为）
    events_out: str | None = None      # 事件流导出（JSONL：events + audit），供 visualize.html 时间轴

    def __post_init__(self):
        if type(self.seed) is not int:
            raise ValueError("seed 必须是整数（bool/float/str 拒绝）")
        for name in ("nights", "agents", "corrupt_times"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} 必须是整数（bool/float 拒绝）")
        if isinstance(self.budget, bool) or not isinstance(self.budget, (int, float)):
            raise ValueError("budget 必须是数（bool 拒绝）")
        if self.nights < 0 or self.agents < 0 or self.budget < 0:
            raise ValueError("nights/agents/budget 必须非负")
        if self.agents > 10**6 or self.nights > 10**5 or self.corrupt_times > 10**4:
            raise ValueError("agents 须 <= 10^6、nights 须 <= 10^5、corrupt_times 须 <= 10^4"
                             "（量级上限，防无界构造/近无限循环，R13 NEW-R13-4 / R14 NEW-R14-1）")
        if not _finite(self.budget):
            raise ValueError("budget 必须是有限数（NaN/Inf 拒绝）")
        if self.corrupt_times < 1:
            raise ValueError("corrupt_times 必须 >= 1")
        if self.memory_ttl is not None and (type(self.memory_ttl) is not int or self.memory_ttl < 1):
            raise ValueError("memory_ttl 必须是 >= 1 的整数（天；bool/float/NaN 拒绝）")
        for name in ("batch", "storm", "resume"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} 必须是 bool（R9 NEW-2）")
        for name in ("crash_frac", "corrupt_frac", "corrupt_plan_frac"):
            v = getattr(self, name)
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))
                                  or not (0.0 <= v < 1.0)):
                raise ValueError(f"{name} 必须在 [0,1) 区间（bool/str 拒绝）")
        for name in ("p_rate", "p_bad", "p_invalid"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0.0 <= v <= 1.0):
                raise ValueError(f"{name} 必须在 [0,1] 区间（bool/str 拒绝）")


def new_counters():
    return {"conversations_llm": 0, "conversations_degraded": 0,
            "reflections_accepted": 0, "reflections_rejected": 0,
            "reflections_degraded": 0, "rate_limit_hits": 0, "malformed_hits": 0,
            "breaker_opens": 0, "breaker_skips": 0, "breaker_closes": 0,
            "backoff_skips": 0, "budget_degradations": 0, "budget_refusals": 0,
            "memories_pruned": 0}


def make_snapshot(tick, w, llm, rng_event, counters, meta):
    return {"schema_version": 2, "tick": tick, "world": w.to_dict(),
            "rng": {"llm": llm.rng.state, "event": rng_event.state},
            "llm": llm.to_dict(), "counters": counters, "meta": meta}


def _run(cfg, store, injections, resume, meta):
    resumed_from = resume["tick"] if resume is not None else 0
    if resume is not None:
        w = World.from_dict(resume["world"])
        llm = MockLLM.from_dict(resume["llm"])
        rng_event = Rng(resume["rng"]["event"])
        counters = resume["counters"]
        for k, v in new_counters().items():
            counters.setdefault(k, v)  # 跨版本检查点缺失计数键补齐（R5 MINOR-3）
        tick = resume["tick"]
        meta.update(resume.get("meta") or {})  # 干预计数入检查点，崩溃安全
    else:
        w = World(cfg.seed, cfg.agents)
        rng_event = Rng(fnv1a(f"{cfg.seed}:events"))
        llm = MockLLM(Rng(fnv1a(f"{cfg.seed}:llm")), batch=cfg.batch,
                      p_rate=cfg.p_rate, p_bad=cfg.p_bad, p_invalid=cfg.p_invalid)
        counters = new_counters()
        tick = 0
        store.save(make_snapshot(tick, w, llm, rng_event, counters, meta))
    sup = Supervisor(cfg.agents, cfg.budget)
    total = cfg.nights * TICKS_PER_NIGHT
    crash_tick = int(cfg.crash_frac * total) if cfg.crash_frac is not None else -1
    corrupt_ticks = set()
    if cfg.corrupt_frac is not None:
        for k in range(max(1, cfg.corrupt_times)):
            t = int((cfg.corrupt_frac + 0.05 * k) * total)
            if t < total:
                corrupt_ticks.add(t)
    plan_tick = int(cfg.corrupt_plan_frac * total) if cfg.corrupt_plan_frac is not None else -1

    while tick < total:
        if injections["crash_left"] > 0 and tick == crash_tick:
            # 真实崩溃：不存新检查点，回退到最近周期检查点并重放（最多丢 6 tick）
            raise SimCrash()
        if tick in corrupt_ticks and tick not in injections["corrupt_fired"]:
            if w.residents:
                w.residents.pop()  # 注入非法写入：模拟绕过校验的坏补丁（军规8演练）
            injections["corrupt_fired"].add(tick)  # 已触发集合在快照外：回滚重放不重复触发
        step_tick(w, llm, rng_event, tick, cfg.budget, counters, cfg)
        injected = False
        if injections["corrupt_plan_left"] > 0 and tick == plan_tick and w.residents:
            # 计划/记忆违例注入：必须在 step_tick 之后（日界 rebuild_plans 会重建计划），
            # 选下一次检查必被抽样的居民（I2/I4 实弹演练）
            victim = sample_indices(tick + 1, len(w.residents))[0]
            r = w.residents[victim]
            w.plans[r["id"]][0]["end"] = 1500
            r["memories"][-1]["importance"] = 99.0
            injections["corrupt_plan_left"] -= 1
            injected = True
        tick += 1
        # 先体检后存档：检查点只存看门狗验证过的干净状态
        # （v2 BLOCKER 教训：存档先于检查时，1/6 相位的污染会被 baked-in 进检查点，
        #  回滚永远加载脏快照；回归测试 test_roster_corrupt_checkpoint_phase）
        violations = sup.check(w, llm, tick, full=(tick % TICKS_PER_NIGHT == 0))
        if violations:
            meta["violations_detected"] += len(violations)
            snap = store.load()
            if snap is None or meta["rollbacks"] >= 3:
                meta["unresolved"] = violations  # 体面停机，不带病运行（军规8）
                break
            w = World.from_dict(snap["world"])
            llm = MockLLM.from_dict(snap["llm"])
            rng_event = Rng(snap["rng"]["event"])
            counters = snap["counters"]
            tick = snap["tick"]
            meta["rollbacks"] += 1  # meta 随快照恢复但不随回滚重置：干预计数单调累计
            w.audit.append({"day": tick // TICKS_PER_NIGHT,
                            "minute": (tick * TICK_MINUTES) % 1440,
                            "type": "rollback",
                            "detail": f"检出{len(violations)}项违例，回滚至tick{tick}"})
            # 回滚后立即存档：干预审计与 meta 计数即时持久化，
            # 关闭「回滚后→下次存档前崩溃」的干预痕迹丢失窗口（v2 MAJOR）
            store.save(make_snapshot(tick, w, llm, rng_event, counters, meta))
        elif (tick % 6 == 0 or tick == total) and not injected:
            # 每模拟小时存检查点（军规5）；刚注入违例的 tick 双保险跳过存档
            store.save(make_snapshot(tick, w, llm, rng_event, counters, meta))

    unresolved = sup.check(w, llm, tick, full=True) if tick == total else meta["unresolved"]
    snap = make_snapshot(tick, w, llm, rng_event, counters, meta)
    conv = counters["conversations_llm"] + counters["conversations_degraded"]
    refl = (counters["reflections_accepted"] + counters["reflections_rejected"]
            + counters["reflections_degraded"])
    events_total = conv + refl
    llm_events = counters["conversations_llm"] + counters["reflections_accepted"]
    green = (tick == total and not unresolved and llm.cost <= cfg.budget + 1e-9
             and events_total > 0 and meta["rollbacks"] <= 3)
    audit_summary = {}
    for a in w.audit:
        t = a.get("type")
        t = t if isinstance(t, str) else "unknown"  # 运行时防御（R10 MINOR-2）
        audit_summary[t] = audit_summary.get(t, 0) + 1
    agent_ticks = cfg.agents * tick
    if cfg.events_out:
        # 事件流导出（JSONL）：世界事件 + 审计（_stream 标记），供 visualize.html 时间轴
        def _write_events():
            with open(cfg.events_out, "w", encoding="utf-8") as f:
                for e in w.events:
                    f.write(json.dumps(e, ensure_ascii=False, allow_nan=False) + "\n")
                for a in w.audit:
                    f.write(json.dumps(dict(a, _stream="audit"), ensure_ascii=False, allow_nan=False) + "\n")
        _retry_on_lock(_write_events)  # R61：终点导出瞬时锁重试（模拟已完成、世界已落盘）
    # 世界本体哈希：居民/计划/事件（跨干预不变量）；全量哈希另含审计与计费状态
    world_core = {"day": w.day, "abs_minute": w.abs_minute,
                  "residents": w.residents, "plans": w.plans, "events": w.events}
    return {
        "status": "GREEN" if green else "RED",
        "seed": cfg.seed, "nights_planned": cfg.nights, "agents": cfg.agents,
        "ticks_completed": tick, "ticks_planned": total,
        "resumed_from_tick": resumed_from,  # 本进程最后一次检查点续跑点（冷重启起点或内部崩溃恢复点）；
        # >0 证明发生过续跑，但不区分冷/热；派生自 resume 快照而非执行计数（R4 MINOR-4 语义声明）
        "sim_days": round(tick / TICKS_PER_NIGHT, 2),
        "population_final": len(w.residents),
        "counters": counters,
        "conversations_total": conv, "reflections_total": refl,
        "llm_calls": llm.calls,  # 总尝试次数（含限流/坏输出失败），非成功数
        "llm_coverage_pct": round(100.0 * llm.calls / agent_ticks, 4) if agent_ticks else 0,
        "tokens": llm.tokens, "cost_usd": round(llm.cost, 6),
        "memory_ttl": cfg.memory_ttl, "memories_pruned": counters["memories_pruned"],
        "budget_cap_usd": cfg.budget,
        "budget_used_pct": round(100.0 * llm.cost / cfg.budget, 2) if cfg.budget else 0,
        "cost_per_event_usd": round(llm.cost / events_total, 6) if events_total else None,
        "cost_per_llm_event_usd": round(llm.cost / llm_events, 6) if llm_events else None,
        "interventions_rollbacks": meta["rollbacks"],
        "violations_detected": meta["violations_detected"],
        "violations_unresolved": unresolved,
        "audit_summary": audit_summary, "audit_entries": len(w.audit),
        "sample_events": w.events[:2] + [e for e in w.events[-2:] if e not in w.events[:2]],
        "world_hash": canonical_hash(world_core),
        "final_hash": canonical_hash(snap),
    }


def _validate_snapshot(snap):
    """检查点 schema 校验（R10 修订、R11 收紧：覆盖**已知运行时消费字段**，枚举见下；
    与消费点运行时防御（retrieve/audit_summary/build_day）构成纵深——两层用**不同机制**
    （校验：ASCII 数字谓词+前缀一致；build_day：try-int），避免共享 flawed 谓词使纵深失效。
    冷重启/热恢复/回滚三路径共用单点（CheckpointStore.load）。
    数值字段（cost/p_*/tokens 对/imp_sum/importance）须有限（拒 NaN/inf，R11 MINOR-1；
    并经 _finite 安全版拒超 float 范围的有限大整数如 10**400，避免 math.isfinite 抛 OverflowError，R12 NEW-1）；
    看门狗 I3/I4 亦显式查 _finite，存档 allow_nan=False 为最终闸门。
    不声称穷尽任意篡改——未知形态由看门狗不变量与体面停机兜底。
    已知消费字段缺键/错类型/非有限 → 干净 ValueError。"""
    if not isinstance(snap, dict):
        raise ValueError("检查点格式错误：顶层不是对象")
    for key in ("tick", "world", "rng", "llm", "counters", "meta"):
        if key not in snap:
            raise ValueError(f"检查点缺少必需字段：{key}")
    if type(snap["tick"]) is not int or snap["tick"] < 0:
        raise ValueError("检查点 tick 必须是非负整数（bool 拒绝）")
    if "schema_version" in snap and type(snap["schema_version"]) is not int:
        raise ValueError("检查点 schema_version 类型错误")
    w = snap["world"]
    if not isinstance(w, dict):
        raise ValueError("检查点 world 必须是对象")
    for key in ("seed", "n", "day", "abs_minute", "residents", "plans", "events", "audit"):
        if key not in w:
            raise ValueError(f"检查点 world 缺少必需字段：{key}")
    if not (isinstance(w["residents"], list) and isinstance(w["plans"], dict)
            and isinstance(w["events"], list) and isinstance(w["audit"], list)):
        raise ValueError("检查点 world 字段类型错误：residents/plans/events/audit")
    if not isinstance(snap["rng"], dict) or "llm" not in snap["rng"] or "event" not in snap["rng"]:
        raise ValueError("检查点 rng 缺少 llm/event 状态")
    if not isinstance(snap["llm"], dict) or "rng" not in snap["llm"]:
        raise ValueError("检查点 llm 缺少 rng 状态")
    if not isinstance(snap["counters"], dict):
        raise ValueError("检查点 counters 必须是对象")
    if not isinstance(snap["meta"], dict):
        raise ValueError("检查点 meta 必须是对象")
    # 叶子类型（R6 NEW-1：容器校验之外的深层形态）
    for key in ("seed", "n", "day", "abs_minute"):
        if type(w[key]) is not int:
            raise ValueError(f"检查点 world.{key} 必须是整数")
    for key in ("llm", "event"):
        if type(snap["rng"][key]) is not int:
            raise ValueError(f"检查点 rng.{key} 必须是整数")
    for key in ("rng", "batch", "p_rate", "p_bad", "p_invalid", "calls", "cost",
                "tokens", "prefix_written", "consec_fail", "breaker_until"):
        if key not in snap["llm"]:
            raise ValueError(f"检查点 llm 缺少必需字段：{key}")
    if type(snap["llm"]["rng"]) is not int:
        raise ValueError("检查点 llm.rng 必须是整数")
    for key in ("calls", "consec_fail", "breaker_until"):
        if type(snap["llm"][key]) is not int:
            raise ValueError(f"检查点 llm.{key} 必须是整数")
    if (isinstance(snap["llm"]["cost"], bool) or not isinstance(snap["llm"]["cost"], (int, float))
            or not _finite(snap["llm"]["cost"])):
        raise ValueError("检查点 llm.cost 必须是有限数")
    if not isinstance(snap["llm"]["tokens"], dict):
        raise ValueError("检查点 llm.tokens 必须是对象")
    # R8 MINOR-2：llm 兄弟字段（batch/p_*/prefix_written/backoff/half_open/tokens 对）
    if not isinstance(snap["llm"]["batch"], bool):
        raise ValueError("检查点 llm.batch 必须是 bool")
    for key in ("p_rate", "p_bad", "p_invalid"):
        v = snap["llm"][key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not _finite(v):
            raise ValueError(f"检查点 llm.{key} 必须是有限数")
    if not isinstance(snap["llm"]["prefix_written"], dict):
        raise ValueError("检查点 llm.prefix_written 必须是对象")
    if "backoff_until" in snap["llm"] and type(snap["llm"]["backoff_until"]) is not int:
        raise ValueError("检查点 llm.backoff_until 必须是整数")
    if "breaker_half_open" in snap["llm"] and not isinstance(snap["llm"]["breaker_half_open"], bool):
        raise ValueError("检查点 llm.breaker_half_open 必须是 bool")
    for tier in ("T1", "T2"):
        if not isinstance(snap["llm"]["prefix_written"].get(tier), bool):
            raise ValueError(f"检查点 llm.prefix_written.{tier} 必须是 bool")
        pair = snap["llm"]["tokens"].get(tier)
        if not (isinstance(pair, list) and len(pair) == 2
                and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                        and _finite(x) for x in pair)):
            raise ValueError(f"检查点 llm.tokens.{tier} 必须是有限数值对")
    for k, v in snap["counters"].items():
        if type(v) is not int:
            raise ValueError(f"检查点 counters.{k} 必须是整数")
    for k in ("rollbacks", "violations_detected"):
        if k in snap["meta"] and type(snap["meta"][k]) is not int:
            raise ValueError(f"检查点 meta.{k} 必须是整数")
    if not isinstance(snap["meta"].get("unresolved", []), list):
        raise ValueError("检查点 meta.unresolved 必须是列表")
    for e in w["events"] + w["audit"]:
        if not isinstance(e, dict):
            raise ValueError("检查点 events/audit 元素必须是对象")
    for e in w["audit"]:
        if not isinstance(e.get("type"), str):
            raise ValueError("检查点 audit 元素 type 必须是字符串")
    ids = set()
    for r in w["residents"]:
        if not isinstance(r, dict):
            raise ValueError("检查点 residents 元素必须是对象")
        for key in ("id", "role", "home", "work"):
            if not isinstance(r.get(key), str):
                raise ValueError(f"检查点 residents.{key} 必须是字符串")
        if r["role"] in NIGHT_SHIFT_ROLES:
            parts = r["id"].rsplit("-", 1)
            # R11 MAJOR-1：ASCII 数字谓词（isdigit 对 ²/① 为 True 但 int() 抛）；
            # R11 MINOR-3：前缀须与 role 一致，非 ASCII 十进制（٣/１）一并收紧拒绝。
            if (len(parts) != 2 or parts[0] != r["role"]
                    or not parts[1].isascii() or not parts[1].isdigit()):
                raise ValueError(f"检查点夜班 residents.id 格式必须为 {r['role']}-<ASCII 数字后缀>（前缀须与 role 一致）")
        if r["id"] in ids:
            raise ValueError(f"检查点 residents.id 重复：{r['id']}")
        ids.add(r["id"])
        if (isinstance(r.get("imp_sum"), bool) or not isinstance(r.get("imp_sum"), (int, float))
                or not _finite(r.get("imp_sum"))):
            raise ValueError("检查点 residents.imp_sum 必须是有限数")
        if type(r.get("last_ref_day")) is not int:
            raise ValueError("检查点 residents.last_ref_day 必须是整数")
        if r.get("focus") is not None and not isinstance(r.get("focus"), str):
            raise ValueError("检查点 residents.focus 必须是字符串或 null")
        if not isinstance(r.get("memories"), list):
            raise ValueError("检查点 residents.memories 必须是列表")
        for m in r["memories"]:
            if not isinstance(m, dict):
                raise ValueError("检查点 memories 元素必须是对象")
            if type(m.get("day")) is not int or type(m.get("minute")) is not int:
                raise ValueError("检查点 memories.day/minute 必须是整数")
            if not isinstance(m.get("text"), str):
                raise ValueError("检查点 memories.text 必须是字符串")
            if (isinstance(m.get("importance"), bool) or not isinstance(m.get("importance"), (int, float))
                    or not _finite(m.get("importance"))):
                raise ValueError("检查点 memories.importance 必须是有限数")
            if not isinstance(m.get("kind"), str):
                raise ValueError("检查点 memories.kind 必须是字符串")
            kw = m.get("keywords")
            if not (isinstance(kw, list) and len(kw) >= 1
                    and all(isinstance(x, str) for x in kw)):
                raise ValueError("检查点 memories.keywords 必须是非空字符串列表")
    for rid in ids:
        if rid not in w["plans"]:
            raise ValueError(f"检查点 plans 缺少居民键：{rid}")
    for plan in w["plans"].values():
        if not isinstance(plan, list) or len(plan) < 1:
            raise ValueError("检查点 plans 值必须是非空列表")
        for s in plan:
            if not isinstance(s, dict):
                raise ValueError("检查点 plans 段必须是对象")
            if type(s.get("start")) is not int or type(s.get("end")) is not int:
                raise ValueError("检查点 plans 段 start/end 必须是整数")
            if not isinstance(s.get("state"), str) or not isinstance(s.get("location"), str):
                raise ValueError("检查点 plans 段 state/location 必须是字符串")


def run_overnight(cfg: Config) -> dict:
    store = CheckpointStore(cfg.checkpoint_dir)
    injections = {"crash_left": 1 if cfg.crash_frac is not None else 0,
                  "corrupt_fired": set(),  # 已触发注入 tick：回滚重放不重复触发（分散注入语义）
                  "corrupt_plan_left": 1 if cfg.corrupt_plan_frac is not None else 0}
    meta = {"rollbacks": 0, "violations_detected": 0, "unresolved": []}
    resume, crashes = None, 0
    if cfg.resume:
        resume = store.load()  # load() 内含语义校验（冷/热/回滚单点）
        if resume is None:
            raise FileNotFoundError("--resume：未找到检查点（需指定 --checkpoint-dir 且已有 ckpt.json）")
        w0 = resume["world"]
        if w0["seed"] != cfg.seed or w0["n"] != cfg.agents:
            raise ValueError(f"--resume 配置不匹配：检查点 seed={w0['seed']}/agents={w0['n']}，"
                             f"当前 seed={cfg.seed}/agents={cfg.agents}（世界以快照为准，请用匹配参数）")
        if resume["tick"] > cfg.nights * TICKS_PER_NIGHT:
            raise ValueError(f"--resume：检查点 tick={resume['tick']} 超出当前 nights 总长 "
                             f"{cfg.nights * TICKS_PER_NIGHT}（nights 不能小于检查点进度）")
    while True:
        try:
            report = _run(cfg, store, injections, resume, meta)
            report["crashes_recovered"] = crashes
            return report
        except SimCrash:
            crashes += 1
            injections["crash_left"] -= 1
            resume = store.load()
            if resume is None:
                raise


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows GBK 控制台防乱码
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="千人小镇通宵无人值守 mock 演示")
    p.add_argument("--seed", type=int, default=20260818)
    p.add_argument("--nights", type=int, default=3)
    p.add_argument("--agents", type=int, default=1000)
    p.add_argument("--budget", type=float, default=2.0)
    p.add_argument("--crash-frac", type=float, default=0.4)
    p.add_argument("--no-crash", action="store_true")
    p.add_argument("--corrupt-frac", type=float, default=None)
    p.add_argument("--corrupt-times", type=int, default=1)
    p.add_argument("--corrupt-plan-frac", type=float, default=None)
    p.add_argument("--no-storm", action="store_true")
    p.add_argument("--batch", action="store_true", help="Batch API 5折计价模式")
    p.add_argument("--p-rate", type=float, default=0.02)
    p.add_argument("--p-bad", type=float, default=0.02)
    p.add_argument("--p-invalid", type=float, default=0.03)
    p.add_argument("--checkpoint-dir", default=None)
    p.add_argument("--resume", action="store_true",
                   help="冷重启：从 checkpoint-dir/ckpt.json 续跑（干预计数随快照恢复）")
    p.add_argument("--memory-ttl", type=int, default=None,
                   help="记忆过期天数（opt-in，移植 GA 30 天过期 [S19]）；默认不过期")
    p.add_argument("--events-out", default=None,
                   help="事件流 JSONL 导出路径（events+audit），供 visualize.html 时间轴")
    p.add_argument("--out", default=None)
    a = p.parse_args(argv)
    if a.budget < 0 or a.agents < 0 or a.nights < 0 or a.corrupt_times < 1:
        p.error("budget/agents/nights 必须非负，corrupt-times 必须 >= 1")
    if not _finite(a.budget):
        p.error("budget 必须是有限数（NaN/Inf 拒绝）")
    for name, val in (("--p-rate", a.p_rate), ("--p-bad", a.p_bad), ("--p-invalid", a.p_invalid)):
        if not (0.0 <= val <= 1.0):
            p.error(f"{name} 必须在 [0,1] 区间")
    for name, val in (("--crash-frac", a.crash_frac), ("--corrupt-frac", a.corrupt_frac),
                      ("--corrupt-plan-frac", a.corrupt_plan_frac)):
        if val is not None and not (0.0 <= val < 1.0):
            p.error(f"{name} 必须在 [0,1) 区间（=1 时注入点落在循环外，静默无操作）")
    try:
        cfg = Config(seed=a.seed, nights=a.nights, agents=a.agents, budget=a.budget,
                     crash_frac=None if a.no_crash else a.crash_frac,
                     corrupt_frac=a.corrupt_frac, corrupt_times=a.corrupt_times,
                     corrupt_plan_frac=a.corrupt_plan_frac, storm=not a.no_storm,
                     p_rate=a.p_rate, p_bad=a.p_bad, p_invalid=a.p_invalid,
                     batch=a.batch, checkpoint_dir=a.checkpoint_dir, resume=a.resume,
                     memory_ttl=a.memory_ttl, events_out=a.events_out)
        rep = run_overnight(cfg)
    except (ValueError, OSError, OverflowError, RecursionError) as e:
        p.error(str(e))  # 干净报错，不抛裸 traceback（R3–R6 校验家族；R12 OverflowError / R13 RecursionError 兜底）
    c = rep["counters"]
    print("=== 早晨报告 · seed=%d ===" % rep["seed"])
    print("状态: %s" % rep["status"])
    print("模拟进度: %d/%d ticks (%.1f 模拟天) · 人口 %d/%d"
          % (rep["ticks_completed"], rep["ticks_planned"], rep["sim_days"],
             rep["population_final"], rep["agents"]))
    print("崩溃恢复: %d 次 · 自动回滚: %d 次 · 违例累计: %d · 未解决: %d"
          % (rep["crashes_recovered"], rep["interventions_rollbacks"],
             rep["violations_detected"], len(rep["violations_unresolved"])))
    print("对话: %d (LLM %d / 规则兜底 %d)"
          % (rep["conversations_total"], c["conversations_llm"], c["conversations_degraded"]))
    print("反思: %d (采纳 %d / 拒绝 %d / 降级 %d)"
          % (rep["reflections_total"], c["reflections_accepted"],
             c["reflections_rejected"], c["reflections_degraded"]))
    print("限流命中: %d · 退避跳过: %d · 熔断开/关: %d/%d · 坏JSON: %d · 预算降级: %d · 预算拒绝: %d"
          % (c["rate_limit_hits"], c["backoff_skips"], c["breaker_opens"],
             c["breaker_closes"], c["malformed_hits"],
             c["budget_degradations"], c["budget_refusals"]))
    print("LLM 调用: %d 次 · 覆盖率 %.4f%% 代理-tick（焦点激活，军规1）"
          % (rep["llm_calls"], rep["llm_coverage_pct"]))
    print("成本: $%.4f / 封顶 $%.2f (%.2f%%) · 每事件 $%s · 每LLM有效事件 $%s"
          % (rep["cost_usd"], rep["budget_cap_usd"], rep["budget_used_pct"],
             rep["cost_per_event_usd"], rep["cost_per_llm_event_usd"]))
    print("审计条目: %d · 类型: %s" % (rep["audit_entries"], rep["audit_summary"]))
    print("终态哈希: %s" % rep["final_hash"])
    if a.out:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

            def _write_report():
                with open(a.out, "w", encoding="utf-8") as f:
                    json.dump(rep, f, ensure_ascii=False, indent=2, allow_nan=False)
            _retry_on_lock(_write_report)  # R61：报告写瞬时锁重试（永久失败仍走 except 体面）
        except (OSError, ValueError) as e:
            p.error(f"报告写盘失败：{e}")
        print("报告已写入: %s" % a.out)
    return 0 if rep["status"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
