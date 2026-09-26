# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
"""Q2 正式算法对比：同种子共享独立初始解、固定预算与统一排程。"""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))

import argparse
import json
import statistics

from mountain_flood.core.domain import Model, RESULT, save
from mountain_flood.problem2.search import (
    METHODS, decode, minimum_energy_margin, nondominated, plan_from_routes,
    refine_timefirst, search,
)
from mountain_flood.problem2.transport import construct, metrics
from mountain_flood.validation.replay import validate


def plain(value):
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def stable_search_record(record):
    """Remove wall-clock observations while retaining the actual work count."""
    cleaned={k:v for k,v in record.items() if k!="elapsed_s"}
    cleaned["history"]=[{k:v for k,v in item.items() if k!="elapsed_s"}
                        for item in record["history"]]
    return cleaned


def stable_solver_record(stages):
    """Keep reproducible objectives; solver FEASIBLE/OPTIMAL timing may vary."""
    return [{k:v for k,v in stage.items() if k in ("stage","objective")}
            for stage in stages]


def vector(candidate):
    z=candidate["metrics"]
    return (z["weighted_tardiness"], z["makespan"], z["energy"],
            z["count"], -z["minimum_energy_margin"])


def pareto(candidates):
    out=[]
    for item in candidates:
        a=vector(item)
        if not any(other is not item and all(x <= y+1e-8 for x,y in zip(vector(other),a))
                   and any(x < y-1e-8 for x,y in zip(vector(other),a))
                   for other in candidates):
            out.append(item)
    # 同一解可由多个算法、种子或 profile 重复到达。Pareto 输出按
    # “目标向量 + 路线签名”去重，避免把同一 warm-start 伪装成多个折中解。
    unique=[];seen=set()
    for item in out:
        route_signature=tuple(sorted(
            (route["g"],tuple(route["boxes"]),tuple(route["order"]))
            for route in item["routes"]
        ))
        key=(tuple(vector(item)),route_signature)
        if key not in seen:
            seen.add(key);unique.append(item)
    return unique


def summary(rows):
    answer={}
    for method in METHODS:
        group=[row for row in rows if row["method"]==method]
        record={"runs":len(group),"feasible_runs":sum(row["validation"]["pass_"] for row in group)}
        for key in ("weighted_tardiness","makespan","weighted_arrival","energy","count","minimum_energy_margin"):
            values=[row["metrics"][key] for row in group]
            record[key]={"mean":statistics.mean(values),"std":statistics.pstdev(values),"best":min(values) if key!="minimum_energy_margin" else max(values)}
        record["evaluations"]=[row["search"]["valid_candidates_evaluated"] for row in group]
        record["wall_guard_hits"]=sum(row["search"]["wall_clock_guard_hit"] for row in group)
        answer[method]=record
    return answer


