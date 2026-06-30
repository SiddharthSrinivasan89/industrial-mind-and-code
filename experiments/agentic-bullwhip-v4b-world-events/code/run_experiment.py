"""
V4 WorldEvents Experiment entry point.

Combines V3's 36-month world-events simulation with V4's intent classification
output interface. The LLM classifies buffer intent (5 discrete labels); a
deterministic lookup table converts the label to a safety stock multiplier;
the OUT-style formula executes the order.

Key parameters
--------------
  36-month demand series (Jan 2025 -- Dec 2027)
  SimPy discrete-event simulation, stochastic lead times and fill rates
  WorldEvents: pandemic (periods 7-12), conflict (19-21), port disruption (28-30)
  Three prompt conditions: blind, context, unstructured
  Heuristic baselines: 100 Monte Carlo runs (demand noise varies each run)
  LLM experiments: 20 runs per condition

Usage
-----
    python run_experiment.py --experiments baselines E1_IC_azure E2_IC_azure --runs 20 --env .env.azure
    python run_experiment.py --experiments baselines --runs 100   # heuristic baseline Monte Carlo
    python run_experiment.py --experiments E1_IC_phi E2_IC_nemotron E3_IC --env .env.local
    DRY_RUN=1 python run_experiment.py --experiments baselines E1_IC_azure --runs 2  # pipeline check

Experiment groups
-----------------
    baselines      — naive_passthrough, order_up_to, exp_smoothing (100 Monte Carlo runs each)
    E1_IC_azure    — intent × gpt-4.1-mini (lightweight) × 3 conditions × 20 runs
    E1_IC_phi      — intent × phi4:14b (lightweight) × 3 conditions × 10 runs
    E2_IC_azure    — intent × o4-mini (reasoning) × 3 conditions × 20 runs
    E2_IC_nemotron — intent × nemotron-super 120B (reasoning) × 3 conditions × 10 runs
    E3_IC          — ablation: world events OFF × phi4 lightweight × blind/context × 10 runs
    E4_IC_azure    — neutral-prior prompt × gpt-4.1-mini × blind_neutral/context_neutral × 20 runs
    E4_IC_o4mini   — neutral-prior prompt × o4-mini × blind_neutral/context_neutral × 20 runs
    E4_IC_phi      — neutral-prior prompt × phi4:14b × blind_neutral/context_neutral × 10 runs
"""

import argparse
import hashlib
import json
import logging
import os
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from simulation import run_simulation
from metrics import summarise_condition
from world_events import WorldEvents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

RESULTS_DIR = Path("results")
DATA_FILE   = Path("data/synthetic/tatva_monthly_dispatches_36m.csv")

TIERS         = ["OEM", "Ancillary", "Component"]
NOISE_CV      = 0.08    # 8% CV multiplicative demand noise
HEURISTIC_RUNS = 100    # Monte Carlo runs for each heuristic baseline

# GPU thermal cool-down for local runs: run 4h → rest 30 min → repeat
COOLDOWN_INTERVAL_H = 4.0
COOLDOWN_DURATION_S = 1800   # 30 minutes

_last_cooldown_at: float = 0.0   # set to time.time() at main() start

# ---------------------------------------------------------------------------
# Experiment registry
# ---------------------------------------------------------------------------

