# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""问题二运输方案生成、资源排程及共用指标计算。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
from mountain_flood.problem1.packing import q1
from mountain_flood.core.domain import *
from itertools import combinations, permutations, product
import random, time


def metrics(m,rs):
    deliveries={int(b):r['start']+t for r in rs for b,t in r['deliver'].items()}
    return dict(count=len(rs),energy=sum(r['energy'] for r in rs),makespan=max(r['end'] for r in rs),weighted_tardiness=sum(m.boxes[b]['priority']*max(0,t-m.boxes[b]['due']) for b,t in deliveries.items()),weighted_arrival=sum(m.boxes[b]['priority']*t for b,t in deliveries.items()),hard_violations=sum(t>m.boxes[b]['deadline']+1e-6 for b,t in deliveries.items()),delivered=len(deliveries),last_delivery=max(deliveries.values()))

def construct(m,seed,multi=True,earliest=0):
    rng=random.Random(seed)
    remaining=set(range(80));routes=[]
    units={u:0. for us in m.units.values() for u in us}
    bat={g:[0.]*t['batteries'] for g,t in m.types.items()}
    # 优先级扰动用于改变装箱和访问顺序；每次路线构造仍显式检查硬时限。
    jitter={i:rng.uniform(.75,1.25) for i in remaining}
    exp=rng.uniform(.1,.8);energy_weight=rng.uniform(0,.2)
    while remaining:
        choices=[]
        for g in m.types:
            u=min(m.units[g],key=units.get);bi=int(np.argmin(bat[g]));start=max(units[u],bat[g][bi],earliest)
            seeds=sorted(remaining,key=lambda i:(m.boxes[i]['deadline'] if m.boxes[i]['deadline']<1e8 else m.boxes[i]['due']+10000)*jitter[i])[:12]
            seeds=list(dict.fromkeys(next(i for i in seeds if m.boxes[i]['node']==node) for node in dict.fromkeys(m.boxes[i]['node'] for i in seeds)))
            for seedbox in seeds:
                r=m.route(g,[seedbox]);ids=[seedbox]
                if r is None:continue
                if any(start+t>m.boxes[i]['deadline'] for i,t in r['deliver'].items()):continue
                while True:
                    add=[]
                    for b in sorted(remaining-set(ids)):
                        node=m.boxes[b]['node'];order=r['order']
                        if not multi and node not in order:continue
                        if node not in order and len(order)>=3:continue
                        orders=[order] if node in order else [order[:j]+[node]+order[j:] for j in range(len(order)+1)]
                        for o in orders:
                            trial=m.route(g,ids+[b],o)
                            if trial is None:continue
                            if any(start+t>m.boxes[i]['deadline'] for i,t in trial['deliver'].items()):continue
                            benefit=m.boxes[b]['priority']*(3 if m.boxes[b]['deadline']<1e8 else 1)*jitter[b]
                            marginal=(trial['duration']-r['duration'])/600+energy_weight*(trial['energy']-r['energy'])+.15
                            add.append((benefit/marginal,b,trial))
                    if not add:break
                    _,b,r=max(add,key=lambda a:a[0]);ids.append(b)
                benefit=sum(m.boxes[b]['priority']*(3 if m.boxes[b]['deadline']<1e8 else 1)*jitter[b] for b in ids)
                late=sum(m.boxes[b]['priority']*max(0,start+t-m.boxes[b]['due'])/3600 for b,t in r['deliver'].items())
                score=benefit/((start+r['duration'])/1000)**exp/(r['duration']/1000+energy_weight*r['energy'])-late
                choices.append((score,u,bi,start,r))
        if not choices:return None
        _,u,bi,start,r=max(choices,key=lambda a:a[0]);g=r['g']
        r.update(start=start,end=start+r['duration'],unit=u,battery=f'{g}B{bi+1:02}',id=f'T{len(routes)+1:03}')
        units[u]=r['end'];bat[g][bi]=r['end']+charge(r['soc'],m.types[g]['charge'])
        remaining.difference_update(r['boxes']);routes.append(r)
    return routes

