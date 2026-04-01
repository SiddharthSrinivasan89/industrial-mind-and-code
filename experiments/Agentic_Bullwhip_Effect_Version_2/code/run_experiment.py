"""
Experiment entry point.

This is the only script you need to run. It:
  1. Loads the demand dataset and verifies its SHA-256 checksum
  2. Derives the Order-Up-To target S from the data
  3. Runs every condition in the requested experiments
  4. Saves results as records.parquet + summary.json + provenance.json

Setup
-----
    First-time env configuration (do this once):
        cp env.local.template .env.local    # local Ollama backend
        cp env.azure.template .env.azure    # Azure backend
    Both templates document every variable including the temperature design
    rationale (blind=0.0, context=0.3) and the Azure forced-1.0 constraint.

Usage
-----
    # Azure backend
    python run_experiment.py --experiments E1 E2 --runs 20 --env .env.azure

    # Local backend (Ollama, LM Studio, etc.)
    python run_experiment.py --experiments E1 --runs 5 --env .env.local

    # Heuristic baselines only (no API calls, no env file needed)
    python run_experiment.py --experiments baselines

Experiment labels
-----------------
    baselines  — naive_passthrough, order_up_to, exp_smoothing (heuristic only)
    E1         — blind vs context × lightweight (gpt-4.1-mini on Azure)
    E2         — blind vs context × reasoning (o4-mini on Azure)
    E4         — Local vs Azure inference (phi4:14b local vs gpt-4.1-mini Azure — replication + infra comparison)

Multiple experiments can be passed together: --experiments E1 E2 E4
Each experiment produces its own results sub-directory.
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

# ---------------------------------------------------------------------------
# Paths — relative to the directory this script lives in
# ---------------------------------------------------------------------------

RESULTS_DIR     = Path("../results")   # overridden by --results-dir at runtime
DATA_FILE       = Path("../data/tatva_monthly_dispatches_25m.csv")
PROVENANCE_FILE = Path("docs/demand_provenance_25m.md")

TIERS = ["OEM", "Ancillary", "Component"]


# ---------------------------------------------------------------------------
# Experiment definitions
# ---------------------------------------------------------------------------
# Each experiment is a list of condition "specs". A spec is a dict that
# describes one condition: what ordering policy to use, which model tier,
# which prompt condition, and optionally which env var holds the model name.
#
# The EXPERIMENTS dict is the single source of truth for what gets run.
# Adding a new condition means adding a spec here — no other code needs changing.

EXPERIMENTS = {
    "baselines": [
        # Deterministic heuristics. Run exactly once (no stochasticity, no LLM).
        # These are the benchmarks LLM conditions must beat.
        {"label": "naive_passthrough",  "policy": "naive",         "condition": "blind", "model_tier": None},
        {"label": "order_up_to",        "policy": "order_up_to",   "condition": "blind", "model_tier": None},
        {"label": "exp_smoothing",      "policy": "exp_smoothing", "condition": "blind", "model_tier": None},
    ],
    "E1": [
        # Lightweight model × 2 prompt conditions.
        # Primary test of whether calendar context helps (H1, H3, H5 via difference).
        {"label": "blind_lightweight",   "policy": "llm", "condition": "blind",   "model_tier": "lightweight"},
        {"label": "context_lightweight", "policy": "llm", "condition": "context", "model_tier": "lightweight"},
    ],
    "E2": [
        # Reasoning model × 2 prompt conditions.
        # Tests whether stronger reasoning amplifies or mitigates the bullwhip (H2, H4, H6).
        {"label": "blind_reasoning",   "policy": "llm", "condition": "blind",   "model_tier": "reasoning"},
        {"label": "context_reasoning", "policy": "llm", "condition": "context", "model_tier": "reasoning"},
    ],
    "E4": [
        # OSS reasoning model (Phi-4-reasoning-plus) × 2 prompt conditions.
        # model_env_key tells run_one() to read MODEL_OSS_REASONING from env at runtime
        # rather than MODEL_REASONING, so E2 and E4 use different models but
        # the same model_tier="reasoning" setting for max_tokens and temperature.
        {"label": "blind_oss_reasoning",   "policy": "llm", "condition": "blind",   "model_tier": "reasoning", "model_env_key": "MODEL_OSS_REASONING"},
        {"label": "context_oss_reasoning", "policy": "llm", "condition": "context", "model_tier": "reasoning", "model_env_key": "MODEL_OSS_REASONING"},
        # E4 proprietary conditions reuse E2 results — not re-run here.
        # Compare blind_oss_reasoning vs blind_reasoning (from E2 output) post-hoc.
    ],
}


# ---------------------------------------------------------------------------
# Dataset verification
# ---------------------------------------------------------------------------

def verify_dataset(demand_df: pd.DataFrame) -> str:
    """
    Compute and log the SHA-256 checksum of the demand CSV.
    Logged for reproducibility — allows any run to be traced back to
    the exact dataset version via git history.
    """
    raw = DATA_FILE.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    logger.info("Demand file SHA-256: %s", checksum)
    return checksum


def derive_S(demand_df: pd.DataFrame) -> int:
    """
    Compute the Order-Up-To target S from the demand dataset.

    Formula: S = mean(demand) + 1.65 × std(demand)

    This targets approximately a 95% service level with a lead time of 1 period
    (L=1). It is the standard formula for a base-stock policy under normally
    distributed demand.

    Why derive S at runtime rather than hard-coding it?
      The value of S depends on the dataset. Computing it from the file ensures
      the heuristic baselines are calibrated to the actual synthetic demand, and
      the initial inventory (set to S) starts all conditions in steady state.

    S is derived at runtime from the CSV so heuristic baselines are always
    calibrated to the actual demand data. Uses sample std (ddof=1), which
    gives S ≈ 43,600 for the 25-month series.
    """
    mu    = demand_df["retail_demand"].mean()
    sigma = demand_df["retail_demand"].std(ddof=1)
    S = int(round(mu + 1.65 * sigma))
    logger.info("Derived S = %d  (mean=%.1f, std=%.1f)", S, mu, sigma)
    return S


def derive_safety_stock(demand_df: pd.DataFrame, S: int) -> int:
    """
    Compute the fixed safety stock used by the forecast-based OUT baseline.

    The OUT baseline uses a dynamic target position of:
      smoothed_forecast + safety_stock

    We derive safety_stock from the same demand moments as S so the heuristic
    remains tied to the dataset:
      safety_stock = S - mean_demand
    """
    mean_demand = int(round(demand_df["retail_demand"].mean()))
    safety_stock = max(0, S - mean_demand)
    logger.info(
        "Derived safety stock = %d  (mean_demand=%d, initial_inventory=%d)",
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
    Execute a single simulation run for one condition spec.

    Returns
    -------
    list[dict]  — 75 records (25 periods × 3 tiers) on success
    None        — if the LLM backend raises RuntimeError (all 3 parse attempts failed)

    run_id is constructed from the condition label, a sequential run index, and
    a short UUID fragment. This makes log messages uniquely traceable without
    being too long to read.

    model_name resolution for E4
    -----------------------------
    If spec contains "model_env_key" (e.g. "MODEL_OSS_REASONING"), we read
    that env var at runtime to get the actual model name string. This decouples
    the experiment spec from the model name so you can change models just by
    editing the env file, and it means the provenance stamp can record exactly
    which model was used.

    If the env var is missing entirely, we exit immediately — running E4 without
    MODEL_OSS_REASONING set would silently fall back to MODEL_REASONING, which
    would produce contaminated data.
    """
    run_id = f"{spec['label']}_r{run_index:02d}_{str(uuid.uuid4())[:6]}"

    # Resolve model override for E4 OSS conditions
    model_name = None
    if "model_env_key" in spec:
        model_name = os.environ.get(spec["model_env_key"])
        if not model_name:
            logger.error(
                "Spec requires env var %s for condition %s but it is not set.",
                spec["model_env_key"], spec["label"],
            )
            sys.exit(1)

    try:
        records = run_simulation(
            demand_series     = demand_df,
            condition         = spec["condition"],       # "blind" or "context"
            model_tier        = spec["model_tier"] or "lightweight",  # None for heuristics
            policy            = spec["policy"],          # "llm", "naive", "order_up_to", "exp_smoothing"
            S                 = S,                       # common opening inventory anchor for all conditions
            safety_stock      = safety_stock,            # used by forecast-based order_up_to heuristic
            initial_inventory = S,                       # all tiers start from the same stock position
            condition_label   = spec["label"],           # e.g. "context_lightweight"
            model_name        = model_name,              # None for E1/E2; set for E4
            run_id            = run_id,
        )
        return records
    except RuntimeError as exc:
        # LLM backend exhausted all retry attempts — this run is invalid
        logger.error("Run %s failed with unrecoverable parse error: %s", run_id, exc)
        return None


