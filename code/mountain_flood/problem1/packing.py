# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""问题一：用精确计数状态动态规划完成组批，并分析返航储备敏感性。"""

from functools import lru_cache
from itertools import product
import math

from mountain_flood.core.domain import Model
from mountain_flood.core.parameters import optimization_parameters

def q1(m,rho=None,objective='count'):
    if rho is None:
        reserves={t['rho'] for t in m.types.values()}
        if len(reserves)!=1:raise ValueError('Q1 default reserve requires equal model reserve percentages')
        rho=reserves.pop()/100
    allroutes=[];capacities=[];certs=[]
    for node in range(1,16):
        for g,t in m.types.items():
            lo,hi=0.,float(t['Q'])
            for _ in range(optimization_parameters()['q1_capacity_bisection_iterations']):
                mid=(lo+hi)/2
                if m.energy(g,0,node,mid)+m.energy(g,node,0,0)<=(1-rho)*t['E']:lo=mid
                else:hi=mid
            capacities.append(dict(node=node,g=g,rho=rho,maxload=lo))
        ids=[i for i,b in enumerate(m.boxes) if b['node']==node]
        kinds=list(dict.fromkeys(m.boxes[i]['kind'] for i in ids))
        buckets=[[i for i in ids if m.boxes[i]['kind']==k] for k in kinds]
        counts=tuple(map(len,buckets));patterns=[]
        for sizes in product(*(range(c+1) for c in counts)):
            if not any(sizes):continue
            chosen=[b for bucket,n in zip(buckets,sizes) for b in bucket[:n]]
            for g in m.types:
                r=m.route(g,chosen,[node],rho)
                if r:
                    cost=(1,r['energy'],r['duration']) if objective=='count' else ((r['energy'],1,r['duration']) if objective=='energy' else (r['duration'],1,r['energy']))
                    patterns.append((sizes,g,cost))
        @lru_cache(None)
        def dp(state):
            if not any(state):return (0.,0.,0.),()
            best=(float('inf'),)*3;path=()
            first=next(i for i,v in enumerate(state) if v)
            for j,(sz,g,cost) in enumerate(patterns):
                if sz[first]==0 or any(a>b for a,b in zip(sz,state)):continue
                val,tail=dp(tuple(b-a for a,b in zip(sz,state)))
                value=tuple(a+b for a,b in zip(val,cost))
                if value<best:best=value;path=(j,)+tail
            return best,path
        value,path=dp(counts)
        if not math.isfinite(value[0]):
            return dict(routes=[],capacities=capacities,certificates=certs,summary=dict(feasible=False,failed_node=node,status=2,message='Exact count-state dynamic program infeasible'))
        offsets=[0]*len(counts)
        for j in path:
            sizes,g,_=patterns[j];chosen=[]
            for k,n in enumerate(sizes):chosen.extend(buckets[k][offsets[k]:offsets[k]+n]);offsets[k]+=n
            allroutes.append(m.route(g,chosen,[node],rho))
        certs.append(dict(node=node,status=0,gap=0.,candidates=len(patterns),states=dp.cache_info().currsize,method='exact_count_state_DP'))
    return dict(routes=allroutes,capacities=capacities,certificates=certs,summary=dict(count=len(allroutes),energy=sum(r['energy'] for r in allroutes),time=sum(r['duration'] for r in allroutes)))
