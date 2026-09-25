"""重算单服务区组批方案及不同返航储备比例下的敏感性结果。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
from mountain_flood.core.domain import Model, save
from mountain_flood.problem1.packing import q1


def run():
    m = Model()
    for pct in (10, 20, 30, 40):
        save(f'q1_rho{pct}.json', q1(m, pct / 100))
        print('Q1 reserve', pct, flush=True)
    for objective in ('energy', 'time'):
        save(f'q1_{objective}.json', q1(m, .2, objective))
        print('Q1 objective', objective, flush=True)


if __name__ == '__main__':
    run()
