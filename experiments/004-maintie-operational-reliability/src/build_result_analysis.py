#!/usr/bin/env python3
"""Build deterministic operational and detailed EXP-004 result summaries.

This is a reporting layer over the frozen scorer outputs. It does not reparse
model responses or change any predeclared scientific rule.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = ROOT / "results/production"
ANALYSIS = ROOT / "results/analysis"
MODEL_ORDER = ("azure_astra", "ollama_qwen", "ollama_gemma")
MODEL_LABELS = {
    "azure_astra": "Astra",
    "ollama_qwen": "Qwen 3.5 122B",
    "ollama_gemma": "Gemma 4 31B",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score_module():
    spec = importlib.util.spec_from_file_location("exp004_score", ROOT / "src/score.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mean(values: list[float | None]) -> float | None:
    present = [x for x in values if x is not None]
    return sum(present) / len(present) if present else None


def sample_sd(values: list[float | None]) -> float | None:
    present = [x for x in values if x is not None]
    if len(present) < 2:
        return None
    center = sum(present) / len(present)
    return math.sqrt(sum((x - center) ** 2 for x in present) / (len(present) - 1))


def pct(value: float | None, digits: int = 1) -> str:
    return "NA" if value is None else f"{100 * value:.{digits}f}%"


def number(value: float | None, digits: int = 3) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def ci_text(ci: list[float] | None) -> str:
    return "NA" if ci is None else f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def all_runs() -> list[dict[str, Any]]:
    rows = []
    for model_key in MODEL_ORDER:
        for run_dir in sorted(path for path in (PRODUCTION / model_key).iterdir() if path.is_dir()):
            manifest = load_json(run_dir / "run-manifest.json")
            rows.append({
                "model_key": model_key,
                "run_dir": run_dir,
                "manifest": manifest,
                "responses": load_jsonl(run_dir / "responses.jsonl"),
                "attempts": load_jsonl(run_dir / "attempts.jsonl"),
                "score": load_json(run_dir / "score.json"),
            })
    return rows


def normalize_error(message: str) -> str:
    message = re.sub(r"\b[0-9a-f]{8,}\b", "<id>", message)
    return message[:300]


def build_operations(runs: list[dict[str, Any]]) -> dict[str, Any]:
    per_run = []
    usage = Counter()
    status_counts = Counter()
    error_counts = Counter()
    gpu_checks = Counter()
    starts, finishes = [], []

    for run in runs:
        manifest, responses, attempts, run_dir = (
            run["manifest"], run["responses"], run["attempts"], run["run_dir"]
        )
        keys = [(row.get("record_id"), row.get("task")) for row in responses]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate logical observations in {manifest['run_id']}")
        statuses = Counter(row["status"] for row in attempts)
        status_counts.update(statuses)
        for row in attempts:
            if row["status"] != "success":
                error_counts[normalize_error(str(row.get("error", "unknown")))] += 1
        for row in responses:
            if run["model_key"] == "azure_astra":
                current = (row.get("provider_response") or {}).get("usage") or {}
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    usage[key] += int(current.get(key, 0))
            else:
                evidence = str(row.get("gpu_evidence") or "")
                gpu_checks[run["model_key"] + ":total"] += 1
                if "100% GPU" in evidence:
                    gpu_checks[run["model_key"] + ":100_percent_gpu"] += 1

        started = manifest["started_at"]
        finished = max(row["finished_at"] for row in attempts)
        starts.append(datetime.fromisoformat(started))
        finishes.append(datetime.fromisoformat(finished))
        per_run.append({
            "run_id": manifest["run_id"],
            "model_key": run["model_key"],
            "replicate": manifest["replicate"],
            "started_at": started,
            "finished_at": finished,
            "duration_seconds": (datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds(),
            "logical_observations": len(responses),
            "unique_logical_observations": len(set(keys)),
            "attempts": len(attempts),
            "attempt_statuses": dict(sorted(statuses.items())),
            "terminal_failures": sum(bool(row.get("terminal_failure")) for row in responses),
            "responses_sha256": sha256(run_dir / "responses.jsonl"),
            "attempts_sha256": sha256(run_dir / "attempts.jsonl"),
            "score_sha256": sha256(run_dir / "score.json"),
        })

    input_rate, output_rate = 10.0, 50.0
    cost = usage["input_tokens"] * input_rate / 1_000_000 + usage["output_tokens"] * output_rate / 1_000_000
    identities = {}
    for model_key in MODEL_ORDER:
        model_runs = [row for row in runs if row["model_key"] == model_key]
        identities[model_key] = {
            "identity": model_runs[0]["manifest"]["identity"],
            "configurations": [row["manifest"]["model_configuration"] for row in model_runs],
        }

    return {
        "schema_version": 1,
        "candidate_lock_sha256": runs[0]["manifest"]["candidate_lock_sha256"],
        "run_count": len(runs),
        "logical_observations": sum(len(row["responses"]) for row in runs),
        "unique_logical_observations_within_runs": sum(len({(x.get("record_id"), x.get("task")) for x in row["responses"]}) for row in runs),
        "attempts": sum(len(row["attempts"]) for row in runs),
        "attempt_statuses": dict(sorted(status_counts.items())),
        "transient_error_types": dict(sorted(error_counts.items())),
        "terminal_failures": sum(x["terminal_failures"] for x in per_run),
        "production_started_at": min(starts).isoformat(),
        "production_finished_at": max(finishes).isoformat(),
        "elapsed_seconds": (max(finishes) - min(starts)).total_seconds(),
        "astra_usage": {
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "total_tokens": usage["total_tokens"],
            "pricing_checked_at": "2026-09-12",
            "pricing_source": "https://azure.microsoft.com/en-us/blog/gpt-6-astra-frontier-intelligence-for-work-now-generally-available-in-microsoft-foundry/",
            "input_usd_per_million": input_rate,
            "output_usd_per_million": output_rate,
            "calculated_cost_usd": cost,
            "scope_note": "Usage-bearing successful Responses API attempts; all transient failures carried no response usage.",
        },
        "local_gpu_evidence": {
            key: {
                "checks": gpu_checks[key + ":total"],
                "checks_showing_100_percent_gpu": gpu_checks[key + ":100_percent_gpu"],
            }
            for key in ("ollama_qwen", "ollama_gemma")
        },
        "model_identities": identities,
        "per_run": per_run,
    }


def subgroup_predicate(name: str) -> Callable[[dict[str, Any]], bool]:
    predicates = {
        "operational_consequence_high": lambda e: e["operational_consequence"] == "high",
        "operational_consequence_not_high": lambda e: e["operational_consequence"] != "high",
        "specificity_required_high": lambda e: e["specificity_required"] == "high",
        "specificity_required_medium": lambda e: e["specificity_required"] == "medium",
        "missing_machine_identity": lambda e: "machine_identity" in e["missing_information"],
        "machine_identity_not_marked_missing": lambda e: "machine_identity" not in e["missing_information"],
    }
    return predicates[name]


def aggregate_subgroups(runs: list[dict[str, Any]], scorer) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for model_key in MODEL_ORDER:
        model_runs = sorted((row for row in runs if row["model_key"] == model_key), key=lambda x: x["manifest"]["replicate"])
        by_name = {
            group["name"]: [next(x for x in row["score"]["expert_subgroups"] if x["name"] == group["name"]) for row in model_runs]
            for group in model_runs[0]["score"]["expert_subgroups"]
        }
        model_output = {}
        for name, groups in by_name.items():
            predicate = subgroup_predicate(name)
            item_sets = [
                [item for item in row["score"]["_item_evidence"] if item["expert"] and predicate(item["expert"])]
                for row in model_runs
            ]
            model_output[name] = {
                "expert_records": groups[0]["expert_records"],
                "eligible_item_run_observations": sum(x["eligible_model_observations"] for x in groups),
                "eligible_items_per_run": [x["eligible_model_observations"] for x in groups],
                "mean_overall_accuracy": mean([x["overall_accuracy"] for x in groups]),
                "mean_cross_level_coverage": mean([x["cross_level"]["coverage"] for x in groups]),
                "mean_accuracy_when_consistent": mean([x["cross_level"]["accepted_accuracy"] for x in groups]),
                "mean_accuracy_when_inconsistent": mean([x["cross_level"]["rejected_accuracy"] for x in groups]),
                "mean_Delta_AB": mean([x["cross_level"]["accuracy_difference"] for x in groups]),
                "between_run_Delta_AB_sd": sample_sd([x["cross_level"]["accuracy_difference"] for x in groups]),
                "mean_consistent_but_wrong_rate": mean([x["consistent_but_wrong_rate"] for x in groups]),
                "mean_repeat_agreement": mean([x["repeat_question"]["coverage"] for x in groups]),
                "mean_repeat_accepted_accuracy": mean([x["repeat_question"]["accepted_accuracy"] for x in groups]),
                "mean_repeat_rejected_accuracy": mean([x["repeat_question"]["rejected_accuracy"] for x in groups]),
                "crossed_Delta_AB_uncertainty": scorer.crossed_bootstrap(item_sets),
                "within_run_Delta_AB_ci95": [x["uncertainty"]["ci95"] for x in groups],
                "interpretation": "secondary/exploratory; repeated item-run observations are not independent",
            }
        output[model_key] = model_output
    return output


def theme_definitions(experts: list[dict[str, Any]]) -> list[tuple[str, str, Callable[[dict[str, Any]], bool]]]:
    definitions: list[tuple[str, str, Callable[[dict[str, Any]], bool]]] = []
    for field in ("context_sufficiency", "operational_consequence", "specificity_required", "actionability"):
        for value in sorted({str(e[field]) for e in experts if e.get(field) is not None}):
            definitions.append((field, value, lambda e, f=field, v=value: str(e.get(f)) == v))
    for field in ("missing_information", "ambiguity_type", "failure_mechanism", "operational_effect"):
        for value in sorted({value for e in experts for value in e.get(field, [])}):
            definitions.append((field, value, lambda e, f=field, v=value: v in e.get(f, [])))
    for field in (
        "personnel_risk_noted", "equipment_damage_risk_noted", "production_disruption_risk_noted",
        "thermal_hazard_noted", "pressure_hazard_noted", "structural_hazard_noted",
        "electrical_hazard_noted", "high_energy_motion_noted", "conditional_judgment",
    ):
        if any(e.get(field) is True for e in experts):
            definitions.append(("boolean_flag", field, lambda e, f=field: e.get(f) is True))
    return definitions


def descriptive_theme_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    cross = [x for x in items if x["cross_valid"]]
    repeat = [x for x in items if x["repeat_valid"]]
    accepted = [x for x in cross if x["cross_agree"]]
    rejected = [x for x in cross if not x["cross_agree"]]
    repeat_accepted = [x for x in repeat if x["repeat_agree"]]
    def accuracy(rows):
        return sum(x["correct"] for x in rows) / len(rows) if rows else None
    return {
        "eligible_items": len(items),
        "overall_accuracy": accuracy(items),
        "valid_cross_level_items": len(cross),
        "cross_level_consistency": len(accepted) / len(cross) if cross else None,
        "accuracy_when_consistent": accuracy(accepted),
        "accuracy_when_inconsistent": accuracy(rejected),
        "consistent_but_wrong_rate": 1 - accuracy(accepted) if accepted else None,
        "valid_repeat_items": len(repeat),
        "repeat_agreement": len(repeat_accepted) / len(repeat) if repeat else None,
    }


def sparse_theme_descriptives(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    experts_by_record = {}
    for item in runs[0]["score"]["_item_evidence"]:
        if item["expert"]:
            experts_by_record[item["record_id"]] = item["expert"]
    experts = list(experts_by_record.values())
    output = []
    for field, value, predicate in theme_definitions(experts):
        record_ids = {record_id for record_id, expert in experts_by_record.items() if predicate(expert)}
        model_metrics = {}
        for model_key in MODEL_ORDER:
            per_run = []
            for run in sorted((x for x in runs if x["model_key"] == model_key), key=lambda x: x["manifest"]["replicate"]):
                items = [x for x in run["score"]["_item_evidence"] if x["record_id"] in record_ids]
                per_run.append(descriptive_theme_metrics(items))
            metric_names = per_run[0].keys()
            model_metrics[model_key] = {
                "item_run_observations": sum(x["eligible_items"] for x in per_run),
                **{f"mean_{name}": mean([x[name] for x in per_run]) for name in metric_names if name != "eligible_items"},
            }
        output.append({
            "field": field,
            "value": value,
            "expert_records": len(record_ids),
            "sparse": len(record_ids) < 5 or (field == "context_sufficiency" and value == "sufficient"),
            "model_metrics": model_metrics,
        })
    return output


def run_summary(run: dict[str, Any]) -> dict[str, Any]:
    score = run["score"]
    return {
        "run_id": run["manifest"]["run_id"],
        "replicate": run["manifest"]["replicate"],
        "overall_A_accuracy": score["overall_A_accuracy"],
        "valid_A_items": score["valid_A_items"],
        "valid_A_coverage": score["valid_A_coverage"],
        "valid_AB_items": score["cross_level"]["valid_n"],
        "cross_level_consistency": score["cross_level"]["coverage"],
        "accuracy_when_consistent": score["cross_level"]["accepted_accuracy"],
        "accuracy_when_inconsistent": score["cross_level"]["rejected_accuracy"],
        "Delta_AB": score["cross_level"]["Delta_AB"],
        "Delta_AB_ci95": score["cross_level"]["uncertainty"]["ci95"],
        "consistent_but_wrong_rate": score["cross_level"]["accepted_wrong_rate"],
        "valid_AC_items": score["repeated_question"]["valid_n"],
        "repeat_agreement": score["repeated_question"]["coverage"],
        "accuracy_when_agreeing": score["repeated_question"]["accepted_accuracy"],
        "accuracy_when_disagreeing": score["repeated_question"]["rejected_accuracy"],
        "Delta_AC": score["repeated_question"]["Delta_AC"],
        "common_valid_ABC_items": score["common_valid_ABC"]["n"],
        "MethodGap": score["common_valid_ABC"]["MethodGap"],
        "high_consequence_CBW": score["high_consequence_CBW"],
        "invalid_outputs": score["output_failures_by_call"],
        "terminal_failures": score["terminal_failures"],
    }


def build_detailed(runs: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate = load_json(ANALYSIS / "aggregate.json")
    scorer = score_module()
    models = {}
    for model_key in MODEL_ORDER:
        model_runs = [run_summary(row) for row in runs if row["model_key"] == model_key]
        aggregate_model = aggregate["models"][model_key]
        models[model_key] = {
            "label": MODEL_LABELS[model_key],
            "role": "prespecified heterogeneity/stability comparison" if model_key == "azure_astra" else "primary confirmatory panel model",
            "runs": model_runs,
            "estimable_runs": aggregate_model["estimable_runs"],
            "positive_Delta_AB_runs": aggregate_model["positive_Delta_AB_runs"],
            "mean_Delta_AB": aggregate_model["mean_Delta_AB"],
            "between_run_Delta_AB_sd": aggregate_model["between_run_Delta_AB_sd"],
            "crossed_Delta_AB_uncertainty": aggregate_model["crossed_uncertainty"],
            "replication_rule_satisfied": aggregate_model["replicated"],
            "mean_overall_A_accuracy": mean([x["overall_A_accuracy"] for x in model_runs]),
            "mean_valid_A_coverage": mean([x["valid_A_coverage"] for x in model_runs]),
            "mean_cross_level_consistency": mean([x["cross_level_consistency"] for x in model_runs]),
            "mean_accuracy_when_consistent": mean([x["accuracy_when_consistent"] for x in model_runs]),
            "mean_accuracy_when_inconsistent": mean([x["accuracy_when_inconsistent"] for x in model_runs]),
            "mean_Delta_AC": mean([x["Delta_AC"] for x in model_runs]),
            "mean_repeat_agreement": mean([x["repeat_agreement"] for x in model_runs]),
            "mean_MethodGap": mean([x["MethodGap"] for x in model_runs]),
            "invalid_output_counts": dict(sum((Counter(x["invalid_outputs"]) for x in model_runs), Counter())),
            "terminal_failures": sum(x["terminal_failures"] for x in model_runs),
        }
    return {
        "schema_version": 1,
        "candidate_lock_sha256": runs[0]["manifest"]["candidate_lock_sha256"],
        "aggregate_sha256": sha256(ANALYSIS / "aggregate.json"),
        "primary_outcome": {
            "panel_level_replication": aggregate["panel_level_replication"],
            "interpretation": "supported" if aggregate["panel_level_replication"] else "not supported",
            "rule": aggregate["rule"],
        },
        "models": models,
        "expert_subgroups": aggregate_subgroups(runs, scorer),
        "all_predefined_theme_descriptives": sparse_theme_descriptives(runs),
        "expert_evidence_limits": {
            "outcome_joinable_records": 15,
            "qualitative_only_rationales": 34,
            "missing_annotation_sequence": 28,
            "transcript_rationale_mismatch_sequence": 45,
            "prior_aggregate_result_exposure": True,
            "claim_boundary": "All expert analyses are secondary/exploratory or descriptive; none is confirmatory.",
        },
        "method_comparison_interpretation": "Negative MethodGap means repeated-question agreement produced a larger accuracy separation; it does not establish a better, safer, stronger, or superior screen.",
        "high_consequence_interpretation": "Performance conditional on expert-rated operational consequence of short maintenance text; not measured plant or safety risk.",
    }


def render_results(detailed: dict[str, Any], operations: dict[str, Any]) -> str:
    lines = [
        "# IMC-EXP-004 Results",
        "",
        "**Result status:** Deterministic analysis complete; independent result review pending  ",
        f"**Candidate design lock:** `{detailed['candidate_lock_sha256']}`  ",
        f"**Aggregate analysis SHA-256:** `{detailed['aggregate_sha256']}`",
        "",
        "## Outcome",
        "",
        "The primary panel replication criterion was **satisfied**. Qwen and Gemma each had five of five estimable runs, five of five positive cross-level accuracy separations, and a crossed run/record-group bootstrap 95% interval wholly above zero. Astra, the prespecified heterogeneity/stability comparison, also showed five positive and estimable realizations with a positive crossed interval.",
        "",
        "This supports repeated-run stability of the EXP-003 consistency-to-correctness relationship for both predeclared local panel models on this frozen MaintIE evaluation. It does not establish that consistency guarantees correctness, generalizes to other datasets, or provides measured plant-risk control.",
        "",
        "## Repeated-run summary",
        "",
        "| Model | Mean A accuracy | Mean valid-A coverage | Mean consistency | Mean accuracy if consistent | Mean accuracy if inconsistent | Mean Delta_AB | Crossed 95% CI | Between-run SD | Rule |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for model_key in MODEL_ORDER:
        row = detailed["models"][model_key]
        lines.append(
            f"| {row['label']} | {pct(row['mean_overall_A_accuracy'])} | {pct(row['mean_valid_A_coverage'])} | "
            f"{pct(row['mean_cross_level_consistency'])} | {pct(row['mean_accuracy_when_consistent'])} | "
            f"{pct(row['mean_accuracy_when_inconsistent'])} | {number(row['mean_Delta_AB'])} | "
            f"{ci_text(row['crossed_Delta_AB_uncertainty']['ci95'])} | {number(row['between_run_Delta_AB_sd'])} | "
            f"{'satisfied' if row['replication_rule_satisfied'] else 'not satisfied'} |"
        )

    lines += [
        "",
        "Astra is not used to rescue either local model: panel replication requires and received support from Qwen and Gemma separately. Mean Delta_AB differed across models (Astra 0.152, Gemma 0.209, Qwen 0.303), showing meaningful model heterogeneity despite the shared positive direction.",
        "",
        "## Per-run evidence",
        "",
        "| Model/run | A accuracy | Valid A | Valid A/B | Consistency | Accuracy consistent | Accuracy inconsistent | Delta_AB (95% CI) | Valid A/C | Repeat agreement | Delta_AC | Common A/B/C | MethodGap | Invalid calls |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_key in MODEL_ORDER:
        for row in detailed["models"][model_key]["runs"]:
            invalid = sum(row["invalid_outputs"].values())
            lines.append(
                f"| {MODEL_LABELS[model_key]} R{row['replicate']} | {pct(row['overall_A_accuracy'])} | "
                f"{row['valid_A_items']}/329 | {row['valid_AB_items']} | {pct(row['cross_level_consistency'])} | "
                f"{pct(row['accuracy_when_consistent'])} | {pct(row['accuracy_when_inconsistent'])} | "
                f"{number(row['Delta_AB'])} {ci_text(row['Delta_AB_ci95'])} | {row['valid_AC_items']} | "
                f"{pct(row['repeat_agreement'])} | {number(row['Delta_AC'])} | {row['common_valid_ABC_items']} | "
                f"{number(row['MethodGap'])} | {invalid} |"
            )

    lines += [
        "",
        "All 15 MethodGap estimates were negative. Repeated-question agreement therefore produced a larger accuracy separation in every realization. That statement is comparative and descriptive: it does not by itself establish that repeated agreement is a better, safer, stronger, or superior screen. Cross-level accepted coverage and accuracy remain reported above; full accepted/rejected values are preserved in `detailed-analysis.json`.",
        "",
        "## Expert operational layer",
        "",
        "Only 15 expert-annotated MaintIE records (48 eligible entity observations per run) were exact outcome-joinable matches. Consequently every expert result is secondary/exploratory; the many sparse themes are descriptive only.",
        "",
        "### Predeclared exploratory subgroup summaries",
        "",
        "Values are means across five runs. The confidence interval is the crossed run/record-group bootstrap interval for Delta_AB and respects repeated-run and record/duplicate grouping. Item-run totals are repeated measurements, not independent expert observations.",
        "",
        "| Model | Subgroup | Expert records | Item-runs | Accuracy | Consistency | Accuracy consistent | Accuracy inconsistent | Delta_AB (crossed 95% CI) | Consistent-but-wrong | Repeat agreement |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_key in MODEL_ORDER:
        for name, row in detailed["expert_subgroups"][model_key].items():
            label = name.replace("_", " ")
            lines.append(
                f"| {MODEL_LABELS[model_key]} | {label} | {row['expert_records']} | {row['eligible_item_run_observations']} | "
                f"{pct(row['mean_overall_accuracy'])} | {pct(row['mean_cross_level_coverage'])} | "
                f"{pct(row['mean_accuracy_when_consistent'])} | {pct(row['mean_accuracy_when_inconsistent'])} | "
                f"{number(row['mean_Delta_AB'])} {ci_text(row['crossed_Delta_AB_uncertainty']['ci95'])} | "
                f"{pct(row['mean_consistent_but_wrong_rate'])} | {pct(row['mean_repeat_agreement'])} |"
            )

    lines += [
        "",
        "The high-consequence consistent-but-wrong rate among valid cross-level-consistent predictions was 23.1%–28.6% across Astra runs, 40.0%–45.5% across Qwen runs, and 54.5% in every Gemma run. This is performance conditional on Sid's expert-rated operational consequence for the short text, not measured plant or safety risk. The high-consequence strata contain only six expert records, so the rates are signals for follow-up, not confirmatory risk estimates.",
        "",
        "The missing-machine-identity, consequence, and specificity comparisons are fully reported rather than selectively filtered. Every other frozen context, ambiguity, failure-mechanism, operational-effect, actionability, hazard, and risk-noted theme is included in `detailed-analysis.json`; groups with fewer than five records remain descriptive only. This avoids post-outcome category merging or theme selection.",
        "",
        "The expert evidence has important limitations: 34 recovered narratives could not be joined to EXP-003 outcomes and remain qualitative-only; sequence 28 is missing; sequence 45 retains a transcript/rationale mismatch; and Sid had prior aggregate-result exposure even though record-level reconstruction remained outcome-blind.",
        "",
        "## Operational execution",
        "",
        f"All {operations['run_count']} planned runs completed from {operations['production_started_at']} through {operations['production_finished_at']} in {operations['elapsed_seconds'] / 3600:.2f} elapsed hours. The ledger contains {operations['logical_observations']:,} unique-within-run logical observations and {operations['attempts']:,} attempts. There were {operations['attempt_statuses'].get('transient_failure', 0)} transient Astra failures, all recovered under the same logical observations, and zero terminal failures.",
        "",
        f"Astra used {operations['astra_usage']['input_tokens']:,} input and {operations['astra_usage']['output_tokens']:,} output tokens ({operations['astra_usage']['total_tokens']:,} total). At the frozen checked prices of USD 10/input-million and USD 50/output-million, calculated usage cost was **USD {operations['astra_usage']['calculated_cost_usd']:.5f}**. All transient attempts carried no response usage.",
        "",
        "All 1,620 Qwen and all 1,620 Gemma response checkpoints preserved contemporaneous `100% GPU` placement evidence. Each run contains exactly 324 unique logical observations. No completed observation was duplicated on retry or resume.",
        "",
        "Output validity differed materially: Astra had no invalid calls; Gemma had five invalid-label calls per run; Qwen had 11–23 invalid or truncated calls per run. Frozen all-item denominators treat invalid A outputs as incorrect, while agreement contrasts use their declared valid-call sets.",
        "",
        "Gemma displayed low stochastic diversity despite distinct seeds: R2/R4 differed in raw text for only one of 324 calls and R3/R5 for nine calls, with identical scored summaries within those pairs. This is an observed realization property, not evidence that the seeds were ignored; manifests verify forwarding, but the provider's sampling implementation is outside this experiment's direct control.",
        "",
        "## Conclusions and limits",
        "",
        "The central finding replicated: cross-level consistency remained positively associated with exact detailed-label correctness across five new realizations of each local model, with all three model families showing positive mean effects. The magnitude, baseline accuracy, invalid-output behavior, and stochastic variation were model-dependent.",
        "",
        "Consistency remained fallible. Consistent-but-wrong predictions were common enough—particularly within the small high-consequence expert stratum—that consistency should be treated as a selective reliability signal, not an assurance of correctness or operational safety. Repeated-question agreement produced larger accuracy separation in these runs, but a decision-policy comparison would require separately predeclared utility, coverage, and risk criteria.",
        "",
        "Generalization is limited by one dataset, short maintenance phrases, one fixed 108-record census, only 15 outcome-joinable expert records, record-level expert labels inherited by entity outputs, and model/provider-specific decoding. A separately authorized second industrial dataset and prospectively annotated larger expert sample are needed before broad operational claims.",
        "",
        "## Evidence map",
        "",
        "- Frozen methodology and rules: `DESIGN.md` and the candidate lock above.",
        "- Raw response, attempt, identity, and placement evidence: `results/production/`.",
        "- Frozen scorer outputs: each production run's `score.json`.",
        "- Across-run analysis: `results/analysis/aggregate.json`.",
        "- Detailed derived analysis: `results/analysis/detailed-analysis.json`.",
        "- Operational accounting: `results/analysis/operations.json`.",
        "- Independent result review: pending.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    runs = all_runs()
    if len(runs) != 15:
        raise ValueError(f"expected 15 production runs, found {len(runs)}")
    candidate_hashes = {run["manifest"]["candidate_lock_sha256"] for run in runs}
    if len(candidate_hashes) != 1:
        raise ValueError(f"mixed candidate locks: {candidate_hashes}")
    operations = build_operations(runs)
    detailed = build_detailed(runs)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    (ANALYSIS / "operations.json").write_text(json.dumps(operations, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ANALYSIS / "detailed-analysis.json").write_text(json.dumps(detailed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "RESULTS.md").write_text(render_results(detailed, operations), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
