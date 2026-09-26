# MATLAB 绘图版

这是 `code/mountain_flood/figure` 的 MATLAB 对照实现，读取项目 `results/` 中已核验的 JSON，不重新求解模型。当前移植了 16 张基于结果数据的图，包括载荷散点/热力图、任务时间线、搜索方案比较、通信裕量以及资源需求和缺口。地图、DEM 底图和 DrawIO 技术路线图仍由原 Python/DrawIO 脚本生成。

在 MATLAB 中运行本目录的 `run_all.m`。PNG 预览与嵌入式栅格 PDF 会写入项目根目录 `figures_matlab/`，不会覆盖 `figures/` 里的 Python 版本。

脚本使用 MATLAB 基础绘图函数，中文字体默认设为 macOS 的 PingFang SC；其他系统可把 `run_all.m` 开头的字体改为本机可用的中文字体。
