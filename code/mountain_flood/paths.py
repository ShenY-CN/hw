"""统一定义项目根目录、输入目录和结果目录。"""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
INPUT = Path(os.environ.get("D_INPUT", str(ROOT / "input")))
RESULT = ROOT / "results"
RESULT.mkdir(parents=True, exist_ok=True)
