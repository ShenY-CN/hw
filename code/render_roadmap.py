# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""Render the editable DrawIO roadmap to PDF when Electron CLI is unavailable."""

import html
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "figures" / "fig_roadmap.drawio"
TARGET = ROOT / "figures" / "fig_roadmap.pdf"
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"


def geometry(cell):
    g = cell.find("mxGeometry")
    return tuple(float(g.get(key)) for key in ("x", "y", "width", "height"))


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

    for i in range(1, 9):
        cell = cells[f"n{i}"]
        x, y, w, h = geometry(cell)
        style = dict(part.split("=", 1) for part in cell.get("style").split(";")
                     if "=" in part)
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=12",
            linewidth=1.5, edgecolor=style.get("strokeColor", "#4477AA"),
            facecolor=style.get("fillColor", "#E8F0FA")))
        label = html.unescape(cell.get("value")).replace("<br>", "\n")
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontproperties=font, linespacing=1.25)

    for i in range(1, 8):
        xa, ya, wa, ha = geometry(cells[f"n{i}"])
        xb, yb, wb, hb = geometry(cells[f"n{i+1}"])
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
        "Title": "总体建模流程", "Creator": "Render of fig_roadmap.drawio"})
    plt.close(fig)
    print(TARGET)


if __name__ == "__main__":
    run()
