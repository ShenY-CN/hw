# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
"""Independently replay archived K-scan route witnesses without rerunning wall-clock search."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from independent_solution_audit import Raw, audit_transport


ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "results/kmax_scan_20260926.json"
OUTPUT = ROOT / "results/kmax_archive_audit_20260926.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    data = json.loads(SCAN.read_text(encoding="utf-8"))
    protocol = data["protocol"]
    expected = {(k, seed, method) for k in (2, 3, 4, 5)
                for seed in (0, 1, 2)
                for method in ("grasp", "hill", "anneal", "tabu")}
    errors = []
    if len(data["trials"]) != 48 or {(t["kmax"], t["seed"], t["method"])
                                        for t in data["trials"]} != expected:
        errors.append("K-scan trial inventory is incomplete or duplicated")
    if protocol["source_hashes"]["base_parameters"] != sha(ROOT / "config/base_parameters.json"):
        errors.append("Base parameters changed since K scan")
    if protocol["source_hashes"]["optimization_parameters"] != sha(ROOT / "config/optimization_parameters.json"):
        errors.append("Optimization parameters changed since K scan")
    raw = Raw()
    rows = []
    for trial in data["trials"]:
        ident = f"K{trial['kmax']}/{trial['seed']}/{trial['method']}"
        trial_errors = []
        if trial["status"] != "PASS":
            trial_errors.append("Archived trial status is not PASS")
        routes = trial.get("routes", [])
        if not routes or any(len(route["order"]) > trial["kmax"] for route in routes):
            trial_errors.append("Route stop limit violated or witness missing")
        else:
            replay = audit_transport(raw, ident, {"routes": routes, "summary": trial["metrics"]})
            trial_errors.extend(replay["errors"])
            if abs(replay["min_transport_soc"] - trial["min_return_soc"]) > 1e-7:
                trial_errors.append("Minimum SOC mismatch")
        rows.append({"trial": ident, "pass_": not trial_errors, "errors": trial_errors})
        errors.extend(f"{ident}: {message}" for message in trial_errors)
    output = {"status": "PASS" if not errors else "FAIL",
              "scan_sha256": sha(SCAN), "trial_count": len(rows),
              "passed": sum(row["pass_"] for row in rows),
              "errors": errors, "trials": rows,
              "scope": "archive witness replay; does not repeat wall-clock search"}
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{output['status']} {output['passed']}/{len(rows)} K-scan witnesses")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
