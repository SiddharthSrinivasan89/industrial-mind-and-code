"""
Experiment entry point — V4 Intent Classifier.

Tests whether discrete intent classification (5 labels → lookup → multiplier) improves
on V3b's continuous float output while using the same OUT-style formula and demand data.

Setup
-----
    cp env.azure.template .env.azure   # fill in Azure credentials
    cp env.local.template .env.local   # fill in Ollama endpoint + model

Usage
-----
    # Azure backend (gpt-4.1-mini), 10 runs
    python run_experiment.py --experiments baselines H1_IC H2_IC H3_IC --runs 10 --env .env.azure

    # Local backend (nemotron-3-super:120b), 5 runs
    python run_experiment.py --experiments baselines H1_IC H2_IC H3_IC --runs 5 --env .env.local

    # Dry run — validates pipeline without any LLM calls
    DRY_RUN=1 python run_experiment.py --experiments H1_IC --runs 2 --env .env.azure

Experiment labels
-----------------
    baselines — exp_smoothing, hybrid_control (deterministic, 1 run each)
    H1_IC     — IC-Blind × azure + local
    H2_IC     — IC-Context × azure + local
    H3_IC     — IC-Stateful × azure + local

Each experiment group contains both a local and an azure condition spec.
When BACKEND=azure, local specs are skipped; when BACKEND=local, azure specs are skipped.
Run azure and local as separate invocations with their respective env files.
"""

import argparse
import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from simulation import run_simulation
from metrics import summarise_condition
from agent_interface import INTENT_MULTIPLIER_MAP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

RESULTS_DIR = Path("../results")
DATA_FILE   = Path("../data/tatva_monthly_dispatches_25m.csv")
TIERS       = ["OEM", "Ancillary", "Component"]


# ---------------------------------------------------------------------------
# Experiment registry
# ---------------------------------------------------------------------------

EXPERIMENTS: dict[str, list[dict]] = {
    "baselines": [
        {"label": "exp_smoothing",  "policy": "exp_smoothing",  "condition": "blind", "model_tier": None},
        {"label": "hybrid_control", "policy": "hybrid_control", "condition": "blind", "model_tier": None},
    ],

    # H1_IC — IC-Blind: LLM sees state variables only; no calendar context.
    "H1_IC": [
        {"label": "ic_blind_azure",      "policy": "intent", "condition": "blind", "model_tier": "lightweight", "backend": "azure"},
        {"label": "ic_blind_local",      "policy": "intent", "condition": "blind", "model_tier": "reasoning",   "backend": "local"},
        {"label": "ic_blind_local_phi",  "policy": "intent", "condition": "blind", "model_tier": "lightweight", "backend": "local"},
    ],

    # H2_IC — IC-Context: calendar month + tier persona.
    "H2_IC": [
        {"label": "ic_context_azure",     "policy": "intent", "condition": "context", "model_tier": "lightweight", "backend": "azure"},
        {"label": "ic_context_local",     "policy": "intent", "condition": "context", "model_tier": "reasoning",   "backend": "local"},
        {"label": "ic_context_local_phi", "policy": "intent", "condition": "context", "model_tier": "lightweight", "backend": "local"},
    ],

    # H3_IC — IC-Stateful: context + last 3 periods of (demand, order, intent, backlog, stockout).
    "H3_IC": [
        {"label": "ic_stateful_azure",     "policy": "intent", "condition": "stateful", "model_tier": "lightweight", "backend": "azure"},
        {"label": "ic_stateful_local",     "policy": "intent", "condition": "stateful", "model_tier": "reasoning",   "backend": "local"},
        {"label": "ic_stateful_local_phi", "policy": "intent", "condition": "stateful", "model_tier": "lightweight", "backend": "local"},
    ],
}


# ---------------------------------------------------------------------------
# Dataset utilities
# ---------------------------------------------------------------------------

def verify_dataset(demand_df: pd.DataFrame) -> str:
    raw = DATA_FILE.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    logger.info("Demand file SHA-256: %s", checksum)
    return checksum


def derive_S(demand_df: pd.DataFrame) -> int:
    mu = demand_df["retail_demand"].mean()
    sigma = demand_df["retail_demand"].std(ddof=1)
    S = int(round(mu + 1.65 * sigma))
    logger.info("Derived S = %d  (mean=%.1f, std=%.1f)", S, mu, sigma)
    return S


def derive_safety_stock(demand_df: pd.DataFrame, S: int) -> int:
    mean_demand = int(round(demand_df["retail_demand"].mean()))
    safety_stock = max(0, S - mean_demand)
    logger.info("Derived base safety stock = %d  (mean_demand=%d, S=%d)",
                safety_stock, mean_demand, S)
    return safety_stock


# ---------------------------------------------------------------------------
# Run management
# ---------------------------------------------------------------------------

