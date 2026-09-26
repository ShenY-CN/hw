"""问题一论文图：空间场景、安全载荷、单次航程能耗和返航余量。"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]

import numpy as np
from mountain_flood.figure.common import (
    COLORS, FLIGHT_TIME_CMAP, Model, NEUTRAL, draw_region, load_result, save_figure,
)
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def plot_region(model):
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    draw_region(ax, model, annotate=False, view="township")
    ax.legend(handles=[
        Line2D([0], [0], color="#B66A50", linewidth=1, label="主要道路"),
        Line2D([0], [0], color="#2878A8", linewidth=1, label="河流/溪流"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor="#7B3294",
               label="镇龙乡镇点"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#555555",
               label="村庄点位"),
        Line2D([0], [0], marker="*", color="black", label="调度中心"),
        Line2D([0], [0], marker="o", color=NEUTRAL, markerfacecolor="white",
               label="服务区"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=7, ncol=3)
    save_figure(fig, "q1_dem_nodes")


def plot_safe_capacity(data):
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    offsets = {"A": -0.2, "B": 0, "C": 0.2}
    markers = {"A": "o", "B": "s", "C": "^"}
    for drone_type, color in COLORS.items():
        rows = [row for row in data["capacities"] if row["g"] == drone_type]
        rows.sort(key=lambda row: row["node"])
        ax.scatter([row["node"] + offsets[drone_type] for row in rows],
                   [row["maxload"] for row in rows], color=color,
                   marker=markers[drone_type], label=f"{drone_type}型", s=34)
    ax.set_xticks(range(1, 16), [f"{node:03}" for node in range(1, 16)])
    ax.set_xlabel("服务区编号")
    ax.set_ylabel("最大安全载荷 / kg")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(ncol=3)
    save_figure(fig, "q1_safe_capacity")


def plot_capacity_heatmap(data):
    drone_types = list(COLORS)
    matrix = np.zeros((len(drone_types), 15))
    for row in data["capacities"]:
        matrix[drone_types.index(row["g"]), row["node"] - 1] = row["maxload"]
    fig, ax = plt.subplots(figsize=(8.2, 2.8))
    image = ax.imshow(matrix, aspect="auto", cmap=FLIGHT_TIME_CMAP)
    ax.set_yticks(range(len(drone_types)), [f"{drone_type}型" for drone_type in drone_types])
    ax.set_xticks(range(15), [f"{node:03}" for node in range(1, 16)])
    ax.set_xlabel("服务区编号")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            ax.text(column, row, f"{matrix[row, column]:.0f}",
                    ha="center", va="center", fontsize=7,
                    color="white" if matrix[row, column] > matrix.max() * 0.62 else "black")
    fig.colorbar(image, ax=ax, label="最大安全载荷 / kg", pad=0.02)
    save_figure(fig, "q1_capacity_heatmap")


def plot_typical_elevation_profile(model, data):
    """沿最长组批路线重建飞行高度与 DEM 地面的剖面。"""
    def route_distance(route):
        nodes = [0] + route["order"] + [0]
        return sum(model.D[first, second] for first, second in zip(nodes, nodes[1:]))

    route = max(data["routes"], key=route_distance)
    distances, flight_altitude, ground_altitude = [], [], []
    offset = 0.0
    for segment in route["segments"]:
        start, end = segment["a"], segment["b"]
        horizontal_length = model.geo.inv(start[0], start[1], end[0], end[1])[2]
        fractions = np.linspace(0, 1, max(2, int(horizontal_length / 180) + 2))
        if distances:
            fractions = fractions[1:]
        longitude = start[0] + (end[0] - start[0]) * fractions
        latitude = start[1] + (end[1] - start[1]) * fractions
        distances.extend((offset + horizontal_length * fractions) / 1000)
        flight_altitude.extend(start[2] + (end[2] - start[2]) * fractions)
        ground_altitude.extend(model.ground(longitude, latitude))
        offset += horizontal_length

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.fill_between(distances, ground_altitude, color="#B8B8B8", alpha=0.65,
                    label="DEM 地面高程")
    ax.plot(distances, flight_altitude, color=COLORS["A"], linewidth=1.5,
            label="无人机飞行高度")
    ax.set_xlabel("沿航段累计水平距离 / km")
    ax.set_ylabel("高程 / m")
    ax.legend()
    ax.grid(alpha=0.2)
    save_figure(fig, "q1_typical_elevation_profile")


def plot_payload_energy(model, data):
    """最远服务区的载荷—往返能耗关系（终稿版：加大图高与字号，临界线更醒目）。"""
    farthest = int(np.argmax(model.D[0, 1:]) + 1)
    capacities = {(row["g"], row["node"]): row["maxload"]
                  for row in data["capacities"]}
    figure, axes = plt.subplots(1, 3, figsize=(9.4, 3.9), sharey=True)
    for ax, (drone_type, spec) in zip(axes, model.types.items()):
        payloads = np.linspace(0, spec["Q"], 80)
        energies = [model.energy(drone_type, 0, farthest, payload)
                    + model.energy(drone_type, farthest, 0, 0)
                    for payload in payloads]
        cap = capacities[(drone_type, farthest)]
        ax.plot(payloads, energies, color=COLORS[drone_type], linewidth=1.7)
        ax.axhline(0.8 * spec["E"], color=NEUTRAL, linestyle="--", linewidth=1.4,
                   alpha=0.95, label="20%返航储备下的可用能量")
        ax.axvline(cap, color=COLORS["C"], linestyle=":", linewidth=1.6,
                   alpha=0.95, label=f"最大安全载荷 {cap:.1f} kg")
        ax.set_title(f"{drone_type}型", fontsize=11)
        ax.set_xlabel("载荷 / kg", fontsize=10)
        ax.tick_params(labelsize=9.5)
        ax.grid(alpha=0.22)
    axes[0].set_ylabel(f"往返飞行能耗 / kWh（服务区 S{farthest:03}）", fontsize=10)
    axes[0].legend(fontsize=7.5, loc="upper left")
    save_figure(figure, "q1_payload_energy")


def plot_objective_solutions():
    energy_solution = load_result("q1_energy.json")["summary"]
    time_solution = load_result("q1_time.json")["summary"]
    rows = [("最小能耗方案", energy_solution), ("最短时间方案", time_solution)]
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    for (label, summary), color in zip(rows, (COLORS["A"], COLORS["B"])):
        ax.scatter(summary["energy"], summary["time"] / 60, s=70,
                   color=color, label=label)
        ax.annotate(label, (summary["energy"], summary["time"] / 60),
                    xytext=(5, 5), textcoords="offset points", fontsize=8)
    ax.set_xlabel("总能耗 / kWh")
    ax.set_ylabel("总飞行时间 / min")
    ax.grid(alpha=0.2)
    ax.legend()
    save_figure(fig, "q1_objective_solutions")


RHO_FEASIBLE_LIMIT = 35.2678
# 25%/35% 两点取自论文表 5-6 的定稿数值：仓库 results/ 仅有 rho10/20/30/40 正式结果文件，
# 无 q1_rho25.json / q1_rho35.json，故此处只引用已定稿数值，不重新求解、不插值。
SENSITIVITY_TABLE_POINTS = {25: {"count": 19, "energy": 61.0734},
                            35: {"count": 25, "energy": 75.6076}}


def _sensitivity_series():
    reserves = (10, 20, 25, 30, 35)
    counts, energies = [], []
    for reserve in reserves:
        if reserve in SENSITIVITY_TABLE_POINTS:
            point = SENSITIVITY_TABLE_POINTS[reserve]
            counts.append(point["count"])
            energies.append(point["energy"])
        else:
            summary = load_result(f"q1_rho{reserve}.json")["summary"]
            counts.append(summary["count"])
            energies.append(summary["energy"])
    return reserves, counts, energies


def plot_sensitivity():
    """图9-1：返航安全余量对最少架次与总能耗的影响（终稿版，含 25%/35% 与可行边界）。"""
    reserves, counts, energies = _sensitivity_series()
    figure, axes = plt.subplots(1, 2, figsize=(7.6, 3.5))
    axes[0].plot(reserves, counts, marker="o", markersize=5.5, linewidth=1.5,
                 color=COLORS["A"])
    axes[1].plot(reserves, energies, marker="s", markersize=5.5, linewidth=1.5,
                 color=COLORS["B"])
    for ax, values in zip(axes, (counts, energies)):
        ax.axvspan(RHO_FEASIBLE_LIMIT, max(reserves) + 2, color="#D9A0A0", alpha=0.18,
                   zorder=0)
        ax.axvline(RHO_FEASIBLE_LIMIT, color="#8C3B3B", linestyle="--", linewidth=1.2,
                   zorder=1)
        ax.annotate("整体可行边界 ≈35.27%", xy=(RHO_FEASIBLE_LIMIT, ax.get_ylim()[1]),
                    xytext=(-6, -12), textcoords="offset points", ha="right",
                    fontsize=8, color="#8C3B3B")
        ax.set_xlabel("返航安全余量 / %", fontsize=10)
        ax.set_xticks(reserves)
        ax.tick_params(labelsize=9.5)
        ax.grid(alpha=0.22)
    for xvalue, value in zip(reserves, counts):
        axes[0].annotate(f"{value}", (xvalue, value), xytext=(0, 6),
                         textcoords="offset points", ha="center", fontsize=8)
    for xvalue, value in zip(reserves, energies):
        axes[1].annotate(f"{value:.2f}", (xvalue, value), xytext=(0, 6),
                         textcoords="offset points", ha="center", fontsize=8)
    axes[0].set_ylabel("最少架次", fontsize=10)
    axes[1].set_ylabel("总能耗 / kWh", fontsize=10)
    save_figure(figure, "q1_sensitivity")


def plot_sensitivity_compact():
    """图9-1 备选版：仅使用 results/ 中 10%/20%/30% 正式结果文件。"""
    reserves = (10, 20, 30)
    summaries = [load_result(f"q1_rho{reserve}.json")["summary"] for reserve in reserves]
    figure, axes = plt.subplots(1, 2, figsize=(7.0, 3.3))
    axes[0].plot(reserves, [summary["count"] for summary in summaries],
                 marker="o", markersize=5.5, linewidth=1.5, color=COLORS["A"])
    axes[1].plot(reserves, [summary["energy"] for summary in summaries],
                 marker="s", markersize=5.5, linewidth=1.5, color=COLORS["B"])
    for ax in axes:
        ax.set_xlabel("返航安全余量 / %", fontsize=10)
        ax.set_xticks(reserves)
        ax.tick_params(labelsize=9.5)
        ax.grid(alpha=0.22)
    axes[0].set_ylabel("最少架次", fontsize=10)
    axes[1].set_ylabel("总能耗 / kWh", fontsize=10)
    save_figure(figure, "q1_sensitivity_compact")


def plot_return_soc(data, model):
    """问题一 18 个架次的返航剩余电量（终稿版：突出 20% 安全线与最紧架次）。"""
    routes = sorted(data["routes"], key=lambda row: (row["g"], row["order"][0]))
    figure, ax = plt.subplots(figsize=(7.4, 3.9))
    positions = np.arange(1, len(routes) + 1)
    socs = np.array([route["soc"] * 100 for route in routes])
    tight = int(np.argmin(socs))
    for drone_type, color in COLORS.items():
        selected = [(positions[index], socs[index])
                    for index, route in enumerate(routes) if route["g"] == drone_type]
        if selected:
            ax.scatter([item[0] for item in selected], [item[1] for item in selected],
                       color=color, label=f"{drone_type}型", s=42, zorder=3)
    ax.axhline(20, color=COLORS["C"], linestyle="--", linewidth=1.6,
               label="返航安全线 20%")
    ax.scatter([positions[tight]], [socs[tight]], s=170, facecolor="none",
               edgecolor="black", linewidth=1.2, zorder=4,
               label=f"最紧架次 {socs[tight]:.4f}%")
    ax.annotate(f"最低返航 SOC {socs[tight]:.4f}%",
                (positions[tight], socs[tight]), xytext=(10, 16),
                textcoords="offset points", fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="black", linewidth=0.8))
    ax.set_xticks(positions, [f"S{route['order'][0]:03}" for route in routes],
                  rotation=45, ha="right", fontsize=8)
    ax.set_xlabel("问题一运输架次（按机型、服务区排序）", fontsize=10)
    ax.set_ylabel("返航剩余电量 / %", fontsize=10)
    ax.set_ylim(bottom=0)
    ax.tick_params(axis="y", labelsize=9.5)
    ax.grid(axis="y", alpha=0.22)
    ax.legend(ncol=2, fontsize=8)
    save_figure(figure, "q1_return_soc")


def run():
    model = Model()
    data = load_result("q1_rho20.json")
    plot_region(model)
    plot_safe_capacity(data)
    plot_capacity_heatmap(data)
    plot_typical_elevation_profile(model, data)
    plot_payload_energy(model, data)
    plot_objective_solutions()
    plot_sensitivity()
    plot_return_soc(data, model)


if __name__ == "__main__":
    run()
