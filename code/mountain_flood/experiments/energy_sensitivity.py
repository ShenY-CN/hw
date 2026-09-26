# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""在既定运输能耗模型下，对固定路线进行能耗敏感性分析。

本程序由 OpenAI Codex（GPT-6）辅助编写，参赛队须自行理解并复核。
"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
from mountain_flood.core.domain import Model, RESULT, save
import json


def breakdown(model, route):
    g = route['g']
    t = model.types[g]
    boxes = route['boxes']
    remaining = sum(model.boxes[i]['w'] for i in boxes)
    horizontal = climb = 0.0
    prev = 0
    for node in list(route['order']) + [0]:
        equivalent_range = t['L0'] - (t['L0'] - t['LF']) * (remaining / t['Q']) ** 1.5
        horizontal += t['E'] * model.D[prev, node] / equivalent_range
        climb += (t['mass'] + remaining) * model.parameters['gravity_m_s2'] * (
            model.H[prev, node] - model.op[prev]) / (t['eta'] * 3.6e6)
        if node:
            remaining -= sum(model.boxes[i]['w'] for i in boxes
                             if model.boxes[i]['node'] == node)
        prev = node
    if abs(horizontal + climb - route['energy']) > 1e-8:
        raise AssertionError(f"Route {route['id']} energy does not match physical model")
    limit = (1 - t['rho'] / 100) * t['E']
    return dict(id=route['id'], model=g, horizontal_kwh=horizontal,
                climb_kwh=climb, actual_kwh=route['energy'], limit_kwh=limit,
                slack_kwh=limit - route['energy'],
                horizontal_increase_percent=100 * ((limit - climb) / horizontal - 1),
                climb_increase_percent=100 * ((limit - horizontal) / climb - 1),
                all_energy_increase_percent=100 * (limit / route['energy'] - 1))


def run():
    model = Model()
    output = {}
    for question, filename in [('q1', 'q1_rho20.json'),
                               ('q2', 'q2.json'), ('q3', 'q3.json')]:
        routes = json.loads((RESULT / filename).read_text(encoding='utf8'))['routes']
        rows = [breakdown(model, dict(route, id=route.get('id', f'Q1-{i:02d}')))
                for i, route in enumerate(routes, 1)]
        tight = min(rows, key=lambda row: row['horizontal_increase_percent'])
        output[question] = dict(route_count=len(rows),
                                total_horizontal_kwh=sum(r['horizontal_kwh'] for r in rows),
                                total_climb_kwh=sum(r['climb_kwh'] for r in rows),
                                tightest=tight,
                                violations_if_horizontal_plus_1pct=sum(
                                    r['horizontal_kwh'] * 1.01 + r['climb_kwh'] > r['limit_kwh'] + 1e-9
                                    for r in rows))
    save('energy_sensitivity.json', output)
    for q, result in output.items():
        print(q, result['tightest']['id'],
              round(result['tightest']['horizontal_increase_percent'], 4),
              result['violations_if_horizontal_plus_1pct'])


if __name__ == '__main__':
    run()
