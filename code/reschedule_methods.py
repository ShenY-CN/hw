"""Apply the revised completion-first common decoder to archived route trials."""
import json

from common import Model, RESULT, save
from compare_methods import decode, refine_timefirst, nondominated
from partition_validate import validate
from solve_transport import metrics


def run(seconds=8):
    m = Model()
    archive = json.loads((RESULT / 'method_comparison.json').read_text())
    candidates = []
    for trial in archive['trials']:
        original = decode(m, trial['plan'])
        if original is None:
            raise RuntimeError(('invalid archived route plan', trial['method'], trial['seed']))
        routes, solver = refine_timefirst(m, original, seconds=seconds)
        if routes is None:
            raise RuntimeError(('no hard-feasible schedule', trial['method'], trial['seed'], solver))
        check = validate(m, dict(routes=routes), 2)
        if not check['pass_']:
            raise RuntimeError((trial['method'], trial['seed'], check['errors']))
        candidates.append(dict(method=trial['method'], seed=trial['seed'], routes=routes,
                               metrics=metrics(m, routes), solver=solver, validation=check))
        print('RESCHEDULE', trial['method'], trial['seed'], candidates[-1]['metrics']['makespan'], flush=True)
    baseline = next(x for x in archive['candidates'] if x['method'] == 'existing_baseline')
    candidates.append(dict(method='existing_baseline', seed=None, routes=baseline['routes'],
                           metrics=metrics(m, baseline['routes']), solver={'status':'archived'},
                           validation=validate(m, dict(routes=baseline['routes']), 2)))
    feasible = [x for x in candidates if x['validation']['pass_'] and x['metrics']['hard_violations'] == 0]
    frontier = nondominated(feasible)
    selected = min(feasible, key=lambda x:(x['metrics']['makespan'], x['metrics']['weighted_arrival'],
                                           x['metrics']['energy'], x['metrics']['count']))
    for x in candidates:
        x['on_frontier'] = x in frontier
        x['selected'] = x is selected
    archive['candidates'] = candidates
    archive['protocol']['schedule_seconds'] = seconds
    archive['protocol']['decoder_objective'] = ['hard_due','makespan','weighted_arrival']
    archive['protocol']['objective'] = ['all_boxes_on_time','makespan','weighted_arrival','energy','count']
    save('method_comparison.json', archive)
    save('q2_time_energy_candidate.json', dict(routes=selected['routes'], summary=selected['metrics'],
                                               source=dict(method=selected['method'], seed=selected['seed'],
                                                           algorithm_comparison='method_comparison.json')))
    print('SELECTED', selected['method'], selected['seed'], selected['metrics'], flush=True)


if __name__ == '__main__':
    run()
