# 跨媒介一致性审计（2026-09-26）

| 审计项 | 状态 | 证据与范围 |
|---|---|---|
| 附件→共享模型→正式Q1–Q4 JSON | PASSED | `check_consistency.py`逐箱/逐航次回放；隔离目录全流程PASS |
| 四算法同预算与设计差异标注 | PASSED | `results/q2_formal_protocol.json`；每种子四法共享独立初始解，4法×10种子、30次有效评估、90 s墙钟保护；论文比较返航时间、能耗、架次的均值±标准差 |
| Q1→Q2→Q3→Q4数据继承 | PASSED | Q3路线为Q2箱组拆分；Q4固定Q3任务；报告第6节 |
| 数学公式→代码 | PASSED | `reports/audits/equation_code_mapping.md` |
| 正式JSON→提交表逐行 | PASSED | `check_consistency.py`检查Q2/Q3所有航次与逐箱交付 |
| JSON→论文图与表 | PASSED | `reports/audits/figure_result_mapping.csv`逐项记录37个图像文件和29个表格引用；34张结果/空间图由当前绘图流程生成（33张在`paper_full_20260926`，另有总体路线图），另有3张原始输入概览图。Q2搜索比较图已改由`q2_formal_protocol.json`生成。 |
| 当前LaTeX源→编译PDF | PASSED | XeLaTeX生成54页A4 PDF；根目录副本哈希相同，36个图号、37个图像路径均已解析，未见空白页、裁切或重叠。 |

**结论：**模型数据、代码、JSON、提交表、图表映射和LaTeX源一致；PDF已更新为本次修订版本；封面身份信息仍由参赛队填写。完整分级与结论见`reports/当前方案一致性审计报告.md`。
