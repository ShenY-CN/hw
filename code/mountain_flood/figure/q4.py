"""问题四论文图：两类任务分区、工作量、资源需求与库存缺口。"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]

from mountain_flood.figure.common import COLORS, Model, draw_region, load_result, save_figure
import matplotlib.pyplot as plt
import numpy as np


def _plot_partition_map(model, groups, group_count):
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    draw_region(ax, model, annotate=False)
    markers = ["o", "s", "^"]
    for index, group in enumerate(groups):
        nodes = group["nodes"]
        xy = model.xy[nodes] / 1000
        color = list(COLORS.values())[index]
        ax.scatter(xy[:, 0], xy[:, 1], color=color, marker=markers[index],
                   s=48, label=f"第{index + 1}组")
        for node, (x, y) in zip(nodes, xy):
            ax.annotate(f"{node:03}", (x, y), xytext=(3, 4),
                        textcoords="offset points", fontsize=7)
    ax.legend(loc="best", fontsize=8)
    save_figure(fig, f"q4_partition_{group_count}groups")


def plot_resource_demand(data, inventory):
    labels = ["A型机", "B型机", "C型机", "A型电池", "B型电池", "C型电池",
              "中继无人机", "中继电池"]
    x = np.arange(len(labels))
    width = 0.24
    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    for index, group_count in enumerate((2, 3)):
        total = data["schemes"][str(group_count)]["selected"]["total"]
        ax.bar(x + (index - 0.5) * width, total, width,
               label=f"{group_count}组需求", color=("#0072B2", "#D55E00")[index])
    ax.scatter(x, inventory, marker="D", color="#222222", s=28, label="现有库存", zorder=4)
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylabel("资源数量")
    ax.grid(axis="y", alpha=0.2)
    ax.legend()
    save_figure(fig, "q4_resource_demand")


def plot_workload(data):
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.4))
    for ax, group_count in zip(axes, (2, 3)):
        selected = data["schemes"][str(group_count)]["selected"]
        groups = selected["groups"]
        index = np.arange(len(groups))
        bars = ax.bar(index, [group["work"] / 3600 for group in groups],
               color=[list(COLORS.values())[i] for i in index])
        ax.set_xticks(index, [f"第{i + 1}组" for i in index])
        ax.set_title(f"{group_count}组方案")
        ax.set_ylabel("累计飞行工作时长 / h")
        ax.grid(axis="y", alpha=0.2)
        for bar, group in zip(bars, groups):
            ax.annotate(f"{group['boxes']}箱", (bar.get_x() + bar.get_width() / 2,
                        bar.get_height()), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=7)
    save_figure(fig, "q4_workload")


def plot_resource_deficit(data, inventory):
    labels = ["A型机", "B型机", "C型机", "A型电池", "B型电池", "C型电池",
              "中继无人机", "中继电池"]
    x = np.arange(len(labels))
    width = 0.34
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    for index, group_count in enumerate((2, 3)):
        deficit = data["schemes"][str(group_count)]["selected"]["deficit"]
        ax.bar(x + (index - 0.5) * width, deficit, width,
               label=f"{group_count}组方案的库存缺口",
               color=("#0072B2", "#D55E00")[index])
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylabel("缺少数量")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(fontsize=8)
    save_figure(fig, "q4_resource_deficit")


def plot_task_network(model, data, q3):
    """用第三问已固定的路线关联关系展示不可拆分服务区组件。"""
    edge_counts = {}
    for route in q3["routes"]:
        order = route["order"]
        for start, end in zip(order, order[1:]):
            edge = tuple(sorted((start, end)))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    for (start, end), count in edge_counts.items():
        first, second = model.xy[start] / 1000, model.xy[end] / 1000
        ax.plot([first[0], second[0]], [first[1], second[1]],
                color="#888888", linewidth=0.8 + 0.35 * count, alpha=0.45, zorder=1)
    markers = ["o", "s", "^", "D", "v", "P", "X", "<"]
    for component_id, component in enumerate(data["components"]):
        xy = model.xy[component] / 1000
        ax.scatter(xy[:, 0], xy[:, 1], s=45, marker=markers[component_id % len(markers)],
                   label=f"组件{component_id + 1}", zorder=2)
    for node in range(1, len(model.nodes)):
        x, y = model.xy[node] / 1000
        ax.annotate(f"{node:03}", (x, y), xytext=(3, 4),
                    textcoords="offset points", fontsize=7)
    ax.scatter(0, 0, marker="*", s=100, color="black", label="调度中心", zorder=3)
    ax.set_aspect("equal")
    ax.set_xlabel("东向距离 / km")
    ax.set_ylabel("北向距离 / km")
    ax.legend(ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    ax.grid(alpha=0.15)
    save_figure(fig, "q4_task_network")


def run():
    model = Model()
    data = load_result("q4.json")
    q3 = load_result("q3.json")
    for group_count in (2, 3):
        selected = data["schemes"][str(group_count)]["selected"]
        _plot_partition_map(model, selected["groups"], group_count)
    plot_resource_demand(data, data["inventory"])
    plot_workload(data)
    plot_resource_deficit(data, data["inventory"])
    plot_task_network(model, data, q3)


if __name__ == "__main__":
    run()