def improve_schedule(m,rs,seconds=15,earliest=0,start_after=None):
    """对固定路线使用 CP-SAT 联合安排同型号无人机和电池的占用时段。"""
    from ortools.sat.python import cp_model
    model=cp_model.CpModel();starts=[];ends=[];iv=[];biv=[];horizon=20000
    start_after=start_after or {}
    for j,r in enumerate(rs):
        dur=math.ceil(r['duration']);chg=math.ceil(charge(r['soc'],m.types[r['g']]['charge']))
        s=model.new_int_var(math.ceil(max(earliest,start_after.get(r['id'],0))),horizon,f's{j}');e=model.new_int_var(0,horizon,f'e{j}')
        iv.append(model.new_interval_var(s,dur,e,f'i{j}'))
        be=model.new_int_var(0,horizon+5000,f'be{j}')
        biv.append(model.new_interval_var(s,dur+chg,be,f'bi{j}'))
        starts.append(s);ends.append(e);model.add_hint(s,math.ceil(r['start']))
        for b,t in r['deliver'].items():
            if m.boxes[int(b)]['deadline']<1e8:model.add(s<=math.floor(m.boxes[int(b)]['deadline']-t))
    for g in m.types:
        js=[j for j,r in enumerate(rs) if r['g']==g]
        model.add_cumulative([iv[j] for j in js],[1]*len(js),len(m.units[g]))
        model.add_cumulative([biv[j] for j in js],[1]*len(js),m.types[g]['batteries'])
    makespan=model.new_int_var(0,horizon,'Cmax');model.add_max_equality(makespan,ends)
    penalties=[]
    for j,r in enumerate(rs):
        for b,t in r['deliver'].items():
            b=int(b);v=model.new_int_var(0,horizon*1000,'late')
            model.add_max_equality(v,[0,1000*starts[j]+round(t*1000)-round(m.boxes[b]['due']*1000)])
            penalties.append(m.boxes[b]['priority']*v)
    tardiness=sum(penalties)
    model.minimize(tardiness)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=1;solver.parameters.random_seed=42
    status=solver.solve(model)
    if status not in [cp_model.OPTIMAL,cp_model.FEASIBLE]:return rs,dict(status=solver.status_name(status))
    first=dict(status=solver.status_name(status),objective=solver.objective_value,bound=solver.best_objective_bound)
    chosen=[solver.value(s) for s in starts]
    model.add(tardiness<=round(solver.objective_value))
    model.minimize(makespan)
    status=solver.solve(model)
    second=dict(status=solver.status_name(status))
    if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
        chosen=[solver.value(s) for s in starts]
        second.update(objective=solver.objective_value,bound=solver.best_objective_bound)
    out=[]
    for j,r in enumerate(rs):
        rr=dict(r);rr.update(start=float(chosen[j]),end=float(chosen[j])+r['duration']);out.append(rr)
    for g in m.types:
        us=[0.]*len(m.units[g]);bs=[0.]*m.types[g]['batteries']
        for r in sorted([r for r in out if r['g']==g],key=lambda r:r['start']):
            ui=next(i for i,t in enumerate(us) if t<=r['start']+1e-6);bi=next(i for i,t in enumerate(bs) if t<=r['start']+1e-6)
            r['unit']=m.units[g][ui];r['battery']=f'{g}B{bi+1:02}';us[ui]=r['end'];bs[bi]=r['end']+charge(r['soc'],m.types[g]['charge'])
    return out,dict(status=second['status'],tardiness_stage=first,makespan_stage=second)


def relocate_candidates(m,rs,limit=3):
    """通过在不同架次间移动整箱货物，生成新的物理可行路线组合。"""
    options=[]
    for i,a in enumerate(rs):
        for j,b in enumerate(rs):
            if i==j or a['g']!=b['g']:continue
            for box in a['boxes']:
                kept=[x for x in a['boxes'] if x!=box]
                left=m.route(a['g'],kept,[n for n in a['order'] if any(m.boxes[x]['node']==n for x in kept)]) if kept else None
                if kept and left is None:continue
                node=m.boxes[box]['node']
                orders=[b['order']] if node in b['order'] else (
                    [b['order'][:k]+[node]+b['order'][k:] for k in range(len(b['order'])+1)]
                    if len(b['order'])<3 else [])
                for order in orders:
                    right=m.route(b['g'],b['boxes']+[box],order)
                    if right is None:continue
                    trial=[]
                    for k,r in enumerate(rs):
                        if k==i:
                            if left is None:continue
                            replacement=dict(left,id=r['id'],start=r['start'])
                        elif k==j:
                            replacement=dict(right,id=r['id'],start=r['start'])
                        else:
                            replacement=dict(r)
                        replacement['end']=replacement['start']+replacement['duration']
                        trial.append(replacement)
                    mm=metrics(m,trial)
                    options.append(((mm['hard_violations'],mm['weighted_tardiness'],mm['makespan'],
                                     mm['energy'],mm['count']),trial))
    options.sort(key=lambda item:item[0])
    return [trial for _,trial in options[:limit]]

