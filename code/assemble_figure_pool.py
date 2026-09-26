# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
"""Assemble the 2026 submission audit figure pool from reproducible figures."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "figures" / os.environ.get("MOUNTAIN_FLOOD_FIGURE_SET", "audit_verified_20260925")
POOL = ROOT / "figures" / "rigor_pool_20260926"
MAP = {
    "flow_overall_model": "fig_roadmap",
    "raw_q1_dem_nodes": "q1_dem_nodes",
    "process_q1_sensitivity": "q1_sensitivity",
    "result_q1_safe_capacity": "q1_safe_capacity",
    "process_q2_search_comparison": "q2_search_comparison",
    "result_q2_transport_routes": "q2_transport_routes",
    "process_q3_communication_timeline": "q3_communication_timeline",
    "result_q3_joint_timeline": "q3_joint_timeline",
    "process_q4_task_network": "q4_task_network",
    "result_q4_resource_deficit": "q4_resource_deficit",
}
RAW = ("raw_q2_box_deadline_mix", "raw_q3_link_budgets", "raw_q4_initial_inventory")
FORMATS = ("pdf", "png", "svg")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not SOURCE.is_dir():
        raise FileNotFoundError(SOURCE)
    POOL.mkdir(parents=True, exist_ok=True)
    for target, source in MAP.items():
        for extension in FORMATS:
            shutil.copy2(SOURCE / f"{source}.{extension}", POOL / f"{target}.{extension}")
    expected = {f"{name}.{extension}" for name in (*MAP, *RAW) for extension in FORMATS}
    actual = {path.name for path in POOL.iterdir() if path.suffix in (".pdf", ".png", ".svg")}
    if actual != expected:
        raise RuntimeError(f"Figure pool incomplete: missing={expected-actual}, extra={actual-expected}")
    manifest = {
        "source_set": SOURCE.name,
        "generated_sources": MAP,
        "raw_input_figures": list(RAW),
        "file_sha256": {name: sha(POOL / name) for name in sorted(expected)},
    }
    (POOL / "figure_pool_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"PASS {len(expected)//3} figures, 3 formats each: {POOL}")


if __name__ == "__main__":
    main()
