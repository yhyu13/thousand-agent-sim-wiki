# -*- coding: utf-8 -*-
"""操作员换班工件（不参与模拟，不读世界状态）。

对应跨会话 harness：功能清单用 JSON，条目先失败；只允许把某一条的
passes 改成 true。删条目、改描述、改字段集合都拒绝。进度文件只追加。
"""
import json
from pathlib import Path

CANONICAL = (
    {"id": "ticks", "description": "ticks_completed 等于计划 ticks", "passes": False},
    {"id": "structure", "description": "violations_unresolved 为空", "passes": False},
    {"id": "budget", "description": "cost_usd 不超过 budget", "passes": False},
    {"id": "society", "description": "对话与反思之和大于 0", "passes": False},
    {"id": "repro", "description": "world_hash 与同失败配置的对照跑一致，且 final_hash 与同配置重跑一致", "passes": False},
    {"id": "audit", "description": "熔断、降级、回滚、拒绝都有模拟时间的审计条目", "passes": False},
)


def canonical_list():
    return [dict(item) for item in CANONICAL]


def write_feature_list(path):
    Path(path).write_text(
        json.dumps(canonical_list(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("功能清单必须是数组")
    expect = canonical_list()
    if [item.get("id") for item in data] != [item["id"] for item in expect]:
        raise ValueError("功能清单的 id 与顺序不得增删")
    allowed = {"id", "description", "passes"}
    for got, exp in zip(data, expect):
        if set(got) != allowed:
            raise ValueError("功能条目只允许 id、description、passes")
        if got["description"] != exp["description"]:
            raise ValueError("不许改功能描述：%s" % exp["id"])
        if type(got["passes"]) is not bool:
            raise ValueError("passes 必须是布尔，不能是 0/1")
    return data


def set_passing(path, feature_id):
    """一班只把一条标成通过。其他条目的 passes 与描述保持原样。"""
    data = _load(path)
    ids = [item["id"] for item in data]
    if feature_id not in ids:
        raise ValueError("未知功能：%s" % feature_id)
    for item in data:
        if item["id"] == feature_id:
            item["passes"] = True
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def append_progress(path, line):
    if not isinstance(line, str) or not line.strip() or "\n" in line:
        raise ValueError("进度一次只能追加一行非空文本")
    target = Path(path)
    previous = target.read_text(encoding="utf-8") if target.exists() else ""
    with target.open("a", encoding="utf-8") as handle:
        handle.write(line.strip() + "\n")
    current = target.read_text(encoding="utf-8")
    if not current.startswith(previous):
        raise ValueError("进度文件前缀被改写")
