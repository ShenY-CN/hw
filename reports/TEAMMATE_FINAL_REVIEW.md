# 最终图表审查（终稿图表专项）

执行：图表终稿专项（Codex 辅助）　日期：2026-09-27
依据：`teammate_final_figures_prompt.md`；主负责人批准：图 9-1 用**密版**、**批准覆盖**、图 8-2 维持方案 B。
范围：13 张目标图重出并落地到正文引用路径；**未修改任何 `.tex`**。

---

## 0. 结论

13 张图已全部重出并覆盖到正文引用路径（`figures/paper_full_20260926/`、`figures/audit_verified_20260925/`），
隔离编译验证通过：**0 致命错误、66 页、告警集合与改前完全一致**，无缺图/无尺寸告警。
数据零改动；其中 2 处数据来源与排版限制需主负责人知悉（见 C 节）。

> 过程说明：本专项第一版成果（脚本修改 + `final_review.py` + 审阅图组 + 本报告）在 2026-09-27 04:22 被一次外部
> 仓库同步/重置清除（当时 `git status` 变为完全干净）。全部内容已按原方案重建并落地，工程脚本与原始图备份均另存于
> 本机工作区，可随时恢复。

---

## A. 必须修（影响正确性/理解）——已处理

| 图 | 问题 | 处理 | 数据 |
|---|---|---|---|
| 图 7-4 | 纵轴范围过大，0.09378 dB 的最小裕度贴在横轴上无法辨识 | 主图保留全时域下包络；新增 T021a 最小区间局部放大 inset，标注"最小证书裕度 = 0.09378 dB" | 未改（取 `results/q3.json` 的 4061 个区间） |
| 图 7-5 | 缺乏"为何该区间计入 10 dB 遮挡"的物理标注 | 新增最大遮挡箭头标注；剖面按**模型自用采样规则**重建，复算 **29.47 m**，与表 7-2 一致 | 未改 |
| 图 9-1 | 只画到 10/20/30，未体现 25%/35% 与 35.2678% 可行边界 | **密版（已批准）**：10/20/25/30/35 + `x=35.2678%` 竖线 + 不可行浅阴影 + 逐点数值标注 | 25%/35% 取表 5-6 定稿值（见 C-1） |
| 图 5-5 | 图意与图题不一致（图主要表达 SOC） | 强化 SOC：20% 线加粗、逐架次 S0xx 标签、最低 SOC 单独圈注并标数值 | 未改 |
| 图 8-3 | 纵轴名"累计飞行工作时长"与论文定义（含准备/装载/交接/返航）不符 | 纵轴改为"累计运输任务时长 / h"；两子图统一纵轴；保留箱数；加 CV 小字标注（0.9243 / 1.0335） | 未改 |

### 图 7-5 采样口径诊断（供核查）

| 采样方式 | 最大遮挡高度 |
|---|---|
| 均匀 1.0 m | 30.08 m |
| 均匀 5.0 m | 29.94 m |
| 均匀 30 m | 29.81 m |
| **模型自用规则（连线与经纬网格交点→像元中点，174 点）** | **29.47 m ← 与表 7-2 一致** |
| 栅格交点 | 30.06–30.10 m |

端点几何与表 7-2 逐项一致：运输机海拔 293.23 m、网关海拔 147.70 m、水平距离 3910.32 m、三维距离 3913.03 m。
结论：表 7-2 的 29.47 m 来自模型"像元中点"采样；出图采用同一口径，故图上标注与论文一致。**未改动任何论文数值。**

---

## B. 建议修（观感与可读性）——已处理

| 图 | 处理要点 |
|---|---|
| 图 5-3 | 图高 3.2→3.9 in，轴标签/刻度字号增大，可用能量线与最大安全载荷线加粗，三子图样式统一 |
| 图 6-1 | 单站航线弱化（alpha 0.28、lw 0.7）；多站航线加粗（lw 1.7）并加方向箭头；DEM 透明度 0.55；服务区标签 7.5 pt；图例区分单站/多站 |
| 图 6-3 | 三态可区分：任务占用（机型色）/充电（灰底斜线 hatch+深灰边）/空闲（白底灰边图例），X 轴限制到全时段 |
| 图 6-6 | 最紧航次 T010 黑边强调 + 标注"T010 最低 20.4065%"，保留 20% 安全线 |
| 图 7-1 | W/E/N 悬停点菱形放大到 150、加黑边与描边文字标签；R01/R02 采样分层设色；DEM 透明度 0.6；服务区标签降权 |
| 图 8-1 | 各不可拆组件质心直接标 C1–C8（白描边）；图例压缩为 4 列 |
| 图 8-2 | 地图有效区放大（DEM 降权、标记 72、标签 8.5 pt 白描边）、组内淡色凸包、图例单行含箱数；**上下排列未做（需改 tex）** |
| 图 8-4 | 缺口资源柱顶直接标 `+1/+2`（只标真正缺口的资源类型），增加顶部留白 |

---

## C. 需要正文负责人同步（本分支不改 tex）

