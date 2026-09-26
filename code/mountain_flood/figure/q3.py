"""问题三论文图：中继部署、通信连续性、联合排程和链路裕量。"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]

from mountain_flood.figure.common import (
    COLORS, RELAY_COLORS, Model, NEUTRAL, draw_region, load_result, save_figure,
)
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


def plot_relay_map(model, data):
    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    draw_region(ax, model)
    for route in data["routes"]:
        points = model.xy[[0] + route["order"] + [0]] / 1000
        ax.plot(points[:, 0], points[:, 1], color=NEUTRAL, lw=0.55, alpha=0.35)
    shown = set()
    for relay in data["relays"]:
        site = relay["site"]
        if site not in shown:
            shown.add(site)
            x, y = model.local(*relay["pos"][:2])
            color = RELAY_COLORS[site]
            ax.scatter(x / 1000, y / 1000, s=90, marker="D", color=color, zorder=7)
            ax.annotate(site, (x / 1000, y / 1000), xytext=(4, 4),
                        textcoords="offset points", color=color)
            ax.plot([0, x / 1000], [0, y / 1000], linestyle="--", color=color, alpha=0.8)
        relay_routes = {item["route"] for item in data["communication"]
                        if item["relay_task"] == relay["id"]}
        nodes = {node for route in data["routes"] if route["id"] in relay_routes
                 for node in route["order"]}
        x, y = model.local(*relay["pos"][:2])
        for node in nodes:
            ax.plot([x / 1000, model.xy[node, 0] / 1000],
                    [y / 1000, model.xy[node, 1] / 1000],
                    color=RELAY_COLORS[site], linestyle=":", lw=0.7, alpha=0.7)
    handles = [Line2D([0], [0], color=color, marker="D", linestyle="--",
                      label=f"{site}中继点") for site, color in RELAY_COLORS.items()
               if site in shown]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.12),
              fontsize=8, ncol=max(1, len(handles)))
    save_figure(fig, "q3_relay_map")


def plot_relay_coverage_points(model, data):
    """把通信证书中的中继服务区间映射回航线上，展示直连盲区的中继覆盖。"""
    routes = {route["id"]: route for route in data["routes"]}
    points = {}
    relay_provider_color = {"R01": "#69549A", "R02": "#258A91"}
    for interval in data["communication"]:
        provider = interval["provider"]
        if provider == "G01":
            continue
        route = routes[interval["route"]]
        elapsed = (interval["start"] + interval["end"]) / 2 - route["start"]
        segment = next((item for item in route["segments"]
                        if item["start"] - 1e-6 <= elapsed <= item["end"] + 1e-6), None)
        if segment is None:
            continue
        span = segment["end"] - segment["start"]
        fraction = 0 if span <= 1e-12 else (elapsed - segment["start"]) / span
        first, second = segment["a"], segment["b"]
        longitude = first[0] + fraction * (second[0] - first[0])
        latitude = first[1] + fraction * (second[1] - first[1])
        x, y = model.local(longitude, latitude)
        color = relay_provider_color.get(provider, COLORS["C"])
        points.setdefault(color, [[], []])[0].append(x / 1000)
        points[color][1].append(y / 1000)

    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    draw_region(ax, model)
    for route in data["routes"]:
        path = model.xy[[0] + route["order"] + [0]] / 1000
        ax.plot(path[:, 0], path[:, 1], color=NEUTRAL, linewidth=0.5, alpha=0.25)
    relay_labels = {"#69549A": "R01中继覆盖采样", "#258A91": "R02中继覆盖采样",
                    COLORS["C"]: "其他中继覆盖采样"}
    for color, (x_values, y_values) in points.items():
        if x_values:
            ax.scatter(x_values, y_values, s=7, color=color, alpha=0.55,
                       label=relay_labels.get(color, "中继覆盖采样"), zorder=4)
    shown = set()
    for relay in data["relays"]:
        if relay["site"] in shown:
            continue
        shown.add(relay["site"])
        x, y = model.local(*relay["pos"][:2])
        ax.scatter(x / 1000, y / 1000, marker="D", s=75,
                   color=RELAY_COLORS[relay["site"]], edgecolor="black", linewidth=0.4,
                   label=f"{relay['site']}中继站", zorder=6)
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    save_figure(fig, "q3_relay_coverage_points")


def _merge_status_intervals(communication):
    """合并同一路线连续且通信提供方相同的证书小区间。"""
    grouped = {}
    for interval in sorted(communication, key=lambda item: (item["route"], item["start"])):
        key = (interval["route"], interval["provider"])
        ranges = grouped.setdefault(key, [])
        if ranges and abs(ranges[-1][1] - interval["start"]) < 1e-6:
            ranges[-1] = (ranges[-1][0], interval["end"])
        else:
            ranges.append((interval["start"], interval["end"]))
    return grouped


def plot_communication_timeline(data):
    routes = sorted(data["routes"], key=lambda route: route["id"])
    route_index = {route["id"]: index for index, route in enumerate(routes)}
    grouped = _merge_status_intervals(data["communication"])
    providers = sorted({provider for _, provider in grouped})
    palette = {"G01": NEUTRAL, "R01": "#69549A", "R02": "#258A91"}
    fig, ax = plt.subplots(figsize=(9.0, max(5.0, 0.24 * len(routes))))
    for (route_id, provider), ranges in grouped.items():
        bars = [(start / 60, (end - start) / 60) for start, end in ranges]
        ax.broken_barh(bars, (route_index[route_id] - 0.32, 0.64),
                       facecolors=palette.get(provider, COLORS["C"]), linewidth=0)
    ax.set_yticks(range(len(routes)), [route["id"] for route in routes])
    ax.invert_yaxis()
    ax.set_xlabel("时刻 / min")
    ax.set_ylabel("运输架次")
    ax.grid(axis="x", alpha=0.2)
    ax.legend(handles=[Patch(color=palette.get(provider, COLORS["C"]), label=
                             "调度中心直连" if provider == "G01" else f"{provider}中继")
                       for provider in providers], loc="upper right", ncol=len(providers), fontsize=8)
    save_figure(fig, "q3_communication_timeline")


def plot_link_margin(data):
    direct = [item["margin"] for item in data["communication"] if item["provider"] == "G01"]
    relayed = [item["margin"] for item in data["communication"] if item["provider"] != "G01"]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.hist([direct, relayed], bins=28, label=["调度中心直连", "中继链路"],
            color=[NEUTRAL, "#69549A"], alpha=0.75)
    minimum = min(item["margin"] for item in data["communication"])
    ax.axvline(0, color=COLORS["C"], linestyle="--", label="链路可行阈值")
    ax.axvline(minimum, color="#258A91", linestyle=":",
               label=f"最小证书裕量 {minimum:.2f} dB")
    ax.set_xlabel("链路裕量 / dB")
    ax.set_ylabel("认证区间数")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(fontsize=8)
    save_figure(fig, "q3_link_margin")


def plot_joint_timeline(data):
    tasks = [("运输", route) for route in data["routes"]]
    tasks.extend(("中继", relay) for relay in data["relays"])
    units = sorted({task["unit"] for _, task in tasks})
    unit_index = {unit: index for index, unit in enumerate(units)}
    fig, ax = plt.subplots(figsize=(8.4, max(4.2, 0.35 * len(units))))
    for kind, task in tasks:
        lane = unit_index[task["unit"]]
        start, end = task["start"] / 60, task["end"] / 60
        if kind == "运输":
            color = COLORS[task["g"]]
            ax.barh(lane, end - start, left=start, height=0.58, color=color,
                    edgecolor="white", linewidth=0.4)
        else:
            ax.barh(lane, end - start, left=start, height=0.58, color="#9381B2",
                    edgecolor="white", linewidth=0.4)
            service_start, service_end = task["ready"] / 60, task["service_end"] / 60
            ax.barh(lane, service_end - service_start, left=service_start,
                    height=0.3, color="#69549A")
        if end - start >= 4:
            ax.text((start + end) / 2, lane, task.get("id", ""), ha="center", va="center",
                    fontsize=6.5, color="white")
    ax.set_yticks(range(len(units)), units)
    ax.invert_yaxis()
    ax.set_xlabel("时刻 / min")
    ax.set_ylabel("运输机与中继机")
    ax.grid(axis="x", alpha=0.2)
    handles = [Patch(color=COLORS[g], label=f"{g}型运输") for g in "ABC"]
    handles.extend((Patch(color="#9381B2", label="中继飞行"),
                    Patch(color="#69549A", label="中继服务窗")))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncol=5, fontsize=7)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    save_figure(fig, "q3_joint_timeline", tight=False)


def plot_relay_soc(data):
    relays = sorted(data["relays"], key=lambda relay: relay["id"])
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    ax.bar([relay["id"] for relay in relays], [relay["soc"] * 100 for relay in relays],
           color=[RELAY_COLORS[relay["site"]] for relay in relays])
    ax.axhline(20, color=COLORS["C"], linestyle="--", linewidth=1,
               label="最低返航储备 20%")
    ax.set_xlabel("中继任务")
    ax.set_ylabel("返航剩余电量 / %")
    ax.grid(axis="y", alpha=0.2)
    ax.legend()
    save_figure(fig, "q3_relay_soc")


def plot_q2_q3_comparison(q2, q3):
    labels = ["问题二", "问题三"]
    values = [
        ([q2["summary"]["energy"], q3["summary"]["energy"]], "总能耗 / kWh"),
        ([q2["summary"]["makespan"] / 60, q3["summary"]["makespan"] / 60], "完工时间 / min"),
        ([q2["summary"]["count"], q3["summary"]["count"]], "运输架次数"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(8.4, 3.1))
    for ax, (pair, ylabel) in zip(axes, values):
        ax.bar(labels, pair, color=[COLORS["A"], COLORS["B"]])
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.2)
    save_figure(fig, "q3_q2_q3_comparison")


def run():
    model = Model()
    q2 = load_result("q2.json")
    q3 = load_result("q3.json")
    from mountain_flood.figure.q2 import plot_battery_timeline
    plot_relay_map(model, q3)
    plot_relay_coverage_points(model, q3)
    plot_communication_timeline(q3)
    plot_link_margin(q3)
    plot_joint_timeline(q3)
    plot_battery_timeline(model, q3, "q3_battery_timeline")
    plot_relay_soc(q3)
    plot_q2_q3_comparison(q2, q3)


if __name__ == "__main__":
    run()
