# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；公开仓库方案仅作对照。
"""用独立生成的问题二路线候选，检查既有问题三中继排班是否仍可行。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import json
from mountain_flood.core.domain import Model, RESULT, save
from mountain_flood.problem3.joint_solver import split_for_partitions
from mountain_flood.problem3.schedule import solve as schedule_with_relays
from mountain_flood.problem3.schedule import allowed_starts
from mountain_flood.validation.replay import validate

def main():
    m=Model()
    q2=json.loads((RESULT/'q2_time_energy_candidate.json').read_text())
    base=json.loads((RESULT/'q3.json').read_text())
    routes,split=split_for_partitions(m,q2['routes'])
    changes=[]
    # 仅拆分无法放入既有认证中继服务窗的多站架次。
    while True:
        stuck=next((r for r in routes if not allowed_starts(m,r,base['relays'])),None)
        if stuck is None or len(stuck['order'])<2:break
        routes=[r for r in routes if r['id']!=stuck['id']]
        parts=[]
        for k,node in enumerate(stuck['order']):
            ids=[b for b in stuck['boxes'] if m.boxes[b]['node']==node]
            part=m.route(stuck['g'],ids,[node])
            if part is None:raise RuntimeError('Cannot split '+stuck['id'])
            part.update(id=stuck['id']+chr(97+k),start=0.,end=part['duration'])
            parts.append(part)
        routes.extend(parts);changes.append(dict(route=stuck['id'],parts=[p['id'] for p in parts]))
    rec=dict(q2_source=q2['source'],split=split,additional_splits=changes,baseline=base['summary'],status='unsolved')
    try:
        solved=schedule_with_relays(m,routes,base['relays'],seconds=20,verbose=False,priority_arrival=True)
        if solved is not None:
            check=validate(m,solved,3)
            rec['status']='feasible' if check['pass_'] else 'validation_failed'
            rec['validation']=check
            rec['summary']=solved['summary']
            if check['pass_']:save('q3_fusion_probe_solution.json',solved)
        else:rec['status']='no_verified_solution_under_fixed_relay_windows'
    except Exception as exc:
        rec['status']='error';rec['error']=str(exc)
    save('q3_fusion_probe.json',rec)
    print(rec['status'],rec.get('summary',{}),rec.get('error',''),flush=True)

if __name__=='__main__':main()