def direct_relief_candidates(m,rs):
    """针对软时限迟到货箱，尝试使用各可用机型拆出合法的单箱直送架次。"""
    late=[]
    for r in rs:
        for b,t in r['deliver'].items():
            b=int(b)
            if r['start']+t>m.boxes[b]['due']+1e-7:late.append((r['id'],b))
    out=[]
    for source,b in late:
        for g in m.types:
            extra=m.route(g,[b],[m.boxes[b]['node']])
            if extra is None:continue
            trial=[]
            for r in rs:
                if r['id']!=source:
                    trial.append(dict(r));continue
                kept=[x for x in r['boxes'] if x!=b]
                if not kept:continue
                order=[node for node in r['order'] if any(m.boxes[x]['node']==node for x in kept)]
                replacement=m.route(r['g'],kept,order)
                if replacement is None:break
                replacement.update(id=r['id'],start=r['start'],end=r['start']+replacement['duration'])
                trial.append(replacement)
            else:
                extra.update(id=f'T{len(rs)+1:03}',start=0.,end=extra['duration'])
                trial.append(extra)
                out.append((m.boxes[b]['id'],g,trial))
    return out

def run():
    m=Model()
    for rho in [.1,.2,.3,.4]:
        if (RESULT/f'q1_rho{int(rho*100)}.json').exists():continue
        z=q1(m,rho);save(f'q1_rho{int(rho*100)}.json',z);print('Q1',rho,z['summary'],flush=True)
    for obj in ['energy','time']:
        if (RESULT/f'q1_{obj}.json').exists():continue
        z=q1(m,.2,obj);save(f'q1_{obj}.json',z);print('Q1',obj,z['summary'],flush=True)
    history=[]
    for multi in [False,True]:
        localbest=None;scorebest=None
        for seed in range(24):
            rs=construct(m,seed,multi)
            if rs is None:continue
            mm=metrics(m,rs);history.append(dict(seed=seed,multi=multi,**mm))
            score=(mm['hard_violations'],mm['weighted_tardiness'],mm['makespan'],mm['energy'],mm['count'])
            if scorebest is None or score<scorebest:scorebest=score;localbest=rs
            if seed%6==0:print('Q2 trial',multi,seed,mm,flush=True)
        if localbest is None:raise RuntimeError('No feasible construction')
        localbest,cert=improve_schedule(m,localbest,30)
        if cert['status'] not in ('FEASIBLE','OPTIMAL'):raise RuntimeError(f'Q2 schedule failed: {cert}')
        if multi:
            selected=(metrics(m,localbest)['hard_violations'],metrics(m,localbest)['weighted_tardiness'],
                      metrics(m,localbest)['makespan'],metrics(m,localbest)['energy'],metrics(m,localbest)['count'])
            for trial in relocate_candidates(m,localbest):
                candidate,candidate_cert=improve_schedule(m,trial,10)
                if candidate_cert['status'] not in ('FEASIBLE','OPTIMAL'):continue
                mm=metrics(m,candidate)
                trial_score=(mm['hard_violations'],mm['weighted_tardiness'],mm['makespan'],mm['energy'],mm['count'])
                if trial_score<selected:
                    localbest,cert,selected=candidate,candidate_cert,trial_score
            for box_id,g,trial in direct_relief_candidates(m,localbest):
                candidate,candidate_cert=improve_schedule(m,trial,40)
                if candidate_cert['status'] not in ('FEASIBLE','OPTIMAL'):continue
                mm=metrics(m,candidate)
                trial_score=(mm['hard_violations'],mm['weighted_tardiness'],mm['makespan'],mm['energy'],mm['count'])
                history.append(dict(candidate='direct_relief',box=box_id,type=g,**mm))
                if trial_score<selected:
                    localbest,cert,selected=candidate,candidate_cert,trial_score
        label='q2' if multi else 'q2_baseline';save(label+'.json',dict(routes=localbest,summary=metrics(m,localbest),solver=cert))
        print(label,metrics(m,localbest),flush=True)
    save('search_history.json',history)

if __name__=='__main__':run()
