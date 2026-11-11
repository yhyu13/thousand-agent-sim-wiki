#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""distributed_replica 测试套件（23 项）：python -m unittest test_distributed_replica -v
守卫规模化路线的确定性基础：无状态 worker / 命名空间 RNG / 排序施加 / 并行==串行 / 检查点续跑。
R36 硬化：续跑 focal_period 不匹配拒绝 / 损坏检查点拒绝 / 量级上限。
R37 硬化：键齐全但值类型损坏拒绝（bool 不算整数）/ schema_version 读取校验 / focal_period 严格整数化（封 True==1、10.0==10 等值陷阱）。
R38 硬化：深嵌套合法 JSON RecursionError 拒绝 / 负 tick 拒绝（防无界多跑）/ residents 数量与 n 交叉校验 / 写路径 OSError 干净拒绝。
R39 硬化：snap/world 未知键拒绝（封额外键深嵌套崩溃窗 W1/W2）/ 顶层 RecursionError 兜底（计算/序列化点未知深嵌套干净拒绝）。
R40 硬化：顶层兜底扩四家族对齐主 demo（ValueError/OSError/OverflowError/RecursionError；孤立代理对 UnicodeEncodeError ⊂ ValueError 干净拒绝）。
R59 硬化：检查点原子替换 Windows 瞬时文件锁短重试（_atomic_replace，与 overnight_town 同模式；瞬时 PermissionError 退避重试/永久失败抛出/happy path，3 项）。"""
import copy
import json
import os
import tempfile
import unittest
from unittest import mock

import distributed_replica as dr


def small_world(n=40, seed=20260818):
    return dr.init_world(seed, n)


class TestDistributedReplica(unittest.TestCase):
    def test_parallel_equals_sequential(self):
        """核心论点：无状态 worker + 排序补丁 → 并行结果 == 串行结果（军规2）。"""
        w_seq, w_par = small_world(), small_world()
        dr.run_sequential(w_seq, 30, 10)
        dr.run_parallel(w_par, 30, 10, workers=4)
        self.assertEqual(dr.world_hash(w_seq), dr.world_hash(w_par))

    def test_determinism_double_run(self):
        """同种子双跑 world_hash 逐位一致。"""
        w1, w2 = small_world(), small_world()
        dr.run_sequential(w1, 30, 10)
        dr.run_sequential(w2, 30, 10)
        self.assertEqual(dr.world_hash(w1), dr.world_hash(w2))

    def test_worker_pure_stateless(self):
        """worker 是纯函数：同输入→同输出，不依赖共享状态（可并行前提）。"""
        w = small_world()
        job = (w["seed"], 5, w["residents"][0], True)
        p1 = dr.step_resident(job)
        p2 = dr.step_resident(job)
        self.assertEqual(p1, p2)
        # 不修改输入 resident
        before = copy.deepcopy(w["residents"][0])
        dr.step_resident(job)
        self.assertEqual(w["residents"][0], before)

    def test_worker_rng_namespace(self):
        """RNG 由 (seed:id:tick) 命名空间：不同 tick/id 派生不同序列。"""
        w = small_world()
        r = w["residents"][0]
        a = dr.step_resident((w["seed"], 1, r, True))
        b = dr.step_resident((w["seed"], 2, r, True))
        # 不同 tick 至少能量轨迹不同（极小概率相同则换 id 比较）
        c = dr.step_resident((w["seed"], 1, w["residents"][1], True))
        self.assertTrue(a["energy"] != b["energy"] or a["energy"] != c["energy"])

    def test_focal_selection_deterministic(self):
        """焦点选择确定性子集，规模 ≈ n/period（军规1）。"""
        w = small_world(n=100)
        f0 = dr.focal_ids(w, 10)
        self.assertEqual(len(f0), 10)
        self.assertEqual(f0, dr.focal_ids(w, 10))  # 确定性
        w["tick"] = 1
        self.assertNotEqual(f0, dr.focal_ids(w, 10))  # 旋转

    def test_apply_patches_order_independent(self):
        """补丁施加与输入顺序无关（按 id 排序）→ 并行收集顺序不影响结果。"""
        w1, w2 = small_world(), small_world()
        focal = dr.focal_ids(w1, 10)
        jobs = [(w1["seed"], 0, r, r["id"] in focal) for r in w1["residents"]]
        patches = [dr.step_resident(j) for j in jobs]
        dr.apply_patches(w1, patches)
        dr.apply_patches(w2, list(reversed(patches)))
        self.assertEqual(dr.world_hash(w1), dr.world_hash(w2))

    def test_resume_equals_full(self):
        """检查点续跑终态 == 无中断全程（军规4/5）。"""
        with tempfile.TemporaryDirectory() as d:
            dr.main(["--seed", "7", "--agents", "30", "--ticks", "20",
                     "--checkpoint-dir", d, "--mode", "sequential",
                     "--out", os.path.join(d, "c1.json")])
            dr.main(["--seed", "7", "--agents", "30", "--ticks", "40",
                     "--checkpoint-dir", d, "--resume", "--mode", "sequential",
                     "--out", os.path.join(d, "c2.json")])
            dr.main(["--seed", "7", "--agents", "30", "--ticks", "40",
                     "--mode", "sequential", "--out", os.path.join(d, "full.json")])
            with open(os.path.join(d, "c2.json"), encoding="utf-8") as f:
                c2 = json.load(f)
            with open(os.path.join(d, "full.json"), encoding="utf-8") as f:
                full = json.load(f)
            self.assertEqual(c2["world_hash"], full["world_hash"])
            self.assertEqual(c2["resumed_from_tick"], 20)

    def test_cli_validation(self):
        """非法参数干净拒绝（rc=2）。"""
        for argv in (["--agents", "0"], ["--ticks", "-1"], ["--focal-period", "0"],
                     ["--workers", "0"], ["--resume"]):
            with self.assertRaises(SystemExit) as cm:
                dr.main(argv)
            self.assertEqual(cm.exception.code, 2)

    def test_resume_focal_period_mismatch(self):
        """R36 MINOR-1：续跑 focal_period 不匹配须拒绝（防混合轨迹）；v3.31：bool/float 不算整数。"""
        with tempfile.TemporaryDirectory() as d:
            dr.main(["--seed", "7", "--agents", "20", "--ticks", "10", "--focal-period", "10",
                     "--checkpoint-dir", d, "--mode", "sequential", "--out", os.path.join(d, "a.json")])
            ck = os.path.join(d, "dist_ckpt.json")
            with open(ck, encoding="utf-8") as f:
                good = json.load(f)
            # (检查点 fp, 额外 CLI 参数)：不匹配 / True==1 bool 陷阱 / 10.0==10 float 陷阱
            forms = [(10, ["--focal-period", "5"]), (True, ["--focal-period", "1"]), (10.0, [])]
            for fp, extra in forms:
                snap = copy.deepcopy(good)
                snap["focal_period"] = fp
                with open(ck, "w", encoding="utf-8") as f:
                    json.dump(snap, f)
                with self.subTest(focal_period=repr(fp)):
                    with self.assertRaises(SystemExit) as cm:
                        dr.main(["--seed", "7", "--agents", "20", "--ticks", "20",
                                 "--checkpoint-dir", d, "--resume", "--mode", "sequential",
                                 "--out", os.path.join(d, "b.json")] + extra)
                    self.assertEqual(cm.exception.code, 2)

    def test_resume_corrupt_checkpoint(self):
        """R36 O-1：损坏检查点干净拒绝（rc=2，无裸 traceback）。"""
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            for payload in ('{bad json', '', '{"schema_version":1}', '{"world":{"seed":7}}'):
                with open(ck, "w", encoding="utf-8") as f:
                    f.write(payload)
                with self.assertRaises(SystemExit) as cm:
                    dr.main(["--seed", "7", "--agents", "20", "--ticks", "20",
                             "--checkpoint-dir", d, "--resume", "--out", os.path.join(d, "b.json")])
                self.assertEqual(cm.exception.code, 2)

    def test_cli_magnitude_caps(self):
        """R36 O-5：量级上限拒绝。"""
        for argv in (["--agents", str(10**6 + 1)], ["--ticks", str(10**7 + 1)],
                     ["--focal-period", str(10**6 + 1)], ["--workers", "65"]):
            with self.assertRaises(SystemExit) as cm:
                dr.main(argv)
            self.assertEqual(cm.exception.code, 2)

    def test_resume_value_type_corruption(self):
        """R37 O-1a/b：键齐全但值类型损坏 → 干净拒绝 rc=2（bool 不算整数）。"""
        base = {"schema_version": 1, "focal_period": 10,
                "world": {"seed": 7, "n": 20, "tick": 5,
                          "residents": [{"id": "r-0000", "role": "resident", "energy": 60}]}}
        forms = [("residents", "garbage"), ("residents", 123), ("residents", None),
                 ("tick", "5"), ("tick", True), ("seed", "7"), ("n", None)]
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            for key, bad in forms:
                snap = copy.deepcopy(base)
                snap["world"][key] = bad
                with open(ck, "w", encoding="utf-8") as f:
                    json.dump(snap, f)
                with self.subTest(key=key, bad=repr(bad)):
                    with self.assertRaises(SystemExit) as cm:
                        dr.main(["--seed", "7", "--agents", "20", "--ticks", "20",
                                 "--checkpoint-dir", d, "--resume", "--out", os.path.join(d, "b.json")])
                    self.assertEqual(cm.exception.code, 2)

    def test_resume_schema_version_unsupported(self):
        """R37 O-1c：schema_version 读取校验（999/缺失/True/1.0/"1" → rc=2，bool/float 不算整数）。"""
        base = {"focal_period": 10,
                "world": {"seed": 7, "n": 20, "tick": 5,
                          "residents": [{"id": "r-0000", "role": "resident", "energy": 60}]}}
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            for sv in (999, None, True, 1.0, "1"):
                snap = copy.deepcopy(base)
                if sv is not None:
                    snap["schema_version"] = sv
                with open(ck, "w", encoding="utf-8") as f:
                    json.dump(snap, f)
                with self.subTest(schema_version=repr(sv)):
                    with self.assertRaises(SystemExit) as cm:
                        dr.main(["--seed", "7", "--agents", "20", "--ticks", "20",
                                 "--checkpoint-dir", d, "--resume", "--out", os.path.join(d, "b.json")])
                    self.assertEqual(cm.exception.code, 2)

    def test_resume_deep_nested_json(self):
        """R38 N-1：深嵌套*语法合法* JSON → RecursionError 捕获转干净 rc=2（与 overnight_town R13 同型）。"""
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            payload = '{"schema_version":1,"focal_period":10,"world":' + "[" * 5000 + "0" + "]" * 5000 + "}"
            with open(ck, "w", encoding="utf-8") as f:
                f.write(payload)
            with self.assertRaises(SystemExit) as cm:
                dr.main(["--seed", "7", "--agents", "20", "--ticks", "20",
                         "--checkpoint-dir", d, "--resume", "--out", os.path.join(d, "b.json")])
            self.assertEqual(cm.exception.code, 2)

    def test_resume_negative_tick(self):
        """R38 N-2：负 tick 拒绝（防无界多跑/挂死，绕过 ticks 上限意图）；巨负整数亦干净拒绝。"""
        base = {"schema_version": 1, "focal_period": 10, "world": dr.init_world(7, 20)}
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            for bad in (-3, -(10**400)):
                snap = copy.deepcopy(base)
                snap["world"]["tick"] = bad
                with open(ck, "w", encoding="utf-8") as f:
                    json.dump(snap, f)
                with self.subTest(tick=bad if bad > -10**6 else "-10**400"):
                    with self.assertRaises(SystemExit) as cm:
                        dr.main(["--seed", "7", "--agents", "20", "--ticks", "20",
                                 "--checkpoint-dir", d, "--resume", "--out", os.path.join(d, "b.json")])
                    self.assertEqual(cm.exception.code, 2)

    def test_resume_residents_count_mismatch(self):
        """R38 O-1：residents 数量与 n 交叉校验（空/少/多均拒绝）。"""
        world = dr.init_world(7, 20)
        forms = [[], world["residents"][:3],
                 world["residents"] + [{"id": f"x-{i}", "role": "resident", "energy": 60} for i in range(5)]]
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            for residents in forms:
                snap = {"schema_version": 1, "focal_period": 10,
                        "world": {"seed": 7, "n": 20, "tick": 5, "residents": residents}}
                with open(ck, "w", encoding="utf-8") as f:
                    json.dump(snap, f)
                with self.subTest(count=len(residents)):
                    with self.assertRaises(SystemExit) as cm:
                        dr.main(["--seed", "7", "--agents", "20", "--ticks", "20",
                                 "--checkpoint-dir", d, "--resume", "--out", os.path.join(d, "b.json")])
                    self.assertEqual(cm.exception.code, 2)

    def test_write_path_oserror(self):
        """R38 O-2：写路径 OSError 干净拒绝 rc=2（--out 目录不存在 / --checkpoint-dir 是普通文件）。"""
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as cm:
                dr.main(["--seed", "7", "--agents", "10", "--ticks", "2", "--mode", "sequential",
                         "--out", os.path.join(d, "no_such_dir", "r.json")])
            self.assertEqual(cm.exception.code, 2)
            regular_file = os.path.join(d, "afile")
            with open(regular_file, "w", encoding="utf-8") as f:
                f.write("x")
            with self.assertRaises(SystemExit) as cm:
                dr.main(["--seed", "7", "--agents", "10", "--ticks", "2", "--mode", "sequential",
                         "--checkpoint-dir", regular_file])
            self.assertEqual(cm.exception.code, 2)

    def test_resume_unknown_keys(self):
        """R39：snap/world 未知键拒绝（封额外键携带深嵌套的 W1 deepcopy/W2 写盘崩溃窗）。"""
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            # world 额外键（浅值）
            snap = {"schema_version": 1, "focal_period": 10,
                    "world": {"seed": 7, "n": 1, "tick": 5, "extra": 1,
                              "residents": [{"id": "r-0000", "role": "resident", "energy": 60}]}}
            with open(ck, "w", encoding="utf-8") as f:
                json.dump(snap, f)
            with self.subTest(form="world_extra_shallow"):
                with self.assertRaises(SystemExit) as cm:
                    dr.main(["--seed", "7", "--agents", "1", "--ticks", "20",
                             "--checkpoint-dir", d, "--resume", "--mode", "both"])
                self.assertEqual(cm.exception.code, 2)
            # world 额外键（深 800，可解析；旧版 both 模式 deepcopy 裸崩窗）
            payload = ('{"schema_version":1,"focal_period":10,"world":{"seed":7,"n":1,"tick":5,'
                       '"residents":[{"id":"r-0000","role":"resident","energy":60}],"extra":'
                       + "[" * 800 + "0" + "]" * 800 + "}}")
            with open(ck, "w", encoding="utf-8") as f:
                f.write(payload)
            with self.subTest(form="world_extra_deep800_both"):
                with self.assertRaises(SystemExit) as cm:
                    dr.main(["--seed", "7", "--agents", "1", "--ticks", "20",
                             "--checkpoint-dir", d, "--resume", "--mode", "both"])
                self.assertEqual(cm.exception.code, 2)
            # snap 顶层额外键
            snap2 = {"schema_version": 1, "focal_period": 10, "extra": 1,
                     "world": {"seed": 7, "n": 1, "tick": 5,
                               "residents": [{"id": "r-0000", "role": "resident", "energy": 60}]}}
            with open(ck, "w", encoding="utf-8") as f:
                json.dump(snap2, f)
            with self.subTest(form="snap_extra"):
                with self.assertRaises(SystemExit) as cm:
                    dr.main(["--seed", "7", "--agents", "1", "--ticks", "20",
                             "--checkpoint-dir", d, "--resume", "--mode", "sequential"])
                self.assertEqual(cm.exception.code, 2)

    def test_deep_nesting_residents_envelope(self):
        """R39：residents 元素内深嵌套（域外载体）由顶层 RecursionError 兜底干净拒绝。
        深度 1500：> deepcopy 上限(~500) 且 > json.dump 上限(~1000)、< json.load 上限(~3000)。"""
        payload = ('{"schema_version":1,"focal_period":10,"world":{"seed":7,"n":1,"tick":5,'
                   '"residents":[{"id":"r-0000","role":"resident","energy":60,"deep":'
                   + "[" * 1500 + "0" + "]" * 1500 + "}]}}")
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            with open(ck, "w", encoding="utf-8") as f:
                f.write(payload)
            for mode in ("both", "sequential"):
                with self.subTest(mode=mode):
                    with self.assertRaises(SystemExit) as cm:
                        dr.main(["--seed", "7", "--agents", "1", "--ticks", "20",
                                 "--checkpoint-dir", d, "--resume", "--mode", mode])
                    self.assertEqual(cm.exception.code, 2)

    def test_surrogate_string_envelope(self):
        """R40 O-1：元素字符串内孤立代理对（域外载体）→ world_hash .encode 抛
        UnicodeEncodeError ⊂ ValueError，顶层四家族兜底干净 rc=2（全模式）。"""
        payload = ('{"schema_version":1,"focal_period":10,"world":{"seed":7,"n":1,"tick":0,'
                   '"residents":[{"id":"r-0000","role":"resident","energy":60,"note":"\\ud800"}]}}')
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            with open(ck, "w", encoding="utf-8") as f:
                f.write(payload)
            for mode in ("both", "sequential", "parallel"):
                with self.subTest(mode=mode):
                    with self.assertRaises(SystemExit) as cm:
                        dr.main(["--seed", "7", "--agents", "1", "--ticks", "20",
                                 "--checkpoint-dir", d, "--resume", "--mode", mode])
                    self.assertEqual(cm.exception.code, 2)


class TestAtomicReplaceRetry(unittest.TestCase):
    """R59 硬化：Windows 瞬时文件锁短重试（与 overnight_town 同模式）。"""

    def test_happy_path_moves_file(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = os.path.join(d, "t.tmp"); target = os.path.join(d, "t.json")
            with open(tmp, "w") as f:
                f.write("x")
            dr._atomic_replace(tmp, target)
            self.assertFalse(os.path.exists(tmp))
            with open(target) as f:
                self.assertEqual(f.read(), "x")

    def test_transient_permission_then_success(self):
        calls = {"n": 0}
        real_replace = os.replace

        def flaky(tmp, target):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise PermissionError(13, "模拟瞬时锁")
            return real_replace(tmp, target)

        with tempfile.TemporaryDirectory() as d:
            tmp = os.path.join(d, "t.tmp"); target = os.path.join(d, "t.json")
            with open(tmp, "w") as f:
                f.write("y")
            with mock.patch.object(dr.os, "replace", side_effect=flaky), \
                 mock.patch.object(dr.time, "sleep") as slp:
                dr._atomic_replace(tmp, target)
            self.assertEqual(calls["n"], 3)
            self.assertEqual(slp.call_count, 2)
            with open(target) as f:
                self.assertEqual(f.read(), "y")

    def test_permanent_permission_raises(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = os.path.join(d, "t.tmp"); target = os.path.join(d, "t.json")
            with open(tmp, "w") as f:
                f.write("z")
            with mock.patch.object(dr.os, "replace", side_effect=PermissionError(13, "永久锁")), \
                 mock.patch.object(dr.time, "sleep"):
                with self.assertRaises(PermissionError):
                    dr._atomic_replace(tmp, target, attempts=3)
            self.assertTrue(os.path.exists(tmp))


if __name__ == "__main__":
    unittest.main(verbosity=2)