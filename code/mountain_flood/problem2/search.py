# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；算法独立编写，未复制公开参赛仓库代码。
"""在统一物理模型和同等搜索预算下比较问题二的多种路线搜索方法。"""
from __future__ import annotations

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
import argparse
import json
import math
import random
import time
from pathlib import Path
from mountain_flood.core.domain import Model, RESULT, save, charge
from mountain_flood.problem2.transport import construct, metrics
from mountain_flood.validation.replay import validate
from mountain_flood.core.parameters import optimization_parameters

METHODS = tuple(optimization_parameters()['method_comparison']['methods'])

def plan_from_routes(routes):
    return [(r['g'], tuple(r['boxes']), tuple(r['order'])) for r in sorted(routes,key=lambda z:z['start'])]

def normalize_order(m, boxes, old_order):
    nodes={m.boxes[b]['node'] for b in boxes}
    kept=list(dict.fromkeys(n for n in old_order if n in nodes))
    return tuple(kept+sorted(nodes-set(kept)))

def decode(m, plan):
    if sorted(b for _,bs,_ in plan for b in bs)!=list(range(len(m.boxes))):return None
    units={g:[0.]*len(m.units[g]) for g in m.types}
    batteries={g:[0.]*m.types[g]['batteries'] for g in m.types}
    out=[]
    for index,(g,boxes,order) in enumerate(plan):
        required={m.boxes[b]['node'] for b in boxes}
        if not boxes or len(order)>optimization_parameters()['route_search']['max_stops_per_route'] or len(order)!=len(set(order)) or set(order)!=required:return None
        r=m.route(g,list(boxes),list(order))
        if r is None:return None
        ui=min(range(len(units[g])), key=lambda k: units[g][k])
        bi=min(range(len(batteries[g])), key=lambda k: batteries[g][k])
        start=max(units[g][ui],batteries[g][bi])
        r.update(id=f'T{index+1:03}',start=start,end=start+r['duration'],unit=m.units[g][ui],battery=f'{g}B{bi+1:02}')
        units[g][ui]=r['end'];batteries[g][bi]=r['end']+charge(r['soc'],m.types[g]['charge'])
        out.append(r)
    return out

def score(m, routes):
    z=metrics(m,routes)
    return (z['hard_violations'],z['weighted_tardiness'],z['makespan'],z['weighted_arrival'],z['energy'],z['count'])

def scalar(z):
    # 该标量只用于模拟退火接受概率，不作为论文或结果报告中的模型目标值。
    p=optimization_parameters()['anneal_scalar']
    return p['hard_violation_weight']*z[0]+p['soft_tardiness_weight']*z[1]+z[2]/p['makespan_divisor']+z[3]/p['arrival_divisor']+z[4]

def signature(plan):
    return tuple((g,tuple(sorted(bs)),tuple(order)) for g,bs,order in plan)

def mutate(m, plan, rng):
    """五种搜索策略共用的路线变换之一；生成结果均经过物理可行性筛选。"""
    n=len(plan)
    for _ in range(optimization_parameters()['route_search']['mutation_attempts']):
        kind=rng.randrange(5)
        q=list(plan)
        if kind==0 and n>1:  # 调整架次执行顺序
            i,j=rng.sample(range(n),2);q[i],q[j]=q[j],q[i]
        elif kind==1 and n>1:  # 将整箱货物移至另一架次
            i,j=rng.sample(range(n),2);g,a,o=q[i];h,b,p=q[j]
            box=rng.choice(a);a2=tuple(x for x in a if x!=box);b2=b+(box,)
            if a2:q[i]=(g,a2,normalize_order(m,a2,o))
            else:q.pop(i);j-=j>i
            q[j]=(h,b2,normalize_order(m,b2,p))
        elif kind==2:  # 将一个货箱拆为单独直送架次
            i=rng.randrange(n);g,a,o=q[i]
            if len(a)<2:continue
            box=rng.choice(a);a2=tuple(x for x in a if x!=box)
            q[i]=(g,a2,normalize_order(m,a2,o))
            h=rng.choice(tuple(m.types))
            direct=(h,(box,),(m.boxes[box]['node'],))
            q.insert(rng.randrange(len(q)+1),direct)
        elif kind==3:  # 更换机型或调整服务区访问顺序
            i=rng.randrange(n);g,a,o=q[i]
            if rng.random()<.5:
                h=rng.choice(tuple(t for t in m.types if t!=g));q[i]=(h,a,o)
            else:
                if len(o)<2:continue
                p=list(o);rng.shuffle(p);q[i]=(g,a,tuple(p))
        elif kind==4 and n>1:  # 合并两个架次
            i,j=sorted(rng.sample(range(n),2));g,a,o=q[i];h,b,p=q[j]
            both=a+b;order=normalize_order(m,both,o+p)
            if len(order)>optimization_parameters()['route_search']['max_stops_per_route']:continue
            q[i]=(rng.choice((g,h)),both,order);q.pop(j)
        else:continue
        if signature(q)==signature(plan):continue
        routes=decode(m,q)
        if routes is not None:return q,routes
    return None,None