EXPERIMENTS: dict[str, list[dict]] = {
    "baselines": [
        {"label": "naive_passthrough", "policy": "naive",         "condition": "blind", "model_tier": None},
        {"label": "exp_smoothing",     "policy": "exp_smoothing", "condition": "blind", "model_tier": None},
        {"label": "order_up_to",       "policy": "order_up_to",   "condition": "blind", "model_tier": None},
    ],

    # E1_IC — lightweight model, 3 prompt conditions
    # Azure: gpt-4.1-mini, 20 runs  |  Local: phi4:14b, 10 runs
    "E1_IC_azure": [
        {"label": "ic_blind_gpt41mini",        "policy": "intent", "condition": "blind",        "model_tier": "lightweight", "runs": 20},
        {"label": "ic_context_gpt41mini",      "policy": "intent", "condition": "context",      "model_tier": "lightweight", "runs": 20},
        {"label": "ic_unstructured_gpt41mini", "policy": "intent", "condition": "unstructured", "model_tier": "lightweight", "runs": 20},
    ],
    "E1_IC_phi": [
        {"label": "ic_blind_phi",        "policy": "intent", "condition": "blind",        "model_tier": "lightweight", "runs": 10},
        {"label": "ic_context_phi",      "policy": "intent", "condition": "context",      "model_tier": "lightweight", "runs": 10},
        {"label": "ic_unstructured_phi", "policy": "intent", "condition": "unstructured", "model_tier": "lightweight", "runs": 10},
    ],

    # E2_IC — reasoning model, 3 prompt conditions
    # Azure: o4-mini, 20 runs  |  Local: nemotron 120B, 10 runs
    "E2_IC_azure": [
        {"label": "ic_blind_o4mini",        "policy": "intent", "condition": "blind",        "model_tier": "reasoning", "runs": 20},
        {"label": "ic_context_o4mini",      "policy": "intent", "condition": "context",      "model_tier": "reasoning", "runs": 20},
        {"label": "ic_unstructured_o4mini", "policy": "intent", "condition": "unstructured", "model_tier": "reasoning", "runs": 20},
    ],
    "E2_IC_nemotron": [
        {"label": "ic_blind_nemotron",        "policy": "intent", "condition": "blind",        "model_tier": "reasoning", "runs": 10},
        {"label": "ic_context_nemotron",      "policy": "intent", "condition": "context",      "model_tier": "reasoning", "runs": 10},
        {"label": "ic_unstructured_nemotron", "policy": "intent", "condition": "unstructured", "model_tier": "reasoning", "runs": 10},
    ],

    # E3_IC — ablation: world events OFF, lightweight model, 10 runs local
    "E3_IC": [
        {"label": "ic_blind_no_events_phi",   "policy": "intent", "condition": "blind",   "model_tier": "lightweight", "no_events": True, "runs": 10},
        {"label": "ic_context_no_events_phi", "policy": "intent", "condition": "context", "model_tier": "lightweight", "no_events": True, "runs": 10},
    ],

    # E4_IC — neutral-prior prompt variant: default to NEUTRAL unless signal is strong
    # Tests whether biasing toward inaction reduces order variance amplification.
    # Unstructured excluded — explicit event headlines override ambiguity by design.
    "E4_IC_azure": [
        {"label": "ic_blind_neutral_gpt41mini",   "policy": "intent", "condition": "blind_neutral",   "model_tier": "lightweight", "runs": 20},
        {"label": "ic_context_neutral_gpt41mini", "policy": "intent", "condition": "context_neutral", "model_tier": "lightweight", "runs": 20},
    ],
    "E4_IC_o4mini": [
        {"label": "ic_blind_neutral_o4mini",   "policy": "intent", "condition": "blind_neutral",   "model_tier": "reasoning", "runs": 20},
        {"label": "ic_context_neutral_o4mini", "policy": "intent", "condition": "context_neutral", "model_tier": "reasoning", "runs": 20},
    ],
    "E4_IC_phi": [
        {"label": "ic_blind_neutral_phi",   "policy": "intent", "condition": "blind_neutral",   "model_tier": "lightweight", "runs": 10},
        {"label": "ic_context_neutral_phi", "policy": "intent", "condition": "context_neutral", "model_tier": "lightweight", "runs": 10},
    ],
}

# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

def verify_dataset(demand_df: pd.DataFrame, data_file: Path) -> str:
    raw      = data_file.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    logger.info("Demand file SHA-256: %s", checksum)
    return checksum


def derive_S(demand_df: pd.DataFrame) -> int:
    mu    = demand_df["retail_demand"].mean()
    sigma = demand_df["retail_demand"].std(ddof=1)
    S     = int(round(mu + 1.65 * sigma))
    logger.info("Derived S = %d  (mean=%.1f, std=%.1f)", S, mu, sigma)
    return S


def derive_safety_stock(demand_df: pd.DataFrame, S: int) -> int:
    mean_demand  = int(round(demand_df["retail_demand"].mean()))
    safety_stock = max(0, S - mean_demand)
    logger.info("Derived safety stock = %d", safety_stock)
    return safety_stock

# ---------------------------------------------------------------------------
# Temperature resolution
# ---------------------------------------------------------------------------

def resolve_temperature(condition: str, model_tier: str) -> float:
    env_map = {
        ("blind",           "lightweight"): ("TEMP_LIGHTWEIGHT",             "0.4"),
        ("blind_neutral",   "lightweight"): ("TEMP_LIGHTWEIGHT",             "0.4"),
        ("context",         "lightweight"): ("TEMP_CONTEXT_LIGHTWEIGHT",     "0.4"),
        ("context_neutral", "lightweight"): ("TEMP_CONTEXT_LIGHTWEIGHT",     "0.4"),
        ("unstructured",    "lightweight"): ("TEMP_UNSTRUCTURED_LIGHTWEIGHT","0.4"),
        ("blind",           "reasoning"):   ("TEMP_REASONING",               "0.0"),
        ("blind_neutral",   "reasoning"):   ("TEMP_REASONING",               "0.0"),
        ("context",         "reasoning"):   ("TEMP_CONTEXT_REASONING",       "0.3"),
        ("context_neutral", "reasoning"):   ("TEMP_CONTEXT_REASONING",       "0.3"),
        ("unstructured",    "reasoning"):   ("TEMP_UNSTRUCTURED_REASONING",  "0.3"),
    }
    env_var, default = env_map.get((condition, model_tier), ("TEMP_LIGHTWEIGHT", "0.4"))
    return float(os.environ.get(env_var, default))

