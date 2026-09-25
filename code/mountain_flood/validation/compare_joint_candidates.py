"""重新核验并比较有限集合中的问题三准时联合方案。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import json
import re
from pathlib import Path

from mountain_flood.core.domain import Model, RESULT, save
from mountain_flood.validation.replay import validate


PATTERNS = (
    ('selected_q2_hill1', 'q3_hard_hill1_e*_trim.json'),
    ('alternate_q2_hill0', 'q3_hard_newq2_e*_trim.json'),
    ('prior_q2', 'q3_hard_q2_e*_completion_trim.json'),
    ('prior_q2', 'q3_hard_q2_e*_buffer15_trim.json'),
)


def dominates(a, b):
    keys = ('joint_completion_s', 'weighted_arrival_s', 'total_energy_kwh')
    av = [a[k] for k in keys]
    bv = [b[k] for k in keys]
    return all(x <= y + 1e-7 for x, y in zip(av, bv)) and any(x < y - 1e-7 for x, y in zip(av, bv))


def run():
    m = Model()
    rows = []
    for origin, pattern in PATTERNS:
        for path in sorted(RESULT.glob(pattern)):
            certified = path.with_name(path.name.replace('_trim.json', '_margin.json'))
            if certified.exists():
                path = certified
            data = json.loads(path.read_text())
            check = validate(m, data, 3)
            s = data['summary']
            match = re.search(r'_e(\d+)', path.stem)
            row = dict(source=path.name, route_origin=origin,
                       east_window_end_s=int(match.group(1)) if match else None,
                       verified=check['pass_'], late_boxes=check['checks']['late_boxes'],
                       min_due_slack_s=check['checks']['min_due_slack'],
                       transport_flights=s['count'], relay_flights=s['relay_count'],
                       joint_completion_s=s['makespan'],
                       weighted_arrival_s=s['weighted_arrival'],
                       weighted_average_delivery_min=s['weighted_arrival']/sum(b['priority'] for b in m.boxes)/60,
                       total_energy_kwh=s['energy'], transport_energy_kwh=s['transport_energy'],
                       relay_energy_kwh=s['relay_energy'],
                       solver_status=data.get('solver', {}).get('status', 'archived'))
            if not check['pass_']:
                row['errors'] = check['errors']
            rows.append(row)
    feasible = [x for x in rows if x['verified'] and x['late_boxes'] == 0]
    if not feasible:
        raise RuntimeError('No all-on-time verified joint plan')
    for x in rows:
        x['pareto'] = x in feasible and not any(y is not x and dominates(y, x) for y in feasible)
        x['selected'] = False
    selected = min(feasible, key=lambda x:(x['joint_completion_s'], x['weighted_arrival_s'],
                                          x['total_energy_kwh'], x['transport_flights']))
    selected['selected'] = True
    report = dict(protocol=dict(box_delivery_due='hard', box_destination='hard',
                                continuous_communication='required', time_priority='joint completion, then weighted arrival',
                                carbon_factor=None, scope='finite archived route families and east relay windows'),
                  candidates=rows, selected=selected['source'])
    save('joint_comparison.json', report)
    print('JOINT COMPARISON', len(rows), 'verified', len(feasible),
          'selected', selected['source'], 'completion', selected['joint_completion_s'])


if __name__ == '__main__':
    run()
