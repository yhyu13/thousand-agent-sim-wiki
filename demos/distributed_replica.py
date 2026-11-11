#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
distributed_replica.py — 分布式规模化路线最小复刻（零依赖，纯标准库）
====================================================================
演示 AgentSociety 2 [S08] 的「无状态执行体 + 确定性世界 + 焦点激活」规模化路线，
用 stdlib multiprocessing 替代 Ray（教学复刻，非生产分布式框架）。

核心论点（01 页 §2 路线 B / 02 页架构）：
  * 世界层是确定性的纯数据；worker 是**无状态纯函数**（输入→补丁，不共享可变状态）。
  * 每个 worker 的 RNG 由 (seed, resident_id, tick) 命名空间派生（FNV-1a + mulberry32，
    与 overnight_town.py / resident-plan.js 同常量），故执行顺序无关。
  * 补丁按 resident_id 排序后施加 → **并行结果 == 串行结果**（可复现，军规2）。
  * 焦点激活：每 tick 只调度确定性子集（军规1），其余走规则层，成本第一杠杆。

与 overnight_town.py 的关系：后者是单进程全量小镇（含 LLM 网关/记忆/看门狗）；
本文件剥离出「可并行化的无状态计算内核」，证明规模化路线的确定性基础。

用法：
  python -I distributed_replica.py --seed 20260818 --agents 1000 --ticks 144 --workers 4 --mode both
  python -I distributed_replica.py --checkpoint-dir out/dist --ticks 144   # 落检查点
  python -I distributed_replica.py --checkpoint-dir out/dist --resume --ticks 288  # 续跑
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import sys
import time


def _atomic_replace(tmp: str, target: str, attempts: int = 5):
    """原子替换 + Windows 瞬时文件锁短重试（R59 硬化，与 overnight_town 同模式）。
    杀软/索引器短暂持有目标致 os.replace 抛 PermissionError(WinError 5)时退避重试，
    永久失败仍抛出（调用方 except OSError 转干净 rc=2）；无锁时行为同 os.replace。"""
    for i in range(attempts):
        try:
            os.replace(tmp, target)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.05 * (i + 1))


def fnv1a(text: str) -> int:
    """FNV-1a 32bit，与 overnight_town.py / resident-plan.js:50 同常量。"""
    h = 0x811C9DC5
    for ch in text:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


