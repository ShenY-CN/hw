# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI）。
# 参赛队须自行理解、复核与改写；公开仓库仅用于思路对照。
"""回放已归档的救援时效方案，复核通过后再导出提交材料。

随机算法比较用于记录候选发现过程；最终选定方案另行归档，因此复现结果
不依赖不同机器上的限时搜索是否返回同一个候选。
"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import json
import shutil
from mountain_flood.core.domain import Model, RESULT, save
from mountain_flood.problem2.transport import metrics
from mountain_flood.problem4.partition import partition
from mountain_flood.validation.replay import validate
from mountain_flood.problem3.communication import certify_routes


def load(name):
    return json.loads((RESULT/name).read_text(encoding='utf8'))


def checked(name, question):
    data=load(name)
    result=validate(Model(),data,question)
    if not result['pass_']:
        raise RuntimeError(f'{name}: {result["errors"]}')
    recalculated=metrics(Model(),data['routes'])
    for key in ('count','weighted_tardiness','weighted_arrival','last_delivery','hard_violations','delivered'):
        if abs(recalculated[key]-data['summary'][key])>1e-5:
            raise RuntimeError(f'{name}: stale summary {key}')
    if question==2:
        for key in ('energy','makespan'):
            if abs(recalculated[key]-data['summary'][key])>1e-5:
                raise RuntimeError(f'{name}: stale summary {key}')
    else:
        s=data['summary']
        certified,failures=certify_routes(Model(),data['routes'],data['relays'],verbose=False)
        if failures:
            raise RuntimeError(f'Q3 continuous communication failed on {len(failures)} intervals')
        if len(certified)!=len(data['communication']):
            raise RuntimeError('Q3 communication certificate length mismatch')
        for regenerated,archived in zip(certified,data['communication']):
            for key in ('route','relay_task'):
                if regenerated[key]!=archived[key]:
                    raise RuntimeError(f'Q3 communication certificate {key} mismatch')
            for key in ('start','end','margin'):
                if abs(regenerated[key]-archived[key])>1e-6:
                    raise RuntimeError(f'Q3 communication certificate {key} mismatch')
        if abs(s['transport_energy']-recalculated['energy'])>1e-5:
            raise RuntimeError('Q3 transport energy mismatch')
        if abs(s['relay_energy']-sum(r['energy'] for r in data['relays']))>1e-5:
            raise RuntimeError('Q3 relay energy mismatch')
        if abs(s['energy']-s['transport_energy']-s['relay_energy'])>1e-5:
            raise RuntimeError('Q3 total energy mismatch')
        end=max([recalculated['makespan']]+[r['end'] for r in data['relays']])
        if abs(s['makespan']-end)>1e-5:
            raise RuntimeError('Q3 completion time mismatch')
    return data,result


def run():
    q2,c2=checked('q2_time_energy_candidate.json',2)
    q3,c3=checked('q3_hard_hill1_e3900_margin.json',3)
    legacy=RESULT/'q3_soft_legacy.json'
    if not legacy.exists() and (RESULT/'q3.json').exists():
        shutil.copy2(RESULT/'q3.json',legacy)
    save('q2.json',q2)
    save('q3.json',q3)
    partition(Model(),q3)
    save('validation.json',{'2':c2,'3':c3})
    save('fusion_selection.json',dict(
        criterion='all boxes at assigned service areas; medical due and first-batch cutoff hard; then weighted soft tardiness, joint completion, weighted arrival, energy',
        q2_source='q2_time_energy_candidate.json',
        q3_source='q3_hard_hill1_e3900_margin.json',
        comparisons=['method_comparison.json','joint_comparison.json'],
        search_replay='selected feasible plans are archived and independently checked; finite search comparisons are documented separately',
        validation={'2':c2,'3':c3}))
    print('FUSION PASS',q2['summary'],q3['summary'],flush=True)


if __name__=='__main__':
    run()
