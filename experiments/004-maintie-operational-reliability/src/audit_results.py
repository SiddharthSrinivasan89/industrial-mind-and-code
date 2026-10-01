#!/usr/bin/env python3
"""Maker audit of the complete EXP-004 production and result package."""
from __future__ import annotations

import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    score = module("exp004_score_audit", ROOT / "src/score.py")
    report = module("exp004_report_audit", ROOT / "src/build_result_analysis.py")
    score.verify_candidate()
    runs = report.all_runs()
    require(len(runs) == 15, "production run count")
    require(Counter(run["model_key"] for run in runs) == {"azure_astra": 5, "ollama_qwen": 5, "ollama_gemma": 5}, "model/run census")
    expected_tasks = {"A_detailed", "B_broad", "C_detailed_reworded"}
    total_attempts = 0
    transient = 0
    for run in runs:
        responses, attempts = run["responses"], run["attempts"]
        keys = [(x["record_id"], x["task"]) for x in responses]
        require(len(responses) == 324 and len(set(keys)) == 324, f"logical census {run['manifest']['run_id']}")
        require({x["task"] for x in responses} == expected_tasks, f"task census {run['manifest']['run_id']}")
        require(len({x["record_id"] for x in responses}) == 108, f"record census {run['manifest']['run_id']}")
        require(sum(x["status"] == "success" for x in attempts) == 324, f"success census {run['manifest']['run_id']}")
        require(sum(x["attempt_count"] for x in responses) == len(attempts), f"attempt linkage {run['manifest']['run_id']}")
        require(not any(x.get("terminal_failure") for x in responses), f"terminal failure {run['manifest']['run_id']}")
        recomputed = score.score_run(run["run_dir"] / "responses.jsonl")
        require(recomputed == run["score"], f"score mismatch {run['manifest']['run_id']}")
        total_attempts += len(attempts)
        transient += sum(x["status"] == "transient_failure" for x in attempts)
    require(total_attempts == 4905 and transient == 45, "attempt totals")
    aggregate = load_json(ROOT / "results/analysis/aggregate.json")
    score_paths = [run["run_dir"] / "score.json" for run in runs]
    require(score.aggregate(score_paths) == aggregate, "aggregate recomputation")
    operations = report.build_operations(runs)
    detailed = report.build_detailed(runs)
    require(operations == load_json(ROOT / "results/analysis/operations.json"), "operational summary recomputation")
    require(detailed == load_json(ROOT / "results/analysis/detailed-analysis.json"), "detailed summary recomputation")
    require(aggregate["panel_level_replication"] is True, "panel replication outcome")
    for model_key in ("ollama_qwen", "ollama_gemma"):
        value = aggregate["models"][model_key]
        require(value["estimable_runs"] == 5, f"estimable runs {model_key}")
        require(value["positive_Delta_AB_runs"] == 5, f"positive runs {model_key}")
        require(value["crossed_uncertainty"]["ci95"][0] > 0, f"crossed interval {model_key}")
    authorization = load_json(ROOT / "PRODUCTION-AUTHORIZATION.json")
    require(authorization["authorized"] is False and authorization["authorization_state"] == "closed_completed", "authorization closure")
    require(authorization["completed_logical_calls"] == 4860 and authorization["completed_runs"] == 15, "authorization completion census")
    expert_text = (ROOT / "expert/expert-annotations-final.jsonl").read_text(encoding="utf-8")
    for forbidden in ('"correct"', '"cross_agree"', '"repeat_agree"', '"model_answer"'):
        require(forbidden not in expert_text, f"outcome leakage token {forbidden}")
    print(json.dumps({
        "status": "PASS",
        "runs": len(runs),
        "logical_observations": sum(len(x["responses"]) for x in runs),
        "attempts": total_attempts,
        "transient_failures_recovered": transient,
        "terminal_failures": 0,
        "per_run_scores_recomputed": 15,
        "aggregate_recomputed": True,
        "reporting_outputs_recomputed": True,
        "panel_level_replication": True,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
