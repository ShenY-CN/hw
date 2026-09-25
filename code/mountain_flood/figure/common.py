"""各问题绘图脚本共用的路径、样式、数据读取和地图底图函数。"""

from pathlib import Path
import json
import os
import tempfile

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
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

from mountain_flood.core.domain import Model, ROOT, RESULT, charge


FIGURE_DIR = ROOT / "figures"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
COLORS = {"A": "#0072B2", "B": "#D55E00", "C": "#009E73"}
RELAY_COLORS = {"W": "#CC79A7", "E": "#0072B2", "N": "#D55E00"}
FONT = "DejaVu Sans"
for _candidate in ("PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei"):
    try:
        font_manager.findfont(_candidate, fallback_to_default=False)
        FONT = _candidate
        break
    except ValueError:
        pass

plt.rcParams.update({
    "font.family": FONT,
    "font.size": 10,
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
})


def load_result(name):
    """读取 results/ 下的 JSON 结果文件。"""
    return json.loads((RESULT / name).read_text(encoding="utf-8"))


def save_figure(fig, name, dpi=180):
    """同时导出论文用 PDF 和预览用 PNG，并关闭图对象。"""
    fig.tight_layout()
    pdf_path = FIGURE_DIR / f"{name}.pdf"
    png_path = FIGURE_DIR / f"{name}.png"
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=dpi)
    plt.close(fig)
    print(pdf_path)


def draw_region(ax, model, annotate=True):
    """绘制 DEM、调度中心和服务区，供空间路线图复用。"""
    ax.set_aspect("equal")
    ax.set_xlabel("东向距离 / km")
    ax.set_ylabel("北向距离 / km")
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
    ax.imshow(elevation, origin="lower", extent=extent, cmap="Greys", alpha=0.32, aspect="equal")
    ax.scatter(0, 0, s=100, marker="*", color="black", zorder=6, label="调度中心")
    if annotate:
        ax.text(0.13, -0.4, "O01", fontsize=9)
    for index, (x, y) in enumerate(model.xy[1:], 1):
        ax.scatter(x / 1000, y / 1000, s=30, color="black", zorder=5)
        if annotate:
            ax.annotate(f"S{index:03}", (x / 1000, y / 1000), xytext=(4, 5),
                        textcoords="offset points", fontsize=8)
    ax.set_xlim(-8, 8)
    ax.set_ylim(-1, 10)


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