def search(m, method, initial_plan, seed, budget):
    rng=random.Random(100000+seed)
    start=time.monotonic();limit=start+budget
    curr_plan=list(initial_plan);curr_routes=decode(m,curr_plan)
    if curr_routes is None:raise RuntimeError('invalid initial plan')
    curr_score=score(m,curr_routes);best_plan=list(curr_plan);best_score=curr_score
    seen={signature(curr_plan)};tabu={};history=[];iterations=0
    while time.monotonic()<limit:
        iterations+=1
        if method=='grasp':
            # 随机化构造重启属于独立的搜索策略类别。
            fresh=construct(m,seed*10000+iterations,multi=True)
            if fresh is None:continue
            q=plan_from_routes(fresh);routes=decode(m,q)
            if routes is None:continue
            z=score(m,routes);curr_plan,curr_score=q,z
        elif method=='hill':
            candidates=[]
            for _ in range(optimization_parameters()['route_search']['hill_neighbors']):
                q,routes=mutate(m,curr_plan,rng)
                if q is not None:candidates.append((score(m,routes),q))
            if not candidates:continue
            z,q=min(candidates,key=lambda x:x[0])
            if z<curr_score:curr_plan,curr_score=q,z
            elif iterations%optimization_parameters()['route_search']['hill_restart_interval']==0:curr_plan=list(best_plan);curr_score=best_score
        elif method=='anneal':
            q,routes=mutate(m,curr_plan,rng)
            if q is None:continue
            z=score(m,routes);temp=max(optimization_parameters()['route_search']['anneal_min_temperature'],1-(time.monotonic()-start)/budget)
            delta=scalar(z)-scalar(curr_score)
            if delta<=0 or rng.random()<math.exp(-min(700,delta/(optimization_parameters()['route_search']['anneal_acceptance_scale']*temp))):
                curr_plan,curr_score=q,z
        elif method=='tabu':
            candidates=[]
            for _ in range(optimization_parameters()['route_search']['tabu_neighbors']):
                q,routes=mutate(m,curr_plan,rng)
                if q is None:continue
                sig=signature(q);z=score(m,routes)
                if tabu.get(sig,0)<=iterations or z<best_score:candidates.append((z,q,sig))
            if not candidates:continue
            z,q,sig=min(candidates,key=lambda x:x[0]);curr_plan,curr_score=q,z
            tabu[sig]=iterations+optimization_parameters()['route_search']['tabu_tenure']
        if curr_score<best_score:
            best_plan=list(curr_plan);best_score=curr_score
            history.append({'iteration':iterations,'elapsed_s':round(time.monotonic()-start,3),'score':best_score})
    routes=decode(m,best_plan)
    return dict(method=method,seed=seed,budget_s=budget,elapsed_s=time.monotonic()-start,iterations=iterations,
                heuristic=metrics(m,routes),history=history,plan=best_plan)

def nondominated(items):
    def vector(x):
        z=x['metrics'];return (z['weighted_tardiness'],z['weighted_arrival'],z['makespan'],z['energy'])
    out=[]
    for x in items:
        a=vector(x)
        if not any(y is not x and all(b<=c+1e-7 for b,c in zip(vector(y),a)) and any(b<c-1e-7 for b,c in zip(vector(y),a)) for y in items):out.append(x)
    return out

