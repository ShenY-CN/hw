# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""问题四：将不可拆分的运输路线组件分配给不同救援小组，并比较资源方案。"""

from collections import defaultdict
from functools import lru_cache

import numpy as np

from mountain_flood.core.domain import RESULT, charge, save
from mountain_flood.validation.resources import peak


def partition(model, data, output="q4.json"):
    """穷举路线组件在 2 组和 3 组之间的分配，并保存资源需求结果。"""
    routes = data["routes"]
    relays = data["relays"]
    communication = data["communication"]

    # 同一条多服务区路线上的服务区不可拆分，先用并查集构造原子组件。
    parent = list(range(16))

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for route in routes:
        first = route["order"][0]
        for node in route["order"][1:]:
            parent[find(node)] = find(first)

    components_by_root = defaultdict(list)
    for node in range(1, 16):
        components_by_root[find(node)].append(node)
    components = list(components_by_root.values())
    component_count = len(components)
    print("partition components", components, flush=True)

    inventory = [4, 2, 2, 6, 4, 4, 2, 6]

    @lru_cache(None)
    def group(mask):
        nodes = [
            node
            for index, component in enumerate(components)
            if mask >> index & 1
            for node in component
        ]
        tasks = [route for route in routes if route["order"][0] in nodes]
        transport_ids = {route["id"] for route in tasks}
        relay_ids = {
            interval["relay_task"]
            for interval in communication
            if interval["route"] in transport_ids and interval["relay_task"]
        }
        relay_tasks = [relay for relay in relays if relay["id"] in relay_ids]

        resources = []
        for drone_type in model.types:
            resources.append(
                peak(
                    [
                        (route["start"], route["end"])
                        for route in tasks
                        if route["g"] == drone_type
                    ]
                )
            )
        for drone_type in model.types:
            resources.append(
                peak(
                    [
                        (
                            route["start"],
                            route["end"]
                            + charge(route["soc"], model.types[drone_type]["charge"]),
                        )
                        for route in tasks
                        if route["g"] == drone_type
                    ]
                )
            )
        resources.append(
            peak([(relay["start"], relay["end"] + 300) for relay in relay_tasks])
        )
        resources.append(
            peak(
                [
                    (relay["start"], relay["end"] + charge(relay["soc"], 1800))
                    for relay in relay_tasks
                ]
            )
        )
        return dict(
            nodes=nodes,
            resources=resources,
            work=sum(route["duration"] for route in tasks),
            boxes=sum(len(route["boxes"]) for route in tasks),
            transport_ids=sorted(transport_ids),
            relay_ids=sorted(relay_ids),
        )

    all_mask = (1 << component_count) - 1
    answer = {}
    for group_count in (2, 3):
        best = None
        balanced = None
        evaluated = 0
        frontier = {}

        def visit(index, masks):
            nonlocal best, balanced, evaluated
            if index == component_count:
                if len(masks) != group_count:
                    return
                evaluated += 1
                groups = [group(mask) for mask in masks]
                total = np.sum([item["resources"] for item in groups], axis=0).astype(int).tolist()
                deficit = [max(0, target - available) for target, available in zip(total, inventory)]
                workloads = [item["work"] for item in groups]
                cv = float(np.std(workloads) / np.mean(workloads))
                score = (sum(deficit), sum(total), cv)
                record = dict(
                    K=group_count,
                    groups=groups,
                    total=total,
                    deficit=deficit,
                    unused=[max(0, available - used) for used, available in zip(total, inventory)],
                    cv=cv,
                    score=score,
                )
                if best is None or score < tuple(best["score"]):
                    best = record
                balance_score = (sum(deficit), cv, sum(total))
                if balanced is None or balance_score < (
                    sum(balanced["deficit"]), balanced["cv"], sum(balanced["total"])
                ):
                    balanced = record
                key = (sum(deficit), sum(total))
                if key not in frontier or cv < frontier[key]["cv"]:
                    frontier[key] = record
                return

            # 递归时将下一个原子组件放入现有小组，或新建一个小组。
            for group_index in range(len(masks)):
                next_masks = masks.copy()
                next_masks[group_index] |= 1 << index
                visit(index + 1, next_masks)
            if len(masks) < group_count:
                visit(index + 1, masks + [1 << index])

        visit(0, [])
        if best is None:
            raise RuntimeError("不可拆分组件数量不足，无法组成要求数量的救援小组")
        answer[str(group_count)] = dict(
            selected=best,
            balanced=balanced,
            evaluated=evaluated,
            frontier=list(frontier.values()),
        )
        print(
            "Q4",
            group_count,
            "evaluated",
            evaluated,
            "resources",
            best["total"],
            "deficit",
            best["deficit"],
            "cv",
            best["cv"],
            flush=True,
        )

    save(output, dict(components=components, inventory=inventory, schemes=answer))
    return dict(components=components, inventory=inventory, schemes=answer)


if __name__ == "__main__":
    import json

    from mountain_flood.core.domain import Model

    model = Model()
    data = json.loads((RESULT / "q3.json").read_text(encoding="utf-8"))
    partition(model, data)
