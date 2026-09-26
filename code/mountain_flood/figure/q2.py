"""问题二论文图：运输路线、资源排程、时限表现和搜索方法比较。"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]

from mountain_flood.figure.common import (
    COLORS, Model, NEUTRAL, charge_duration, draw_region, load_result, save_figure,
)
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


METHOD_COLORS = {
    "grasp": COLORS["A"], "hill": COLORS["B"], "anneal": "#258A91",
    "tabu": "#69549A", "existing_baseline": NEUTRAL,
}
METHOD_LABELS = {
    "grasp": "随机化构造", "hill": "局部爬山", "anneal": "模拟退火",
    "tabu": "禁忌搜索", "existing_baseline": "局部爬山（前轮归档）",
}


def plot_routes(model, data):
    """问题二 24 架次航线（终稿版：弱化单站、突出多站并加方向箭头）。"""
    figure, ax = plt.subplots(figsize=(6.8, 4.7))
    draw_region(ax, model, terrain_alpha=0.55, service_label_size=7.5,
                service_marker_size=26)
    single = [route for route in data["routes"] if len(route["order"]) == 1]
    multi = [route for route in data["routes"] if len(route["order"]) > 1]
    for route in single:
        points = model.xy[[0] + route["order"] + [0]] / 1000
        ax.plot(points[:, 0], points[:, 1], color=COLORS[route["g"]],
                linewidth=0.7, alpha=0.28, zorder=3)
    for route in multi:
        points = model.xy[[0] + route["order"] + [0]] / 1000
        ax.plot(points[:, 0], points[:, 1], color=COLORS[route["g"]],
                linewidth=1.7, alpha=0.95, zorder=5)
        for first, second in zip(points[:-1], points[1:]):
            ax.annotate("", xy=second, xytext=first,
                        arrowprops=dict(arrowstyle="-|>", color=COLORS[route["g"]],
                                        linewidth=0.9, alpha=0.9,
                                        shrinkA=3, shrinkB=3), zorder=6)
    handles = [Line2D([0], [0], color=color, label=f"{drone_type}型航线")
               for drone_type, color in COLORS.items()]
    handles.append(Line2D([0], [0], color=NEUTRAL, linewidth=1.7, label="多站航次（含方向箭头）"))
    handles.append(Line2D([0], [0], color=NEUTRAL, linewidth=0.7, alpha=0.35, label="单站航次"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.11),
              fontsize=8, ncol=5)
    save_figure(figure, "q2_transport_routes")


def plot_drone_timeline(data):
    routes = data["routes"]
    units = sorted({route["unit"] for route in routes})
    unit_index = {unit: index for index, unit in enumerate(units)}
    fig, ax = plt.subplots(figsize=(8.0, max(3.8, 0.32 * len(units))))
    for route in routes:
        lane = unit_index[route["unit"]]
        start, end = route["start"] / 60, route["end"] / 60
        ax.barh(lane, end - start, left=start, height=0.64,
                color=COLORS[route["g"]], edgecolor="white", linewidth=0.4)
        ax.text((start + end) / 2, lane, route["id"], ha="center", va="center",
                fontsize=6.5, color="white")
    ax.set_yticks(range(len(units)), units)
    ax.invert_yaxis()
    ax.set_xlabel("时刻 / min")
    ax.set_ylabel("运输无人机")
    ax.grid(axis="x", alpha=0.2)
    save_figure(fig, "q2_drone_timeline")


def plot_battery_timeline(model, data, figure_name="q2_battery_timeline"):
    """共享电池占用（终稿版：任务/充电/空闲三态在打印后仍可区分）。"""
    routes = data["routes"]
    batteries = sorted({route["battery"] for route in routes})
    battery_index = {battery: index for index, battery in enumerate(batteries)}
    horizon = max(route["end"] + charge_duration(model, route) for route in routes) / 60
    figure, ax = plt.subplots(figsize=(8.4, max(4.0, 0.34 * len(batteries))))
    for route in routes:
        lane = battery_index[route["battery"]]
        start, end = route["start"] / 60, route["end"] / 60
        charge_end = end + charge_duration(model, route) / 60
        ax.barh(lane, end - start, left=start, height=0.62,
                color=COLORS[route["g"]], edgecolor="white", linewidth=0.5, zorder=3)
        ax.barh(lane, charge_end - end, left=end, height=0.62,
                color="#C9CDD2", hatch="////", edgecolor="#5C6672", linewidth=0.5,
                zorder=3)
    ax.set_xlim(0, horizon * 1.02)
    ax.set_yticks(range(len(batteries)), batteries)
    ax.invert_yaxis()
    ax.set_xlabel("时刻 / min", fontsize=10)
    ax.set_ylabel("共享电池", fontsize=10)
    ax.tick_params(labelsize=9)
    ax.legend(handles=[Patch(facecolor="white", edgecolor="#5C6672", label="空闲"),
                       Patch(facecolor=COLORS["A"], label="运输任务占用"),
                       Patch(facecolor="#C9CDD2", hatch="////", edgecolor="#5C6672",
                             label="充电占用")],
              loc="best", fontsize=8)
    ax.grid(axis="x", alpha=0.2)
    save_figure(figure, figure_name)


def plot_deadlines(model, data):
    rows = []
    for route in data["routes"]:
        for box_key, relative_delivery in route["deliver"].items():
            box_index = int(box_key)
            box = model.boxes[box_index]
            rows.append((box_index, route["start"] + relative_delivery,
                         box["due"], box["first"], box["medical"], box["deadline"]))
    rows.sort(key=lambda row: row[0])
    actual = np.array([row[1] / 60 for row in rows])
    stated_due = np.array([(row[5] if row[5] < 1e8 else row[2]) / 60 for row in rows])
    medical = np.array([row[4] for row in rows], dtype=bool)
    first_batch = np.array([row[3] and not row[4] for row in rows], dtype=bool)
    ordinary = ~(medical | first_batch)
    fig, ax = plt.subplots(figsize=(5.4, 4.5))
    ax.scatter(stated_due[ordinary], actual[ordinary], s=20,
               color=COLORS["A"], label="其他物资（期望时刻）")
    ax.scatter(stated_due[first_batch], actual[first_batch], s=27,
               marker="*", color=COLORS["B"], label="首批保障（硬截止）")
    ax.scatter(stated_due[medical], actual[medical], s=27,
               marker="D", color=COLORS["C"], label="医疗物资（硬截止）")
    maximum = max(float(actual.max()), float(stated_due.max()))
    ax.plot([0, maximum], [0, maximum], color=NEUTRAL, linestyle="--",
            linewidth=1, label="时刻参照线")
    ax.set_xlabel("硬截止或期望送达时刻 / min")
    ax.set_ylabel("实际送达时刻 / min")
    ax.grid(alpha=0.2)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.99),
               ncol=2, fontsize=8)
    fig.subplots_adjust(top=0.77, left=0.14, right=0.97, bottom=0.14)
    save_figure(fig, "q2_delivery_deadlines", tight=False)


def plot_return_soc(data):
    """问题二逐架次返航电量（终稿版：突出最紧航次 T010 与 20% 安全线）。"""
    routes = sorted(data["routes"], key=lambda route: route["id"])
    socs = [route["soc"] * 100 for route in routes]
    tight = int(np.argmin(socs))
    figure, ax = plt.subplots(figsize=(7.8, 3.7))
    x = np.arange(len(routes))
    ax.bar(x, socs, color=[COLORS[route["g"]] for route in routes],
           edgecolor=["black" if index == tight else "none" for index in range(len(routes))],
           linewidth=[1.5 if index == tight else 0 for index in range(len(routes))])
    ax.axhline(20, color=COLORS["C"], linestyle="--", linewidth=1.5,
               label="返航安全线 20%")
    ax.annotate(f"{routes[tight]['id']} 最低 {socs[tight]:.4f}%",
                (x[tight], socs[tight]), xytext=(12, 20), textcoords="offset points",
                fontsize=8.5, arrowprops=dict(arrowstyle="->", color="black", linewidth=0.8))
    ax.set_xticks(x, [route["id"] for route in routes], rotation=60, ha="right",
                  fontsize=7.5)
    ax.set_xlabel("运输架次", fontsize=10)
    ax.set_ylabel("返航剩余电量 / %", fontsize=10)
    ax.set_ylim(bottom=0)
    ax.tick_params(axis="y", labelsize=9.5)
    ax.grid(axis="y", alpha=0.22)
    ax.legend(fontsize=8)
    save_figure(figure, "q2_return_soc")


def plot_search_comparison():
    comparison = load_result("q2_formal_protocol.json")
    statistics = comparison["algorithm_statistics"]
    methods = ("grasp", "hill", "anneal", "tabu")
    panels = (
        ("makespan", "平均最晚返航 / min", 60),
        ("energy", "平均能耗 / kWh", 1),
        ("count", "平均运输架次 / 次", 1),
    )
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8))
    for ax, (metric, ylabel, scale) in zip(axes, panels):
        for index, method in enumerate(methods):
            summary = statistics[method][metric]
            ax.errorbar(
                index,
                summary["mean"] / scale,
                yerr=summary["std"] / scale,
                fmt="o",
                color=METHOD_COLORS[method],
                capsize=3,
                markersize=5,
            )
        ax.set_xticks(range(len(methods)), [METHOD_LABELS[m] for m in methods],
                      rotation=18, ha="right")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.2)
    fig.suptitle("四种搜索方法的10种子均值与总体标准差", y=1.02)
    save_figure(fig, "q2_search_comparison")


def plot_route_energy(data):
    routes = sorted(data["routes"], key=lambda route: route["id"])
    fig, ax = plt.subplots(figsize=(8.0, 3.7))
    positions = np.arange(len(routes))
    ax.bar(positions, [route["energy"] for route in routes],
           color=[COLORS[route["g"]] for route in routes])
    ax.set_xticks(positions, [route["id"] for route in routes], rotation=60, ha="right", fontsize=7)
    ax.set_xlabel("运输架次")
    ax.set_ylabel("架次能耗 / kWh")
    ax.grid(axis="y", alpha=0.2)
    save_figure(fig, "q2_route_energy")


def run():
    model = Model()
    data = load_result("q2.json")
    plot_routes(model, data)
    plot_drone_timeline(data)
    plot_battery_timeline(model, data)
    plot_deadlines(model, data)
    plot_return_soc(data)
    plot_search_comparison()
    plot_route_energy(data)


if __name__ == "__main__":
    run()
