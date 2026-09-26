"""将可编辑的 DrawIO 总体技术路线图导出为论文 PDF。"""

from pathlib import Path
import sys
import html
import xml.etree.ElementTree as ET
import os
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]

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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from mountain_flood.figure.common import FIGURE_DIR, update_figure_manifest

SOURCE = PROJECT_ROOT / "figures" / "fig_roadmap.drawio"
TARGET = FIGURE_DIR / "fig_roadmap.pdf"
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"


def _geometry(cell):
    geometry = cell.find("mxGeometry")
    return tuple(float(geometry.get(key)) for key in ("x", "y", "width", "height"))


def run():
    graph = ET.parse(SOURCE).getroot().find(".//mxGraphModel")
    cells = {cell.get("id"): cell for cell in graph.findall(".//mxCell")}
    width, height = (float(graph.get(key)) for key in ("pageWidth", "pageHeight"))
    font = font_manager.FontProperties(fname=FONT, size=16)
    fig, ax = plt.subplots(figsize=(width / 72, height / 72))
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis("off")

    for index in range(1, 9):
        cell = cells[f"n{index}"]
        x, y, box_width, box_height = _geometry(cell)
        style = dict(part.split("=", 1) for part in cell.get("style").split(";")
                     if "=" in part)
        ax.add_patch(FancyBboxPatch(
            (x, y), box_width, box_height,
            boxstyle="round,pad=0.02,rounding_size=12",
            linewidth=1.5,
            edgecolor=style.get("strokeColor", "#4477AA"),
            facecolor=style.get("fillColor", "#E8F0FA"),
        ))
        label = html.unescape(cell.get("value")).replace("<br>", "\n")
        ax.text(x + box_width / 2, y + box_height / 2, label,
                ha="center", va="center", fontproperties=font, linespacing=1.25)

    for index in range(1, 8):
        xa, ya, wa, ha = _geometry(cells[f"n{index}"])
        xb, yb, wb, hb = _geometry(cells[f"n{index + 1}"])
        if ya == yb:
            start, end = ((xa + wa + 3, ya + ha / 2), (xb - 6, yb + hb / 2)) \
                if xb > xa else ((xa - 3, ya + ha / 2), (xb + wb + 6, yb + hb / 2))
        else:
            start, end = (xa + wa / 2, ya + ha + 3), (xb + wb / 2, yb - 6)
        ax.add_patch(FancyArrowPatch(
            start, end, arrowstyle="-|>", mutation_scale=20,
            linewidth=2.2, color="#555555"))

    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(TARGET, format="pdf", metadata={
        "Title": "总体建模流程", "Creator": "fig_roadmap.drawio 渲染结果"})
    fig.savefig(FIGURE_DIR / "fig_roadmap.png", dpi=300)
    fig.savefig(FIGURE_DIR / "fig_roadmap.svg")
    plt.close(fig)
    update_figure_manifest()
    print(TARGET)


if __name__ == "__main__":
    run()
