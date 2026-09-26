# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
"""从原始附件生成 Q2/Q3/Q4 输入数据候选图，用于建模证据池。"""

from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import load_workbook
from mountain_flood.figure.export_figure import export_figure


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures/rigor_pool_20260926"
plt.rcParams.update({"font.family": "PingFang SC", "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "none"})


def rows(name, tab="数据"):
    return list(load_workbook(ROOT / "input" / f"{name}.xlsx", read_only=True,
                              data_only=True)[tab].values)


def export(fig, name, size):
    fig.tight_layout()
    export_figure(fig, str(OUT / name), formats=("pdf", "svg", "png"),
                  dpi=300, size_inches=size, grayscale_preview=False, tight=False)
    plt.close(fig)


def raw_q2():
    boxes = rows("物资需求与配送时限", "逐箱货箱清单")[1:]
    hard, soft = Counter(), Counter()
    for row in boxes:
        (hard if row[2] == "医疗物资" or row[5] == "是" else soft)[row[1]] += 1
    labels = [f"S{i:03}" for i in range(1, 16)]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.bar(labels, [hard[x] for x in labels], color="#315E9D", label="医疗或首批硬时限")
    ax.bar(labels, [soft[x] for x in labels], bottom=[hard[x] for x in labels],
           color="#CE853D", label="其他货箱")
    ax.set_ylabel("原始货箱数 / 箱")
    ax.set_xlabel("原始服务区")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.grid(axis="y", alpha=0.2)
    ax.tick_params(axis="x", labelrotation=45)
    export(fig, "raw_q2_box_deadline_mix", (7.2, 3.6))


def raw_q3():
    data = rows("通信链路参数")
    sensor, fade, system = data[5][4], data[6][4], data[3][4]
    transmit = {"transport": (data[7][4], data[8][4]),
                "access": (data[9][4], data[10][4]),
                "backhaul": (data[11][4], data[12][4]),
                "gateway": (data[13][4], data[14][4])}
    groups = [("运输—网关", "transport", "gateway"),
              ("运输—中继", "transport", "access"),
              ("中继—网关", "backhaul", "gateway")]
    values = []
    for _, a, b in groups:
        first, second = transmit[a], transmit[b]
        values.append(min(first[0] + first[1] + second[1],
                          second[0] + second[1] + first[1]) - sensor - fade - system)
    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    bars = ax.bar([x[0] for x in groups], values, color=["#315E9D", "#CE853D", "#69549A"])
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value + 0.5, f"{value:.0f}", ha="center")
    ax.set_ylim(0, max(values) * 1.15)
    ax.set_ylabel("原始参数推得双向允许损耗 / dB")
    ax.grid(axis="y", alpha=0.2)
    export(fig, "raw_q3_link_budgets", (5.8, 3.2))


def raw_q4():
    transport = rows("运输无人机数据")
    relay = rows("中继无人机数据")
    labels = ["A机", "B机", "C机", "A电池", "B电池", "C电池", "R机", "R组件"]
    values = [sum(row[1] == g for row in transport[8:16]) for g in "ABC"]
    values += [transport[i][1] for i in range(19, 22)]
    values += [len(relay[6:8]), relay[11][1]]
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    bars = ax.bar(labels, values, color=["#315E9D"]*3 + ["#CE853D"]*3 + ["#69549A"]*2)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value + 0.1, str(value), ha="center")
    ax.set_ylim(0, max(values) * 1.2)
    ax.set_ylabel("原始可用库存 / 件或组")
    ax.grid(axis="y", alpha=0.2)
    export(fig, "raw_q4_initial_inventory", (6.2, 3.3))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    raw_q2()
    raw_q3()
    raw_q4()
