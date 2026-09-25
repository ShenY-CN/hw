"""将公开方案归档路线与本题官方逐箱目的地进行核对。

用法：python code/audit_public_reference.py /公开方案仓库路径
"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import argparse
import json
from pathlib import Path

from mountain_flood.core.domain import Model, save


def audit(m, name, flights):
    by_id = {b['id']: b for b in m.boxes}
    seen = []
    mismatches = []
    for flight in flights:
        for stop, ids in flight['route']:
            for bid in ids:
                seen.append(bid)
                expected = m.nodes[by_id[bid]['node']]['id']
                if stop != expected:
                    mismatches.append(dict(flight=flight['fid'], box=bid,
                                           listed_stop=stop, required_stop=expected))
    return dict(name=name, flights=len(flights), boxes_listed=len(seen),
                unique_boxes=len(set(seen)), destination_errors=len(mismatches),
                affected_flights=len({x['flight'] for x in mismatches}),
                mismatches=mismatches)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repository', type=Path)
    args = ap.parse_args()
    root = args.repository / '求解代码与结果'
    sample = json.loads((root / '实验/samples/best_tabu_s7.json').read_text())
    pareto = json.loads((root / 'results/p2_pareto.json').read_text())
    m = Model()
    report = dict(source='https://github.com/Akun-python/mountain-flood-uav-optimization',
                  audited_witnesses=[audit(m, '21-flight archived Tabu seed 7', sample['flights']),
                                     audit(m, '26-flight archived balanced', pareto['balanced']['flights'])],
                  note='The separate 21-flight 62.46 kWh Pareto entry has metrics but no flight witness in p2_pareto.json.')
    save('public_reference_audit.json', report)
    for row in report['audited_witnesses']:
        print(row['name'], 'wrong destinations', row['destination_errors'],
              'affected flights', row['affected_flights'])


if __name__ == '__main__':
    main()
