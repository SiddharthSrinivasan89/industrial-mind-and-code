"""
Experiment entry point — V3b Hybrid Architecture.

Tests whether LLMs can improve supply chain ordering performance by adjusting the
safety stock parameter of a deterministic ordering policy rather than issuing orders
directly. Each condition routes to a specific backend (local or azure) via the
BACKEND env var; the two backends produce separate result sets that are combined at
analysis time.

Setup
-----
    cp env.local.template .env.local    # local backend (Ollama)
    cp env.azure.template .env.azure    # Azure backend

Usage
-----
    # Local backend (nemotron-3-super:120b)
    BACKEND=local /usr/bin/python3 run_experiment.py --experiments baselines H1 H2 H3 --runs 20 --env .env.local

    # Azure backend (gpt-4.1-mini)
    BACKEND=azure /usr/bin/python3 run_experiment.py --experiments baselines H1 H2 H3 --runs 20 --env .env.azure

    # Heuristic baselines only (no API calls needed)
    /usr/bin/python3 run_experiment.py --experiments baselines

    # Dry run — validates pipeline without any LLM calls
    DRY_RUN=1 BACKEND=local /usr/bin/python3 run_experiment.py --experiments H1 --runs 2 --env .env.local

Experiment labels
-----------------
    baselines  — naive_passthrough, exp_smoothing, hybrid_control (deterministic, no LLM)
    H1         — Hybrid-Blind × local + azure (no seasonal context, 20 runs each)
    H2         — Hybrid-Context × local + azure (with calendar month + tier persona)
    H3         — Hybrid-Stateful × local + azure (context + 3-period order/multiplier history)

Each backend runs independently. Local conditions skip when BACKEND=azure and vice versa.
"""

import argparse
import hashlib
import json
import logging
import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

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
TIERS = ["OEM", "Ancillary", "Component"]


# ---------------------------------------------------------------------------
# Experiment definitions
# ---------------------------------------------------------------------------