def run_condition(
    spec: dict,
    demand_df: pd.DataFrame,
    S: int,
    safety_stock: int,
    n_runs: int,
) -> list[dict]:
    """
    Collect n_runs valid simulations for one condition.

    Why replace failed runs rather than skipping them?
      A run that failed mid-way (parse error on period 17, for example) has
      incomplete records. Including partial runs would bias the mean by
      mixing 75-record runs with shorter records. Replacing them ensures
      every run contributes a full 75 records.

    Heuristic policies
      Are deterministic — the same demand series produces the same output
      every time. We run them exactly once (target = 1) regardless of n_runs.

    max_attempts safety cap
      Set to target × 5. If more than 80% of attempts fail, something is
      systemically wrong (API down, model not deployed, etc.) and we exit
      rather than looping indefinitely.
    """
    all_records  = []
    is_heuristic = spec["policy"] != "llm"
    target       = 1 if is_heuristic else n_runs   # heuristics run once
    completed    = 0
    attempts     = 0
    replacements = 0
    max_attempts = target * 5                      # safety cap to prevent infinite loops

    while completed < target and attempts < max_attempts:
        attempts += 1
        records = run_one(spec, demand_df, S, safety_stock, run_index=completed + 1)
        if records is not None:
            all_records.extend(records)
            completed += 1
            logger.info(
                "Condition %s: completed %d/%d (attempt %d, replacements so far: %d)",
                spec["label"], completed, target, attempts, replacements,
            )
        else:
            replacements += 1
            logger.warning(
                "Condition %s: run failed on attempt %d — triggering replacement #%d",
                spec["label"], attempts, replacements,
            )

    if completed < target:
        # We hit max_attempts without completing all runs — this is a hard failure
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
    """
    Write a partial records.parquet after each condition completes.

    This is a safety net against API crashes mid-experiment. If the process
    dies before save_results() is called, the last checkpoint contains every
    record collected up to that point. Re-run only the remaining conditions.

    The checkpoint is overwritten after each condition — only the latest
    (most complete) snapshot is kept. The final save_results() call writes
    the authoritative records.parquet, summary.json, and provenance.json.
    """
    pd.DataFrame(all_records).to_parquet(out_dir / "records.checkpoint.parquet", index=False)
    logger.info("Checkpoint written to %s (%d records)", out_dir, len(all_records))


