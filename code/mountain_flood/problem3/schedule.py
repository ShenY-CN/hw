# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""问题三联合排程：结合通信可行时段和资源约束安排运输架次。"""

import math
import numpy as np
from ortools.sat.python import cp_model
from mountain_flood.core.domain import Model, charge
from mountain_flood.problem3.communication import gateway, certify_routes, certificate
from mountain_flood.validation.replay import validate
from mountain_flood.problem2.transport import metrics
from mountain_flood.core.parameters import optimization_parameters

def intersect(a,b):
    out=[]
    for x,y in a:
        for u,v in b:
            lo=max(x,u);hi=min(y,v)
            if lo<=hi:out.append((lo,hi))
    out.sort()
    merged=[]
    for x,y in out:
        if merged and x<=merged[-1][1]+1:merged[-1]=(merged[-1][0],max(merged[-1][1],y))
        else:merged.append((x,y))
    return merged

def allowed_starts(m,r,relays,step=None,horizon=None):
    settings=optimization_parameters()
    if step is None:step=settings['communication_certificate']['step_s']
    if horizon is None:horizon=settings['q3_schedule_horizon_s']
    gw=gateway(m);allowed=[(0,horizon)]
    for s in r['segments']:
        d=s['end']-s['start'];n=max(1,math.ceil(d/step))
        a=np.array(s['a']);b=np.array(s['b'])
        for f0,f1 in zip(np.linspace(0,1,n+1)[:-1],np.linspace(0,1,n+1)[1:]):
            p=(a+(b-a)*f0).tolist();q=(a+(b-a)*f1).tolist()
            if certificate(m,p,q,gw,m.comm['thresholds_db']['direct'])[0]>=0:continue
            tau0=s['start']+d*float(f0);tau1=s['start']+d*float(f1)
            windows=[]
            for v in relays:
                if certificate(m,p,q,v['pos'],m.comm['thresholds_db']['access'])[0]>=0:
                    lo=math.ceil(v['ready']-tau0-1e-7);hi=math.floor(v['service_end']-tau1+1e-7)
                    if lo<=hi:windows.append((lo,hi))
            allowed=intersect(allowed,windows)
            if not allowed:return []
    for b,t in r['deliver'].items():
        deadline=m.boxes[int(b)]['deadline']
        if deadline<1e8:allowed=intersect(allowed,[(0,math.floor(deadline-t+1e-7))])
    return allowed

def solve(m,rs,relays,seconds=15,verbose=False,priority_arrival=False):
    model=cp_model.CpModel();starts=[];ends=[];iv=[];biv=[];lates=[];arrivals=[]
    for j,r in enumerate(rs):
        domains=allowed_starts(m,r,relays)
        if not domains:raise RuntimeError('no feasible start for '+r['id'])
        if verbose:print(r['id'],'allowed',domains,'current',r['start'],flush=True)
        start=model.new_int_var_from_domain(cp_model.Domain.from_intervals(domains),f's{j}')
        duration=math.ceil(r['duration']);chg=math.ceil(charge(r['soc'],m.types[r['g']]['charge']))
        end=model.new_int_var(0,25000,f'e{j}')
        iv.append(model.new_interval_var(start,duration,end,f'i{j}'))
        be=model.new_int_var(0,30000,f'be{j}')
        biv.append(model.new_interval_var(start,duration+chg,be,f'bi{j}'))
        starts.append(start);ends.append(end)
        if any(a<=round(r['start'])<=b for a,b in domains):model.add_hint(start,round(r['start']))
        for b,t in r['deliver'].items():
            box=m.boxes[int(b)]
            late=model.new_int_var(0,30000000,f'l{j}_{b}')
            model.add_max_equality(late,[0,1000*start+round(t*1000)-round(box['due']*1000)])
            if not box['medical']:lates.append(box['priority']*late)
            arrivals.append(box['priority']*(1000*start+round(t*1000)))
    for g in m.types:
        js=[j for j,r in enumerate(rs) if r['g']==g]
        model.add_cumulative([iv[j] for j in js],[1]*len(js),len(m.units[g]))
        model.add_cumulative([biv[j] for j in js],[1]*len(js),m.types[g]['batteries'])
    cmax=model.new_int_var(0,25000,'cmax');model.add_max_equality(cmax,ends)
    obj=sum(lates);model.minimize(obj)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=1;solver.parameters.random_seed=optimization_parameters()['method_comparison']['cp_sat_seed']
    status=solver.solve(model)
    if verbose:print('stage1',solver.status_name(status),solver.objective_value,solver.best_objective_bound,flush=True)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return None
    first_status=solver.status_name(status);first_objective=solver.objective_value;first_bound=solver.best_objective_bound
    target=round(solver.objective_value)
    model.add(obj<=target)
    arrival_stage=None
    if priority_arrival:
        arrival_obj=sum(arrivals);model.minimize(arrival_obj)
        status=solver.solve(model)
        if verbose:print('arrival stage',solver.status_name(status),solver.objective_value,solver.best_objective_bound,flush=True)
        if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return None
        arrival_stage=dict(status=solver.status_name(status),objective=solver.objective_value,bound=solver.best_objective_bound)
        model.add(arrival_obj<=round(solver.objective_value))
    model.minimize(cmax)
    status=solver.solve(model)
    if verbose:print('stage2',solver.status_name(status),solver.objective_value,solver.best_objective_bound,flush=True)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return None
    second_status=solver.status_name(status);second_objective=solver.objective_value;second_bound=solver.best_objective_bound
    out=[]
    for j,r in enumerate(rs):
        rr=dict(r);rr.update(start=float(solver.value(starts[j])),end=float(solver.value(starts[j]))+r['duration']);out.append(rr)
    for g in m.types:
        us=[0.]*len(m.units[g]);bs=[0.]*m.types[g]['batteries']
        for r in sorted([r for r in out if r['g']==g],key=lambda r:r['start']):
            ui=next(i for i,t in enumerate(us) if t<=r['start']+1e-6)
            bi=next(i for i,t in enumerate(bs) if t<=r['start']+1e-6)
            r['unit']=m.units[g][ui];r['battery']=f'{g}B{bi+1:02}'
            us[ui]=r['end'];bs[bi]=r['end']+charge(r['soc'],m.types[g]['charge'])
    records,fails=certify_routes(m,out,relays,verbose=verbose)
    if fails:return None
    check=validate(m,dict(routes=out,relays=relays,communication=records),3)
    if not check['pass_']:return None
    summary=metrics(m,out)
    summary.update(transport_energy=summary['energy'],relay_energy=sum(r['energy'] for r in relays),relay_count=len(relays),transport_makespan=summary['makespan'],makespan=max(summary['makespan'],max(r['end'] for r in relays)),comm_intervals=len(records),comm_min_margin=min(r['margin'] for r in records))
    summary['energy']+=summary['relay_energy']
    cert=dict(stage1_status=first_status,stage1_objective=first_objective,stage1_bound=first_bound,stage2_status=second_status,stage2_objective=second_objective,stage2_bound=second_bound)
    if arrival_stage is not None:cert['arrival_stage']=arrival_stage
    return dict(routes=out,relays=relays,communication=records,summary=summary,solver=cert)