def refine_timefirst(m, rs, seconds=6.0):
    """医疗及首批硬截止通过后，依次压低其他物资迟到、返航收尾与交付时刻。"""
    from ortools.sat.python import cp_model
    model=cp_model.CpModel();starts=[];ends=[];intervals=[];battery_intervals=[]
    tardy_terms=[];arrival_terms=[];horizon=optimization_parameters()['route_search']['schedule_horizon_s']
    for j,r in enumerate(rs):
        duration=math.ceil(r['duration'])
        recharge=math.ceil(charge(r['soc'],m.types[r['g']]['charge']))
        start=model.new_int_var(0,horizon,f's{j}')
        end=model.new_int_var(0,horizon+duration,f'e{j}')
        intervals.append(model.new_interval_var(start,duration,end,f'u{j}'))
        bend=model.new_int_var(0,horizon+duration+recharge,f'be{j}')
        battery_intervals.append(model.new_interval_var(start,duration+recharge,bend,f'b{j}'))
        starts.append(start);ends.append(end)
        model.add_hint(start,math.ceil(r['start']))
        for b,t in r['deliver'].items():
            b=int(b);box=m.boxes[b]
            if box['deadline']<1e8:model.add(start<=math.floor(box['deadline']-t))
            delay=model.new_int_var(0,horizon*1000,f'late{j}_{b}')
            model.add_max_equality(delay,[0,1000*start+round(t*1000)-round(box['due']*1000)])
            if not box['medical']:tardy_terms.append(box['priority']*delay)
            arrival_terms.append(box['priority']*(1000*start+round(t*1000)))
    for g in m.types:
        js=[j for j,r in enumerate(rs) if r['g']==g]
        model.add_cumulative([intervals[j] for j in js],[1]*len(js),len(m.units[g]))
        model.add_cumulative([battery_intervals[j] for j in js],[1]*len(js),m.types[g]['batteries'])
    cmax=model.new_int_var(0,horizon+max(math.ceil(r['duration']) for r in rs),'cmax')
    model.add_max_equality(cmax,ends)
    tardiness=sum(tardy_terms);arrival=sum(arrival_terms)
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1;solver.parameters.random_seed=optimization_parameters()['method_comparison']['cp_sat_seed']
    stage=[];chosen=None
    for label,objective in [('weighted_tardiness',tardiness),('makespan',cmax),('weighted_arrival',arrival)]:
        model.minimize(objective)
        solver.parameters.max_time_in_seconds=max(1.0,seconds/3)
        status=solver.solve(model)
        info=dict(stage=label,status=solver.status_name(status))
        if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
            stage.append(info);break
        chosen=[solver.value(s) for s in starts]
        info.update(objective=solver.objective_value,bound=solver.best_objective_bound)
        stage.append(info)
        model.add(objective<=round(solver.objective_value))
    if chosen is None:return None,stage
    out=[]
    for r,start in zip(rs,chosen):
        q=dict(r);q.update(start=float(start),end=float(start)+r['duration']);out.append(q)
    for g in m.types:
        units=[0.]*len(m.units[g]);batteries=[0.]*m.types[g]['batteries']
        for r in sorted([z for z in out if z['g']==g],key=lambda z:z['start']):
            available_units=[k for k,t in enumerate(units) if t<=r['start']+1e-6]
            available_batteries=[k for k,t in enumerate(batteries) if t<=r['start']+1e-6]
            if not available_units or not available_batteries:return None,stage
            ui=available_units[0];bi=available_batteries[0]
            r['unit']=m.units[g][ui];r['battery']=f'{g}B{bi+1:02}'
            units[ui]=r['end'];batteries[bi]=r['end']+charge(r['soc'],m.types[g]['charge'])
    return out,stage

