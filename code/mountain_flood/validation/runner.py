"""命令行入口：回放问题二、三归档方案并重算问题四分区。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import json

from mountain_flood.core.domain import Model, RESULT, save
from mountain_flood.problem4.partition import partition
from mountain_flood.validation.replay import validate

def run():
    model = Model()
    output = {}
    for question in (2, 3):
        data = json.loads((RESULT / f"q{question}.json").read_text(encoding="utf8"))
        output[str(question)] = validate(model, data, question)
        if question == 3:
            partition(model, data)
    save("validation.json", output)
    print(output, flush=True)

if __name__ == "__main__":
    run()
