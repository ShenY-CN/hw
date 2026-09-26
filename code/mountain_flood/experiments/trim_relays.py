# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
# 参赛队须自行理解、复核与改写。
"""删除未被通信证书使用的中继任务，并将服务窗缩短到最后一次已证明的使用时刻。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import argparse
import json
from mountain_flood.core.domain import Model, RESULT, save
from mountain_flood.problem3.communication import relay_flight, certify_routes
from mountain_flood.problem2.transport import metrics
from mountain_flood.validation.replay import validate

def run(source, output):
    m=Model();data=json.loads((RESULT/source).read_text());used={c['relay_task'] for c in data['communication'] if c['relay_task']}
    relays=[];changes=[]
    for r in data['relays']:
        if r['id'] not in used:
            changes.append(dict(id=r['id'],change='removed_unused'));continue
        last=max(c['end'] for c in data['communication'] if c['relay_task']==r['id'])
        v=relay_flight(m,*r['pos'])
        power=m.relay['hover_power']+m.relay['comm_power']
        expected=v['fly_energy']+(r['service_end']-r['ready']+m.relay['link_setup'])*power/3600
        if abs(expected-r['energy'])>1e-6:raise AssertionError((r['id'],expected,r['energy']))
        new=dict(r);new['service_end']=min(r['service_end'],last+1.0);new['end']=new['service_end']+v['ret']
        new['energy']=v['fly_energy']+(new['service_end']-new['ready']+m.relay['link_setup'])*power/3600
        new['soc']=1-new['energy']/m.relay['E']
        relays.append(new);changes.append(dict(id=r['id'],change='shortened',old_end=r['service_end'],new_end=new['service_end']))
    records,fails=certify_routes(m,data['routes'],relays,verbose=False)
    if fails:raise RuntimeError(f'{len(fails)} communication intervals failed after trimming')
    z=metrics(m,data['routes']);z.update(transport_energy=z['energy'],relay_energy=sum(r['energy'] for r in relays),relay_count=len(relays),transport_makespan=z['makespan'])
    z['energy']+=z['relay_energy'];z['makespan']=max(z['makespan'],max(r['end'] for r in relays))
    z['comm_intervals']=len(records);z['comm_min_margin']=min(c['margin'] for c in records)
    data.update(relays=relays,communication=records,summary=z,relay_trim=changes)
    check=validate(m,data,3)
    if not check['pass_']:raise RuntimeError(check['errors'])
    save(output,data)
    print(output,z,changes,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',default='q3_fusion_refined_solution.json');ap.add_argument('--output',default='q3_fusion_trimmed_solution.json')
    a=ap.parse_args();run(a.source,a.output)