def run_one(
    spec: dict,
    demand_df: pd.DataFrame,
    S: int,
    safety_stock: int,
    run_index: int,
) -> list[dict] | None:
    run_id = f"{spec['label']}_r{run_index:02d}_{str(uuid.uuid4())[:6]}"

    model_name = None
    if "model_env_key" in spec:
        model_name = os.environ.get(spec["model_env_key"])
        if not model_name:
            logger.error("Spec %s requires env var %s but it is not set.",
                         spec["label"], spec["model_env_key"])
            sys.exit(1)

    try:
        records = run_simulation(
            demand_series     = demand_df,
            condition         = spec["condition"],
            model_tier        = spec["model_tier"] or "lightweight",
            policy            = spec["policy"],
            S                 = S,
            safety_stock      = safety_stock,
            initial_inventory = S,
            condition_label   = spec["label"],
            model_name        = model_name,
            run_id            = run_id,
            backend           = spec.get("backend"),
        )
        return records
    except RuntimeError as exc:
        logger.error("Run %s failed with unrecoverable error: %s", run_id, exc)
        return None


def run_condition(
    spec: dict,
    demand_df: pd.DataFrame,
    S: int,
    safety_stock: int,
    n_runs: int,
    checkpoint_path: Path | None = None,
) -> tuple[list[dict], dict]:
    all_records  = []
    is_heuristic = spec["policy"] not in ("intent",)
    target       = 1 if is_heuristic else n_runs
    completed    = 0
    attempts     = 0
    replacements = 0
    max_attempts = target * 5

    if checkpoint_path is not None and checkpoint_path.exists() and not is_heuristic:
        df_cp = pd.read_parquet(checkpoint_path)
        seen = dict.fromkeys(df_cp["run_id"].tolist())
        ordered_ids = list(seen.keys())[:target]
        df_cp = df_cp[df_cp["run_id"].isin(ordered_ids)]
        all_records = df_cp.to_dict("records")
        completed   = len(ordered_ids)
        logger.info("Resuming condition %s: loaded %d/%d runs from checkpoint",
                    spec["label"], completed, target)

    while completed < target and attempts < max_attempts:
        attempts += 1
        records = run_one(spec, demand_df, S, safety_stock, run_index=completed + 1)
        if records is not None:
            all_records.extend(records)
            completed += 1
            logger.info("Condition %s: completed %d/%d (attempt %d, replacements: %d)",
                        spec["label"], completed, target, attempts, replacements)
            if checkpoint_path is not None and not is_heuristic:
                pd.DataFrame(all_records).to_parquet(checkpoint_path, index=False)
        else:
            replacements += 1
            logger.warning("Condition %s: attempt %d failed — replacement #%d",
                           spec["label"], attempts, replacements)

    if completed < target:
        logger.error("Condition %s: only %d/%d runs completed after %d attempts.",
                     spec["label"], completed, target, attempts)
        sys.exit(1)

    logger.info("Condition %s: finished — %d valid runs in %d attempts (%d replacement(s))",
                spec["label"], completed, attempts, replacements)
    return all_records, {"attempts": attempts, "replacements": replacements}


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _checkpoint(all_records: list[dict], out_dir: Path) -> None:
    pd.DataFrame(all_records).to_parquet(out_dir / "records.checkpoint.parquet", index=False)
    logger.info("Checkpoint written (%d records)", len(all_records))


