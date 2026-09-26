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
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    draw_region(ax, model)
    for route in data["routes"]:
        points = model.xy[[0] + route["order"] + [0]] / 1000
        ax.plot(points[:, 0], points[:, 1], color=COLORS[route["g"]], lw=1, alpha=0.7)
    ax.legend(handles=[Line2D([0], [0], color=color, label=f"{drone_type}型航线")
                       for drone_type, color in COLORS.items()],
              loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=8, ncol=3)
    save_figure(fig, "q2_transport_routes")


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
    routes = data["routes"]
    batteries = sorted({route["battery"] for route in routes})
    battery_index = {battery: index for index, battery in enumerate(batteries)}
    fig, ax = plt.subplots(figsize=(8.0, max(3.8, 0.32 * len(batteries))))
    for route in routes:
        lane = battery_index[route["battery"]]
        start, end = route["start"] / 60, route["end"] / 60
        charge_end = end + charge_duration(model, route) / 60
        ax.barh(lane, end - start, left=start, height=0.62,
                color=COLORS[route["g"]], edgecolor="white", linewidth=0.4)
        ax.barh(lane, charge_end - end, left=end, height=0.62,
                color="#D9D9D9", hatch="///", edgecolor="white", linewidth=0.4)
    ax.set_yticks(range(len(batteries)), batteries)
    ax.invert_yaxis()
    ax.set_xlabel("时刻 / min")
    ax.set_ylabel("共享电池")
    ax.legend(handles=[Patch(color="#777777", label="运输任务"),
                       Patch(facecolor="#D9D9D9", hatch="///", label="充电")], loc="best")
    ax.grid(axis="x", alpha=0.2)
    save_figure(fig, figure_name)


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
    routes = sorted(data["routes"], key=lambda route: route["id"])
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    x = np.arange(len(routes))
    ax.bar(x, [route["soc"] * 100 for route in routes],
           color=[COLORS[route["g"]] for route in routes])
    ax.axhline(20, color=COLORS["C"], linestyle="--", linewidth=1,
               label="最低返航储备 20%")
    ax.set_xticks(x, [route["id"] for route in routes], rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("返航剩余电量 / %")
    ax.set_xlabel("运输架次")
    ax.legend()
    ax.grid(axis="y", alpha=0.2)
    save_figure(fig, "q2_return_soc")


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
