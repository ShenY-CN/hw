# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
# 参赛队须自行理解、复核与改写。
"""重新解码归档的同预算路线候选，独立复算指标并检查可行性。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import json
from mountain_flood.core.domain import Model, RESULT, save
from mountain_flood.problem2.transport import metrics
from mountain_flood.validation.replay import validate
from mountain_flood.problem2.search import decode


def run():
    m=Model()
    archive=json.loads((RESULT/'method_comparison.json').read_text(encoding='utf8'))
    selected_plan=json.loads((RESULT/'q2_time_energy_candidate.json').read_text(encoding='utf8'))
    expected={(method,seed) for method in ('grasp','hill','anneal','tabu') for seed in (0,1,2)}
    trial_keys=set()
    for trial in archive['trials']:
        key=(trial['method'],trial['seed'])
        if key in trial_keys:raise RuntimeError(f'duplicate heuristic trial {key}')
        trial_keys.add(key)
        decoded=decode(m,trial['plan'])
        if decoded is None:raise RuntimeError(f'{key}: invalid heuristic plan')
        recomputed=metrics(m,decoded)
        for field,value in trial['heuristic'].items():
            if abs(recomputed[field]-value)>1e-5:
                raise RuntimeError(f'{key}: stale heuristic {field}')
    if trial_keys!=expected:raise RuntimeError(f'heuristic trial set differs: {trial_keys}')
    seen=set();selected=[];rows=[]
    for candidate in archive['candidates']:
        key=(candidate['method'],candidate['seed'])
        if key in seen:raise RuntimeError(f'duplicate comparison candidate {key}')
        seen.add(key)
        recomputed=metrics(m,candidate['routes'])
        for field,value in candidate['metrics'].items():
            if abs(recomputed[field]-value)>1e-5:
                raise RuntimeError(f'{key}: stale {field}')
        check=validate(m,dict(routes=candidate['routes']),2)
        if not check['pass_']:
            raise RuntimeError(f'{key}: {check["errors"]}')
        if key in expected:
            trial=next(t for t in archive['trials'] if (t['method'],t['seed'])==key)
            if sorted((g,tuple(sorted(boxes)),tuple(order)) for g,boxes,order in trial['plan'])!=sorted(
                (route['g'],tuple(sorted(route['boxes'])),tuple(route['order'])) for route in candidate['routes']):
                raise RuntimeError(f'{key}: scheduled routes differ from heuristic route plan')
        if candidate['selected']:
            selected.append(key)
            if candidate['routes']!=selected_plan['routes']:
                raise RuntimeError('selected Q2 plan differs from comparison archive')
        rows.append(dict(method=key[0],seed=key[1],verified=True))
    if seen!=expected|{('existing_baseline',None)}:
        raise RuntimeError(f'comparison methods/seeds differ: {seen}')
    if len(selected)!=1:
        raise RuntimeError(f'expected one selected candidate, got {selected}')
    save('method_comparison_validation.json',dict(pass_=True,count=len(rows),selected=selected[0],rows=rows))
    print('METHOD COMPARISON PASS',len(rows),selected[0],flush=True)


if __name__=='__main__':
    run()
