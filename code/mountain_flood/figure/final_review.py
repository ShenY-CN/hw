"""终稿图表专项：Q3 裕度包络、Q3 LOS 剖面，以及 13 张目标图的统一入口。"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from mountain_flood.figure.common import (
    COLORS, NEUTRAL, Model, load_result, save_figure,
)
from mountain_flood.problem3.communication import gateway


def margin_envelope(data, step=5.0):
    """按时间网格取区间最小通信裕度，构成时间下包络（只用正式结果文件）。"""
    intervals = sorted(data["communication"], key=lambda item: item["start"])
    lows = np.array([item["start"] for item in intervals])
    highs = np.array([item["end"] for item in intervals])
    margins = np.array([item["margin"] for item in intervals])
    tight_index = int(np.argmin(margins))
    grid = np.arange(lows.min(), highs.max(), step)
    grid = np.unique(np.append(grid, lows[tight_index]))
    values = []
    for moment in grid:
        inside = (lows <= moment) & (moment < highs)
        values.append(margins[inside].min() if inside.any() else np.nan)
    return grid / 60.0, np.asarray(values), float(margins[tight_index]), \
        float(lows[tight_index]) / 60.0


def plot_margin_envelope(data):
    """图7-4：连续通信证书裕度的时间下包络 + 最小裕度局部放大。"""
    minutes, envelope, minimum, minute_of_minimum = margin_envelope(data)
    figure, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.plot(minutes, envelope, color=COLORS["A"], linewidth=1.1,
            label="区间最小证书裕度（时间下包络）")
    ax.axhline(0, color=COLORS["C"], linestyle="--", linewidth=1.2,
               label="通信可行阈值 0 dB")
    ax.set_xlabel("时刻 / min", fontsize=10)
    ax.set_ylabel("通信证书裕量 / dB", fontsize=10)
    ax.tick_params(labelsize=9.5)
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8.5, loc="upper right")

    window = (minutes >= minute_of_minimum - 1.5) & (minutes <= minute_of_minimum + 1.5)
    inset = ax.inset_axes([0.50, 0.40, 0.47, 0.50])
    inset.plot(minutes[window], envelope[window], color=COLORS["A"], linewidth=1.5,
               marker="o", markersize=3)
    inset.axhline(0, color=COLORS["C"], linestyle="--", linewidth=1.0)
    top = float(np.nanmax(envelope[window])) if window.any() else 1.0
    inset.set_ylim(0, max(0.5, top * 1.35))
    inset.set_title(f"T021a 最小区间：最小证书裕度 = {minimum:.5f} dB", fontsize=8.5)
    inset.tick_params(labelsize=7.5)
    inset.grid(alpha=0.2)
    ax.indicate_inset_zoom(inset, edgecolor=NEUTRAL)
    save_figure(figure, "q3_margin_envelope")


def _aircraft_position(route, moment):
    elapsed = moment - route["start"]
    segment = next((item for item in route["segments"]
                    if item["start"] - 1e-6 <= elapsed <= item["end"] + 1e-6), None)
    if segment is None:
        raise ValueError("时刻不在该航次飞行区间内")
    span = segment["end"] - segment["start"]
    fraction = 0.0 if span <= 1e-12 else (elapsed - segment["start"]) / span
    first = np.asarray(segment["a"], dtype=float)
    second = np.asarray(segment["b"], dtype=float)
    return first + fraction * (second - first)


def los_profile(model, route, moment, step_m=1.0):
    """按模型自用规则采样端点连线的视线剖面（几何复算，不改变任何方案数值）。"""
    start = _aircraft_position(route, moment)
    end = np.asarray(gateway(model), dtype=float)
    distance = model.geo.inv(start[0], start[1], end[0], end[1])[2]
    # 与 Model.cells / Model.blocked 相同的规则：取连线与经纬网格线的全部交点，
    # 在每个像元内取中点，使最大遮挡高度与论文表 7-2 的 29.47 m 同口径。
    cuts, _ = model.cells(start[0], start[1], end[0], end[1])
    fractions = np.clip((cuts[:-1] + cuts[1:]) / 2.0, 0.0, 1.0)
    longitude = start[0] + (end[0] - start[0]) * fractions
    latitude = start[1] + (end[1] - start[1]) * fractions
    sight = start[2] + (end[2] - start[2]) * fractions
    terrain = model.ground(longitude, latitude)
    return distance * fractions, sight, terrain


def plot_tight_los_profile(model, certificate, data):
    """图7-5：最紧通信区间的 DEM 视线剖面，并标注最大遮挡高度。"""
    dense = certificate["tightest_dense"]
    route = next(item for item in data["routes"] if item["id"] == dense["route"])
    moment = dense["worst_time_s"]
    distance, sight, terrain = los_profile(model, route, moment)
    gap = terrain - sight
    worst = int(np.argmax(gap))
    figure, ax = plt.subplots(figsize=(7.4, 3.8))
    ax.fill_between(distance / 1000, terrain, color="#B8B8B8", alpha=0.7,
                    label="DEM 地面高程")
    ax.plot(distance / 1000, sight, color=COLORS["A"], linewidth=1.6,
            label="视线（运输机—网关）")
    ax.fill_between(distance / 1000, sight, terrain, where=(gap > 0),
                    color=COLORS["C"], alpha=0.30, label="地形高于视线（计 10 dB 遮挡）")
    ax.annotate(f"最大遮挡约 {gap[worst]:.2f} m",
                (distance[worst] / 1000, terrain[worst]), xytext=(12, 16),
                textcoords="offset points", fontsize=8.5,
                arrowprops=dict(arrowstyle="->", color="black", linewidth=0.8))
    ax.set_xlabel("沿视线距离 / km", fontsize=10)
    ax.set_ylabel("高程 / m", fontsize=10)
    ax.tick_params(labelsize=9.5)
    ax.grid(alpha=0.22)
    ax.legend(fontsize=8, loc="upper left")
    save_figure(figure, "q3_tight_los_profile")
    return float(gap[worst])


def run():
    from mountain_flood.figure import q1, q2, q3, q4

    model = Model()
    q1_data = load_result("q1_rho20.json")
    q2_data = load_result("q2.json")
    q3_data = load_result("q3.json")
    q4_data = load_result("q4.json")
    certificate = load_result("solution_certificate.json")

    q1.plot_payload_energy(model, q1_data)        # 图5-3
    q1.plot_return_soc(q1_data, model)            # 图5-5
    q1.plot_sensitivity()                         # 图9-1（含 25%/35% 与可行边界）
    q1.plot_sensitivity_compact()                 # 图9-1 备选（仅 10/20/30）
    q2.plot_routes(model, q2_data)                # 图6-1
    q2.plot_battery_timeline(model, q2_data)      # 图6-3
    q2.plot_return_soc(q2_data)                   # 图6-6
    q3.plot_relay_coverage_points(model, q3_data)  # 图7-1
    plot_margin_envelope(q3_data)                 # 图7-4
    worst_gap = plot_tight_los_profile(model, certificate, q3_data)  # 图7-5
    q4.plot_task_network(model, q4_data, q3_data)  # 图8-1
    for group_count in (2, 3):                     # 图8-2
        selected = q4_data["schemes"][str(group_count)]["selected"]
        q4._plot_partition_map(model, selected["groups"], group_count)
    q4.plot_workload(q4_data)                      # 图8-3
    q4.plot_resource_demand(q4_data, q4_data["inventory"])  # 图8-4
    print(f"图7-5 复算最大遮挡高度：{worst_gap:.2f} m")


if __name__ == "__main__":
    run()


