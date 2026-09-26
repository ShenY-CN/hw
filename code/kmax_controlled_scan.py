# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
"""K=2/3/4/5 受控搜索：相同种子、方法与预算，输出完整路线见证。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from mountain_flood.core.domain import Model
from mountain_flood.core.parameters import optimization_parameters
from mountain_flood.problem2.search import METHODS, decode, plan_from_routes, refine_timefirst, search
from mountain_flood.problem2.transport import construct, metrics
from mountain_flood.validation.replay import validate


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, content: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2,
                                    default=lambda value: value.item() if hasattr(value, "item") else str(value)),
                         encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/kmax_scan_20260926.json")
    parser.add_argument("--search-seconds", type=float, default=6.0)
    parser.add_argument("--schedule-seconds", type=float, default=8.0)
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--methods", default=",".join(METHODS))
    args = parser.parse_args()
    output = ROOT / args.output
    if not output.resolve().is_relative_to(ROOT):
        raise ValueError("Output must remain inside the project")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite an existing scan: {output}")
    seeds = [int(value) for value in args.seeds.split(",")]
    methods = args.methods.split(",")
    if any(method not in METHODS for method in methods):
        raise ValueError("Unknown method")
    if args.search_seconds <= 0 or args.schedule_seconds <= 0:
        raise ValueError("Search and scheduling budgets must be positive")
    model = Model()
    settings = optimization_parameters()
    content = dict(protocol=dict(k_values=[2, 3, 4, 5], seeds=seeds, methods=methods,
                                 search_budget_s=args.search_seconds,
                                 schedule_budget_s=args.schedule_seconds,
                                 objective=["hard_violations", "weighted_tardiness", "makespan",
                                            "weighted_arrival", "energy", "count"],
                                 initial_seed_policy="first hard-feasible seed from seed*100 to seed*100+29",
                                 archived_q2_in_candidate_pool=False,
                                 wall_clock_discovery_is_not_bitwise_deterministic=True,
                                 source_hashes={"base_parameters": digest(ROOT / "config/base_parameters.json"),
                                                "optimization_parameters": digest(ROOT / "config/optimization_parameters.json")}),
                   trials=[])
    for k in content["protocol"]["k_values"]:
        settings["route_search"]["max_stops_per_route"] = k
        for seed in seeds:
            initial = None
            initial_seed = None
            for trial_seed in range(seed * 100, seed * 100 + settings["route_search"]["initial_seed_attempts"]):
                initial = construct(model, trial_seed, multi=True)
                if initial is not None:
                    initial_seed = trial_seed
                    break
            if initial is None:
                for method in methods:
                    content["trials"].append(dict(kmax=k, seed=seed, method=method,
                                                  status="NO_HARD_FEASIBLE_INITIAL_PLAN"))
                save(output, content)
                continue
            initial_plan = plan_from_routes(initial)
            for method in methods:
                started = time.monotonic()
                rec = search(model, method, initial_plan, seed, args.search_seconds)
                routes = decode(model, rec["plan"])
                refined, stages = refine_timefirst(model, routes, args.schedule_seconds)
                trial = dict(kmax=k, seed=seed, initial_seed=initial_seed, method=method,
                             search_elapsed_s=rec["elapsed_s"],
                             total_elapsed_s=time.monotonic() - started,
                             valid_candidates_evaluated=rec["valid_candidates_evaluated"],
                             iterations=rec["iterations"], history=rec["history"],
                             search_plan=rec["plan"], search_metrics=rec["heuristic"],
                             schedule_stages=stages)
                if refined is None:
                    trial["status"] = "SCHEDULE_FAILED"
                else:
                    for index, route in enumerate(refined, 1):
                        route["id"] = f"T{index:03d}"
                    check = validate(model, dict(routes=refined), 2)
                    trial.update(status="PASS" if check["pass_"] else "VALIDATION_FAILED",
                                 metrics=metrics(model, refined),
                                 min_return_soc=min(r["soc"] for r in refined),
                                 validation=check, routes=refined)
                content["trials"].append(trial)
                save(output, content)
                print(f"K={k} seed={seed} {method}: {trial['status']} "
                      f"valid={trial['valid_candidates_evaluated']} "
                      f"makespan={trial.get('metrics', {}).get('makespan')}", flush=True)
    print(f"Saved {len(content['trials'])} controlled trials to {output}", flush=True)


if __name__ == "__main__":
    main()