def run(budget=None,seeds=None,schedule_seconds=None):
    settings=optimization_parameters()['method_comparison']
    if budget is None:budget=settings['search_budget_s']
    if seeds is None:seeds=tuple(settings['seeds'])
    if schedule_seconds is None:schedule_seconds=settings['schedule_budget_s']
    m=Model();root=RESULT
    baseline=root/'q2.json'
    base=json.loads(baseline.read_text(encoding='utf8'))['routes']
    trials=[];starts={};initial_seeds={}
    for seed in seeds:
        for trial_seed in range(seed*100,seed*100+optimization_parameters()['route_search']['initial_seed_attempts']):
            initial=construct(m,trial_seed,multi=True)
            if initial is not None:
                starts[seed]=plan_from_routes(initial)
                initial_seeds[seed]=trial_seed
                break
        if seed not in starts:raise RuntimeError(f'No hard-feasible initial plan for seed {seed}')
    for seed in seeds:
        for method in METHODS:
            rec=search(m,method,starts[seed],seed,budget)
            print('SEARCH',method,seed,rec['iterations'],rec['heuristic']['weighted_tardiness'],flush=True)
            trials.append(rec)
    # 对每种方法的最佳路线划分和既有基线，使用相同的 CP-SAT 排程流程精修。
    candidates=[]
    for rec in trials:
        routes=decode(m,rec['plan'])
        refined,solver=refine_timefirst(m,routes,seconds=schedule_seconds)
        if refined is None:
            print('SCHEDULE_FAILED',rec['method'],rec['seed'],solver,flush=True)
            continue
        z=metrics(m,refined)
        check=validate(m,dict(routes=refined),2)
        candidates.append(dict(method=rec['method'],seed=rec['seed'],metrics=z,solver=solver,validation=check,routes=refined))
        print('SCHEDULE',rec['method'],rec['seed'],z['weighted_tardiness'],z['weighted_arrival'],z['makespan'],check['pass_'],flush=True)
    candidates.append(dict(method='existing_baseline',seed=None,metrics=metrics(m,base),solver={'status':'archived_verified','origin':'prior hill-climbing seed 1 under stricter all-due experiment'},validation=validate(m,dict(routes=base),2),routes=base))
    feasible=[x for x in candidates if x['validation']['pass_'] and x['metrics']['hard_violations']==0 and x['metrics']['delivered']==80]
    frontier=nondominated(feasible)
    selected=min(feasible,key=lambda x:(x['metrics']['weighted_tardiness'],x['metrics']['makespan'],x['metrics']['weighted_arrival'],x['metrics']['energy'],x['metrics']['count']))
    overview=[]
    for x in candidates:
        overview.append(dict(method=x['method'],seed=x['seed'],metrics=x['metrics'],solver=x['solver'],validation=x['validation'],routes=x['routes'],on_frontier=x in frontier,selected=x is selected))
    save('method_comparison.json',dict(protocol=dict(methods=METHODS,seeds=list(seeds),initial_seeds=initial_seeds,budget_s=budget,schedule_seconds=schedule_seconds,hard_deadline='medical due and first-batch cutoff',soft_due='other goods expected delivery time',objective=['hard_feasibility','weighted_tardiness','makespan','weighted_arrival','energy','count'],carbon_factor=None,provenance='independent local code',historical_baseline='prior hill-climbing seed 1 under stricter all-due experiment; not a fifth current-budget run'),trials=trials,candidates=overview))
    source=dict(method=selected['method'],seed=selected['seed'],algorithm_comparison='method_comparison.json')
    if selected['method']=='existing_baseline':source['origin']='hill-climbing seed 1 in method_comparison_strict_archive.json'
    save('q2_time_energy_candidate.json',dict(routes=selected['routes'],summary=selected['metrics'],source=source))
    print('SELECTED',selected['method'],selected['metrics'],flush=True)

if __name__=='__main__':
    settings=optimization_parameters()['method_comparison']
    ap=argparse.ArgumentParser();ap.add_argument('--budget',type=float,default=settings['search_budget_s']);ap.add_argument('--seeds',default=','.join(map(str,settings['seeds'])));ap.add_argument('--schedule-seconds',type=float,default=settings['schedule_budget_s'])
    a=ap.parse_args();run(a.budget,tuple(int(s) for s in a.seeds.split(',')),a.schedule_seconds)
