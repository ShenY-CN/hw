# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
"""固定计划能耗与链路损耗压力表；失败只表示原计划失效。"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "results/solution_certificate.json"
certificate = json.loads(source.read_text(encoding="utf-8"))
if certificate["status"] != "PASS":
    raise SystemExit("Independent certificate must pass before stress analysis")

output = dict(source_certificate_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              interpretation="fixed Q2/Q3 routes, machines and schedule; no reoptimization",
              transport_energy=[], communication_loss=[])
for question in ("q2", "q3"):
    routes = certificate[question]["energy_breakdown"]
    for multiplier in (1.00, 1.01, 1.02, 1.03, 1.05):
        rows = []
        for route in routes:
            energy = route["horizontal_kwh"] * multiplier + route["climb_kwh"]
            rated = route["energy_kwh"] / (1 - route["soc"])
            soc = 1 - energy / rated
            rows.append(dict(route=route["id"], energy_kwh=energy, soc=soc,
                             reserve_margin_kwh=route["reserve_kwh"] - energy))
        failures = [row["route"] for row in rows if row["reserve_margin_kwh"] < -1e-8]
        output["transport_energy"].append(dict(question=question, horizontal_multiplier=multiplier,
                                               violating_routes=failures, violation_count=len(failures),
                                               min_soc=min(row["soc"] for row in rows),
                                               transport_energy_kwh=sum(row["energy_kwh"] for row in rows)))
for extra in (0, 0.5, 1, 2, 3):
    margins = [item["margin_db"] - extra for item in certificate["communication"]["intervals"]]
    output["communication_loss"].append(dict(extra_loss_db=extra,
                                             uncertified_intervals=sum(x < -1e-8 for x in margins),
                                             minimum_remaining_margin_db=min(margins)))
target = ROOT / "results/controlled_stress_20260926.json"
target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(output, ensure_ascii=False, indent=2))
