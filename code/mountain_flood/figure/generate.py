"""在 figures/ 下为每次生成建立独立图组目录。"""

from pathlib import Path
import argparse
from datetime import datetime
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(PROJECT_ROOT / "code"), str(PROJECT_ROOT)]


def run(name=None):
    if name is None:
        name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = PROJECT_ROOT / "figures" / name
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError(f"图组目录已有文件：{folder}")
    os.environ["MOUNTAIN_FLOOD_FIGURE_SET"] = name
    from mountain_flood.figure import q1, q2, q3, q4, spatial, overview

    for module in (q1, q2, q3, q4, spatial, overview):
        module.run()
    from mountain_flood.figure.common import update_figure_manifest
    update_figure_manifest()
    print(f"图组完成：{folder}")
    return folder


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将本次全部论文配图写入独立子目录")
    parser.add_argument("--name", help="图组子目录名；默认使用当前时间")
    args = parser.parse_args()
    run(args.name)
