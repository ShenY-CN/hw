# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
"""Q3 已认证候选的分解协调审计与最大最小链路裕度选择。"""
from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))

import json
import re

from mountain_flood.core.domain import Model, RESULT, save
from mountain_flood.validation.replay import validate


def dominates(a,b):
    keys=("weighted_tardiness","makespan","energy","flights","negative_margin")
    return all(a[k]<=b[k]+1e-8 for k in keys) and any(a[k]<b[k]-1e-8 for k in keys)


def run():
    model=Model();records=[]
    paths=[]
    for pattern in ("q3_hard_hill1_e*_trim.json","q3_hard_newq2_e*_trim.json",
                    "q3_hard_q2_e*_completion_trim.json","q3_hard_q2_e*_buffer15_trim.json",
                    "q3_hard_hill1_e*_margin.json"):
        paths.extend(sorted(RESULT.glob(pattern)))
    # 同一文件只评估一次；所有结论都来自已存的逐区间通信见证。
    for path in dict.fromkeys(paths):
        data=json.loads(path.read_text(encoding="utf8"));check=validate(model,data,3)
        if not check["pass_"]:
            continue
        summary=data["summary"]
        margin=min(item["margin"] for item in data["communication"])
        if "hill1" in path.name: family="hill1"
        elif "newq2" in path.name: family="newq2"
        else: family="q2"
        east_match=re.search(r"_e(\d+)",path.name)
        records.append(dict(
            file=path.name,transport_family=family,
            relay_window_east_s=int(east_match.group(1)) if east_match else None,
            weighted_tardiness=float(summary["weighted_tardiness"]),
            makespan=float(summary["makespan"]),energy=float(summary["energy"]),
            flights=int(summary["count"]+summary["relay_count"]),
            min_link_margin_db=float(margin),negative_margin=float(-margin),
            communication_intervals=len(data["communication"]),validation=check,
        ))
    if not records:
        raise RuntimeError("No independently valid Q3 candidate")
    frontier=[x for x in records if not any(y is not x and dominates(y,x) for y in records)]
    zero=[x for x in records if x["weighted_tardiness"]<=1e-8]
    fastest=min(x["makespan"] for x in zero);least_energy=min(x["energy"] for x in zero)
    epsilon=[x for x in zero if x["makespan"]<=fastest*1.05 and x["energy"]<=least_energy*1.01]
    robust=max(epsilon,key=lambda x:(x["min_link_margin_db"],-x["makespan"],-x["energy"]))

    # 将运输主问题候选族与通信子问题窗口分开记录：
    # 每轮先固定运输族，再由连续通信认证选出其最佳窗口。
    rounds=[]
    for index,family in enumerate(sorted({x["transport_family"] for x in records}),1):
        pool=[x for x in records if x["transport_family"]==family]
        chosen=max(pool,key=lambda x:(x["min_link_margin_db"],-x["makespan"],-x["energy"]))
        rounds.append(dict(round=index,master_transport_family=family,
                           communication_candidates=len(pool),certified_candidates=len(pool),
                           returned_candidate=chosen["file"],
                           returned_min_link_margin_db=chosen["min_link_margin_db"]))
    result=dict(
        protocol=dict(candidate_scope="finite archived transport families and relay windows",
                      transport_master_families=sorted({x["transport_family"] for x in records}),
                      communication_subproblem="continuous interval certificate replay",
                      epsilon=dict(weighted_tardiness=0,makespan_factor_from_fastest=1.05,
                                   energy_factor_from_minimum=1.01)),
        coordination_rounds=rounds,candidates=records,
        pareto=[{k:v for k,v in x.items() if k!="validation"} for x in frontier],
        maximin_link_margin_choice={k:v for k,v in robust.items() if k!="validation"},
        capability_limit=("The current transport master exposes route families but has no callable "
                          "communication-conflict cut interface. This run is therefore a finite "
                          "decomposition-coordination audit, not a proof of joint global optimality."),
    )
    save("q3_formal_coordination_audit.json",result)
    print("PASS",len(records),"candidates; robust",robust["file"],robust["min_link_margin_db"],flush=True)
    return result


if __name__=="__main__":run()