# ---------------------------------------------------------------------------
# Run management
# ---------------------------------------------------------------------------

def run_one(
    spec: dict,
    demand_df: pd.DataFrame,
    S: int,
    safety_stock: int,
    world_events: WorldEvents,
    run_index: int,
    rng_seed: int,
) -> list[dict] | None:
    run_id = f"{spec['label']}_r{run_index:02d}_{str(uuid.uuid4())[:6]}"

    model_name = None
    condition  = spec["condition"]
    model_tier = spec["model_tier"] or "lightweight"
    temperature = resolve_temperature(condition, model_tier) if spec["policy"] == "intent" else 0.0

    try:
        records = run_simulation(
            demand_series   = demand_df,
            condition       = condition,
            model_tier      = model_tier,
            policy          = spec["policy"],
            S               = S,
            safety_stock    = safety_stock,
            world_events    = world_events,
            llm_temperature = temperature,
            condition_label = spec["label"],
            model_name      = model_name,
            run_id          = run_id,
            noise_cv        = NOISE_CV,
            rng_seed        = rng_seed,
        )
        return records
    except RuntimeError as exc:
        logger.error("Run %s failed: %s", run_id, exc)
        return None


def _maybe_cooldown() -> None:
    """
    Sleep 30 min if 4 hours have elapsed since the last cooldown.
    Only applies when BACKEND=local — Azure runs are not GPU-bound.
    """
    global _last_cooldown_at
    if os.environ.get("BACKEND", "azure").lower() != "local":
        return
    elapsed_h = (time.time() - _last_cooldown_at) / 3600
    if elapsed_h >= COOLDOWN_INTERVAL_H:
        logger.info(
            "%.1fh elapsed since last cooldown — resting GPU for %.0f min.",
            elapsed_h, COOLDOWN_DURATION_S / 60,
        )
        time.sleep(COOLDOWN_DURATION_S)
        _last_cooldown_at = time.time()
        logger.info("Cool-down complete. Resuming.")


