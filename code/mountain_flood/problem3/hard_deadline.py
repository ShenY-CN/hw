"""在每个货箱的硬截止时间内联合选择运输机型和起飞时刻。

搜索器只负责提出排程候选；候选必须通过路线、资源和连续通信验证后才会被接受。
"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import argparse
import json
import math
from ortools.sat.python import cp_model

from mountain_flood.core.domain import Model, RESULT, charge, save
from mountain_flood.problem3.communication import certify_routes
from mountain_flood.problem3.schedule import allowed_starts, intersect
from mountain_flood.validation.replay import validate
from mountain_flood.problem2.transport import metrics


def split_by_node(m, routes, route_id, model_by_node=None):
    out = []
    model_by_node = model_by_node or {}
    for r in routes:
        if r['id'] != route_id:
            out.append(r)
            continue
        for k, node in enumerate(r['order']):
            ids = [b for b in r['boxes'] if m.boxes[b]['node'] == node]
            g = model_by_node.get(m.nodes[node]['id'], r['g'])
            part = m.route(g, ids, [node])
            if part is None:
                raise ValueError((route_id, g, m.nodes[node]['id']))
            part.update(id=r['id'] + chr(97 + k), start=0., end=part['duration'])
            out.append(part)
    return out


def solve_choices(m, routes, relays, seconds=45, verbose=False, objective='arrival', due_buffer=0.):
    cp = cp_model.CpModel()
    variants = []
    by_route = []
    arrival_terms = []
    all_ends = []
    for j, original in enumerate(routes):
        group = []
        for g in m.types:
            physical = m.route(g, original['boxes'], original['order'])
            if physical is None:
                continue
            domains = allowed_starts(m, physical, relays)
            if due_buffer:
                for b, delivery_offset in physical['deliver'].items():
                    last_start = math.floor(m.boxes[int(b)]['deadline'] - delivery_offset - due_buffer + 1e-7)
                    domains = intersect(domains, [(0, last_start)])
                    if not domains:
                        break
            if not domains:
                continue
            presence = cp.new_bool_var(f'choose_{j}_{g}')
            start = cp.new_int_var_from_domain(cp_model.Domain.from_intervals(domains), f'start_{j}_{g}')
            end = cp.new_int_var(0, 30000, f'end_{j}_{g}')
            battery_end = cp.new_int_var(0, 40000, f'battery_end_{j}_{g}')
            duration = math.ceil(physical['duration'])
            recharge = math.ceil(charge(physical['soc'], m.types[g]['charge']))
            interval = cp.new_optional_interval_var(start, duration, end, presence, f'flight_{j}_{g}')
            battery_interval = cp.new_optional_interval_var(start, duration + recharge, battery_end, presence, f'battery_{j}_{g}')
            active_start = cp.new_int_var(0, 30000, f'active_{j}_{g}')
            cp.add(active_start == start).only_enforce_if(presence)
            cp.add(active_start == 0).only_enforce_if(presence.Not())
            active_end = cp.new_int_var(0, 30000, f'active_end_{j}_{g}')
            cp.add(active_end == end).only_enforce_if(presence)
            cp.add(active_end == 0).only_enforce_if(presence.Not())
            weight = sum(m.boxes[b]['priority'] for b in original['boxes'])
            offset = sum(m.boxes[int(b)]['priority'] * t for b, t in physical['deliver'].items())
            arrival_terms.append(1000 * weight * active_start + round(1000 * offset) * presence)
            option = dict(j=j, g=g, route=physical, presence=presence, start=start, end=end,
                          interval=interval, battery_interval=battery_interval)
            variants.append(option)
            group.append(option)
            all_ends.append(active_end)
            if g == original['g'] and any(a <= round(original['start']) <= b for a, b in domains):
                cp.add_hint(presence, 1)
                cp.add_hint(start, round(original['start']))
        if not group:
            if verbose: print('no route variant', original['id'], flush=True)
            return None
        cp.add_exactly_one([v['presence'] for v in group])
        by_route.append(group)
    for g in m.types:
        group = [v for v in variants if v['g'] == g]
        cp.add_cumulative([v['interval'] for v in group], [1] * len(group), len(m.units[g]))
        cp.add_cumulative([v['battery_interval'] for v in group], [1] * len(group), m.types[g]['batteries'])
    if objective == 'makespan':
        cmax = cp.new_int_var(0, 30000, 'joint_makespan')
        cp.add_max_equality(cmax, all_ends)
        cp.minimize(cmax)
    else:
        cp.minimize(sum(arrival_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 42
    status = solver.solve(cp)
    if verbose: print('choices', solver.status_name(status), solver.objective_value,
                      solver.best_objective_bound, flush=True)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    chosen = []
    for j, group in enumerate(by_route):
        v = next(v for v in group if solver.value(v['presence']))
        r = dict(v['route'])
        r.update(id=routes[j]['id'], start=float(solver.value(v['start'])))
        r['end'] = r['start'] + r['duration']
        chosen.append(r)
    for g in m.types:
        free_units = [0.] * len(m.units[g])
        free_batteries = [0.] * m.types[g]['batteries']
        for r in sorted((r for r in chosen if r['g'] == g), key=lambda r: r['start']):
            ui = next(i for i, t in enumerate(free_units) if t <= r['start'] + 1e-6)
            bi = next(i for i, t in enumerate(free_batteries) if t <= r['start'] + 1e-6)
            r['unit'] = m.units[g][ui]
            r['battery'] = f'{g}B{bi+1:02}'
            free_units[ui] = r['end']
            free_batteries[bi] = r['end'] + charge(r['soc'], m.types[g]['charge'])
    records, failures = certify_routes(m, chosen, relays, verbose=False)
    if failures:
        if verbose: print('communication failures', len(failures), flush=True)
        return None
    out = dict(routes=chosen, relays=relays, communication=records)
    check = validate(m, out, 3)
    if not check['pass_']:
        if verbose: print('validation failures', check['errors'][:20], flush=True)
        return None
    summary = metrics(m, chosen)
    summary.update(transport_energy=summary['energy'], relay_energy=sum(r['energy'] for r in relays),
                   relay_count=len(relays), transport_makespan=summary['makespan'])
    summary['energy'] += summary['relay_energy']
    summary['makespan'] = max(summary['makespan'], *(r['end'] for r in relays))
    summary['comm_intervals'] = len(records)
    summary['comm_min_margin'] = min(r['margin'] for r in records)
    out['summary'] = summary
    out['solver'] = dict(status=solver.status_name(status), objective=solver.objective_value,
                         bound=solver.best_objective_bound, method='model_choice_CP_SAT',
                         objective_kind=objective)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default='q3.json')
    ap.add_argument('--split', action='append', default=[])
    ap.add_argument('--output', default='q3_hard_candidate.json')
    ap.add_argument('--seconds', type=int, default=45)
    ap.add_argument('--objective', choices=['arrival', 'makespan'], default='arrival')
    ap.add_argument('--buffer', type=float, default=0.)
    args = ap.parse_args()
    m = Model()
    base = json.loads((RESULT / args.source).read_text())
    routes = base['routes']
    for rid in args.split:
        routes = split_by_node(m, routes, rid)
    result = solve_choices(m, routes, base['relays'], seconds=args.seconds,
                           verbose=True, objective=args.objective, due_buffer=args.buffer)
    if result is None:
        print('NO VERIFIED SOLUTION', flush=True)
    else:
        result['source'] = dict(file=args.source, split=args.split)
        save(args.output, result)
        print('VERIFIED', result['summary'], flush=True)


if __name__ == '__main__':
    main()