- **C-1 图 9-1 的 25%/35% 数据来源**：仓库 `results/` 仅有 `q1_rho10/20/30/40.json`，没有 25%/35% 的结果文件；表 5-6 的 25%（19 架次、61.0734 kWh）与 35%（25 架次、75.6076 kWh）全仓只出现在 `paper/sections/5_problem1.tex`，图 5-6 的 `q1_change.png` 也无生成脚本。密版图以常量 `SENSITIVITY_TABLE_POINTS` 显式引用表 5-6 定稿值（不重算、不插值）。若希望每点都可追溯到结果文件，需单批准重跑 ρ=25%/35% 的 Q1 组批。
- **C-2 图 5-5 图题**：现为"18个架次的运输能耗与返航剩余电量"，图实际表达 SOC。建议改为"18个运输架次的返航剩余电量"或"问题一18个运输架次的返航SOC"。
- **C-3 第 9 章表述**：`9_sensitivity.tex` 现写"第5章给出了更密的扫描"；图 9-1 改密版后建议与该句统一口径。
- **C-4 图 5-6 与图 9-1 内容重复**：两者都是 Q1 安全余量扫描，建议明确分工（一密一疏）。
- **C-5 图 8-2 排列**：正文以两个 `.48\textwidth` 并排，无法在不改 tex 的前提下改为上下 (a)/(b)；本轮按方案 B 强化单图可读性。
- **C-6 图 6-1 图例**：图例由 3 条增至 5 条，若版面偏挤可将 `\includegraphics` 宽度由 `.82\textwidth` 调到 `.88\textwidth`（属正文改动）。

---

## D. 落地记录

| 项目 | 内容 |
|---|---|
| 覆盖目标（12 张 × pdf/png/svg） | `figures/paper_full_20260926/`：q1_payload_energy、q1_return_soc、q1_sensitivity、q2_transport_routes、q2_battery_timeline、q2_return_soc、q3_relay_coverage_points、q4_task_network、q4_partition_2groups、q4_partition_3groups、q4_workload、q4_resource_demand（另含 3 个 `.alignment.json`） |
| 覆盖目标（2 张 × pdf） | `figures/audit_verified_20260925/`：q3_margin_envelope、q3_tight_los_profile（该目录原本只有这两个图的 PDF；PNG/SVG 版本存于 `figures/final_20260927/`） |
| 覆盖文件数 | 41 |
| 哈希校验 | 目标文件与生成源逐字节一致（不一致项 0） |
| 生成源图组 | `figures/final_20260927/`（15 组，含图 9-1 备选版） |
| 原图备份 | 本机工作区 `work/figure_backup_20260927/`（41 个原文件，可回退） |
| 新图备份 | 本机工作区 `work/figure_new_20260927/`（42 个文件） |

**涉及脚本（4 改 1 增）**

| 文件 | 改动 |
|---|---|
| `code/mountain_flood/figure/common.py` | `draw_region()` 新增 `terrain_alpha`、`service_label_size`、`service_marker_size`（默认值保持原行为） |
| `code/mountain_flood/figure/q1.py` | 重写 `plot_payload_energy`、`plot_return_soc`、`plot_sensitivity`；新增 `plot_sensitivity_compact` 与常量 `RHO_FEASIBLE_LIMIT`、`SENSITIVITY_TABLE_POINTS` |
| `code/mountain_flood/figure/q2.py` | 重写 `plot_routes`、`plot_battery_timeline`、`plot_return_soc` |
| `code/mountain_flood/figure/q3.py` | 重写 `plot_relay_coverage_points`；新增 `patheffects` 导入 |
| `code/mountain_flood/figure/q4.py` | 重写 `_plot_partition_map`、`plot_resource_demand`、`plot_workload`、`plot_task_network`；新增 `patheffects`/`Polygon`/`ConvexHull` 导入 |
| `code/mountain_flood/figure/final_review.py` | **新增**：图 7-4、图 7-5 与 13 张终稿图统一入口 `run()` |

---

## E. 编译验证（隔离副本树，未写入仓库）

| 指标 | 结果 |
|---|---|
| 命令 | `xelatex -interaction=nonstopmode -halt-on-error main.tex`（连跑 3 遍收敛） |
| 退出码 | 0 / 0 / 0 |
| 致命错误 | 0 |
| 输出 | `main.pdf`，**66 页** |
| 缺图 / 无法确定尺寸告警 | 0 |
| Overfull \hbox | 1（改前基线为 2） |
| Underfull \hbox | 48（改前基线 49） |
| 告警集合 | 与改前完全一致（仅 STXinwei/SimHei/SimSun 字型回退、hyperref 书签层级、字体形状提示，均预存在） |

---

## F. 红线核查

| 核查项 | 结果 |
|---|---|
| 是否修改任何 `.tex` | **否**（`git status` 中无 `.tex` 变更） |
| 是否重新求解 Q1–Q4 | 否（图 9-1 密版仅引用表 5-6 定稿值） |
| 是否改动 `results/` | 否（仅只读读取 q1_rho20/q2/q3/q4/solution_certificate） |
| 是否改动正式结果数字 | 否 |
| 面板对齐自检 | 多面板图 max_deviation = 0.00 pt，全部通过 |
| 中文字形 | 15 张 PDF 文本抽取均可还原中文标签，无缺字 |

---

## G. 提交建议（`.git` 对沙箱只读，提交须由主负责人执行）

```bash
git checkout -b final-figures-review      # 可选；也可直接在 main
git add code/mountain_flood/figure figures reports/TEAMMATE_FINAL_REVIEW.md
git commit -m "finalize paper figures and visual review"
```

注意：
1. 不要 `git add paper/main.aux/log/out/pdf/toc/synctex.gz/missfont.log`（编译产物，仓库已跟踪但会持续产生噪声）。
2. 需要清理的临时目录：`figures/final_20260927/`（生成源图组，可保留备查，也可删除后仅保留覆盖后的图）。
3. 提交前如再做一次 `git status`，应只看到 `code/mountain_flood/figure/*`、`figures/**`、`reports/TEAMMATE_FINAL_REVIEW.md`。
