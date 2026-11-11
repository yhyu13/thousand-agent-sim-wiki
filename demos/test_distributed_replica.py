#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""distributed_replica 测试套件（13 项）：python -m unittest test_distributed_replica -v
守卫规模化路线的确定性基础：无状态 worker / 命名空间 RNG / 排序施加 / 并行==串行 / 检查点续跑。
R36 硬化：续跑 focal_period 不匹配拒绝 / 损坏检查点拒绝 / 量级上限。
R37 硬化：键齐全但值类型损坏拒绝（bool 不算整数）/ schema_version 读取校验。"""
import copy
import json
import os
import tempfile
import unittest

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
        """R36 MINOR-1：续跑 focal_period 不匹配须拒绝（防混合轨迹）。"""
        with tempfile.TemporaryDirectory() as d:
            dr.main(["--seed", "7", "--agents", "20", "--ticks", "10", "--focal-period", "10",
                     "--checkpoint-dir", d, "--mode", "sequential", "--out", os.path.join(d, "a.json")])
            with self.assertRaises(SystemExit) as cm:
                dr.main(["--seed", "7", "--agents", "20", "--ticks", "20", "--focal-period", "5",
                         "--checkpoint-dir", d, "--resume", "--mode", "sequential", "--out", os.path.join(d, "b.json")])
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
        """R37 O-1c：schema_version 读取校验（999/缺失 → rc=2，不再只写不读）。"""
        base = {"focal_period": 10,
                "world": {"seed": 7, "n": 20, "tick": 5,
                          "residents": [{"id": "r-0000", "role": "resident", "energy": 60}]}}
        with tempfile.TemporaryDirectory() as d:
            ck = os.path.join(d, "dist_ckpt.json")
            for sv in (999, None):
                snap = copy.deepcopy(base)
                if sv is not None:
                    snap["schema_version"] = sv
                with open(ck, "w", encoding="utf-8") as f:
                    json.dump(snap, f)
                with self.subTest(schema_version=sv):
                    with self.assertRaises(SystemExit) as cm:
                        dr.main(["--seed", "7", "--agents", "20", "--ticks", "20",
                                 "--checkpoint-dir", d, "--resume", "--out", os.path.join(d, "b.json")])
                    self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)