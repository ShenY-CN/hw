# D题解答与复现

本目录保存原始附件、计算代码、结果提交表、论文源码和验收报告。数值结果的权威来源是 `results/*.json`，提交表和图表由代码从这些结果生成。

## 一键复现

使用 Python 3.12 和 `requirements.lock` 列出的精确版本安装依赖，然后从项目根目录执行：

```sh
python -m pip install -r requirements.lock
python code/reproduce.py --output /path/to/new-empty-output
```

输出目录必须尚不存在。脚本复制原始输入与代码，按顺序重算第一至第四问、约束校验、八张提交表和八组 PDF/PNG 图，并写入 `results/复现清单.json`，记录输入与代码哈希、依赖版本、随机种子及关键指标。完整计算可能需要较长时间。可用 `python code/export_submission.py` 从当前 `results/` 更新根目录提交表。

## 主要文件

- `D题结果提交表.xlsx`：按附件模板填写的八张结果表。
- `reports/RESULTS_REPORT.md`：当前方案与指标。
- `reports/VERIFY_REPORT.md`：按已批准的候选搜索方案，交付验收为PASS；第二问首要迟到目标已证最优，第二问其余目标及第三问的全局最优性主张仍为FAIL。
- `reports/REMEDIATION_PLAN.md`：修复步骤与剩余工作。
- `D题论文.pdf`：依据当前结果重新编译的20页中文论文。
- `paper/main.tex`、`paper/sections/`：中文论文源码；在 `paper/` 运行两遍 XeLaTeX，或运行 `tectonic --reruns 2 main.tex` 重建PDF。中文字体需有 Songti SC、Heiti SC、Kaiti SC。
- `figures/`：由 `code/figures.py` 生成的图。

## 模型边界

水平和爬升能耗依照本方案对附件参数的明示展开，未由实测功率标定。第一问在批准模型内用动态规划精确求解；第二问加权迟到为零，达到该非负首要指标的全局下界，但后续字典序指标未证最优。第三问对有限路线、中继点与服务窗口进行优化并作连续通信回代，不能宣称全局最优。第四问只对第三问固定任务时间表枚举分区。第三问最小通信裕量约0.0061 dB，仅证明标称参数下可行。
