# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；公开仓库方案仅作对照。
"""Try independently generated Q2 candidate against the verified Q3 relay schedule."""
import json
from common import Model, RESULT, save
from solve_joint import split_for_partitions
from joint_schedule import solve as schedule_with_relays
from joint_schedule import allowed_starts
from partition_validate import validate

def main():
    m=Model()
    q2=json.loads((RESULT/'q2_time_energy_candidate.json').read_text())
    base=json.loads((RESULT/'q3.json').read_text())
    routes,split=split_for_partitions(m,q2['routes'])
    changes=[]
    # Split only multi-stop trips that cannot fit the already certified relay windows.
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
