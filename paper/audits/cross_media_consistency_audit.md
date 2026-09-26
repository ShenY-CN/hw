# 跨媒介一致性审计（2026-09-25）

| 审计项 | 状态 | 证据与范围 |
|---|---|---|
| 附件→共享模型→正式Q1–Q4 JSON | PASSED | `check_consistency.py`逐箱/逐航次回放；隔离目录全流程PASS |
| 四算法同预算与设计差异标注 | PASSED | `reports/audits/model_comparison_alignment.csv`；历史候选明确单列 |
| Q1→Q2→Q3→Q4数据继承 | PASSED | Q3路线为Q2箱组拆分；Q4固定Q3任务；报告第6节 |
| 数学公式→代码 | PASSED | `reports/audits/equation_code_mapping.md` |
| 正式JSON→提交表逐行 | PASSED | `check_consistency.py`检查Q2/Q3所有航次与逐箱交付 |
| JSON→论文图与表 | PASSED | `reports/audits/figure_result_mapping.csv`，11图+6表；图组`audit_verified_20260925` |
| 当前LaTeX源→编译PDF | PASSED | 使用临时Tectonic 0.17.0生成19页PDF；根目录副本哈希相同，中文和关键数字可提取，抽页视觉检查通过 |

**结论：**模型数据、代码、JSON、提交表、正式图和LaTeX源一致；PDF已更新为本次修订版本；封面身份信息仍由参赛队填写。完整分级与结论见`reports/当前方案一致性审计报告.md`。