def run(evaluations=30, wall_seconds=90.0, schedule_seconds=1.2):
    model=Model()
    archived=json.loads((RESULT/"q2_time_energy_candidate.json").read_text(encoding="utf8"))
    warm_plan=plan_from_routes(archived["routes"])
    warm_decoded=decode(model,warm_plan)
    warm_metrics=metrics(model,warm_decoded)
    epsilon={"weighted_tardiness":0.0,"makespan":warm_metrics["makespan"]*1.10}
    seeds=list(range(10));rows=[];schedule_cache={};starts={};initial_seeds={}

    # 每个种子只构造一次独立初始解；四种方法共享该起点，保证比较公平。
    # 历史24架次候选仅作为外部 warm-start 基线，不再充当主算法起点。
    for seed in seeds:
        for trial_seed in range(seed*100,seed*100+20):
            initial=construct(model,trial_seed,multi=True)
            if initial is not None:
                starts[seed]=plan_from_routes(initial)
                initial_seeds[seed]=trial_seed
                break
        if seed not in starts:
            raise RuntimeError(f"No hard-feasible independent initial plan for seed {seed}")

    def scheduled(plan):
        key=json.dumps(plan,sort_keys=True)
        if key not in schedule_cache:
            routes=decode(model,plan)
            refined,solver=refine_timefirst(model,routes,schedule_seconds)
            if refined is None:
                raise RuntimeError(f"CP-SAT failed: {solver}")
            schedule_cache[key]=(refined,solver)
        return schedule_cache[key]

    # 四算法共享同一道独立初始解，按相同有效候选数停止。
    for seed in seeds:
        initial_plan=starts[seed]
        initial_decoded=decode(model,initial_plan)
        initial_metrics=metrics(model,initial_decoded)
        epsilon={"weighted_tardiness":initial_metrics["weighted_tardiness"],
                 "makespan":initial_metrics["makespan"]*1.10}
        for method in METHODS:
            rec=search(model,method,initial_plan,seed,wall_seconds,evaluations,"timeliness",epsilon)
            refined,solver=scheduled(rec["plan"])
            z=metrics(model,refined);z["minimum_energy_margin"]=minimum_energy_margin(model,refined)
            check=validate(model,{"routes":refined},2)
            rows.append(dict(profile="timeliness",method=method,seed=seed,
                             initial_seed=initial_seeds[seed],initial_metrics=initial_metrics,
                             search=stable_search_record(rec),
                             solver=stable_solver_record(solver),metrics=z,
                             validation=check,routes=refined))
            print("Q2 formal",method,seed,rec["valid_candidates_evaluated"],z,flush=True)

    # 目标配置也从同一组独立初始解出发；使用 hill 作为补充剖面代表，
    # 不把它混入四算法的主排名。
    tradeoffs=[]
    for profile in ("energy","count","robust"):
        for seed in seeds:
            initial_plan=starts[seed]
            initial_metrics=metrics(model,decode(model,initial_plan))
            epsilon={"weighted_tardiness":initial_metrics["weighted_tardiness"],
                     "makespan":initial_metrics["makespan"]*1.10}
            rec=search(model,"hill",initial_plan,seed,wall_seconds,evaluations,profile,epsilon)
            refined,solver=scheduled(rec["plan"])
            z=metrics(model,refined);z["minimum_energy_margin"]=minimum_energy_margin(model,refined)
            check=validate(model,{"routes":refined},2)
            tradeoffs.append(dict(profile=profile,method="hill",seed=seed,
                                  initial_seed=initial_seeds[seed],initial_metrics=initial_metrics,
                                  search=stable_search_record(rec),
                                  solver=stable_solver_record(solver),metrics=z,
                                  validation=check,routes=refined))
            print("Q2 epsilon",profile,seed,rec["valid_candidates_evaluated"],z,flush=True)

    feasible=[row for row in rows+tradeoffs if row["validation"]["pass_"]]
    frontier=pareto(feasible)
    representatives={
        "timeliness":min(feasible,key=lambda x:(x["metrics"]["weighted_tardiness"],x["metrics"]["makespan"],x["metrics"]["weighted_arrival"])),
        "energy":min(feasible,key=lambda x:(x["metrics"]["energy"],x["metrics"]["makespan"])),
        "count":min(feasible,key=lambda x:(x["metrics"]["count"],x["metrics"]["energy"])),
        "robust":max(feasible,key=lambda x:(x["metrics"]["minimum_energy_margin"],-x["metrics"]["energy"])),
    }
    result=plain(dict(
        protocol=dict(initialization="independent construct per seed; same initial plan shared by all methods",
                      initial_seeds=initial_seeds,
                      warm_start="q2_time_energy_candidate.json: external 24-flight baseline",
                      seeds=seeds,
                      methods=list(METHODS),nominal_valid_candidate_cap=evaluations,
                      wall_clock_guard_s=wall_seconds,schedule_guard_s=schedule_seconds,
                      epsilon_rule="per seed: weighted_tardiness <= initial value; makespan <= 1.10 * initial value",
                      objective_profiles=["timeliness","energy","count","robust"]),
        warm_start_metrics=dict(**warm_metrics,minimum_energy_margin=minimum_energy_margin(model,warm_decoded)),
        algorithm_statistics=summary(rows),trials=rows,tradeoff_trials=tradeoffs,
        pareto=[dict(profile=x["profile"],method=x["method"],seed=x["seed"],metrics=x["metrics"]) for x in frontier],
        representatives={name:dict(profile=x["profile"],method=x["method"],seed=x["seed"],metrics=x["metrics"],routes=x["routes"]) for name,x in representatives.items()},
        tradeoff_conclusion=("The main table compares four methods from matched independent starts. "
                             "Energy/count/robust profiles are supplementary hill-search runs under "
                             "the same starts and budget; the archived 24-flight solution remains a "
                             "warm-start baseline, not a method result."),
    ))
    save("q2_formal_protocol.json",result)
    print("PASS q2_formal_protocol.json",flush=True)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--evaluations",type=int,default=30)
    parser.add_argument("--wall-seconds",type=float,default=90.0)
    parser.add_argument("--schedule-seconds",type=float,default=1.2)
    args=parser.parse_args()
    run(args.evaluations,args.wall_seconds,args.schedule_seconds)