def save_results(
    all_records: list[dict],
    experiment_label: str,
    checksum: str,
    safety_stock: int,
    run_stats: dict | None = None,
    out_dir: Path | None = None,
) -> Path:
    if out_dir is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_dir = RESULTS_DIR / experiment_label / timestamp
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        timestamp = out_dir.name

    df = pd.DataFrame(all_records)
    df.to_parquet(out_dir / "records.parquet", index=False)

    summaries = []
    for label, grp in df.groupby("condition_label"):
        summaries.append(summarise_condition(grp, label))

    def _nan_to_null(obj):
        if isinstance(obj, float) and obj != obj:
            return None
        if isinstance(obj, dict):
            return {k: _nan_to_null(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_nan_to_null(v) for v in obj]
        return obj

    (out_dir / "summary.json").write_text(
        json.dumps(_nan_to_null(summaries), indent=2, allow_nan=False)
    )

    backend = os.environ.get("BACKEND", "unknown")
    llm_df  = df[df["latency_ms"] > 0].copy() if "latency_ms" in df.columns else pd.DataFrame()

    if not llm_df.empty:
        lat = llm_df["latency_ms"]
        latency_stats = {
            "n_calls":                 int(len(llm_df)),
            "mean_ms":                 round(float(lat.mean()), 1),
            "p50_ms":                  round(float(np.percentile(lat, 50)), 1),
            "p95_ms":                  round(float(np.percentile(lat, 95)), 1),
            "total_prompt_tokens":     int(llm_df["prompt_tokens"].sum()),
            "total_completion_tokens": int(llm_df["completion_tokens"].sum()),
            "total_wall_time_s":       round(float(lat.sum()) / 1000, 1),
            "intent_fallback_rate":    round(float(llm_df["intent_fallback"].mean()), 4)
                                       if "intent_fallback" in llm_df.columns else None,
        }
    else:
        latency_stats = {}

    if backend == "local":
        infra_context = {
            "type":      "local",
            "endpoint":  os.environ.get("LOCAL_ENDPOINT", ""),
            "platform":  platform.platform(),
        }
        try:
            gpu_out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                timeout=5, text=True,
            ).strip()
            infra_context["gpu"] = gpu_out
        except Exception:
            infra_context["gpu"] = None
    else:
        infra_context = {
            "type":              "azure",
            "endpoint":          os.environ.get("AZURE_ENDPOINT", ""),
            "api_version":       os.environ.get("AZURE_API_VERSION", ""),
            "model_lightweight": os.environ.get("MODEL_LIGHTWEIGHT", ""),
        }

    stamp = {
        "version":                "V4_IC",
        "experiment":             experiment_label,
        "timestamp_utc":          timestamp,
        "demand_checksum_sha256": checksum,
        "dry_run":                os.environ.get("DRY_RUN", "").strip() == "1",
        "backend":                backend,
        "model_lightweight":      os.environ.get("MODEL_LIGHTWEIGHT", ""),
        "model_reasoning":        os.environ.get("MODEL_REASONING", ""),
        "intent_params": {
            "multiplier_map":  INTENT_MULTIPLIER_MAP,
            "fallback_intent": "NEUTRAL",
            "history_window":  3,
            "formula_alpha":   0.30,
            "base_ss":         safety_stock,
        },
        "run_stats":     run_stats or {},
        "latency_stats": latency_stats,
        "infra_context": infra_context,
    }
    (out_dir / "provenance.json").write_text(json.dumps(stamp, indent=2))

    checkpoint = out_dir / "records.checkpoint.parquet"
    if checkpoint.exists():
        checkpoint.unlink()

    logger.info("Results saved to %s", out_dir)
    return out_dir


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run V4 Intent Classifier experiment")
    parser.add_argument("--experiments", nargs="+", default=["baselines"],
                        choices=list(EXPERIMENTS.keys()))
    parser.add_argument("--runs", type=int, default=10,
                        help="Valid runs per LLM condition (default: 10)")
    parser.add_argument("--env", type=str, default=".env")
    parser.add_argument("--results-dir", type=str, default=None)
    parser.add_argument("--resume-dir", type=Path, default=None)
    args = parser.parse_args()

    load_dotenv(args.env)

    global RESULTS_DIR
    if args.results_dir:
        RESULTS_DIR = Path(args.results_dir)

    if not DATA_FILE.exists():
        logger.error("Demand file not found: %s", DATA_FILE)
        sys.exit(1)

    demand_df = pd.read_csv(DATA_FILE)
    required_cols = {"period", "calendar_month", "retail_demand"}
    if not required_cols.issubset(demand_df.columns):
        logger.error("Demand file missing columns. Required: %s", required_cols)
        sys.exit(1)

    checksum     = verify_dataset(demand_df)
    S            = derive_S(demand_df)
    safety_stock = derive_safety_stock(demand_df, S)

    for exp_name in args.experiments:
        logger.info("=== Starting experiment: %s ===", exp_name)
        all_records = []
        run_stats   = {}

        if args.resume_dir and exp_name == args.experiments[0]:
            out_dir = args.resume_dir
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            out_dir = RESULTS_DIR / exp_name / timestamp
            out_dir.mkdir(parents=True, exist_ok=True)

        if (out_dir / "records.parquet").exists():
            logger.info("=== %s already complete at %s — skipping ===", exp_name, out_dir)
            continue

        active_backend = os.environ.get("BACKEND", "local").lower()
        for spec in EXPERIMENTS[exp_name]:
            spec_backend = spec.get("backend")
            if spec_backend and spec_backend != active_backend:
                logger.info("Skipping condition %s (backend=%s, active=%s)",
                            spec["label"], spec_backend, active_backend)
                continue

            logger.info("Running condition: %s", spec["label"])
            cond_checkpoint = out_dir / f"{spec['label']}.checkpoint.parquet"
            records, stats = run_condition(
                spec, demand_df, S, safety_stock, n_runs=args.runs,
                checkpoint_path=cond_checkpoint,
            )
            all_records.extend(records)
            run_stats[spec["label"]] = stats
            _checkpoint(all_records, out_dir)

        save_results(all_records, exp_name, checksum, safety_stock,
                     run_stats=run_stats, out_dir=out_dir)
        logger.info("=== %s complete — results at %s ===", exp_name, out_dir)


if __name__ == "__main__":
    main()
