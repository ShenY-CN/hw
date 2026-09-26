"""生成与正式证据链一致的总体建模流程图。"""

from pathlib import Path
import os
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[3]
cache = Path(tempfile.gettempdir()) / "mountain_flood_plot_cache"
os.environ.setdefault("MPLCONFIGDIR", str(cache / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(cache / "xdg"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Heiti SC"],
                     "axes.unicode_minus": False, "pdf.fonttype": 42, "svg.fonttype": "none"})

OUT = PROJECT_ROOT / "figures" / "rigor_pool_20260926"


def box(ax, xy, size, title, body, color):
    x, y = xy; w, h = size
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.018,rounding_size=.025",
                                linewidth=1.4, edgecolor=color, facecolor=color + "18"))
    ax.text(x + .025, y + h - .055, title, fontsize=11, fontweight="bold", color=color, va="top")
    ax.text(x + .025, y + h - .105, body, fontsize=8.2, color="#263442", va="top", linespacing=1.35)


def arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14,
                                linewidth=1.5, color="#65727F"))


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11.5, 7.0))
    ax.set(xlim=(0, 1), ylim=(0, 1)); ax.axis("off")
    ax.text(.5, .965, "山区无人机运输—通信—分区配置证据链", ha="center",
            va="top", fontsize=15, fontweight="bold", color="#213547")

    box(ax, (.04, .70), (.25, .18), "统一输入与物理回放",
        "80箱 / 15服务区 / DEM\n载荷—能耗、硬时限\n机体、电池与充电占用", "#315E9D")
    box(ax, (.375, .70), (.25, .18), "Q1  单点直送DP",
        "枚举可行批次模式\nBellman词典序转移\n限定模型内精确最优", "#258A91")
    box(ax, (.71, .70), (.25, .18), "Q2  两层VRPTW调度",
        "路线列启发式 → 固定路线CP-SAT\n共享24架次warm-start\n4法×10种子×固定3评估", "#B64A60")
    arrow(ax, (.29, .79), (.375, .79)); arrow(ax, (.625, .79), (.71, .79))

    box(ax, (.12, .39), (.34, .20), "Q3  连续通信子问题",
        "区间距离/遮挡上界证书\n同一中继：接入与回程同时成立\n32个有限候选，返回可行性与裕度", "#69549A")
    box(ax, (.54, .39), (.34, .20), "有限分解协调边界",
        "运输族 + 中继窗口 → 连续证书\n当前无通信冲突割回传接口\n不宣称强联合或全局最优", "#CE853D")
    arrow(ax, (.835, .70), (.71, .59)); arrow(ax, (.46, .49), (.54, .49))

    box(ax, (.20, .10), (.60, .18), "Q4  固定Q3任务的两组/三组分区",
        "不可拆组件 → 事件时刻资源峰值 → 穷举分组\n分别报告 duplicated（重复配置）、unused（库存闲置）、deficit（库存缺口）\n最终逐箱、逐航次、逐资源、逐通信区间回放验收", "#315E9D")
    arrow(ax, (.71, .39), (.56, .28))
    ax.text(.5, .025, "结论边界：小协议未发现新Pareto点；结果是可执行见证，不是全局最优证明",
            ha="center", fontsize=8.5, color="#536273")
    fig.subplots_adjust(0, 0, 1, 1)
    for ext in ("pdf", "png", "svg"):
        kwargs = {"dpi": 300} if ext == "png" else {}
        fig.savefig(OUT / f"flow_overall_model.{ext}", **kwargs)
    plt.close(fig)
    print(OUT / "flow_overall_model.pdf")


if __name__ == "__main__":
    run()
