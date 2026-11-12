# -*- coding: utf-8 -*-
"""换班工件（11 项）：python -m unittest test_shift_handoff -v

功能清单不许增删或改描述；一班只把一条 passes 改成 true；进度只追加。
不导入 overnight_town，因此不触碰世界哈希。
"""
import json
import tempfile
import unittest
from pathlib import Path

import shift_handoff as sh


class TestShiftHandoff(unittest.TestCase):
    def test_fresh_list_all_failing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.json"
            sh.write_feature_list(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in data], [item["id"] for item in sh.CANONICAL])
            self.assertTrue(all(item["passes"] is False for item in data))

    def test_one_pass_leaves_the_rest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.json"
            sh.write_feature_list(path)
            before = json.loads(path.read_text(encoding="utf-8"))
            sh.set_passing(path, "budget")
            after = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(after[2]["passes"] is True)
            for index, item in enumerate(after):
                self.assertEqual(item["description"], before[index]["description"])
                if item["id"] != "budget":
                    self.assertTrue(item["passes"] is False)

    def test_delete_or_reorder_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.json"
            sh.write_feature_list(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            path.write_text(json.dumps(data[1:], ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                sh.set_passing(path, "budget")

    def test_description_edit_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.json"
            sh.write_feature_list(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data[0]["description"] = "改过的描述"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                sh.set_passing(path, "ticks")
            data[0]["description"] = sh.CANONICAL[0]["description"]
            data[0]["passes"] = 1
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                sh.set_passing(path, "ticks")

    def test_progress_is_append_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.txt"
            sh.append_progress(path, "班次 1：短跑哈希一致")
            sh.append_progress(path, "班次 2：只验收 budget")
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text, "班次 1：短跑哈希一致\n班次 2：只验收 budget\n")
            with self.assertRaises(ValueError):
                sh.append_progress(path, "两行\n不行")

    def test_report_marks_only_what_one_file_can_prove(self):
        report = {
            "ticks_completed": 432, "ticks_planned": 432,
            "violations_unresolved": [],
            "cost_usd": 0.2, "budget_cap_usd": 2.0,
            "conversations_total": 10, "reflections_total": 4,
            "world_hash": "abc", "final_hash": "def",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.json"
            sh.write_feature_list(path)
            proven = sh.apply_report(path, report)
            self.assertEqual(proven, ["ticks", "structure", "budget", "society"])
            data = json.loads(path.read_text(encoding="utf-8"))
            flags = {item["id"]: item["passes"] for item in data}
            self.assertTrue(flags["ticks"] and flags["structure"] and flags["budget"] and flags["society"])
            self.assertTrue(flags["repro"] is False and flags["audit"] is False)

    def test_short_run_does_not_pass_ticks(self):
        report = {
            "ticks_completed": 10, "ticks_planned": 432,
            "violations_unresolved": ["I3"],
            "cost_usd": 3.0, "budget_cap_usd": 2.0,
            "conversations_total": 0, "reflections_total": 0,
        }
        self.assertEqual(sh.passing_from_report(report), [])

    def test_bool_budget_is_not_a_number(self):
        report = {
            "ticks_completed": 1, "ticks_planned": 1,
            "violations_unresolved": [],
            "cost_usd": True, "budget_cap_usd": True,
            "conversations_total": 1, "reflections_total": 0,
        }
        self.assertNotIn("budget", sh.passing_from_report(report))

    def _base(self):
        return {
            "ticks_completed": 4, "ticks_planned": 4,
            "violations_unresolved": [],
            "cost_usd": 0.1, "budget_cap_usd": 2.0,
            "conversations_total": 1, "reflections_total": 1,
            "world_hash": "world", "final_hash": "final",
            "interventions_rollbacks": 1,
            "counters": {"budget_degradations": 0, "breaker_opens": 0, "reflections_rejected": 1},
        }

    def test_repro_needs_both_hashes(self):
        report = self._base()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.json"
            sh.write_feature_list(path)
            self.assertNotIn("repro", sh.apply_report(path, report, control={"world_hash": "world"}))
            sh.write_feature_list(path)
            proven = sh.apply_report(
                path, report,
                control={"world_hash": "world"},
                rerun={"final_hash": "final"},
            )
            self.assertIn("repro", proven)
            flags = {item["id"]: item["passes"] for item in json.loads(path.read_text(encoding="utf-8"))}
            self.assertTrue(flags["repro"] is True)
            self.assertTrue(flags["audit"] is False)

    def test_repro_rejects_mismatched_world(self):
        report = self._base()
        self.assertNotIn("repro", sh.apply_report(
            self._fresh(), report, control={"world_hash": "other"}, rerun={"final_hash": "final"}))

    def test_audit_needs_timestamped_rows(self):
        report = self._base()
        rows = [
            {"day": 0, "minute": 10, "type": "rollback"},
            {"day": 0, "minute": 20, "type": "patch_rejected"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "features.json"
            sh.write_feature_list(path)
            proven = sh.apply_report(path, report, audit_rows=rows)
            self.assertIn("audit", proven)
        bad = [{"day": 0, "type": "rollback"}, {"day": 0, "minute": 20, "type": "patch_rejected"}]
        self.assertNotIn("audit", sh.apply_report(self._fresh(), report, audit_rows=bad))

    def _fresh(self):
        directory = tempfile.mkdtemp()
        path = Path(directory) / "features.json"
        sh.write_feature_list(path)
        return path


if __name__ == "__main__":
    unittest.main()