def run_condition(
    spec: dict,
    demand_df: pd.DataFrame,
    S: int,
    safety_stock: int,
    world_events: WorldEvents,
    n_runs: int,
) -> tuple[list[dict], dict]:
    is_heuristic = spec["policy"] != "intent"
    target       = HEURISTIC_RUNS if is_heuristic else spec.get("runs", n_runs)
    all_records  = []
    completed    = 0
    attempts     = 0
    replacements = 0
    max_attempts = target * 5

    while completed < target and attempts < max_attempts:
        attempts += 1
        rng_seed = (completed + 1) * 1000
        records  = run_one(spec, demand_df, S, safety_stock, world_events, completed + 1, rng_seed)
        if records is not None:
            all_records.extend(records)
            completed += 1
            logger.info(
                "Condition %s: completed %d/%d (attempt %d, replacements: %d)",
                spec["label"], completed, target, attempts, replacements,
            )
            _maybe_cooldown()
        else:
            replacements += 1
            logger.warning(
                "Condition %s: attempt %d failed — replacement #%d",
                spec["label"], attempts, replacements,
            )

    if completed < target:
        logger.error(
            "Condition %s: only %d/%d runs after %d attempts. Check API.",
            spec["label"], completed, target, attempts,
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
    logger.info("Checkpoint written (%d records so far)", len(all_records))


def save_results(
    all_records: list[dict],
    experiment_label: str,
    checksum: str,
    world_events: WorldEvents,
    run_stats: dict | None = None,
    out_dir: Path | None = None,
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    if out_dir is None:
        out_dir = RESULTS_DIR / experiment_label / timestamp
        out_dir.mkdir(parents=True, exist_ok=True)

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

    # Provenance
    backend = os.environ.get("BACKEND", "unknown")
    llm_df  = df[df.get("latency_ms", pd.Series(dtype=float)) > 0] if "latency_ms" in df.columns else pd.DataFrame()

    if not llm_df.empty:
        lat = llm_df["latency_ms"]
        latency_stats = {
            "n_calls":            int(len(llm_df)),
            "mean_ms":            round(float(lat.mean()), 1),
            "p50_ms":             round(float(np.percentile(lat, 50)), 1),
            "p95_ms":             round(float(np.percentile(lat, 95)), 1),
            "total_wall_time_s":  round(float(lat.sum()) / 1000, 1),
        }
    else:
        latency_stats = {}

    from agent_interface import INTENT_MULTIPLIER_MAP

    stamp = {
        "version":                "V4_WorldEvents",
        "experiment":             experiment_label,
        "timestamp_utc":          timestamp,
        "demand_file":            str(DATA_FILE),
        "demand_checksum_sha256": checksum,
        "backend":                backend,
        "noise_cv":               NOISE_CV,
        "world_events_enabled":   list(world_events._enabled),
        "model_lightweight":      os.environ.get("MODEL_LIGHTWEIGHT", ""),
        "model_reasoning":        os.environ.get("MODEL_REASONING", ""),
        "intent_multiplier_map":  INTENT_MULTIPLIER_MAP,
        "temperature_config": {
            "blind_lightweight":         float(os.environ.get("TEMP_LIGHTWEIGHT", "0.4")),
            "context_lightweight":       float(os.environ.get("TEMP_CONTEXT_LIGHTWEIGHT", "0.4")),
            "unstructured_lightweight":  float(os.environ.get("TEMP_UNSTRUCTURED_LIGHTWEIGHT", "0.4")),
            "blind_reasoning":           float(os.environ.get("TEMP_REASONING", "0.0")),
            "context_reasoning":         float(os.environ.get("TEMP_CONTEXT_REASONING", "0.3")),
            "unstructured_reasoning":    float(os.environ.get("TEMP_UNSTRUCTURED_REASONING", "0.3")),
        },
        "run_stats":     run_stats or {},
        "latency_stats": latency_stats,
        "platform":      platform.platform(),
    }
    (out_dir / "provenance.json").write_text(json.dumps(stamp, indent=2))

    checkpoint = out_dir / "records.checkpoint.parquet"
    if checkpoint.exists():
        checkpoint.unlink()

    logger.info("Results saved to %s", out_dir)
    return out_dir

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run V4 WorldEvents Experiment")
    parser.add_argument("--experiments", nargs="+", default=["baselines"],
                        choices=list(EXPERIMENTS.keys()),
                        metavar="EXP")
    parser.add_argument("--runs",        type=int, default=20)
    parser.add_argument("--env",         type=str, default=".env")
    parser.add_argument("--results-dir", type=str, default=None)
    parser.add_argument("--no-events",   action="store_true",
                        help="Disable all world events (global override — use E3_IC for per-spec ablation)")
    args = parser.parse_args()

    load_dotenv(args.env)

    global RESULTS_DIR, _last_cooldown_at
    _last_cooldown_at = time.time()
    if args.results_dir:
        RESULTS_DIR = Path(args.results_dir)

    if not DATA_FILE.exists():
        logger.error(
            "Demand file not found: %s — run generate_demand_36m.py first", DATA_FILE
        )
        sys.exit(1)

    demand_df = pd.read_csv(DATA_FILE)
    required  = {"period", "calendar_month", "retail_demand"}
    if not required.issubset(demand_df.columns):
        logger.error("Demand CSV missing columns: %s", required - set(demand_df.columns))
        sys.exit(1)

    checksum     = verify_dataset(demand_df, DATA_FILE)
    S            = derive_S(demand_df)
    safety_stock = derive_safety_stock(demand_df, S)

    enabled = set() if args.no_events else WorldEvents.ALL_EVENTS
    world_events = WorldEvents(enabled_events=enabled)
    logger.info("World events enabled: %s", world_events._enabled or "none")

    for exp_label in args.experiments:
        specs = EXPERIMENTS[exp_label]
        logger.info("=== Starting experiment: %s ===", exp_label)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_dir   = RESULTS_DIR / exp_label / timestamp
        out_dir.mkdir(parents=True, exist_ok=True)

        all_records = []
        all_stats   = {}

        for spec in specs:
            # E3_IC specs override world events per-spec (no_events: True)
            ev = WorldEvents(enabled_events=set()) if spec.get("no_events") else world_events

            records, stats = run_condition(
                spec, demand_df, S, safety_stock, ev, args.runs
            )
            all_records.extend(records)
            all_stats[spec["label"]] = stats
            _checkpoint(all_records, out_dir)

        we_for_stamp = WorldEvents(enabled_events=set()) if all(spec.get("no_events") for spec in specs) else world_events
        save_results(all_records, exp_label, checksum, we_for_stamp, all_stats, out_dir)
        logger.info("=== %s complete — results at %s ===", exp_label, out_dir)


if __name__ == "__main__":
    main()
