"""问题四论文图：两类任务分区、工作量、资源需求与库存缺口。"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]

from mountain_flood.figure.common import (
    COLORS, GROUP_COLORS, Model, NEUTRAL, draw_region, load_result, save_figure,
)
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patheffects
from matplotlib.patches import Polygon
from scipy.spatial import ConvexHull


def _plot_partition_map(model, groups, group_count):
    """两组/三组分区图（终稿版：放大地图与标签、精简图例、组内加淡色范围）。"""
    figure, ax = plt.subplots(figsize=(6.4, 4.7))
    draw_region(ax, model, annotate=False, show_services=False, terrain_alpha=0.6)
    markers = ["o", "s", "^"]
    for index, group in enumerate(groups):
        nodes = group["nodes"]
        xy = model.xy[nodes] / 1000
        color = GROUP_COLORS[index]
        if len(nodes) >= 3:
            hull = xy[ConvexHull(xy).vertices]
            ax.add_patch(Polygon(hull, closed=True, facecolor=color, alpha=0.12,
                                 edgecolor=color, linewidth=0.7, zorder=1))
        ax.scatter(xy[:, 0], xy[:, 1], color=color, marker=markers[index], s=72,
                   edgecolor="white", linewidth=0.6,
                   label=f"第{index + 1}组（{group['boxes']}箱）", zorder=4)
        for node, (x, y) in zip(nodes, xy):
            label = ax.annotate(f"S{node:03}", (x, y), xytext=(4, 5),
                                textcoords="offset points", fontsize=8.5, zorder=5)
            label.set_path_effects([patheffects.withStroke(linewidth=1.8,
                                                          foreground="white")])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), fontsize=8.5,
              ncol=group_count)
    save_figure(figure, f"q4_partition_{group_count}groups")


def plot_resource_demand(data, inventory):
    """独立执行资源需求与库存（终稿版：缺口资源柱顶直接标 +n）。"""
    labels = ["A型机", "B型机", "C型机", "A型电池", "B型电池", "C型电池",
              "中继无人机", "中继能源组件"]
    x = np.arange(len(labels))
    width = 0.24
    figure, ax = plt.subplots(figsize=(9.2, 4.2))
    for index, group_count in enumerate((2, 3)):
        selected = data["schemes"][str(group_count)]["selected"]
        total = selected["total"]
        deficit = selected["deficit"]
        color = (COLORS["A"], COLORS["B"])[index]
        positions = x + (index - 0.5) * width
        ax.bar(positions, total, width, label=f"{group_count}组需求", color=color)
        for position, value, lack in zip(positions, total, deficit):
            if lack > 0:
                ax.annotate(f"+{lack}", (position, value), xytext=(0, 4),
                            textcoords="offset points", ha="center", fontsize=8.5,
                            fontweight="bold", color=color, zorder=5)
    ax.scatter(x, inventory, marker="D", color=NEUTRAL, s=32, label="现有库存", zorder=4)
    ax.set_xticks(x, labels, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("资源数量", fontsize=10)
    ax.set_ylim(0, max(max(data["schemes"][str(count)]["selected"]["total"])
                       for count in (2, 3)) * 1.22)
    ax.tick_params(axis="y", labelsize=9.5)
    ax.grid(axis="y", alpha=0.22)
    ax.legend(fontsize=8.5)
    save_figure(figure, "q4_resource_demand")


def plot_workload(data):
    """两组/三组工作量对比（终稿版：统一纵轴、纵轴名称与论文定义一致）。"""
    figure, axes = plt.subplots(1, 2, figsize=(7.6, 3.7), sharey=True)
    panels = []
    for group_count in (2, 3):
        selected = data["schemes"][str(group_count)]["selected"]
        panels.append((group_count, selected))
    top = max(group["work"] / 3600 for _, selected in panels
              for group in selected["groups"]) * 1.22
    for ax, (group_count, selected) in zip(axes, panels):
        groups = selected["groups"]
        index = np.arange(len(groups))
        bars = ax.bar(index, [group["work"] / 3600 for group in groups],
                      color=[GROUP_COLORS[i] for i in index])
        ax.set_xticks(index, [f"第{i + 1}组" for i in index])
        ax.set_title(f"{group_count}组方案", fontsize=11)
        ax.set_ylim(0, top)
        ax.tick_params(labelsize=9.5)
        ax.grid(axis="y", alpha=0.22)
        ax.annotate(f"CV = {selected['cv']:.4f}", xy=(0.98, 0.95),
                    xycoords="axes fraction", ha="right", va="top", fontsize=8.5,
                    color=NEUTRAL)
        for bar, group in zip(bars, groups):
            ax.annotate(f"{group['boxes']}箱", (bar.get_x() + bar.get_width() / 2,
                        bar.get_height()), xytext=(0, 4), textcoords="offset points",
                        ha="center", fontsize=8)
    axes[0].set_ylabel("累计运输任务时长 / h", fontsize=10)
    save_figure(figure, "q4_workload")


def plot_resource_deficit(data, inventory):
    labels = ["A型机", "B型机", "C型机", "A型电池", "B型电池", "C型电池",
              "中继无人机", "中继能源组件"]
    x = np.arange(len(labels))
    width = 0.34
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    for index, group_count in enumerate((2, 3)):
        deficit = data["schemes"][str(group_count)]["selected"]["deficit"]
        ax.bar(x + (index - 0.5) * width, deficit, width,
               label=f"{group_count}组方案的库存缺口",
               color=(COLORS["A"], COLORS["B"])[index])
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.set_ylabel("缺少数量")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(fontsize=8)
    save_figure(fig, "q4_resource_deficit")


def plot_task_network(model, data, q3):
    """不可拆服务区组件（终稿版：各组件直接标 C1–C8，颜色仅作辅助）。"""
    edge_counts = {}
    for route in q3["routes"]:
        order = route["order"]
        for start, end in zip(order, order[1:]):
            edge = tuple(sorted((start, end)))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    figure, ax = plt.subplots(figsize=(6.8, 5.0))
    draw_region(ax, model, annotate=False, show_services=False, terrain_alpha=0.6)
    for (start, end), count in edge_counts.items():
        first, second = model.xy[start] / 1000, model.xy[end] / 1000
        ax.plot([first[0], second[0]], [first[1], second[1]],
                color="#888888", linewidth=0.8 + 0.35 * count, alpha=0.45, zorder=1)
    markers = ["o", "s", "^", "D", "v", "P", "X", "<"]
    for component_id, component in enumerate(data["components"]):
        xy = model.xy[component] / 1000
        ax.scatter(xy[:, 0], xy[:, 1], s=52, marker=markers[component_id % len(markers)],
                   label=f"组件{component_id + 1}", zorder=2)
        centroid = xy.mean(axis=0)
        label = ax.annotate(f"C{component_id + 1}", centroid, xytext=(0, 0),
                            textcoords="offset points", ha="center", va="center",
                            fontsize=10, fontweight="bold", color="#101820", zorder=8)
        label.set_path_effects([patheffects.withStroke(linewidth=2.4,
                                                      foreground="white")])
    for node in range(1, len(model.nodes)):
        x, y = model.xy[node] / 1000
        label = ax.annotate(f"S{node:03}", (x, y), xytext=(4, 4),
                            textcoords="offset points", fontsize=7.5, zorder=6)
        label.set_path_effects([patheffects.withStroke(linewidth=1.5,
                                                      foreground="white")])
    ax.annotate("O01", (0, 0), xytext=(5, 4), textcoords="offset points", fontsize=9,
                zorder=7)
    ax.set_aspect("equal")
    ax.set_xlabel("东向距离 / km", fontsize=10)
    ax.set_ylabel("北向距离 / km", fontsize=10)
    ax.tick_params(labelsize=9)
    ax.legend(ncol=4, fontsize=6.8, loc="upper center", bbox_to_anchor=(0.5, 1.14))
    ax.grid(alpha=0.15)
    save_figure(figure, "q4_task_network")


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
