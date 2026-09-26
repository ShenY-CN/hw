# 参考文献核对记录

## 范围与结论

- 题目文件《山区洪涝灾害下无人机运输与通信协同优化.docx》中的10条参考文献均已保留在论文参考文献表中。
- 在这10条中，Dorling、Zhang、ITU-R三条原已在论文中；其余7条已补入。
- 另补6篇可追溯文献，覆盖车辆路径问题、时间窗、随机贪心构造、模拟退火/禁忌搜索及无人机配送。
- 参考文献总数：20篇。正文引用与`\bibitem`键逐项匹配；每条均在正文至少引用一次。
- `references.tex`是当前LaTeX手工编号的实际书目；`refs.bib`保存同一批20条的结构化BibTeX元数据，供后续迁移或编辑使用。

## 引用—论据核对

| 键 | 核对结果 | 正文位置与用途 | 来源记录 |
|---|---|---|---|
| `xinhuaField` | 已核实 | 第1节；洪水导致道路、通信中断及无人机投送背景 | [新华网原文](https://www.xinhuanet.com/politics/20260709/acf8e4b353304bb78007d8224f1cd2ef/c.html) |
| `xinhuaIsland` | 已核实 | 第1节；孤岛状态、徒步补给和救援背景 | [新华网原文](https://www.news.cn/local/20260712/8bd1f64af3124569b5cf4415fc013acd/c.html) |
| `copernicus` | 已核实 | 第2节；DEM产品来源背景；具体栅格参数仍来自题目附件 | [Copernicus DEM官方说明](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) |
| `djiM350` | 已核实 | 第2节；专业无人机公开规格作工程背景，不替代题给机型参数 | [DJI官方规格](https://enterprise.dji.com/matrice-350-rtk/specs) |
| `doodleSense` | 已核实 | 第2节；厂商公布的抗干扰功能作通信工程背景，不替代题给链路参数 | [Doodle Labs原文](https://doodlelabs.com/news/sense-interference-avoidance-release/) |
| `dorling` | 已核实 | 第2节；无人机配送路径及载荷相关能耗模型 | [IEEE DOI记录](https://doi.org/10.1109/TSMC.2016.2582745) |
| `zhang` | 已核实 | 第2节；配送无人机能耗模型综述与适用边界 | [Elsevier DOI记录](https://doi.org/10.1016/j.trd.2020.102668) |
| `tiCharger` | 已核实 | 第2节；锂电池充电控制工程背景；本题充电参数仍以附件为准 | [TI官方应用报告](https://www.ti.com/lit/an/slaa287b/slaa287b.pdf) |
| `itur` | 已核实 | 第2节；自由空间损耗定义及计算依据 | [ITU-R建议书](https://www.itu.int/rec/R-REC-P.525-5-202411-I/en) |
| `zeng` | 已核实 | 第2节；无基础设施覆盖时的无人机辅助无线通信背景 | [IEEE DOI记录](https://doi.org/10.1109/MCOM.2016.7470933) |
| `dantzigramser` | 已核实 | 第6节；车辆路径问题的早期路由基础 | [INFORMS期刊记录](https://pubsonline.informs.org/doi/10.1287/mnsc.6.1.80) |
| `solomon` | 已核实 | 第6节；带时间窗车辆路径与调度算法 | [INFORMS期刊记录](https://pubsonline.informs.org/doi/10.1287/opre.35.2.254) |
| `tothvigo` | 已核实 | 第6节；车辆路径问题方法总览 | [SIAM DOI记录](https://doi.org/10.1137/1.9781611973594) |
| `macrina` | 已核实 | 第6节；无人机辅助配送路径领域综述；仅作为相邻问题背景 | [Elsevier文章记录](https://www.sciencedirect.com/science/article/pii/S0968090X20306744) |
| `murraychu` | 已核实 | 第6节；卡车—无人机协同配送经典问题；正文明确与本题设定不同 | [Elsevier文章记录](https://www.sciencedirect.com/science/article/pii/S0968090X15000844) |
| `kirkpatrick` | 已核实 | 第6节；模拟退火算法依据 | [Science DOI记录](https://doi.org/10.1126/science.220.4598.671) |
| `glover` | 已核实 | 第6节；整数规划与智能搜索方法背景 | [Elsevier DOI记录](https://doi.org/10.1016/0305-0548(86)90048-1) |
| `osman` | 已核实 | 第6节；模拟退火、禁忌搜索在车辆路径问题中的应用 | [Springer文章记录](https://link.springer.com/article/10.1007/BF02023004) |
| `ortools` | 已核实 | 第6节；固定路线资源排程采用CP-SAT的实现文档 | [Google OR-Tools文档](https://developers.google.com/optimization/cp/cp_solver) |
| `feo` | 已核实 | 第6节；随机贪心构造的一般方法背景；正文声明本实现不是标准GRASP | [Springer文章记录](https://link.springer.com/article/10.1007/BF01096763) |

## 核对说明

新闻报道、官方数据/产品/标准网页和厂商应用报告按其原始发布机构核对标题、日期与网址；期刊论文按出版方页面或DOI记录核对作者、刊名、卷期、页码和DOI。补充的无人机配送研究是相邻领域文献，论文没有把卡车—无人机协同模型误称为本题模型。GRASP来源仅作为随机贪心构造的背景，不宣称程序实现了标准GRASP。所有具体机型参数、充电比例、通信频率与门限均以赛题附件为准。
