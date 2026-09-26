# 论文数值表

本目录中的 `.tex` 表格由 `code/generate_paper_tables.py` 从 `results/` 的正式结果和 `results/data_profile.json` 生成，论文各章节通过 `\input{tables/表名}` 引用。

更新正式结果后，在项目根目录运行 `python code/generate_paper_tables.py`，再重新编译 `paper/main.tex`。章节中直接写入的解释性表格和已有算法比较表仍在 `paper/sections/`。逐箱交付的完整清单保存在根目录 `D题结果提交表.xlsx`。