class Rng:
    """mulberry32：单 uint32 状态，可序列化（军规5）。"""

    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFF

    def next_u32(self) -> int:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ ((t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return (t ^ (t >> 14)) & 0xFFFFFFFF

    def randint(self, n: int) -> int:
        return self.next_u32() % n


def canonical_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# 无状态 worker：纯函数 (seed, tick, resident, focal) -> patch。
# 不读写任何全局/共享状态；RNG 由 (seed:id:tick) 命名空间派生 → 顺序无关（军规2/3）。
# 必须为模块顶层函数（Windows spawn 可 pickle）。
# ---------------------------------------------------------------------------
def step_resident(job):
    seed, tick, resident, focal = job
    rid = resident["id"]
    rng = Rng(fnv1a(f"{seed}:{rid}:{tick}"))
    energy = resident["energy"]
    if focal:
        # 焦点代理：反思消耗能量（对应 T2 贵档低频认知）
        delta = -(1 + rng.randint(5))
        action = "reflect"
    else:
        # 非焦点：规则层休整（对应 T0 规则，零 LLM 成本）
        delta = rng.randint(3)
        action = "idle"
    new_energy = max(0, min(100, energy + delta))
    return {"id": rid, "energy": new_energy, "action": action, "tick": tick}


def init_world(seed: int, n: int):
    residents = []
    for i in range(n):
        rng = Rng(fnv1a(f"{seed}:init:{i}"))
        residents.append({"id": f"r-{i:04d}", "role": "resident",
                          "energy": 60 + rng.randint(41)})
    return {"seed": seed, "n": n, "tick": 0, "residents": residents}


def focal_ids(world, focal_period: int):
    """确定性焦点选择：每 tick 旋转子集（军规1）。与执行顺序无关。"""
    tick = world["tick"]
    return {r["id"] for i, r in enumerate(world["residents"])
            if i % focal_period == tick % focal_period}


def apply_patches(world, patches):
    """补丁按 id 排序施加 → 并行/串行结果一致（军规2）。
    前置条件：每 id 每 tick 恰一个补丁（流水线保证）；重复 id 会因稳定排序保留输入序而顺序敏感（域外输入）。"""
    by_id = {r["id"]: r for r in world["residents"]}
    focal_count = 0
    for p in sorted(patches, key=lambda x: x["id"]):
        by_id[p["id"]]["energy"] = p["energy"]
        if p["action"] == "reflect":
            focal_count += 1
    world["tick"] += 1
    return focal_count


def run_sequential(world, ticks: int, focal_period: int):
    focal_total = 0
    for _ in range(ticks):
        focal = focal_ids(world, focal_period)
        jobs = [(world["seed"], world["tick"], r, r["id"] in focal)
                for r in world["residents"]]
        patches = [step_resident(j) for j in jobs]
        focal_total += apply_patches(world, patches)
    return focal_total


def run_parallel(world, ticks: int, focal_period: int, workers: int):
    focal_total = 0
    with mp.Pool(processes=workers) as pool:
        for _ in range(ticks):
            focal = focal_ids(world, focal_period)
            jobs = [(world["seed"], world["tick"], r, r["id"] in focal)
                    for r in world["residents"]]
            patches = pool.map(step_resident, jobs)
            focal_total += apply_patches(world, patches)
    return focal_total


def world_hash(world):
    return canonical_hash({"tick": world["tick"], "residents": world["residents"]})


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="分布式规模化路线最小复刻（无状态 worker + 确定性世界）")
    p.add_argument("--seed", type=int, default=20260818)
    p.add_argument("--agents", type=int, default=1000)
    p.add_argument("--ticks", type=int, default=144)
    p.add_argument("--focal-period", type=int, default=10, help="焦点激活周期（每 tick 1/period 代理）")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--mode", choices=["parallel", "sequential", "both"], default="both")
    p.add_argument("--checkpoint-dir")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--out")
    a = p.parse_args(argv)
    if a.agents < 1 or a.ticks < 0 or a.focal_period < 1 or a.workers < 1:
        p.error("agents/focal-period/workers 须 >= 1，ticks 须 >= 0")
    if a.agents > 10**6 or a.ticks > 10**7 or a.focal_period > 10**6 or a.workers > 64:
        p.error("量级上限：agents/focal-period <= 10^6、ticks <= 10^7、workers <= 64（防无界/挂死）")

    start_tick = 0
    if a.resume:
        if not a.checkpoint_dir:
            p.error("--resume 需 --checkpoint-dir")
        ck = os.path.join(a.checkpoint_dir, "dist_ckpt.json")
        if not os.path.exists(ck):
            p.error(f"--resume：未找到检查点 {ck}")
        try:
            with open(ck, encoding="utf-8") as f:
                snap = json.load(f)
        except (ValueError, OSError, RecursionError) as e:
            # RecursionError：深嵌套*语法合法* JSON（与 overnight_town R13 同型）；UnicodeDecodeError ⊂ ValueError。
            p.error(f"--resume：检查点读取失败（{ck}）：{e}")
        if not isinstance(snap, dict) or not isinstance(snap.get("world"), dict):
            p.error("--resume：检查点格式错误（缺 world 对象）")
        if set(snap) - {"schema_version", "focal_period", "world"}:
            p.error("--resume：检查点含未知顶层键（仅允许 schema_version/focal_period/world）")
        sv = snap.get("schema_version")
        if type(sv) is not int or sv != 1:
            p.error(f"--resume：不支持的检查点 schema_version={sv!r}（仅支持整数 1；bool/float 不算整数）")
        world = snap["world"]
        if not all(k in world for k in ("seed", "n", "tick", "residents")):
            p.error("--resume：检查点 world 缺必需字段（seed/n/tick/residents）")
        if set(world) - {"seed", "n", "tick", "residents"}:
            p.error("--resume：检查点 world 含未知键（仅允许 seed/n/tick/residents；封额外键深嵌套崩溃窗 R39）")
        # 值类型校验（R37 O-1a/b）：键齐全但值损坏也须干净拒绝；type() is int 排除 bool。
        # 域外说明：residents 元素内部结构不做逐条深校验（仅数量与 n 交叉校验；教学复刻，检查点由本程序自身写出）；
        # 元素内未知深嵌套/编码类错误（UnicodeEncodeError ⊂ ValueError，如孤立代理对）由 main() 顶层四家族兜底干净拒绝；
        # 元素垃圾 TypeError/KeyError 不在兜底家族，保持 rc=1（域外，文档明示）。
        if (type(world["seed"]) is not int or type(world["n"]) is not int
                or type(world["tick"]) is not int or not isinstance(world["residents"], list)):
            p.error("--resume：检查点字段类型错误（seed/n/tick 须为整数，residents 须为列表；bool 不算整数）")
        if world["tick"] < 0:
            p.error(f"--resume：检查点 tick={world['tick']} 为负（进度须 >= 0；负值会无界多跑，绕过 ticks 上限意图）")
        if world["seed"] != a.seed or world["n"] != a.agents:
            p.error(f"--resume 配置不匹配：检查点 seed={world['seed']}/n={world['n']}，当前 seed={a.seed}/agents={a.agents}")
        if len(world["residents"]) != world["n"]:
            p.error(f"--resume：检查点 residents 数量 {len(world['residents'])} 与 n={world['n']} 不一致")
        fp = snap.get("focal_period")
        if type(fp) is not int or fp != a.focal_period:
            p.error(f"--resume 配置不匹配：检查点 focal_period={fp!r}，当前 {a.focal_period}（焦点周期改变会产生混合轨迹，须一致；bool/float 不算整数）")
        start_tick = world["tick"]
        if a.ticks < start_tick:
            p.error(f"--resume：ticks={a.ticks} 小于检查点进度 {start_tick}")
    else:
        world = init_world(a.seed, a.agents)

    # 顶层四家族兜底（对齐 overnight_town main()；R39 引入 RecursionError，R40 扩家族）：
    # 三个递归上限不对称（json.load C 扫描器 ~3000 / json.dump iterencode ~1000 / copy.deepcopy ~500），
    # 解析点捕获之外，计算/序列化点（deepcopy/world_hash/写盘）遇未知深嵌套形态亦干净拒绝；
    # UnicodeEncodeError ⊂ ValueError（孤立代理对等域外元素字符串）同被干净拒绝。
    try:
        remaining = a.ticks - start_tick
        report = {"seed": a.seed, "agents": a.agents, "ticks_planned": a.ticks,
                  "resumed_from_tick": start_tick, "focal_period": a.focal_period}

        if a.mode == "both":
            import copy
            w_seq = copy.deepcopy(world)
            w_par = copy.deepcopy(world)
            f_seq = run_sequential(w_seq, remaining, a.focal_period)
            f_par = run_parallel(w_par, remaining, a.focal_period, a.workers)
            h_seq, h_par = world_hash(w_seq), world_hash(w_par)
            report["mode"] = "both"
            report["sequential_hash"] = h_seq
            report["parallel_hash"] = h_par
            report["parallel_equals_sequential"] = (h_seq == h_par)
            report["focal_total"] = f_par
            world = w_par
            if h_seq != h_par:
                print("错误：并行 != 串行（确定性被破坏）", file=sys.stderr)
                return 1
        elif a.mode == "parallel":
            report["focal_total"] = run_parallel(world, remaining, a.focal_period, a.workers)
            report["mode"] = "parallel"
        else:
            report["focal_total"] = run_sequential(world, remaining, a.focal_period)
            report["mode"] = "sequential"

        report["ticks_completed"] = world["tick"]
        report["world_hash"] = world_hash(world)

        if a.checkpoint_dir:
            try:
                os.makedirs(a.checkpoint_dir, exist_ok=True)
                ck = os.path.join(a.checkpoint_dir, "dist_ckpt.json")
                tmp = ck + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump({"schema_version": 1, "focal_period": a.focal_period, "world": world}, f, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                _atomic_replace(tmp, ck)
            except OSError as e:
                p.error(f"检查点写入失败（{a.checkpoint_dir}）：{e}")

        print("=== 分布式复刻报告 ===")
        print("模式: %s · %d 代理 x %d ticks · 焦点周期 1/%d" %
              (report["mode"], a.agents, world["tick"], a.focal_period))
        print("焦点调度总数（本次运行段，非累计）: %d（其余走规则层，零 LLM 成本）" % report["focal_total"])
        if a.mode == "both":
            print("并行 == 串行: %s" % report["parallel_equals_sequential"])
            print("  sequential_hash: %s" % report["sequential_hash"])
            print("  parallel_hash:   %s" % report["parallel_hash"])
        print("world_hash: %s" % report["world_hash"])
        print("论点：无状态 worker + 命名空间 RNG + 排序施加补丁 → 可并行且可复现 [S08]。")

        if a.out:
            try:
                with open(a.out, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
            except OSError as e:
                p.error(f"报告写入失败（{a.out}）：{e}")
        return 0
    except (ValueError, OSError, OverflowError, RecursionError) as e:
        p.error(f"状态无法处理（干净拒绝）：{e}")


if __name__ == "__main__":
    sys.exit(main())