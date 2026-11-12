# -*- coding: utf-8 -*-
"""换班工件（5 项）：python -m unittest test_shift_handoff -v

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


if __name__ == "__main__":
    unittest.main()
