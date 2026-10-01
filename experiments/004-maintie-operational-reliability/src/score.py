#!/usr/bin/env python3
"""Deterministic EXP-004 per-run and repeated-run analysis."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
EXP003 = REPO / "experiments/003-maintie-consistency-correctness"
WITHIN_DRAWS = 10_000
WITHIN_SEED = 4004
ACROSS_DRAWS = 10_000
ACROSS_SEED = 4005
MIN_ITEMS_PER_STRATUM = 30
MIN_GROUPS_PER_STRATUM = 15


def verify_candidate() -> None:
    lock = load_json(ROOT / "data/candidate-artifact-lock.json")
    for name, expected in lock["artifacts"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"candidate artifact mismatch: {name}")
    for name, expected in lock["external_bindings"].items():
        if hashlib.sha256((REPO / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"candidate external binding mismatch: {name}")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


@cache
def baseline_scorer():
    spec = importlib.util.spec_from_file_location("exp003_frozen_score", EXP003 / "src/score.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rate(rows: list[dict[str, Any]], key: str) -> float | None:
    return sum(bool(r[key]) for r in rows) / len(rows) if rows else None


def group_count(rows: list[dict[str, Any]]) -> int:
    return len({r["duplicate_group"] for r in rows})


def contrast(rows: list[dict[str, Any]], agreement: str) -> dict[str, Any]:
    accepted = [r for r in rows if r[agreement]]
    rejected = [r for r in rows if not r[agreement]]
    aa, ra = rate(accepted, "correct"), rate(rejected, "correct")
    return {"valid_n": len(rows), "accepted_n": len(accepted), "rejected_n": len(rejected),
            "accepted_record_groups": group_count(accepted), "rejected_record_groups": group_count(rejected),
            "coverage": len(accepted) / len(rows) if rows else None,
            "accepted_accuracy": aa, "rejected_accuracy": ra,
            "accuracy_difference": aa - ra if aa is not None and ra is not None else None,
            "accepted_wrong_n": sum(not r["correct"] for r in accepted),
            "accepted_wrong_rate": rate([{**r, "wrong": not r["correct"]} for r in accepted], "wrong")}


def estimable(result: dict[str, Any]) -> bool:
    return (result["accepted_n"] >= MIN_ITEMS_PER_STRATUM and result["rejected_n"] >= MIN_ITEMS_PER_STRATUM and
            result["accepted_record_groups"] >= MIN_GROUPS_PER_STRATUM and result["rejected_record_groups"] >= MIN_GROUPS_PER_STRATUM)


def quantiles(values: list[float]) -> list[float] | None:
    if not values:
        return None
    values.sort()
    return [values[round((len(values) - 1) * .025)], values[round((len(values) - 1) * .975)]]


def cluster_bootstrap(rows: list[dict[str, Any]], agreement: str, draws: int = WITHIN_DRAWS, seed: int = WITHIN_SEED) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["duplicate_group"]].append(row)
    groups = sorted(grouped); rng = random.Random(seed); values = []
    for _ in range(draws):
        sample = [r for _ in groups for r in grouped[rng.choice(groups)]]
        value = contrast(sample, agreement)["accuracy_difference"]
        if value is not None:
            values.append(value)
    return {"method": "record_or_exact_duplicate_group_bootstrap", "draws": draws,
            "seed": seed, "estimable_draws": len(values), "ci95": quantiles(values)}


def method_gap_bootstrap(rows: list[dict[str, Any]], draws: int = WITHIN_DRAWS, seed: int = WITHIN_SEED + 2) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["duplicate_group"]].append(row)
    groups = sorted(grouped); rng = random.Random(seed); values = []
    for _ in range(draws):
        sample = [r for _ in groups for r in grouped[rng.choice(groups)]]
        ab = contrast(sample, "cross_agree")["accuracy_difference"]
        ac = contrast(sample, "repeat_agree")["accuracy_difference"]
        if ab is not None and ac is not None:
            values.append(ab - ac)
    return {"method": "paired_record_or_exact_duplicate_group_bootstrap", "draws": draws,
            "seed": seed, "estimable_draws": len(values), "ci95": quantiles(values)}


def parse_run(response_path: Path) -> tuple[list[dict[str, Any]], Counter[str], dict[str, int]]:
    scorer = baseline_scorer()
    labels = load_json(EXP003 / "data/label-space.json")
    inputs = {r["record_id"]: r for r in load_jsonl(EXP003 / "data/evaluation-inputs.jsonl")}
    gold = {r["record_id"]: r for r in load_jsonl(EXP003 / "data/evaluation-gold.jsonl")}
    expert = {r["source_record_id"]: r for r in load_jsonl(ROOT / "expert/expert-annotations-final.jsonl")
              if r["final_disposition"] == "outcome_joinable"}
    responses = load_jsonl(response_path); indexed = {}; failures: Counter[str] = Counter()
    for row in responses:
        key = (row.get("record_id"), row.get("task"))
        if key in indexed:
            raise ValueError(f"duplicate logical observation: {key}")
        indexed[key] = row
    parsed = {}
    for rid, record in inputs.items():
        span_ids = [x["span_id"] for x in record["spans"]]
        for task in ("A_detailed", "B_broad", "C_detailed_reworded"):
            row = indexed.get((rid, task))
            if row is None:
                parsed[(rid, task)] = None; failures["missing_call"] += 1; continue
            if row.get("terminal_failure") or row.get("call_error"):
                parsed[(rid, task)] = None; failures["terminal_failure"] += 1; continue
            permitted = set(labels["broad_permitted_labels"] if task == "B_broad" else labels["detailed_permitted_labels"])
            response = row.get("provider_response") or {}
            truncated = response.get("done_reason") == "length" or response.get("status") == "incomplete"
            value, error = scorer.strict_parse(row.get("raw_text"), span_ids, permitted, truncated)
            parsed[(rid, task)] = value
            if error:
                failures[error] += 1
    items = []
    for rid, truth in gold.items():
        exp = expert.get(rid)
        for entity in truth["gold"]:
            if not entity["eligible"]:
                continue
            sid = entity["span_id"]
            a, b, c = (parsed[(rid, t)] for t in ("A_detailed", "B_broad", "C_detailed_reworded"))
            al, bl, cl = (x.get(sid) if x else None for x in (a, b, c))
            parent = "/".join(al.split("/")[:2]) if al and len(al.split("/")) >= 2 else None
            items.append({"record_id": rid, "duplicate_group": truth["duplicate_group"], "span_id": sid,
                          "correct": al == entity["label"], "a_valid": al is not None,
                          "cross_valid": al is not None and bl is not None and parent is not None,
                          "repeat_valid": al is not None and cl is not None,
                          "abc_valid": al is not None and bl is not None and cl is not None and parent is not None,
                          "cross_agree": parent == bl if parent and bl else None,
                          "repeat_agree": al == cl if al and cl else None,
                          "expert": exp})
    attempts = sum(r.get("attempt_count", 0) for r in responses)
    return items, failures, {"logical_observations_recorded": len(responses), "attempts": attempts}


def subgroup(items: list[dict[str, Any]], name: str, predicate) -> dict[str, Any]:
    subset = [r for r in items if r["expert"] is not None and predicate(r["expert"])]
    cross = [r for r in subset if r["cross_valid"]]
    repeat = [r for r in subset if r["repeat_valid"]]
    cr = contrast(cross, "cross_agree")
    return {"name": name, "expert_records": len({r["record_id"] for r in subset}),
            "eligible_model_observations": len(subset), "overall_accuracy": rate(subset, "correct"),
            "valid_cross_level_observations": len(cross), "cross_level": cr,
            "consistent_but_wrong_rate": cr["accepted_wrong_rate"],
            "repeat_question": contrast(repeat, "repeat_agree"),
            "uncertainty": cluster_bootstrap(cross, "cross_agree") if cross else None}


def score_run(response_path: Path) -> dict[str, Any]:
    items, failures, operations = parse_run(response_path)
    cross = [r for r in items if r["cross_valid"]]; repeat = [r for r in items if r["repeat_valid"]]
    common = [r for r in items if r["abc_valid"]]
    cross_result, repeat_result = contrast(cross, "cross_agree"), contrast(repeat, "repeat_agree")
    common_cross, common_repeat = contrast(common, "cross_agree"), contrast(common, "repeat_agree")
    gap = None if None in (common_cross["accuracy_difference"], common_repeat["accuracy_difference"]) else common_cross["accuracy_difference"] - common_repeat["accuracy_difference"]
    high = [r for r in cross if r["expert"] and r["expert"]["operational_consequence"] == "high" and r["cross_agree"]]
    subgroups = [
        subgroup(items, "operational_consequence_high", lambda e: e["operational_consequence"] == "high"),
        subgroup(items, "operational_consequence_not_high", lambda e: e["operational_consequence"] != "high"),
        subgroup(items, "specificity_required_high", lambda e: e["specificity_required"] == "high"),
        subgroup(items, "specificity_required_medium", lambda e: e["specificity_required"] == "medium"),
        subgroup(items, "missing_machine_identity", lambda e: "machine_identity" in e["missing_information"]),
        subgroup(items, "machine_identity_not_marked_missing", lambda e: "machine_identity" not in e["missing_information"]),
    ]
    return {"schema_version": 1, "eligible_items": len(items),
            "overall_A_accuracy": rate(items, "correct"), "valid_A_items": sum(r["a_valid"] for r in items),
            "valid_A_coverage": sum(r["a_valid"] for r in items) / len(items),
            "cross_level": {**cross_result, "Delta_AB": cross_result["accuracy_difference"],
                            "minimum_evidence_satisfied": estimable(cross_result),
                            "uncertainty": cluster_bootstrap(cross, "cross_agree")},
            "repeated_question": {**repeat_result, "Delta_AC": repeat_result["accuracy_difference"],
                                  "uncertainty": cluster_bootstrap(repeat, "repeat_agree", seed=WITHIN_SEED + 1)},
            "common_valid_ABC": {"n": len(common), "cross_level": common_cross, "repeated_question": common_repeat,
                                 "MethodGap": gap, "uncertainty": method_gap_bootstrap(common)},
            "high_consequence_CBW": {"numerator": sum(not r["correct"] for r in high), "denominator": len(high),
                                     "rate": sum(not r["correct"] for r in high) / len(high) if high else None,
                                     "interpretation": "performance conditional on expert-rated consequence; not measured plant risk"},
            "expert_subgroups": subgroups,
            "sparse_descriptive_themes": ["all frozen qualitative themes except missing_machine_identity"],
            "output_failures_by_call": dict(sorted(failures.items())),
            "terminal_failures": failures["terminal_failure"], "operations": operations,
            "_item_evidence": items}


def crossed_bootstrap(run_items: list[list[dict[str, Any]]], draws: int = ACROSS_DRAWS, seed: int = ACROSS_SEED) -> dict[str, Any]:
    groups = sorted({r["duplicate_group"] for rows in run_items for r in rows if r["cross_valid"]})
    indexed = [{g: [r for r in rows if r["cross_valid"] and r["duplicate_group"] == g] for g in groups} for rows in run_items]
    rng = random.Random(seed); values = []
    for _ in range(draws):
        sampled_runs = [rng.randrange(len(run_items)) for _ in run_items]
        sampled_groups = [rng.choice(groups) for _ in groups]
        effects = []
        for run_index in sampled_runs:
            sample = [r for g in sampled_groups for r in indexed[run_index][g]]
            value = contrast(sample, "cross_agree")["accuracy_difference"]
            if value is not None:
                effects.append(value)
        if effects:
            values.append(sum(effects) / len(effects))
    return {"method": "crossed_run_and_record_group_bootstrap", "draws": draws, "seed": seed,
            "estimable_draws": len(values), "ci95": quantiles(values)}


def aggregate(scored_paths: list[Path]) -> dict[str, Any]:
    runs = [load_json(p) for p in scored_paths]
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path, run in zip(scored_paths, runs):
        manifest = load_json(path.parent / "run-manifest.json")
        run["model_key"] = manifest["model_key"]; run["replicate"] = manifest["replicate"]
        by_model[manifest["model_key"]].append(run)
    output = {}
    for model, model_runs in sorted(by_model.items()):
        model_runs.sort(key=lambda x: x["replicate"])
        effects = [r["cross_level"]["Delta_AB"] for r in model_runs if r["cross_level"]["Delta_AB"] is not None]
        uncertainty = crossed_bootstrap([r["_item_evidence"] for r in model_runs])
        estimable_runs = sum(r["cross_level"]["minimum_evidence_satisfied"] for r in model_runs)
        positive_runs = sum((r["cross_level"]["Delta_AB"] or 0) > 0 for r in model_runs)
        replicated = (len(model_runs) == 5 and estimable_runs >= 4 and positive_runs >= 4 and
                      uncertainty["ci95"] is not None and uncertainty["ci95"][0] > 0)
        output[model] = {"runs": model_runs, "estimable_runs": estimable_runs, "positive_Delta_AB_runs": positive_runs,
                         "mean_Delta_AB": sum(effects) / len(effects) if effects else None,
                         "between_run_Delta_AB_sd": math.sqrt(sum((x - sum(effects) / len(effects)) ** 2 for x in effects) / (len(effects) - 1)) if len(effects) > 1 else None,
                         "crossed_uncertainty": uncertainty, "replicated": replicated}
    panel = all(output.get(m, {}).get("replicated") is True for m in ("ollama_qwen", "ollama_gemma"))
    model_means = {m: v["mean_Delta_AB"] for m, v in output.items() if v["mean_Delta_AB"] is not None}
    return {"schema_version": 1, "models": output, "panel_level_replication": panel,
            "between_model_heterogeneity": {"mean_Delta_AB_by_model": model_means,
                                             "range": max(model_means.values()) - min(model_means.values()) if len(model_means) > 1 else None},
            "rule": "Each local model: >=4/5 estimable, >=4/5 Delta_AB>0, crossed-bootstrap mean-Delta_AB CI wholly >0. Panel requires both local models."}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run"); one.add_argument("responses", type=Path); one.add_argument("--output", type=Path, required=True)
    many = sub.add_parser("aggregate"); many.add_argument("scored", type=Path, nargs="+"); many.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify_candidate()
    value = score_run(args.responses) if args.command == "run" else aggregate(args.scored)
    args.output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