def save_results(all_records: list[dict], experiment_label: str, checksum: str, run_stats: dict | None = None, out_dir: Path | None = None) -> Path:
    """
    Persist simulation output to disk as three files in a timestamped directory.

    Directory structure:
      results/<experiment>/<timestamp>/
        records.parquet          — raw simulation records (one row per period × tier × run)
        records.checkpoint.parquet — rolling checkpoint written after each condition (removed on clean finish)
        summary.json             — per-condition aggregated metrics (OVAR, stockouts, pattern)
        provenance.json          — model names and demand checksum for reproducibility

    Why Parquet?
      Parquet preserves dtypes (bool for stockout, int for quantities) without
      the ambiguity of CSV string parsing. The file is typically ~10–50x smaller
      than CSV for this data. It loads directly into pandas for analysis.

    Why group by condition_label, not "condition"?
      "condition" is either "blind" or "context" — two values.
      "condition_label" is e.g. "naive_passthrough", "blind_lightweight", "context_reasoning" — one per spec.
      Grouping by condition_label keeps each heuristic separate (naive vs order_up_to vs exp_smoothing)
      and keeps E1 and E2 separate within the same "blind" or "context" condition.

    provenance.json records all three model env vars (lightweight, reasoning, oss_reasoning)
    even if only one was used in this run. This makes the stamp complete for any
    experiment, and empty strings make it obvious which vars were not set.
    """
    if out_dir is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_dir = RESULTS_DIR / experiment_label / timestamp
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        timestamp = out_dir.name

    # --- records.parquet ---
    df = pd.DataFrame(all_records)
    records_path = out_dir / "records.parquet"
    df.to_parquet(records_path, index=False)

    # --- summary.json ---
    # One summary dict per condition_label. Each dict contains OVAR, stockout,
    # and pattern score statistics for that condition across all its runs.
    summaries = []
    for label, grp in df.groupby("condition_label"):
        summaries.append(summarise_condition(grp, label))

    def _nan_to_null(obj):
        """Recursively replace float NaN with None so strict JSON emits null."""
        if isinstance(obj, float) and obj != obj:  # NaN is the only float where x != x
            return None
        if isinstance(obj, dict):
            return {k: _nan_to_null(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_nan_to_null(v) for v in obj]
        return obj

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(_nan_to_null(summaries), indent=2, allow_nan=False))

    # --- provenance.json ---
    # A machine-readable stamp that records exactly what was run and with what models,
    # plus infrastructure context (latency, token throughput, hardware) so readers
    # can assess what to expect when replicating on local vs cloud infrastructure.
    backend = os.environ.get("BACKEND", "unknown")

    # Latency stats — LLM calls only (latency_ms == 0.0 for heuristic rows)
    import numpy as np
    llm_df = df[df["latency_ms"] > 0].copy()
    if not llm_df.empty:
        lat          = llm_df["latency_ms"]
        ttft         = llm_df["ttft_ms"]
        total_wall_s = float(lat.sum()) / 1000
        total_prompt     = int(llm_df["prompt_tokens"].sum())
        total_completion = int(llm_df["completion_tokens"].sum())
        total_reasoning  = int(llm_df["reasoning_tokens"].sum()) if "reasoning_tokens" in llm_df.columns else 0
        total_cached     = int(llm_df["cached_tokens"].sum())    if "cached_tokens"    in llm_df.columns else 0
        retry_calls      = int((llm_df["attempt_number"] > 1).sum()) if "attempt_number" in llm_df.columns else 0
        latency_stats = {
            "n_calls":                 int(len(llm_df)),
            "mean_ms":                 round(float(lat.mean()), 1),
            "p50_ms":                  round(float(np.percentile(lat, 50)), 1),
            "p95_ms":                  round(float(np.percentile(lat, 95)), 1),
            "p99_ms":                  round(float(np.percentile(lat, 99)), 1),
            "ttft_mean_ms":            round(float(ttft.mean()), 1) if ttft.sum() > 0 else None,
            "ttft_p95_ms":             round(float(np.percentile(ttft[ttft > 0], 95)), 1) if ttft.sum() > 0 else None,
            "mean_generation_tps":     round(float(llm_df["generation_tps"].mean()), 1) if "generation_tps" in llm_df.columns else None,
            "total_prompt_tokens":     total_prompt,
            "total_completion_tokens": total_completion,
            "total_reasoning_tokens":  total_reasoning,
            "total_cached_tokens":     total_cached,
            "tokens_per_second":       round((total_prompt + total_completion) / total_wall_s, 1) if total_wall_s > 0 else None,
            "retry_rate":              round(retry_calls / len(llm_df), 4),
            "total_wall_time_s":       round(total_wall_s, 1),
        }
    else:
        latency_stats = {}

    # Infrastructure context — hardware for local, SKU info for Azure
    import subprocess
    if backend == "local":
        infra_context = {
            "type":        "local",
            "endpoint":    os.environ.get("LOCAL_ENDPOINT", ""),
            "platform":    platform.platform(),
            "cpu":         platform.processor() or platform.machine(),
            "cpu_cores":   os.cpu_count(),
            "python":      platform.python_version(),
        }
        # GPU info via nvidia-smi
        try:
            gpu_out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader"],
                timeout=5, text=True,
            ).strip()
            infra_context["gpu"] = gpu_out
        except Exception:
            infra_context["gpu"] = None
        # Model quantization level via Ollama /api/show
        # Use the model actually running in this experiment, not always MODEL_LIGHTWEIGHT.
        # E2/E4 use MODEL_REASONING or MODEL_OSS_REASONING; only E1 uses MODEL_LIGHTWEIGHT.
        try:
            import urllib.request, json as _json
            if experiment_label in ("E2",):
                model_tag = os.environ.get("MODEL_REASONING", "") or os.environ.get("MODEL_LIGHTWEIGHT", "")
            elif experiment_label in ("E4",):
                model_tag = os.environ.get("MODEL_OSS_REASONING", "") or os.environ.get("MODEL_LIGHTWEIGHT", "")
            else:
                model_tag = os.environ.get("MODEL_LIGHTWEIGHT", "")
            req = urllib.request.Request(
                "http://localhost:11434/api/show",
                data=_json.dumps({"name": model_tag}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                info = _json.loads(resp.read())
            details = info.get("details", {})
            infra_context["model_quantization"]  = details.get("quantization_level")
            infra_context["model_parameter_size"] = details.get("parameter_size")
            infra_context["model_format"]         = details.get("format")
        except Exception:
            infra_context["model_quantization"]  = None
            infra_context["model_parameter_size"] = None
            infra_context["model_format"]         = None
    else:
        infra_context = {
            "type":        "azure",
            "endpoint":    os.environ.get("AZURE_ENDPOINT", ""),
            "api_version": os.environ.get("AZURE_API_VERSION", ""),
            "model_lightweight_deployment": os.environ.get("MODEL_LIGHTWEIGHT", ""),
            "model_reasoning_deployment":   os.environ.get("MODEL_REASONING", ""),
        }

    stamp = {
        "experiment":             experiment_label,
        "timestamp_utc":          timestamp,
        "demand_checksum_sha256": checksum,
        "backend":                backend,
        "model_lightweight":      os.environ.get("MODEL_LIGHTWEIGHT", ""),
        "model_reasoning":        os.environ.get("MODEL_REASONING", ""),
        "model_oss_reasoning":    os.environ.get("MODEL_OSS_REASONING", ""),
        "temperature_config": {
            "blind_lightweight":   float(os.environ.get("TEMP_LIGHTWEIGHT", "0.0")),
            "context_lightweight": float(os.environ.get("TEMP_CONTEXT_LIGHTWEIGHT", "0.3")),
            "blind_reasoning":     float(os.environ.get("TEMP_REASONING", "0.0")),
            "context_reasoning":   float(os.environ.get("TEMP_CONTEXT_REASONING", "0.3")),
        },
        "run_stats":              run_stats or {},
        "latency_stats":          latency_stats,
        "infra_context":          infra_context,
    }
    (out_dir / "provenance.json").write_text(json.dumps(stamp, indent=2))

    # Remove the rolling checkpoint now that the authoritative files are written
    checkpoint = out_dir / "records.checkpoint.parquet"
    if checkpoint.exists():
        checkpoint.unlink()

    logger.info("Results saved to %s", out_dir)
    return out_dir


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """
    Parse CLI arguments, load env, verify data, and run the requested experiments.

    Each experiment in --experiments gets its own output directory and summary.
    If multiple experiments are passed (e.g. --experiments E1 E2), they run
    sequentially and produce separate directories — results are not mixed.
    """
    parser = argparse.ArgumentParser(description="Run Agentic Bullwhip Experiment")
    parser.add_argument(
        "--experiments", nargs="+", default=["baselines"],
        choices=list(EXPERIMENTS.keys()),
        help="Which experiments to run (e.g. baselines E1 E2 E4)",
    )
    parser.add_argument(
        "--runs", type=int, default=20,
        help="Number of valid runs to collect per LLM condition (default: 20)",
    )
    parser.add_argument(
        "--env", type=str, default=".env",
        help="Path to the .env file to load (default: .env in current directory)",
    )
    parser.add_argument(
        "--results-dir", type=str, default=None,
        help="Output directory for results (default: 'results/'). Use 'test_runs' for smoke tests.",
    )
    args = parser.parse_args()

    # Load environment variables from the specified .env file.
    # These include BACKEND, model names, API keys, temperature, max_tokens.
    load_dotenv(args.env)

    # Override the default results directory if --results-dir was passed.
    global RESULTS_DIR
    if args.results_dir:
        RESULTS_DIR = Path(args.results_dir)

    # Verify demand file exists and has the required columns before any API calls
    if not DATA_FILE.exists():
        logger.error(
            "Demand file not found: %s — provide the dataset before running.", DATA_FILE
        )
        sys.exit(1)

    demand_df = pd.read_csv(DATA_FILE)
    required_cols = {"period", "calendar_month", "retail_demand"}
    if not required_cols.issubset(demand_df.columns):
        logger.error("Demand file missing columns. Required: %s", required_cols)
        sys.exit(1)

    # Verify dataset and derive common baseline parameters from the full demand_df
    checksum = verify_dataset(demand_df)
    S = derive_S(demand_df)
    safety_stock = derive_safety_stock(demand_df, S)

    # Run each requested experiment in turn
    for exp_name in args.experiments:
        logger.info("=== Starting experiment: %s ===", exp_name)
        all_records = []
        run_stats = {}

        # Create output directory upfront so checkpoints can be written after
        # each condition. If the process crashes mid-experiment, records.checkpoint.parquet
        # contains every record collected so far — nothing is lost.
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_dir = RESULTS_DIR / exp_name / timestamp
        out_dir.mkdir(parents=True, exist_ok=True)

        for spec in EXPERIMENTS[exp_name]:
            logger.info("Running condition: %s", spec["label"])
            records, stats = run_condition(spec, demand_df, S, safety_stock, n_runs=args.runs)
            all_records.extend(records)
            run_stats[spec["label"]] = stats
            _checkpoint(all_records, out_dir)

        out_dir = save_results(all_records, exp_name, checksum, run_stats=run_stats, out_dir=out_dir)
        logger.info("=== %s complete — results at %s ===", exp_name, out_dir)


if __name__ == "__main__":
    main()
