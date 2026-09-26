"""Publication schematic for the four-question modeling evidence chain.

Figure contract
---------------
Core conclusion: the four questions pass concrete intermediate results forward
as constraints increase from single-zone capacity to transport, communication,
and independent resource configuration; the resulting plans are replay-checked.
Results-level question: what is inherited at each step, and how is the final
plan's feasibility established?
Archetype: single-panel workflow schematic (schematic-led figure).
Target/output: mathematical-modeling paper, 180 x 135 mm, editable PDF/SVG text.
Evidence hierarchy: four-question handoff chain is primary; shared physical rules,
constraint progression, and final replay checks support that chain.
Statistics/source data: not applicable; this is a method schematic, not a plot.
Reviewer risk: do not imply global optimality for the finite Q2/Q3 candidate search.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[3]
FIGURE_DIR = ROOT / "figures"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
OUT = FIGURE_DIR / "fig_roadmap_nature"

from audit_panel_alignment import require_matplotlib_panel_alignment


WIDTH_MM = 180.0
HEIGHT_MM = 135.0

INK = "#243746"
MUTED = "#607586"
LINE = "#647D91"
BORDER = "#AFBDC8"
NEUTRAL = "#F4F7F9"
PALE_BLUE = "#ECF3F8"
SIGNAL = "#315F85"
ACCENT = "#C87936"
PALE_ACCENT = "#FBF2E9"
WHITE = "#FFFFFF"

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["PingFang SC", "Heiti SC", "Arial Unicode MS", "sans-serif"],
        "font.size": 6.2,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.unicode_minus": False,
        "figure.facecolor": WHITE,
        "savefig.facecolor": WHITE,
        "savefig.edgecolor": WHITE,
    }
)


def add_round_box(ax, x, y, width, height, *, face, edge=BORDER, lw=0.65, radius=1.2):
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle=f"round,pad=0.0,rounding_size={radius}",
        linewidth=lw,
        edgecolor=edge,
        facecolor=face,
        zorder=1,
    )
    ax.add_patch(patch)
    return patch


def add_card(ax, x, y, width, height, title, body, *, face=NEUTRAL, edge=BORDER):
    add_round_box(ax, x, y, width, height, face=face, edge=edge)
    pad_x = 2.0
    ax.text(
        x + pad_x,
        y + height - 2.1,
        title,
        color=SIGNAL,
        fontsize=7.1,
        fontweight="bold",
        ha="left",
        va="top",
        zorder=3,
    )
    ax.text(
        x + pad_x,
        y + height - 5.0,
        body,
        color=INK,
        fontsize=6.15,
        linespacing=1.22,
        ha="left",
        va="top",
        zorder=3,
    )


def add_arrow(ax, start, end, *, color=LINE, lw=0.65, scale=6.0):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=scale,
        linewidth=lw,
        color=color,
        shrinkA=0,
        shrinkB=0,
        zorder=2,
    )
    ax.add_patch(arrow)
    return arrow


def add_handoff(ax, source_y, target_y, label, *, source_x=154.0, target_x=30.5):
    """Route a labelled handoff around its label, with a downward arrowhead."""
    mid_y = (source_y + target_y) / 2.0
    label_artist = ax.text(
        91.0,
        mid_y,
        label,
        color=MUTED,
        fontsize=5.35,
        ha="center",
        va="center",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": WHITE, "edgecolor": "none"},
        zorder=4,
    )
    ax.figure.canvas.draw()
    bbox = label_artist.get_window_extent(renderer=ax.figure.canvas.get_renderer())
    label_width_mm = bbox.width / ax.figure.dpi * 25.4 + 1.7
    label_artist.remove()

    label_left = 91.0 - label_width_mm / 2.0
    label_right = 91.0 + label_width_mm / 2.0
    ax.plot([source_x, source_x], [source_y, mid_y], color=LINE, linewidth=0.62, zorder=2)
    ax.plot([source_x, label_right], [mid_y, mid_y], color=LINE, linewidth=0.62, zorder=2)
    ax.plot([label_left, target_x], [mid_y, mid_y], color=LINE, linewidth=0.62, zorder=2)
    add_arrow(ax, (target_x, mid_y), (target_x, target_y), color=LINE, lw=0.62, scale=5.5)
    ax.text(
        91.0,
        mid_y,
        label,
        color=MUTED,
        fontsize=5.35,
        ha="center",
        va="center",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": WHITE, "edgecolor": "none"},
        zorder=4,
    )


def build_figure():
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, WIDTH_MM)
    ax.set_ylim(0, HEIGHT_MM)
    ax.set_axis_off()
    ax.set_facecolor(WHITE)

    # Title and the shared model/data foundation.
    ax.text(
        8.0,
        131.0,
        "山区无人机运输—通信协同：递进建模与可执行性验收",
        color=INK,
        fontsize=11.6,
        fontweight="bold",
        ha="left",
        va="center",
    )
    ax.text(
        8.0,
        126.7,
        "四问逐层增加约束；每一问输出可被下一问继承的方案或边界",
        color=MUTED,
        fontsize=6.7,
        ha="left",
        va="center",
    )

    x0, base_y, base_w, base_h = 14.5, 109.1, 157.5, 13.4
    add_round_box(ax, x0, base_y, base_w, base_h, face=NEUTRAL, edge=LINE, lw=0.8)
    ax.text(
        x0 + base_w / 2,
        base_y + base_h - 2.1,
        "统一数据与公共物理规则",
        color=SIGNAL,
        fontsize=8.0,
        fontweight="bold",
        ha="center",
        va="top",
    )
    ax.text(
        x0 + base_w / 2,
        base_y + base_h - 5.1,
        "输入：DEM · 80箱/15服务区 · 运输机/电池 · 中继设备 · 硬时限 · 通信参数\n"
        "共享：节点与单位 · 航段净空/时间/能耗 · SOC/充电周转 · 双向链路预算",
        color=INK,
        fontsize=6.25,
        linespacing=1.2,
        ha="center",
        va="top",
    )

    # Constraint ladder at left; one neutral family and one restrained signal accent.
    ax.text(
        6.5,
        108.1,
        "约束\n递增",
        color=ACCENT,
        fontsize=5.5,
        fontweight="bold",
        linespacing=1.05,
        ha="center",
        va="top",
    )

    row_y = [88.5, 68.0, 47.5, 27.0]
    row_h = 16.4
    task_x, task_w = 14.5, 32.0
    method_x, method_w = 50.1, 82.0
    output_x, output_w = 135.0, 37.0
    constraint_labels = [
        "载荷\n能量",
        "+硬时限\n+共享设备",
        "+连续通信\n+中继资源",
        "+独立执行\n+禁跨组共享",
    ]
    task_bodies = [
        "安全载荷边界\n单点直送组批",
        "多服务区/多架次\n硬时限与共享机体、电池",
        "运输任务上的通信保障\n中继机与能源组件",
        "固定 Q3 联合任务\n独立分区的配置代价",
    ]
    method_bodies = [
        "DEM净空 → 最大安全载荷二分\n可行批次枚举 → 计数状态动态规划\n目标：少架次，再少飞行能耗",
        "完整路线列 → 四种搜索方法同预算比较\n固定路线 CP-SAT 排机体与电池时序\n逐箱回放服务区、时限与物理可行性",
        "运输候选族 + 中继窗口 → 有限候选协调\n直连/中继判定 → 连续区间链路证书\n归档候选逐一进行硬约束回放",
        "不可拆任务组件 → 两组/三组分区穷举\n事件时刻资源峰值核算\n配置总量、重复配置与库存缺口评价",
    ]
    output_bodies = [
        "安全载荷边界\n可行组批基准",
        "运输路线与架次\n机体/电池时序\n逐箱送达时刻",
        "运输—中继可行候选\n连续通信认证",
        "两组/三组分区\n独立配置与库存缺口",
    ]

    for i, y in enumerate(row_y):
        cy = y + row_h / 2
        # Constraint badges are vertically connected to make the added scope explicit.
        add_round_box(ax, 0.8, cy - 3.6, 11.5, 7.2, face=PALE_ACCENT, edge="#D6AA7B", lw=0.55, radius=0.9)
        ax.text(
            6.55,
            cy,
            constraint_labels[i],
            color=INK,
            fontsize=5.15,
            linespacing=1.08,
            ha="center",
            va="center",
        )

        task_titles = ["Q1 · 能力基准", "Q2 · 运输调度", "Q3 · 通信协同", "Q4 · 资源配置"]
        add_card(ax, task_x, y, task_w, row_h, task_titles[i], task_bodies[i], face=NEUTRAL)
        add_card(ax, method_x, y, method_w, row_h, "求解过程", method_bodies[i], face=WHITE)
        add_card(ax, output_x, y, output_w, row_h, "本问输出", output_bodies[i], face=PALE_BLUE, edge="#91AFC4")

        add_arrow(ax, (task_x + task_w, cy), (method_x, cy))
        add_arrow(ax, (method_x + method_w, cy), (output_x, cy))

        if i < len(row_y) - 1:
            next_center = row_y[i + 1] + row_h / 2
            add_arrow(ax, (6.55, cy - 3.6), (6.55, next_center + 3.6), color="#C49363", lw=0.55, scale=5.2)

    # Shared rules feed the first solution stage.
    add_arrow(ax, (91.0, base_y), (91.0, row_y[0] + row_h), color=LINE, lw=0.7, scale=5.7)

    handoffs = [
        "继承：安全载荷、航段时间/能耗与组批基准",
        "继承运输候选与时窗；增加全过程连续通信约束",
        "固定 Q3 箱组、站序、运输/中继任务及通信关系",
    ]
    for i, label in enumerate(handoffs):
        source_bottom = row_y[i]
        target_top = row_y[i + 1] + row_h
        add_handoff(ax, source_bottom, target_top, label)

    # Final executable-plan replay and evidence package.
    verify_x, verify_y, verify_w, verify_h = 8.0, 7.2, 164.0, 12.8
    add_round_box(ax, verify_x, verify_y, verify_w, verify_h, face=PALE_BLUE, edge=SIGNAL, lw=0.8)
    ax.text(
        verify_x + 5.0,
        verify_y + verify_h - 2.0,
        "全流程回放验收与成果交付",
        color=SIGNAL,
        fontsize=8.0,
        fontweight="bold",
        ha="left",
        va="top",
    )
    ax.text(
        verify_x + 5.0,
        verify_y + verify_h - 4.9,
        "回放：逐箱目的地/时限 · 逐航次载荷/能耗/返航储备 · 机体/电池/中继周转 · 连续通信区间\n"
        "交付：可执行方案、资源缺口、结果表图与复现材料",
        color=INK,
        fontsize=6.15,
        linespacing=1.17,
        ha="left",
        va="top",
    )
    add_arrow(ax, (153.5, row_y[3]), (153.5, verify_y + verify_h), lw=0.65, scale=5.5)
    ax.text(
        150.5,
        23.4,
        "逐层产出进入统一回放验收",
        color=MUTED,
        fontsize=5.2,
        ha="right",
        va="center",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": WHITE, "edgecolor": "none"},
        zorder=4,
    )

    ax.text(
        8.0,
        3.15,
        "范围：Q1 仅对单点直送模型精确；Q2/Q3 结论限于实际搜索或归档候选；Q4 固定 Q3 任务后核算分区资源。",
        color=MUTED,
        fontsize=5.25,
        ha="left",
        va="center",
    )

    fig.canvas.draw()
    require_matplotlib_panel_alignment(
        fig,
        json_out=f"{OUT}.alignment.json",
        overlay_svg=f"{OUT}.alignment.svg",
        tolerance_pt=1.5,
        gutter_tolerance_pt=1.5,
        strict=True,
    )

    fig.savefig(f"{OUT}.pdf", facecolor=WHITE, bbox_inches=None)
    fig.savefig(f"{OUT}.svg", facecolor=WHITE, bbox_inches=None)
    fig.savefig(f"{OUT}.png", dpi=300, facecolor=WHITE, bbox_inches=None)
    fig.savefig(
        f"{OUT}.tiff",
        dpi=600,
        facecolor=WHITE,
        bbox_inches=None,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    return fig


if __name__ == "__main__":
    figure = build_figure()
    plt.close(figure)
    print(f"Wrote {OUT}.pdf, .svg, .png, and .tiff")
