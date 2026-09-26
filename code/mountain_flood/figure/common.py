"""各问题绘图脚本共用的路径、样式、数据读取和地图底图函数。"""

from pathlib import Path
from collections import defaultdict
import csv
from functools import lru_cache
import json
import os
import re
import tempfile
from datetime import datetime

_cache_root = Path(tempfile.gettempdir()) / "mountain_flood_plot_cache"
_cache_root.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_cache_root / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_cache_root / "xdg"))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["XDG_CACHE_HOME"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib import patheffects
from matplotlib.patches import Patch, Polygon
import numpy as np

from mountain_flood.core.domain import INPUT, Model, ROOT, RESULT, charge


_figure_set = os.environ.get("MOUNTAIN_FLOOD_FIGURE_SET") or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
if not re.fullmatch(r"[\w\-]+", _figure_set):
    raise ValueError("MOUNTAIN_FLOOD_FIGURE_SET 只能包含字母、数字、下划线或连字符")
FIGURE_DIR = ROOT / "figures" / _figure_set
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
COLORS = {"A": "#315E9D", "B": "#CE853D", "C": "#B64A60"}
RELAY_COLORS = {"W": "#69549A", "E": "#258A91", "N": "#9B713C"}
GROUP_COLORS = ("#315E9D", "#CE853D", "#B64A60")
NEUTRAL = "#536273"
TERRAIN_CMAP = LinearSegmentedColormap.from_list(
    "mountain_flood_terrain",
    ["#315A82", "#75A5C4", "#C5DFE6", "#F3E7C7", "#DDAE77", "#A85C52"],
)
FLIGHT_TIME_CMAP = LinearSegmentedColormap.from_list(
    "mountain_flood_time", ["#3D7DAD", "#B9D9E6", "#F6E6BE", "#EBA36C", "#AE4A59"]
)
FIGURE_TITLES = {
    "q1_dem_nodes": "DEM 地形、地理要素与服务点",
    "q1_safe_capacity": "各服务点安全载荷",
    "q1_capacity_heatmap": "安全载荷热力图",
    "q1_typical_elevation_profile": "典型航线高程剖面",
    "q1_payload_energy": "载荷与飞行能耗",
    "q1_objective_solutions": "时间与能耗单目标方案",
    "q1_sensitivity": "安全余量敏感性",
    "q1_return_soc": "问题一返航电量",
    "q2_transport_routes": "问题二运输航线",
    "q2_drone_timeline": "无人机任务时间线",
    "q2_battery_timeline": "电池使用与充电时间线",
    "q2_delivery_deadlines": "逐箱送达与时限",
    "q2_return_soc": "问题二返航电量",
    "q2_search_comparison": "运输方案搜索比较",
    "q2_route_energy": "运输架次能耗",
    "q3_relay_map": "通信中继布设地图",
    "q3_relay_coverage_points": "中继覆盖采样",
    "q3_communication_timeline": "通信提供方时间线",
    "q3_link_margin": "通信链路裕量",
    "q3_joint_timeline": "运输与中继联合时间线",
    "q3_battery_timeline": "问题三运输电池占用与充电",
    "q3_relay_soc": "中继无人机返航电量",
    "q3_q2_q3_comparison": "运输与通信方案比较",
    "q4_partition_2groups": "两组任务分区",
    "q4_partition_3groups": "三组任务分区",
    "q4_resource_demand": "资源需求与库存",
    "q4_workload": "组间工作量",
    "q4_resource_deficit": "资源库存缺口",
    "q4_task_network": "任务关联网络",
    "spatial_terrain_time_partitions": "DEM、六边形参考飞行时间与任务分区",
    "spatial_group_standard_ellipses": "服务点空间标准差椭圆",
    "spatial_terrain_routes_3d": "三维地形、航线与中继位置",
    "spatial_time_sliced_routes": "分时段航线空间分布",
    "fig_roadmap": "总体技术路线图",
}
FONT = "DejaVu Sans"
for _candidate in ("PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei"):
    try:
        font_manager.findfont(_candidate, fallback_to_default=False)
        FONT = _candidate
        break
    except ValueError:
        pass

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [FONT, "Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.labelcolor": "#263442",
    "text.color": "#263442",
    "xtick.color": "#536273",
    "ytick.color": "#536273",
    "axes.edgecolor": "#8996A3",
    "axes.linewidth": 0.7,
    "axes.titleweight": "semibold",
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "legend.frameon": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
})


