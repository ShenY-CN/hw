# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
# 参赛队须自行理解、复核与改写。
"""围绕已通过完整认证的联合排班，尝试逐箱直送修补。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import json
from mountain_flood.core.domain import Model, RESULT, save
from mountain_flood.problem3.schedule import solve as schedule_with_relays, allowed_starts
from mountain_flood.validation.replay import validate

def metric(data):
    s=data['summary']
    return (s['weighted_tardiness'],s['weighted_arrival'],s['makespan'],s['energy'],s['count']+s['relay_count'])

def main():
    m=Model();current=json.loads((RESULT/'q3_fusion_probe_solution.json').read_text())
    relays=current['relays'];history=[]
    for round_no in range(2):
        late=[]
        for r in current['routes']:
            for b,t in r['deliver'].items():
                b=int(b)
                delay=r['start']+t-m.boxes[b]['due']
                if delay>1e-7:late.append((delay*m.boxes[b]['priority'],r['id'],b))
        late.sort(reverse=True)
        if not late:break
        best=None
        for _,rid,b in late[:2]:
            src=next(r for r in current['routes'] if r['id']==rid)
            kept=[x for x in src['boxes'] if x!=b]
            if not kept:continue
            order=[n for n in src['order'] if any(m.boxes[x]['node']==n for x in kept)]
            rem=m.route(src['g'],kept,order)
            if rem is None:continue
            rem.update(id=src['id'],start=src['start'],end=src['start']+rem['duration'])
            for g in m.types:
                direct=m.route(g,[b],[m.boxes[b]['node']])
                if direct is None:continue
                direct.update(id=f'DX{round_no+1}{g}',start=0.,end=direct['duration'])
                routes=[dict(x) for x in current['routes'] if x['id']!=rid]+[rem,direct]
                if any(not allowed_starts(m,x,relays) for x in [rem,direct]):
                    history.append(dict(box=m.boxes[b]['id'],model=g,status='no_allowed_start'))
                    continue
                try:solved=schedule_with_relays(m,routes,relays,seconds=8,priority_arrival=True)
                except Exception as exc:
                    history.append(dict(box=m.boxes[b]['id'],model=g,status='error',message=str(exc)))
                    continue
                if solved is None:
                    history.append(dict(box=m.boxes[b]['id'],model=g,status='no_verified_solution'))
                    continue
                check=validate(m,solved,3)
                history.append(dict(box=m.boxes[b]['id'],model=g,status='feasible' if check['pass_'] else 'failed_validation',score=metric(solved)))
                if check['pass_'] and (best is None or metric(solved)<metric(best[0])):best=(solved,b,g)
        if best is None or metric(best[0])>=metric(current):break
        current,b,g=best
        current['route_adjustment']=dict(kind='direct_relief',box=m.boxes[b]['id'],model=g)
        save('q3_fusion_refined_solution.json',current)
        print('IMPROVED',round_no,metric(current),m.boxes[b]['id'],g,flush=True)
    save('q3_fusion_refinement.json',dict(history=history,selected=metric(current),baseline=metric(json.loads((RESULT/'q3.json').read_text()))))
    print('DONE',metric(current),flush=True)

if __name__=='__main__':main()
