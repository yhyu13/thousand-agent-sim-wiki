#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
roi_calculator.py — 千人级模拟 ROI 估算器（零依赖）
====================================================
基线：OASIS 实测 100 代理 x 激活率1 x 1步 = 335,600 输入 + 16,750 输出 token [S06]
     → 每活跃代理-步 ≈ 3,356 输入 + 167.5 输出。
价格：Claude 平台 2026-11-11 时价 [S13]；Batch 全单 5 折 [S14]；
     qwen 历史为 OASIS README 2024-12-14 价口径 [S06]；Qwen 现价（含 legacy）为北京区 USD 列表价 [S27]（详见 ../04-roi.md §1.5，轮 24 核验）。
公式：cost = active_steps x (in_per_step x P_in x cache_mult + out_per_step x P_out) x batch_mult
     active_steps = agents x steps x activation x nights
     cache_mult = (1-f) + f x read_mult   （f=静态前缀占比，假设，待验证）

用法：python -I roi_calculator.py --agents 1000 --steps 48 --activation 0.1 --nights 1
"""
import argparse
import math
import sys

BASE_IN, BASE_OUT = 3356.0, 167.5  # [S06]

MODELS = {
    "haiku":     {"pin": 0.10, "pout": 0.50, "read": 0.10, "cur": "$",
                  "label": "Claude Haiku 5.5 [S13]"},
    "sonnet":    {"pin": 2.0,  "pout": 10.0, "read": 0.05, "cur": "$",
                  "label": "Claude Sonnet 5.5 [S13]"},
    "opus":      {"pin": 4.0,  "pout": 20.0, "read": 0.05, "cur": "$",
                  "label": "Claude Opus 5.5 [S13]"},
    "qwen-plus": {"step_cny": 0.0026848, "cur": "¥",
                  "label": "qwen-plus（2024-12 价）[S06]"},
    # OASIS 原表 qwen-max 行非线性（0.717x10 != 7.717，疑似上游笔误）；
    # 采用 1000 代理列单价 7.717/100=0.07717，与 100 代理列差 7.6%（wiki 04 页已披露）
    "qwen-max":  {"step_cny": 0.07717, "cur": "¥",
                  "label": "qwen-max（2024-12 价，1000代理列）[S06]"},
    # Qwen 现价（北京区 USD/MTok 列表价，非思考，轮 24 直抓 [S27]，详见 04 §1.5）。
    # read=0.1=缓存命中 10%（创建 125% 忽略，稳态理想化同 Claude）；no_stack=缓存与 Batch 不叠加 [S27]。
    # 分层计价：单请求输入 3356 token 落最低档（<32K）；思考模式 token 计入输出（此处非思考口径）。
    "qwen3.8-max": {"pin": 1.65, "pout": 4.951, "read": 0.10, "no_stack": True, "cur": "$",
                  "label": "qwen3.8-max 现价·北京 [S27]"},
    "qwen-max-current": {"pin": 0.345, "pout": 1.377, "read": 0.10, "no_stack": True, "cur": "$",
                  "label": "qwen-max 现价·北京(legacy) [S27]"},
    "qwen3.7-plus": {"pin": 0.276, "pout": 1.101, "read": 0.10, "no_stack": True, "cur": "$",
                  "label": "qwen3.7-plus 现价·北京 [S27]"},
    "qwen3.8-flash": {"pin": 0.113, "pout": 0.382, "read": 0.10, "no_stack": True, "cur": "$",
                  "label": "qwen3.8-flash 现价·北京 [S27]"},
    "qwen3.7-flash": {"pin": 0.028, "pout": 0.110, "read": 0.10, "no_stack": True, "cur": "$",
                  "label": "qwen3.7-flash 现价·北京 [S27]"},
    # qwen-plus legacy 现价（≤128K 非思考输出 0.287；思考输出 1.147 更贵，此处非思考口径）[S27]
    "qwen-plus-current": {"pin": 0.115, "pout": 0.287, "read": 0.10, "no_stack": True, "cur": "$",
                  "label": "qwen-plus 现价·北京(legacy) [S27]"},
    "local":     {"pin": 0.0, "pout": 0.0, "read": 0.0, "cur": "$",
                  "label": "Ollama 本地（边际成本，硬件另计）[S03]"},
    # DeepSeek 峰谷计价 [S26]：off-peak=半价，北京时间夜间 22:00–08:00 全 off-peak。
    # hit/miss 为绝对单价（$/MTok），cache_f 解释为缓存命中率；无公开 Batch API，不外推。
    "deepseek-flash-offpeak": {"miss": 0.15, "hit": 0.003, "pout": 0.60, "cur": "$",
                  "label": "DeepSeek Flash 谷时（夜间半价）[S26]"},
    "deepseek-v4pro-offpeak": {"miss": 0.66, "hit": 0.022, "pout": 1.98, "cur": "$",
                  "label": "DeepSeek V4-Pro 谷时 [S26]"},
}


def cost_usd(key, active_steps, cache_f=0.0, batch=False):
    m = MODELS[key]
    if "step_cny" in m:
        if cache_f or batch:
            return None  # qwen 表无缓存/批处理口径，不外推
        return active_steps * m["step_cny"]
    if "hit" in m:
        if batch:
            return None  # DeepSeek 无公开 Batch API，不外推 [S26]
        in_price = (1 - cache_f) * m["miss"] + cache_f * m["hit"]
        return active_steps * (BASE_IN * in_price + BASE_OUT * m["pout"]) / 1e6
    mult = (1 - cache_f) + cache_f * m["read"]
    if m.get("no_stack") and cache_f and batch:
        return None  # Qwen 现价缓存与 Batch 不叠加 [S27]
    c = active_steps * (BASE_IN * m["pin"] * mult + BASE_OUT * m["pout"]) / 1e6
    return c * (0.5 if batch else 1.0)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="千人级模拟 ROI 估算（OASIS 基线 x 平台时价）")
    p.add_argument("--agents", type=int, default=1000)
    p.add_argument("--steps", type=int, default=48, help="每夜时间步（8h x 10min = 48）")
    p.add_argument("--activation", type=float, default=0.1)
    p.add_argument("--nights", type=int, default=1)
    p.add_argument("--cache-f", type=float, default=0.7, help="静态前缀占比（假设，待验证）")
    a = p.parse_args(argv)
    # 参数校验与主演示同口径（R5 MINOR-5）
    if not (math.isfinite(a.cache_f) and 0.0 <= a.cache_f <= 1.0):
        p.error("cache-f 必须在 [0,1]（有限数）")
    if not (math.isfinite(a.activation) and 0.0 <= a.activation <= 1.0):
        p.error("activation 必须在 [0,1]（有限数）")
    if a.agents < 0 or a.steps < 0 or a.nights < 0:
        p.error("agents/steps/nights 必须非负")
    active = a.agents * a.steps * a.activation * a.nights
    print("场景: %d 代理 x %d 步/夜 x 激活率 %.2f x %d 夜 = %s 活跃代理-步"
          % (a.agents, a.steps, a.activation, a.nights, f"{active:,.0f}"))
    print("token 基线: 每活跃代理-步 %.0f 输入 + %.1f 输出 [S06]" % (BASE_IN, BASE_OUT))
    print("缓存假设: f=%.2f（Claude/Qwen现价 行=静态前缀占比；DeepSeek 行=缓存命中率；Qwen现价缓存与Batch不叠加→n/a）；Batch=5折 [S13][S14][S26][S27]\n" % a.cache_f)
    hdr = "%-34s %12s %12s %12s %14s" % ("模型", "标准", "+缓存", "+Batch", "+缓存+Batch")
    print(hdr)
    print("-" * len(hdr))
    for key, m in MODELS.items():
        cells = []
        for f, b in ((0.0, False), (a.cache_f, False), (0.0, True), (a.cache_f, True)):
            c = cost_usd(key, active, f, b)
            cells.append("n/a" if c is None else "%s%.2f" % (m["cur"], c))
        print("%-34s %12s %12s %12s %14s" % (m["label"], *cells))
    print("\n提示: 以上为估算（公式+已核验单价/基线，与 demo 的 mock token 模型相互独立）。")
    print("认知分层（T0规则/T1廉价/T2贵）会进一步压低实际成本——见 overnight_town.py 实测:")
    print("1000人x3夜仅 335 次调用、覆盖率 0.0775% 代理-tick、总成本 $0.2050（out/morning_report.json）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
