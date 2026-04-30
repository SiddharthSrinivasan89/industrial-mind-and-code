"""
Experiment entry point — V6 StatelessSwing.

Tests whether LLM-adaptive α ∈ {0.1, 0.3, 0.5, 0.7} can outperform fixed optimal α=0.3
in pure exponential-smoothing ordering. Formula: order = max(0, round(F_t) + backlog_t).

Setup
-----
    cp .env.azure.template .env.azure   # fill in Azure credentials
    cp .env.local.template .env.local   # fill in Ollama endpoint + model

Usage
-----
    # Dry run — validate pipeline without any LLM calls
    DRY_RUN=1 python run_experiment.py --experiments baselines mini_adaptive --runs 2 --env .env.azure

    # Fixed-alpha baselines (deterministic, 1 run each)
    python run_experiment.py --experiments baselines --runs 1 --env .env.azure

    # gpt-4.1-mini smoke test (2 runs)
    python run_experiment.py --experiments mini_adaptive --runs 2 --env .env.azure

    # Full production (10 runs)
    python run_experiment.py --experiments mini_adaptive o4mini_adaptive --runs 10 --env .env.azure
    python run_experiment.py --experiments oss120b_adaptive --runs 10 --env .env.local

Experiment labels
-----------------
    baselines         — exp_smooth_0.1 / 0.3 / 0.5 (deterministic, 1 run each)
    mini_adaptive     — gpt-4.1-mini × blind / context / stateful (Azure)
    o4mini_adaptive   — o4-mini × blind / context / stateful (Azure)
    oss120b_adaptive  — gpt-oss:120b × blind / context / stateful (local Ollama)
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
    # Fixed-alpha baselines — deterministic, 1 run each
    "baselines": [
        {"label": "exp_smooth_0.1", "policy": "exp_smoothing", "condition": "blind",
         "model_tier": None, "alpha": 0.1},
        {"label": "exp_smooth_0.3", "policy": "exp_smoothing", "condition": "blind",
         "model_tier": None, "alpha": 0.3},
        {"label": "exp_smooth_0.5", "policy": "exp_smoothing", "condition": "blind",
         "model_tier": None, "alpha": 0.5},
    ],

    # gpt-4.1-mini via Azure
    "mini_adaptive": [
        {"label": "mini_blind",    "policy": "adaptive_alpha", "condition": "blind",
         "model_tier": "lightweight", "backend": "azure"},
        {"label": "mini_context",  "policy": "adaptive_alpha", "condition": "context",
         "model_tier": "lightweight", "backend": "azure"},
        {"label": "mini_stateful", "policy": "adaptive_alpha", "condition": "stateful",
         "model_tier": "lightweight", "backend": "azure"},
    ],

    # o4-mini via Azure
    "o4mini_adaptive": [
        {"label": "o4_blind",    "policy": "adaptive_alpha", "condition": "blind",
         "model_tier": "reasoning", "backend": "azure"},
        {"label": "o4_context",  "policy": "adaptive_alpha", "condition": "context",
         "model_tier": "reasoning", "backend": "azure"},
        {"label": "o4_stateful", "policy": "adaptive_alpha", "condition": "stateful",
         "model_tier": "reasoning", "backend": "azure"},
    ],

    # gpt-oss:120b via local Ollama
    "oss120b_adaptive": [
        {"label": "oss120b_blind",    "policy": "adaptive_alpha", "condition": "blind",
         "model_tier": "reasoning", "backend": "local"},
        {"label": "oss120b_context",  "policy": "adaptive_alpha", "condition": "context",
         "model_tier": "reasoning", "backend": "local"},
        {"label": "oss120b_stateful", "policy": "adaptive_alpha", "condition": "stateful",
         "model_tier": "reasoning", "backend": "local"},
    ],

    # V6b: context-fix sub-experiment — gpt-4.1-mini via Azure
    "mini_debiased": [
        {"label": "mini_ctx_debiased", "policy": "adaptive_alpha", "condition": "context_debiased",
         "model_tier": "lightweight", "backend": "azure"},
        {"label": "mini_ctx_computed", "policy": "adaptive_alpha", "condition": "context_computed",
         "model_tier": "lightweight", "backend": "azure"},
    ],

    # V6b: context-fix sub-experiment — gpt-oss:120b via local Ollama
    "oss120b_debiased": [
        {"label": "oss120b_ctx_debiased", "policy": "adaptive_alpha", "condition": "context_debiased",
         "model_tier": "reasoning", "backend": "local"},
        {"label": "oss120b_ctx_computed", "policy": "adaptive_alpha", "condition": "context_computed",
         "model_tier": "reasoning", "backend": "local"},
    ],
}

TARGET_RUNS = 10  # per LLM condition; baselines run exactly once


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
            alpha             = spec.get("alpha", 0.30),
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
    is_heuristic = spec["policy"] not in ("adaptive_alpha",)
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
            "alpha_fallback_rate":     round(float(llm_df["alpha_fallback"].mean()), 4)
                                       if "alpha_fallback" in llm_df.columns else None,
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
            "model_reasoning":   os.environ.get("MODEL_REASONING", ""),
        }

    stamp = {
        "version":                "V6_StatelessSwing",
        "experiment":             experiment_label,
        "timestamp_utc":          timestamp,
        "demand_checksum_sha256": checksum,
        "dry_run":                os.environ.get("DRY_RUN", "").strip() == "1",
        "backend":                backend,
        "model_lightweight":      os.environ.get("MODEL_LIGHTWEIGHT", ""),
        "model_reasoning":        os.environ.get("MODEL_REASONING", ""),
        "alpha_params": {
            "alpha_values":    [0.1, 0.3, 0.5, 0.7],
            "alpha_fallback":  0.3,
            "history_window":  3,
            "demand_window":   5,
        },
        "run_stats":     run_stats or {},
        "latency_stats": latency_stats,
        "infra_context": infra_context,
    }
    (out_dir / "provenance.json").write_text(json.dumps(stamp, indent=2))

    for cp in out_dir.glob("*.checkpoint.parquet"):
        cp.unlink()

    logger.info("Results saved to %s", out_dir)
    return out_dir


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run V6 StatelessSwing experiment")
    parser.add_argument("--experiments", nargs="+", default=["baselines"],
                        choices=list(EXPERIMENTS.keys()))
    parser.add_argument("--runs", type=int, default=TARGET_RUNS,
                        help=f"Valid runs per LLM condition (default: {TARGET_RUNS}); baselines always run once")
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
