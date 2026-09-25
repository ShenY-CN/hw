"""问题二论文图：运输路线、资源排程、时限表现和搜索方法比较。"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]

from mountain_flood.figure.common import COLORS, Model, charge_duration, draw_region, load_result, save_figure
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


METHOD_COLORS = {
    "grasp": "#0072B2", "hill": "#D55E00", "anneal": "#009E73",
    "tabu": "#CC79A7", "existing_baseline": "#555555",
}
METHOD_LABELS = {
    "grasp": "随机化构造", "hill": "局部爬山", "anneal": "模拟退火",
    "tabu": "禁忌搜索", "existing_baseline": "既有可行方案",
}


def plot_routes(model, data):
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    draw_region(ax, model)
    for route in data["routes"]:
        points = model.xy[[0] + route["order"] + [0]] / 1000
        ax.plot(points[:, 0], points[:, 1], color=COLORS[route["g"]], lw=1, alpha=0.7)
    ax.legend(handles=[Line2D([0], [0], color=color, label=f"{drone_type}型航线")
                       for drone_type, color in COLORS.items()],
              loc="lower left", fontsize=8)
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


def plot_battery_timeline(model, data):
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
    save_figure(fig, "q2_battery_timeline")


def plot_deadlines(model, data):
    rows = []
    for route in data["routes"]:
        for box_key, relative_delivery in route["deliver"].items():
            box_index = int(box_key)
            box = model.boxes[box_index]
            rows.append((box_index, route["start"] + relative_delivery,
                         box["due"], box["first"], box["deadline"]))
    rows.sort(key=lambda row: row[0])
    actual = np.array([row[1] / 60 for row in rows])
    stated_due = np.array([row[4] / 60 for row in rows])
    first_batch = np.array([row[3] for row in rows], dtype=bool)
    fig, ax = plt.subplots(figsize=(5.4, 4.5))
    ax.scatter(stated_due[~first_batch], actual[~first_batch], s=20,
               color="#0072B2", label="其他货箱")
    ax.scatter(stated_due[first_batch], actual[first_batch], s=27,
               marker="*", color="#D55E00", label="首批保障货箱")
    maximum = max(float(actual.max()), float(stated_due.max()))
    ax.plot([0, maximum], [0, maximum], color="#555555", linestyle="--",
            linewidth=1, label="按时送达边界")
    ax.set_xlabel("最晚允许送达时刻 / min")
    ax.set_ylabel("实际送达时刻 / min")
    ax.grid(alpha=0.2)
    ax.legend()
    save_figure(fig, "q2_delivery_deadlines")


def plot_return_soc(data):
    routes = sorted(data["routes"], key=lambda route: route["id"])
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    x = np.arange(len(routes))
    ax.bar(x, [route["soc"] * 100 for route in routes],
           color=[COLORS[route["g"]] for route in routes])
    ax.axhline(20, color="#D55E00", linestyle="--", linewidth=1,
               label="最低返航储备 20%")
    ax.set_xticks(x, [route["id"] for route in routes], rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("返航剩余电量 / %")
    ax.set_xlabel("运输架次")
    ax.legend()
    ax.grid(axis="y", alpha=0.2)
    save_figure(fig, "q2_return_soc")


def plot_search_comparison(model):
    comparison = load_result("method_comparison.json")
    total_priority = sum(box["priority"] for box in model.boxes)
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    for method, label in METHOD_LABELS.items():
        candidates = [item for item in comparison["candidates"]
                      if item["method"] == method and item["validation"]["pass_"]]
        if not candidates:
            continue
        energy = [item["metrics"]["energy"] for item in candidates]
        weighted_arrival = [item["metrics"]["weighted_arrival"] / total_priority / 60
                            for item in candidates]
        makespan = [item["metrics"]["makespan"] / 60 for item in candidates]
        axes[0].scatter(energy, weighted_arrival, color=METHOD_COLORS[method],
                        s=42, label=label, alpha=0.85)
        axes[1].scatter(energy, makespan, color=METHOD_COLORS[method],
                        s=42, label=label, alpha=0.85)
        for item, x, y1, y2 in zip(candidates, energy, weighted_arrival, makespan):
            if item["selected"]:
                for ax, y in ((axes[0], y1), (axes[1], y2)):
                    ax.scatter([x], [y], facecolors="none", edgecolors="black",
                               s=130, linewidths=1.2, zorder=5)
    axes[0].set_xlabel("运输能耗 / kWh")
    axes[0].set_ylabel("优先加权平均送达时刻 / min")
    axes[1].set_xlabel("运输能耗 / kWh")
    axes[1].set_ylabel("最晚返航时刻 / min")
    for ax in axes:
        ax.grid(alpha=0.2)
    axes[0].legend(fontsize=7, loc="best")
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
    plot_search_comparison(model)
    plot_route_energy(data)


if __name__ == "__main__":
    run()