EXPERIMENTS = {
    "baselines": [
        # Deterministic heuristics — run once, no LLM calls.
        # exp_smoothing is the within-experiment performance benchmark.
        # hybrid_control is the architectural control: same OUT-style formula as hybrid
        # but multiplier fixed at 1.0 with no LLM. This isolates the LLM contribution
        # from the effect of introducing the OUT-style safety stock formula itself.
        {"label": "naive_passthrough",  "policy": "naive",          "condition": "blind", "model_tier": None, "hybrid_condition": None},
        {"label": "exp_smoothing",      "policy": "exp_smoothing",  "condition": "blind", "model_tier": None, "hybrid_condition": None},
        {"label": "hybrid_control",     "policy": "hybrid_control", "condition": "blind", "model_tier": None, "hybrid_condition": None},
    ],
    "H1": [
        # Hybrid-Blind: LLM adjusts safety stock multiplier with NO seasonal context.
        # Tests whether blind parameterisation improves over the within-experiment baselines.
        # backend field: condition is only executed when BACKEND env matches exactly.
        {"label": "hybrid_blind_local", "policy": "hybrid", "condition": "blind", "hybrid_condition": "blind",   "model_tier": "reasoning", "model_env_key": "MODEL_LOCAL", "backend": "local"},
        {"label": "hybrid_blind_azure", "policy": "hybrid", "condition": "blind", "hybrid_condition": "blind",   "model_tier": "lightweight", "backend": "azure"},
    ],
    "H2": [
        # Hybrid-Context: LLM gets calendar month + tier persona.
        # Primary test: does seasonal context improve safety stock parameterisation?
        {"label": "hybrid_context_local", "policy": "hybrid", "condition": "context", "hybrid_condition": "context", "model_tier": "reasoning", "model_env_key": "MODEL_LOCAL", "backend": "local"},
        {"label": "hybrid_context_azure", "policy": "hybrid", "condition": "context", "hybrid_condition": "context", "model_tier": "lightweight", "backend": "azure"},
    ],
    "H3": [
        # Hybrid-Stateful: context + last 3 periods (demand, order, ss_multiplier).
        # Tests whether order history enables self-correction beyond context alone.
        {"label": "hybrid_stateful_local", "policy": "hybrid", "condition": "context", "hybrid_condition": "stateful", "model_tier": "reasoning", "model_env_key": "MODEL_LOCAL", "backend": "local"},
        {"label": "hybrid_stateful_azure", "policy": "hybrid", "condition": "context", "hybrid_condition": "stateful", "model_tier": "lightweight", "backend": "azure"},
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
    """S = mean + 1.65 × std — 95th-percentile service level target."""
    mu = demand_df["retail_demand"].mean()
    sigma = demand_df["retail_demand"].std(ddof=1)
    S = int(round(mu + 1.65 * sigma))
    logger.info("Derived S = %d  (mean=%.1f, std=%.1f)", S, mu, sigma)
    return S


def derive_safety_stock(demand_df: pd.DataFrame, S: int) -> int:
    """base_SS = S - mean_demand. Used by order_up_to heuristic AND hybrid multiplier."""
    mean_demand = int(round(demand_df["retail_demand"].mean()))
    safety_stock = max(0, S - mean_demand)
    logger.info(
        "Derived base safety stock = %d  (mean_demand=%d, S=%d)",
        safety_stock, mean_demand, S,
    )
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
    """
    Execute one simulation run for a condition spec.

    Returns 75 records on success, None if the LLM backend exhausted all retries.
    """
    run_id = f"{spec['label']}_r{run_index:02d}_{str(uuid.uuid4())[:6]}"

    # Resolve model override (e.g. MODEL_LOCAL for local conditions)
    model_name = None
    if "model_env_key" in spec:
        model_name = os.environ.get(spec["model_env_key"])
        if not model_name:
            logger.error(
                "Spec %s requires env var %s but it is not set.",
                spec["label"], spec["model_env_key"],
            )
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
            hybrid_condition  = spec.get("hybrid_condition"),
            condition_label   = spec["label"],
            model_name        = model_name,
            run_id            = run_id,
            backend           = spec.get("backend"),
        )
        return records
    except RuntimeError as exc:
        logger.error("Run %s failed with unrecoverable parse error: %s", run_id, exc)
        return None


def run_condition(
    spec: dict,
    demand_df: pd.DataFrame,
    S: int,
    safety_stock: int,
    n_runs: int,
    checkpoint_path: Path | None = None,
) -> tuple[list[dict], dict]:
    """
    Collect n_runs valid simulations for one condition.

    Heuristics run exactly once (deterministic). LLM conditions run n_runs times.
    Failed runs are replaced (up to 5× the target before hard-failing).
    """
    all_records  = []
    is_heuristic = spec["policy"] not in ("llm", "hybrid")  # hybrid_control is deterministic
    target       = 1 if is_heuristic else n_runs
    completed    = 0
    attempts     = 0
    replacements = 0
    max_attempts = target * 5

    # Resume from per-run checkpoint if available (power-failure recovery).
    # Takes the first `target` unique run_ids so a larger checkpoint is trimmed cleanly.
    if checkpoint_path is not None and checkpoint_path.exists() and not is_heuristic:
        df_cp = pd.read_parquet(checkpoint_path)
        seen: dict[str, None] = {}
        for rid in df_cp["run_id"].tolist():
            seen.setdefault(rid, None)
        ordered_ids = list(seen.keys())[:target]
        df_cp = df_cp[df_cp["run_id"].isin(ordered_ids)]
        all_records = df_cp.to_dict("records")
        completed   = len(ordered_ids)
        logger.info(
            "Resuming condition %s: loaded %d/%d runs from checkpoint (%d records)",
            spec["label"], completed, target, len(all_records),
        )

    while completed < target and attempts < max_attempts:
        attempts += 1
        records = run_one(spec, demand_df, S, safety_stock, run_index=completed + 1)
        if records is not None:
            all_records.extend(records)
            completed += 1
            logger.info(
                "Condition %s: completed %d/%d (attempt %d, replacements: %d)",
                spec["label"], completed, target, attempts, replacements,
            )
            if checkpoint_path is not None and not is_heuristic:
                pd.DataFrame(all_records).to_parquet(checkpoint_path, index=False)
                logger.info(
                    "Per-run checkpoint: %d records (%d/%d runs)",
                    len(all_records), completed, target,
                )
        else:
            replacements += 1
            logger.warning(
                "Condition %s: run failed on attempt %d — triggering replacement #%d",
                spec["label"], attempts, replacements,
            )

    if completed < target:
        logger.error(
            "Condition %s: only %d/%d runs completed after %d attempts (%d replacements). "
            "Check API connectivity and model availability.",
            spec["label"], completed, target, attempts, replacements,
        )
        sys.exit(1)

    logger.info(
        "Condition %s: finished — %d valid runs in %d attempts (%d replacement(s))",
        spec["label"], completed, attempts, replacements,
    )
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
    """
    Persist simulation output: records.parquet + summary.json + provenance.json.

    summary.json includes hybrid-specific metrics (multiplier_stats, llm_compliance_rate,
    multiplier_pattern_score) when the condition is a hybrid policy.
    """
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

    # Provenance stamp
    backend = os.environ.get("BACKEND", "unknown")
    import numpy as np

    llm_df = df[df["latency_ms"] > 0].copy()
    if not llm_df.empty:
        lat = llm_df["latency_ms"]
        total_wall_s = float(lat.sum()) / 1000
        latency_stats = {
            "n_calls":                 int(len(llm_df)),
            "mean_ms":                 round(float(lat.mean()), 1),
            "p50_ms":                  round(float(np.percentile(lat, 50)), 1),
            "p95_ms":                  round(float(np.percentile(lat, 95)), 1),
            "p99_ms":                  round(float(np.percentile(lat, 99)), 1),
            "total_prompt_tokens":     int(llm_df["prompt_tokens"].sum()),
            "total_completion_tokens": int(llm_df["completion_tokens"].sum()),
            "retry_rate":              round(float((llm_df["attempt_number"] > 1).sum()) / len(llm_df), 4),
            "total_wall_time_s":       round(total_wall_s, 1),
            "mean_generation_tps":     round(float(llm_df["generation_tps"].mean()), 1) if "generation_tps" in llm_df else None,
        }
        # Hybrid-specific: multiplier fallback and clamp rates
        if "llm_fallback" in llm_df.columns:
            hybrid_llm = llm_df[llm_df["llm_fallback"].notna()]
            if not hybrid_llm.empty:
                latency_stats["multiplier_fallback_rate"] = round(float(hybrid_llm["llm_fallback"].mean()), 4)
                latency_stats["multiplier_clamp_rate"]    = round(float(hybrid_llm["ss_multiplier_clamped"].mean()), 4)
    else:
        latency_stats = {}

    import subprocess
    if backend == "local":
        infra_context = {
            "type":      "local",
            "endpoint":  os.environ.get("LOCAL_ENDPOINT", ""),
            "platform":  platform.platform(),
            "cpu":       platform.processor() or platform.machine(),
            "cpu_cores": os.cpu_count(),
            "python":    platform.python_version(),
        }
        try:
            gpu_out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"],
                timeout=5, text=True,
            ).strip()
            infra_context["gpu"] = gpu_out
        except Exception:
            infra_context["gpu"] = None
    else:
        infra_context = {
            "type":        "azure",
            "endpoint":    os.environ.get("AZURE_ENDPOINT", ""),
            "api_version": os.environ.get("AZURE_API_VERSION", ""),
            "model_lightweight": os.environ.get("MODEL_LIGHTWEIGHT", ""),
        }

    stamp = {
        "experiment":             experiment_label,
        "timestamp_utc":          timestamp,
        "demand_checksum_sha256": checksum,
        "dry_run":                os.environ.get("DRY_RUN", "").strip() == "1",
        "backend":                backend,
        "model_local":            os.environ.get("MODEL_LOCAL", ""),
        "model_lightweight":      os.environ.get("MODEL_LIGHTWEIGHT", ""),
        "hybrid_params": {
            "alpha":            0.30,
            "base_ss":          safety_stock,
            "multiplier_bounds": [0.5, 3.0],
            "multiplier_fallback": 1.0,
            "history_window":   3,
        },
        "temperature_config": {
            "hybrid_all_conditions": float(os.environ.get("TEMP_HYBRID", "0.3")),
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
    parser = argparse.ArgumentParser(description="Run Agentic Bullwhip V3b — Hybrid Architecture")
    parser.add_argument(
        "--experiments", nargs="+", default=["baselines"],
        choices=list(EXPERIMENTS.keys()),
        help="Which experiments to run (e.g. baselines H1 H2 H3)",
    )
    parser.add_argument("--runs", type=int, default=20,
                        help="Valid runs per LLM condition (default: 20)")
    parser.add_argument("--env", type=str, default=".env",
                        help="Path to .env file (default: .env)")
    parser.add_argument("--results-dir", type=str, default=None,
                        help="Output directory (default: ../results)")
    parser.add_argument(
        "--resume-dir", type=Path, default=None,
        help="Reuse an existing result directory for the FIRST experiment in --experiments. "
             "Checkpoint records are loaded automatically (power-failure resume). "
             "If records.parquet already exists in the dir the experiment is skipped entirely.",
    )
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

        # Use --resume-dir for the first experiment; create a fresh timestamped dir otherwise.
        if args.resume_dir and exp_name == args.experiments[0]:
            out_dir = args.resume_dir
            out_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Resume dir: %s", out_dir)
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            out_dir = RESULTS_DIR / exp_name / timestamp
            out_dir.mkdir(parents=True, exist_ok=True)

        # Skip experiments that are already fully saved (power-cycle idempotency).
        if (out_dir / "records.parquet").exists():
            logger.info("=== %s already complete at %s — skipping ===", exp_name, out_dir)
            continue

        active_backend = os.environ.get("BACKEND", "local").lower()
        for spec in EXPERIMENTS[exp_name]:
            # Skip conditions whose backend field doesn't match the active backend.
            # This ensures _local conditions only run with BACKEND=local and
            # _azure conditions only run with BACKEND=azure — true backend separation.
            spec_backend = spec.get("backend")
            if spec_backend and spec_backend != active_backend:
                logger.info(
                    "Skipping condition %s (backend=%s, active=%s)",
                    spec["label"], spec_backend, active_backend,
                )
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

        save_results(all_records, exp_name, checksum, safety_stock, run_stats=run_stats, out_dir=out_dir)
        logger.info("=== %s complete — results at %s ===", exp_name, out_dir)


if __name__ == "__main__":
    main()
