"""基于已归档结果的地形、六边形参考时间、任务分组和三维航线图。"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]

from mountain_flood.figure.common import (
    COLORS, FLIGHT_TIME_CMAP, GROUP_COLORS, Model, NEUTRAL, TERRAIN_CMAP,
    draw_region, load_result, save_figure,
)
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse, RegularPolygon
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  注册 3D 投影
import numpy as np


def _hex_reference_times(model, radius=0.49):
    """在局部公里网格计算 B 型机从 O01 到假想格心的单程参考飞行时间。"""
    spacing_x = np.sqrt(3) * radius
    spacing_y = 1.5 * radius
    centers = []
    for row, y in enumerate(np.arange(-0.2, 9.4, spacing_y)):
        for x in np.arange(-6.8, 7.0, spacing_x) + (row % 2) * spacing_x / 2:
            longitude, latitude = model.lonlat(float(x * 1000), float(y * 1000))
            bounds = model.raster.bounds
            if not (bounds.left <= longitude <= bounds.right and
                    bounds.bottom <= latitude <= bounds.top):
                continue
            dest_altitude = float(model.ground(longitude, latitude)) + 30
            max_altitude = max(
                model.line_max(model.nodes[0]["lon"], model.nodes[0]["lat"],
                               longitude, latitude) + 50,
                float(model.op[0]), dest_altitude,
            )
            spec = model.types["B"]
            distance = model.geo.inv(model.nodes[0]["lon"], model.nodes[0]["lat"],
                                     longitude, latitude)[2]
            seconds = ((max_altitude - model.op[0]) / spec["vu"]
                       + distance / spec["vc"]
                       + (max_altitude - dest_altitude) / spec["vd"])
            centers.append((float(x), float(y), float(seconds / 60)))
    return np.asarray(centers, dtype=float), radius


def _group_for_centers(model, centers, groups):
    """只为地图辅助描边：格心归属最近服务点所在组，不更改离散优化结果。"""
    node_group = {node: index for index, group in enumerate(groups)
                  for node in group["nodes"]}
    sites = model.xy[1:] / 1000
    nearest = np.argmin(np.sum((centers[:, None, :2] - sites[None, :, :]) ** 2, axis=2),
                        axis=1) + 1
    return np.array([node_group[int(node)] for node in nearest])


def plot_terrain_time_partitions(model, q4):
    """同一 DEM 上对照服务点、B 型参考时间和两种已选分组。"""
    centers, radius = _hex_reference_times(model)
    norm = colors.Normalize(vmin=float(centers[:, 2].min()),
                            vmax=float(centers[:, 2].max()))
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.0), sharex=True, sharey=True)
    axes = axes.ravel()
    draw_region(axes[0], model, annotate=True)
    axes[0].set_title("a  DEM 与调度中心、服务点", loc="left")
    for index, ax in enumerate(axes[1:]):
        draw_region(ax, model, annotate=False, show_services=False)
        group_count = (None, 2, 3)[index]
        groups = (q4["schemes"][str(group_count)]["selected"]["groups"]
                  if group_count else None)
        assigned = _group_for_centers(model, centers, groups) if groups else None
        for cell, (x, y, minutes) in enumerate(centers):
            edge = GROUP_COLORS[int(assigned[cell])] if groups else "#FFFFFF"
            ax.add_patch(RegularPolygon(
                (x, y), numVertices=6, radius=radius, orientation=np.pi / 6,
                facecolor=FLIGHT_TIME_CMAP(norm(minutes)), edgecolor=edge,
                linewidth=0.36 if groups else 0.22, alpha=0.91, zorder=5,
            ))
        if groups:
            for group_index, group in enumerate(groups):
                xy = model.xy[group["nodes"]] / 1000
                ax.scatter(xy[:, 0], xy[:, 1], s=43,
                           facecolor=GROUP_COLORS[group_index], edgecolor="white",
                           linewidth=0.8, zorder=8)
        else:
            ax.scatter(model.xy[1:, 0] / 1000, model.xy[1:, 1] / 1000,
                       s=30, facecolor="white", edgecolor=NEUTRAL,
                       linewidth=0.8, zorder=8)
        ax.scatter(0, 0, s=105, marker="*", facecolor="#1E2833",
                   edgecolor="white", linewidth=0.5, zorder=9)
        ax.set_title(("b  B 型单程参考飞行时间" if groups is None else
                      f"{'c' if group_count == 2 else 'd'}  {group_count} 组任务分区"),
                     loc="left")
    fig.subplots_adjust(left=0.07, right=0.98, top=0.94, bottom=0.19,
                        wspace=0.13, hspace=0.24)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=FLIGHT_TIME_CMAP)
    colorbar_ax = fig.add_axes([0.24, 0.09, 0.52, 0.022])
    fig.colorbar(sm, cax=colorbar_ax, orientation="horizontal",
                 label="O01 至格心的 B 型机单程参考飞行时间 / min")
    fig.text(0.5, 0.022, "六边形描边按最近服务点所属组标识，仅作空间示意；分组结果以彩色服务点为准。",
             ha="center", fontsize=8, color=NEUTRAL)
    save_figure(fig, "spatial_terrain_time_partitions", tight=False)


def _standard_ellipse(ax, coordinates, color, label):
    """以服务点为等权样本，绘制中心和一倍标准差椭圆。"""
    center = coordinates.mean(axis=0)
    ax.scatter(center[0], center[1], s=55, marker="x", color=color,
               linewidth=1.6, zorder=9, label=label)
    if len(coordinates) < 2:
        return
    covariance = np.cov(coordinates.T, bias=True)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues, eigenvectors = eigenvalues[order], eigenvectors[:, order]
    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
    ellipse = Ellipse(center, width=2 * np.sqrt(max(eigenvalues[0], 0)),
                      height=2 * np.sqrt(max(eigenvalues[1], 0)), angle=angle,
                      facecolor=color, edgecolor=color, alpha=0.15,
                      linewidth=1.4, linestyle="--", zorder=5)
    ax.add_patch(ellipse)
    ax.add_patch(Ellipse(center, width=ellipse.width, height=ellipse.height,
                         angle=angle, facecolor="none", edgecolor=color,
                         linewidth=1.2, linestyle="--", zorder=6))


def plot_standard_ellipses(model, q4):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True, sharey=True)
    for ax, group_count in zip(axes, (2, 3)):
        draw_region(ax, model, annotate=False, show_services=False)
        groups = q4["schemes"][str(group_count)]["selected"]["groups"]
        for index, group in enumerate(groups):
            xy = model.xy[group["nodes"]] / 1000
            color = GROUP_COLORS[index]
            ax.scatter(xy[:, 0], xy[:, 1], s=34, facecolor=color,
                       edgecolor="white", linewidth=0.7, zorder=7)
            _standard_ellipse(ax, xy, color, f"第{index + 1}组（n={len(xy)}）")
        ax.set_title(f"{'a' if group_count == 2 else 'b'}  {group_count} 组服务点空间分布", loc="left")
        ax.legend(loc="upper right", fontsize=7)
    fig.text(0.5, 0.01, "虚线椭圆表示组内服务点坐标的 1 倍标准差；单点组仅标出中心。",
             ha="center", fontsize=8, color=NEUTRAL)
    save_figure(fig, "spatial_group_standard_ellipses")


def _terrain_grid(model):
    longitude = np.linspace(109.16, 109.30, 90)
    latitude = np.linspace(22.999, 23.09, 65)
    lon, lat = np.meshgrid(longitude, latitude)
    origin = model.nodes[0]
    azimuth, _, distance = model.geo.inv(
        np.full(lon.shape, origin["lon"]), np.full(lat.shape, origin["lat"]), lon, lat)
    angle = np.deg2rad(azimuth)
    x = distance * np.sin(angle) / 1000
    y = distance * np.cos(angle) / 1000
    z = np.asarray(model.ground(lon, lat), dtype=float)
    return x, y, z


def _plot_flight_segments_3d(ax, model, routes, aircraft_type=None):
    for route in routes:
        if aircraft_type and route["g"] != aircraft_type:
            continue
        for segment in route["segments"]:
            if segment["phase"] == "交接":
                continue
            start, end = segment["a"], segment["b"]
            x0, y0 = model.local(start[0], start[1])
            x1, y1 = model.local(end[0], end[1])
            ax.plot([x0 / 1000, x1 / 1000], [y0 / 1000, y1 / 1000],
                    [start[2], end[2]], color=COLORS[route["g"]],
                    linewidth=0.7, alpha=0.82, zorder=8)


def plot_terrain_routes_3d(model, q2, q3):
    """统一地形、色标和视角，展示运输结果与中继位置。"""
    x, y, z = _terrain_grid(model)
    norm = colors.Normalize(vmin=float(np.nanmin(z)), vmax=float(np.nanmax(z)))
    panels = [
        ("a  问题二运输方案", q2["routes"], None, False),
        ("b  问题三联合方案", q3["routes"], None, False),
        ("c  A 型运输", q3["routes"], "A", False),
        ("d  B 型运输", q3["routes"], "B", False),
        ("e  C 型运输", q3["routes"], "C", False),
        ("f  中继位置与联合航线", q3["routes"], None, True),
    ]
    fig = plt.figure(figsize=(12, 7.0))
    for index, (title, routes, aircraft_type, show_relays) in enumerate(panels, 1):
        ax = fig.add_subplot(2, 3, index, projection="3d", computed_zorder=False)
        ax.plot_surface(x, y, z, cmap=TERRAIN_CMAP, norm=norm,
                        rcount=65, ccount=90, linewidth=0, antialiased=False,
                        alpha=0.88, shade=False, zorder=0)
        _plot_flight_segments_3d(ax, model, routes, aircraft_type)
        if show_relays:
            for relay in q3["relays"]:
                rx, ry = model.local(*relay["pos"][:2])
                ground = float(model.ground(*relay["pos"][:2]))
                ax.plot([rx / 1000, rx / 1000], [ry / 1000, ry / 1000],
                        [ground, relay["pos"][2]], linestyle=":",
                        linewidth=1.2, color="#563E8A", zorder=18)
                ax.scatter([rx / 1000], [ry / 1000], [relay["pos"][2]],
                           s=100, marker="D", color="#563E8A", edgecolor="white",
                           linewidth=0.8, depthshade=False, zorder=20)
        ax.set_xlim(-8, 8)
        ax.set_ylim(-1, 10)
        ax.set_zlim(0, max(1300, float(np.nanmax(z)) * 1.1))
        ax.view_init(elev=29, azim=-69)
        ax.set_box_aspect((1.5, 1, 0.42), zoom=1.12)
        ax.set_title(title, loc="left", fontsize=9)
        ax.set_zticks((0, 400, 800, 1200))
        ax.tick_params(labelsize=6, pad=0)
    handles = [Line2D([0], [0], color=color, lw=1.5, label=f"{kind} 型")
               for kind, color in COLORS.items()]
    relay_sites = " / ".join(str(relay["site"]) for relay in q3["relays"])
    handles.append(Line2D([0], [0], marker="D", linestyle="none", color="#563E8A",
                          label=f"中继位置（{relay_sites}）"))
    fig.subplots_adjust(left=0.015, right=0.99, top=0.96, bottom=0.12,
                        wspace=0.005, hspace=0.02)
    colorbar_ax = fig.add_axes([0.71, 0.055, 0.25, 0.016])
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=TERRAIN_CMAP),
                 cax=colorbar_ax, orientation="horizontal", label="DEM 高程 / m")
    fig.legend(handles=handles, loc="lower left", ncol=4, fontsize=8,
               bbox_to_anchor=(0.025, 0.028))
    save_figure(fig, "spatial_terrain_routes_3d", tight=False)


def _segment_in_window(route, segment, start_seconds, end_seconds):
    if segment["phase"] == "交接":
        return None
    absolute_start = route["start"] + segment["start"]
    absolute_end = route["start"] + segment["end"]
    overlap_start = max(absolute_start, start_seconds)
    overlap_end = min(absolute_end, end_seconds)
    if overlap_end <= overlap_start or absolute_end <= absolute_start:
        return None
    fraction_start = (overlap_start - absolute_start) / (absolute_end - absolute_start)
    fraction_end = (overlap_end - absolute_start) / (absolute_end - absolute_start)
    first = np.asarray(segment["a"][:2], dtype=float)
    last = np.asarray(segment["b"][:2], dtype=float)
    return first + (last - first) * fraction_start, first + (last - first) * fraction_end


def plot_time_sliced_routes(model, q3):
    """按真实飞行段起止时刻裁切，展示三段时间内的活跃空间路线。"""
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4), sharex=True, sharey=True)
    windows = ((0, 40), (40, 80), (80, 120))
    for index, (ax, (start_min, end_min)) in enumerate(zip(axes, windows)):
        draw_region(ax, model, annotate=False)
        for route in q3["routes"]:
            for segment in route["segments"]:
                clipped = _segment_in_window(route, segment, start_min * 60, end_min * 60)
                if clipped is None:
                    continue
                endpoints = [model.local(*point) for point in clipped]
                ax.plot([point[0] / 1000 for point in endpoints],
                        [point[1] / 1000 for point in endpoints],
                        color=COLORS[route["g"]], linewidth=1.0,
                        alpha=0.85, zorder=8)
        for relay in q3["relays"]:
            if relay["ready"] < end_min * 60 and relay["service_end"] > start_min * 60:
                x, y = model.local(*relay["pos"][:2])
                ax.scatter(x / 1000, y / 1000, s=44, marker="D",
                           facecolor="#563E8A", edgecolor="white", linewidth=0.7,
                           zorder=9)
        ax.set_title(f"{chr(97 + index)}  {start_min}–{end_min} min", loc="left")
    handles = [Line2D([0], [0], color=color, lw=1.6, label=f"{kind} 型航段")
               for kind, color in COLORS.items()]
    handles.append(Line2D([0], [0], marker="D", linestyle="none", color="#563E8A",
                          label="当期通信中继"))
    fig.legend(handles=handles, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.02))
    save_figure(fig, "spatial_time_sliced_routes")


def run():
    model = Model()
    q2, q3, q4 = (load_result(name) for name in ("q2.json", "q3.json", "q4.json"))
    plot_terrain_time_partitions(model, q4)
    plot_standard_ellipses(model, q4)
    plot_terrain_routes_3d(model, q2, q3)
    plot_time_sliced_routes(model, q3)


if __name__ == "__main__":
    run()