def load_result(name):
    """读取 results/ 下的 JSON 结果文件。"""
    return json.loads((RESULT / name).read_text(encoding="utf-8"))


def save_figure(fig, name, dpi=300, tight=True):
    """把本次图组的 PDF、SVG 和高分辨率 PNG 写入同一子目录。"""
    if tight:
        fig.tight_layout()
    _audit_panel_alignment(fig, name)
    pdf_path = FIGURE_DIR / f"{name}.pdf"
    png_path = FIGURE_DIR / f"{name}.png"
    svg_path = FIGURE_DIR / f"{name}.svg"
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=dpi)
    fig.savefig(svg_path)
    plt.close(fig)
    update_figure_manifest()
    print(pdf_path)


def update_figure_manifest():
    """根据图组目录中实际存在的配图更新同目录的 Markdown 清单。"""
    formats = ("pdf", "png", "svg")
    names = {path.stem for extension in formats
             for path in FIGURE_DIR.glob(f"*.{extension}")}
    order = {name: index for index, name in enumerate(FIGURE_TITLES)}
    names = sorted(names, key=lambda name: (order.get(name, len(order)), name))
    lines = [
        f"# 图组清单：{FIGURE_DIR.name}",
        "",
        f"配图数量：**{len(names)}** 张。以下清单根据本文件夹内实际存在的配图自动更新。",
        "",
        "| 序号 | 图名 | PDF | PNG | SVG |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for index, name in enumerate(names, 1):
        links = [f"[打开]({name}.{extension})"
                 if (FIGURE_DIR / f"{name}.{extension}").is_file() else "—"
                 for extension in formats]
        lines.append(f"| {index} | {FIGURE_TITLES.get(name, name)} (`{name}`) | "
                     + " | ".join(links) + " |")
    lines.append("")
    (FIGURE_DIR / "图组清单.md").write_text("\n".join(lines), encoding="utf-8")


def _audit_panel_alignment(fig, name, tolerance_pt=1.5):
    """记录最终图面矩形；同一网格中的重复面板必须对齐。"""
    panels = [ax for ax in fig.axes if ax.get_label() != "<colorbar>"]
    if len(panels) < 2:
        return
    fig.canvas.draw()
    scale = 72 / fig.dpi
    rectangles = []
    for ax in panels:
        box = ax.get_window_extent()
        rectangles.append([float(box.x0 * scale), float(box.y0 * scale),
                           float(box.width * scale), float(box.height * scale)])
    rows = []
    for rectangle in sorted(rectangles, key=lambda box: -box[1]):
        center_y = rectangle[1] + rectangle[3] / 2
        row = next((item for item in rows
                    if abs(item[0][1] + item[0][3] / 2 - center_y) < tolerance_pt), None)
        if row is None:
            rows.append([rectangle])
        else:
            row.append(rectangle)
    deviations = []
    for row in rows:
        row.sort(key=lambda box: box[0])
        if len(row) < 2:
            continue
        deviations += [max(box[2] for box in row) - min(box[2] for box in row),
                       max(box[3] for box in row) - min(box[3] for box in row)]
        if len(row) > 2:
            gutters = [row[index + 1][0] - row[index][0] - row[index][2]
                       for index in range(len(row) - 1)]
            deviations.append(max(gutters) - min(gutters))
    same_length_rows = [row for row in rows if len(row) == len(rows[0])]
    if len(same_length_rows) > 1:
        for column in range(len(rows[0])):
            deviations.append(max(row[column][0] for row in same_length_rows)
                              - min(row[column][0] for row in same_length_rows))
            deviations.append(max(row[column][2] for row in same_length_rows)
                              - min(row[column][2] for row in same_length_rows))
    maximum = max(deviations, default=0.0)
    report = {"figure": name, "tolerance_pt": tolerance_pt,
              "max_deviation_pt": maximum, "panels_pt": rectangles,
              "passed": maximum <= tolerance_pt}
    (FIGURE_DIR / f"{name}.alignment.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if maximum > tolerance_pt:
        raise ValueError(f"{name} 的面板未对齐：最大偏差 {maximum:.2f} pt")


def _geo_csv(name):
    """读取镇龙乡空间数据目录中的 UTF-8 CSV 图层。"""
    path = INPUT / "镇龙乡地理空间数据" / "镇龙乡及周边地理数据"
    matches = list(path.rglob(name))
    if not matches:
        raise FileNotFoundError(f"未找到地理图层：{name}；检查 INPUT 下的镇龙乡地理空间数据目录")
    with matches[0].open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _spatial_lines(filename, feature_key, type_key):
    grouped = defaultdict(list)
    for row in _geo_csv(filename):
        grouped[(row[feature_key], row[type_key])].append(
            (int(row["点序号"]), float(row["经度"]), float(row["纬度"]))
        )
    return [
        (feature_type, [(lon, lat) for _, lon, lat in sorted(points)])
        for (_, feature_type), points in grouped.items()
    ]


@lru_cache(maxsize=1)
def _roads():
    return _spatial_lines("镇龙乡及周边道路.csv", "道路要素编号", "道路类型")


@lru_cache(maxsize=1)
def _rivers():
    return _spatial_lines("镇龙乡及周边水系.csv", "水系要素编号", "水系类型")


@lru_cache(maxsize=1)
def _water_polygons():
    grouped = defaultdict(list)
    for row in _geo_csv("镇龙乡及周边水体.csv"):
        key = (row["水体要素编号"], row["多边形编号"], row["环编号"], row["水体类型"])
        grouped[key].append((int(row["点序号"]), float(row["经度"]), float(row["纬度"])))
    return [
        (water_type, [(lon, lat) for _, lon, lat in sorted(points)])
        for (_, _, _, water_type), points in grouped.items()
    ]


@lru_cache(maxsize=1)
def _settlements():
    rows = _geo_csv("镇龙乡及周边村镇点位.csv")
    return [(row["名称"], row["类别"], float(row["经度"]), float(row["纬度"]))
            for row in rows if row["位置"] == "乡内"]


def _local_coordinates(model, coordinates):
    """将 CSV 中的 WGS84 经纬度批量换算为以调度中心为原点的公里坐标。"""
    values = np.asarray(coordinates, dtype=float)
    longitude, latitude = values[:, 0], values[:, 1]
    origin = model.nodes[0]
    azimuth, _, distance = model.geo.inv(
        np.full(longitude.shape, origin["lon"]),
        np.full(latitude.shape, origin["lat"]), longitude, latitude)
    angle = np.deg2rad(azimuth)
    return np.column_stack((distance * np.sin(angle), distance * np.cos(angle))) / 1000


def _visible(coordinates, bounds):
    if not coordinates:
        return False
    longitude = [point[0] for point in coordinates]
    latitude = [point[1] for point in coordinates]
    return not (max(longitude) < bounds[0] or min(longitude) > bounds[1]
                or max(latitude) < bounds[2] or min(latitude) > bounds[3])


def _draw_spatial_layers(ax, model, bounds, label_township=True):
    """按 WGS84 对齐道路、水系、水体面及乡内村镇点位。"""
    water_colors = {"水库": "#5DADE2", "一般水体": "#85C1E9",
                    "池塘": "#76D7C4", "蓄水池": "#48C9B0"}
    for water_type, coordinates in _water_polygons():
        if len(coordinates) < 3 or not _visible(coordinates, bounds):
            continue
        xy = _local_coordinates(model, coordinates)
        ax.add_patch(Polygon(xy, closed=True,
                             facecolor=water_colors.get(water_type, "#85C1E9"),
                             edgecolor="#3182BD", linewidth=0.15,
                             alpha=0.2, zorder=1))

    major_road_types = {"高速公路", "高速公路匝道", "干线公路", "主要道路",
                        "干线公路连接线", "主要道路连接线"}
    for road_type, coordinates in _roads():
        if len(coordinates) < 2 or not _visible(coordinates, bounds):
            continue
        xy = _local_coordinates(model, coordinates)
        is_major = road_type in major_road_types
        ax.plot(xy[:, 0], xy[:, 1],
                color="#B66A50" if road_type.startswith("高速") else "#8A7665",
                linewidth=0.48 if is_major else 0.22,
                alpha=0.7 if is_major else 0.38, zorder=2)

    river_widths = {"河流": 0.7, "溪流": 0.42, "排水沟": 0.25, "渠道": 0.25}
    for water_type, coordinates in _rivers():
        if len(coordinates) < 2 or not _visible(coordinates, bounds):
            continue
        xy = _local_coordinates(model, coordinates)
        ax.plot(xy[:, 0], xy[:, 1], color="#2878A8",
                linewidth=river_widths.get(water_type, 0.35), alpha=0.68, zorder=3)

    settlements = [item for item in _settlements()
                   if bounds[0] <= item[2] <= bounds[1]
                   and bounds[2] <= item[3] <= bounds[3]]
    villages = [item for item in settlements if item[1] == "村庄"]
    townships = [item for item in settlements if item[1] == "乡镇"]
    if villages:
        xy = _local_coordinates(model, [(item[2], item[3]) for item in villages])
        ax.scatter(xy[:, 0], xy[:, 1], s=8, color="#555555", alpha=0.65,
                   marker="o", zorder=4, label="_nolegend_")
    if townships:
        xy = _local_coordinates(model, [(item[2], item[3]) for item in townships])
        ax.scatter(xy[:, 0], xy[:, 1], s=28, color="#7B3294", alpha=0.9,
                   marker="s", zorder=5, label="_nolegend_")
        if label_township:
            for item, point in zip(townships, xy):
                ax.annotate(item[0], point, xytext=(4, 3), textcoords="offset points", fontsize=7)


def draw_region(ax, model, annotate=True, view="local", show_services=True):
    """绘制 DEM 和镇龙乡矢量图层；可选择任务区放大图或全幅地理概览。"""
    ax.set_aspect("equal")
    ax.set_xlabel("东向距离 / km")
    ax.set_ylabel("北向距离 / km")
    raster_bounds = model.raster.bounds
    if view == "township":
        geographic_bounds = (raster_bounds.left, raster_bounds.right,
                             raster_bounds.bottom, raster_bounds.top)
        corners = [(raster_bounds.left, raster_bounds.bottom),
                   (raster_bounds.left, raster_bounds.top),
                   (raster_bounds.right, raster_bounds.bottom),
                   (raster_bounds.right, raster_bounds.top)]
        extent_xy = _local_coordinates(model, corners)
        extent = (extent_xy[:, 0].min(), extent_xy[:, 0].max(),
                  extent_xy[:, 1].min(), extent_xy[:, 1].max())
        ax.imshow(model.dem, origin="upper", extent=extent, cmap=TERRAIN_CMAP, alpha=0.9,
                  aspect="equal", zorder=0)
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
    else:
        longitude = np.linspace(109.16, 109.30, 350)
        latitude = np.linspace(22.999, 23.09, 250)
        xx, yy = np.meshgrid(longitude, latitude)
        elevation = model.ground(xx, yy)
        origin = model.nodes[0]
        extent = [
            model.local(longitude[0], origin["lat"])[0] / 1000,
            model.local(longitude[-1], origin["lat"])[0] / 1000,
            model.local(origin["lon"], latitude[0])[1] / 1000,
            model.local(origin["lon"], latitude[-1])[1] / 1000,
        ]
        geographic_bounds = (longitude[0], longitude[-1], latitude[0], latitude[-1])
        ax.imshow(elevation, origin="lower", extent=extent, cmap=TERRAIN_CMAP, alpha=0.82,
                  aspect="equal", zorder=0)
        ax.set_xlim(-8, 8)
        ax.set_ylim(-1, 10)

    _draw_spatial_layers(ax, model, geographic_bounds, label_township=view == "township")
    ax.scatter(0, 0, s=100, marker="*", color="black", zorder=7, label="_nolegend_")
    if annotate:
        ax.text(0.13, -0.4, "O01", fontsize=9, zorder=8)
    if show_services:
        for index, (x, y) in enumerate(model.xy[1:], 1):
            ax.scatter(x / 1000, y / 1000, s=32, facecolor="white",
                       edgecolor=NEUTRAL, linewidth=0.8, zorder=6)
            if annotate:
                label = ax.annotate(f"S{index:03}", (x / 1000, y / 1000), xytext=(4, 5),
                                    textcoords="offset points", fontsize=8, zorder=8)
                label.set_path_effects([patheffects.withStroke(
                    linewidth=1.5, foreground="white")])


def drone_route_legend():
    """返回三种运输无人机机型的路线图例。"""
    return [Line2D([0], [0], color=color, label=f"{drone_type}型航线")
            for drone_type, color in COLORS.items()]


def charge_duration(model, route):
    """按共享物理模型中的充电函数计算该架次结束后的充电时长。"""
    return charge(route["soc"], model.types[route["g"]]["charge"])


def relay_legend_handles():
    """返回中继点颜色图例。"""
    return [Patch(facecolor=color, label=f"{site}中继点") for site, color in RELAY_COLORS.items()]
