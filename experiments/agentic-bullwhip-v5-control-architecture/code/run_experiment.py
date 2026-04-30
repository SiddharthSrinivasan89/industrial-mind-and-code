"""
V5 ControlArch Experiment entry point.

Tests whether better control architectures let supply-chain agents reduce
bullwhip amplification. All Phase 1 conditions are deterministic (no LLM cost).
LLM conditions (Phase 2) are added only if Phase 1 reveals a policy with leverage.

Run target logic
----------------
  --runs N   overrides everything; all conditions run exactly N times
  (omit)     each spec uses its own "runs" default (typically 5 for screening)

This replaces V4's is_heuristic / HEURISTIC_RUNS branch so that
--runs 50 works for baselines and ablations equally.

Usage
-----
    # Smoke test (dry run, 1 each)
    DRY_RUN=1 python run_experiment.py --experiments baselines A1_oracle --runs 1

    # Baseline replication (5-run screening)
    python run_experiment.py --experiments baselines --runs 5

    # Full Phase 1 screening
    python run_experiment.py --experiments baselines A1_oracle A2_multiplier A3_neutral A4_dampening A5_forecast A6_causal

    # Rerun borderline condition at higher N before gate evaluation
    python run_experiment.py --experiments A4_dampening --runs 50

Experiment groups
-----------------
    baselines      — naive_passthrough, order_up_to, exp_smoothing (5 screening runs)
    A1_oracle      — oracle intent + V4 conservative map (diagnostic upper bound)
    A2_multiplier  — oracle intent + 3 wider multiplier maps
    A3_neutral     — oracle intent + 4 NEUTRAL mechanical variants
    A4_dampening   — oracle intent + order dampening β sweep
    A5_forecast    — oracle intent + forecast oracle (event-adjusted F_t)
    A6_causal      — causal rule-based intent (fair non-LLM baseline)
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

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from simulation import run_simulation
from metrics import summarise_condition
from world_events import WorldEvents
from oracle_policies import MULTIPLIER_MAPS

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

TIERS    = ["OEM", "Ancillary", "Component"]
NOISE_CV = 0.08    # 8% CV multiplicative demand noise

# ---------------------------------------------------------------------------
# Experiment registry
# ---------------------------------------------------------------------------

EXPERIMENTS: dict[str, list[dict]] = {

    # -----------------------------------------------------------------------
    # V4 baselines — same policy logic, 5-run screening
    # -----------------------------------------------------------------------
    "baselines": [
        {"label": "naive_passthrough", "policy": "naive",         "condition": "blind", "model_tier": None, "runs": 5},
        {"label": "exp_smoothing",     "policy": "exp_smoothing", "condition": "blind", "model_tier": None, "runs": 5},
        {"label": "order_up_to",       "policy": "order_up_to",   "condition": "blind", "model_tier": None, "runs": 5},
    ],

    # -----------------------------------------------------------------------
    # A1: Oracle intent — V4 conservative map
    # Diagnostic upper bound: if OVAR stays ~1.77, controller is the bottleneck.
    # Oracle uses GROUND_TRUTH_INTENT (future demand knowledge — NOT deployable).
    # All tiers receive the same OEM demand label (OEM demand drives the chain).
    # -----------------------------------------------------------------------
    "A1_oracle": [
        {"label": "oracle_v4map", "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "out", "dampening_beta": 1.0}},
    ],

    # -----------------------------------------------------------------------
    # A2: Multiplier sweep — oracle labels, wider maps
    # Tests whether the V4 multiplier band (0.80–1.30) was simply too narrow.
    # -----------------------------------------------------------------------
    "A2_multiplier": [
        {"label": "oracle_moderate",   "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "moderate",   "neutral_mode": "out", "dampening_beta": 1.0}},
        {"label": "oracle_aggressive", "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "aggressive", "neutral_mode": "out", "dampening_beta": 1.0}},
        {"label": "oracle_asymmetric", "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "asymmetric", "neutral_mode": "out", "dampening_beta": 1.0}},
    ],

    # -----------------------------------------------------------------------
    # A3: NEUTRAL redefinition — oracle labels, V4 conservative map
    # Tests whether language-level caution should map to mechanical inaction.
    # Note: dampening_beta=1.0 for all A3 specs; dampened_out uses a fixed 0.375
    # factor internally. Never combine A3 neutral_mode with A4 dampening_beta < 1.
    # -----------------------------------------------------------------------
    "A3_neutral": [
        {"label": "neutral_repeat_last",       "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "repeat_last",       "dampening_beta": 1.0}},
        {"label": "neutral_smoothed_forecast", "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "smoothed_forecast", "dampening_beta": 1.0}},
        {"label": "neutral_dampened_out",      "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "dampened_out",      "dampening_beta": 1.0}},
        {"label": "neutral_floor_only",        "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "floor_only",        "dampening_beta": 1.0}},
    ],

    # -----------------------------------------------------------------------
    # A4: Order dampening — oracle intent, V4 conservative map, β sweep
    # Dampening applied to ALL orders (not only NEUTRAL) as a post-formula layer.
    # neutral_mode="out" for all A4 specs. Most likely ablation to reduce OVAR.
    # -----------------------------------------------------------------------
    "A4_dampening": [
        {"label": "dampened_beta75", "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "out", "dampening_beta": 0.75}},
        {"label": "dampened_beta50", "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "out", "dampening_beta": 0.50}},
        {"label": "dampened_beta25", "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "out", "dampening_beta": 0.25}},
    ],

    # -----------------------------------------------------------------------
    # A5: Forecast oracle — event-adjusted F_t
    # world_events.demand_multiplier(period) adjusts the order target only;
    # the EMA chain remains clean (unadjusted F_t stored for next period).
    # NOTE: applies retail demand multiplier to all tiers — diagnostic assumption,
    # not a modelling claim about upstream tier demand.
    # -----------------------------------------------------------------------
    "A5_forecast": [
        {"label": "forecast_oracle_events", "policy": "oracle_intent", "condition": "blind", "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "out", "dampening_beta": 1.0,
                    "use_forecast_oracle": True}},
    ],

    # -----------------------------------------------------------------------
    # A6: Causal deterministic intent — fair non-LLM baseline
    # Uses only information available at decision time: calendar month and
    # world-event headline (for unstructured condition only).
    # causal_context    — calendar only, matches LLM "context" condition
    # causal_unstructured — calendar + event signal, matches LLM "unstructured"
    # -----------------------------------------------------------------------
    "A6_causal": [
        {"label": "causal_context",       "policy": "causal_intent", "condition": "context",      "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "out", "dampening_beta": 1.0}},
        {"label": "causal_unstructured",  "policy": "causal_intent", "condition": "unstructured",  "model_tier": None, "runs": 5,
         "params": {"multiplier_map": "conservative", "neutral_mode": "out", "dampening_beta": 1.0}},
    ],
}

# ---------------------------------------------------------------------------
# Dataset helpers — identical to V4
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
    params = spec.get("params", {})

    # Resolve multiplier_map string → dict
    map_key = params.get("multiplier_map", "conservative")
    if map_key not in MULTIPLIER_MAPS:
        raise ValueError(f"Unknown multiplier_map: {map_key!r}. Valid: {list(MULTIPLIER_MAPS)}")
    resolved_map = MULTIPLIER_MAPS[map_key]

    condition      = spec.get("condition", "blind")
    model_tier     = spec.get("model_tier") or "lightweight"
    policy         = spec["policy"]
    temperature    = 0.0  # deterministic for all Phase 1 specs

    try:
        records = run_simulation(
            demand_series       = demand_df,
            condition           = condition,
            model_tier          = model_tier,
            policy              = policy,
            S                   = S,
            safety_stock        = safety_stock,
            world_events        = world_events,
            llm_temperature     = temperature,
            condition_label     = spec["label"],
            run_id              = run_id,
            noise_cv            = NOISE_CV,
            rng_seed            = rng_seed,
            multiplier_map      = resolved_map,
            dampening_beta      = params.get("dampening_beta", 1.0),
            neutral_mode        = params.get("neutral_mode", "out"),
            use_forecast_oracle = params.get("use_forecast_oracle", False),
        )
        return records
    except RuntimeError as exc:
        logger.error("Run %s failed: %s", run_id, exc)
        return None


def run_condition(
    spec: dict,
    demand_df: pd.DataFrame,
    S: int,
    safety_stock: int,
    world_events: WorldEvents,
    n_runs: int | None,
) -> tuple[list[dict], dict]:
    # V5 run target logic: CLI --runs takes precedence; fall back to spec default
    target      = n_runs if n_runs is not None else spec.get("runs", 5)
    all_records = []
    completed   = 0
    attempts    = 0
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
# Output — identical to V4 pattern with V5 provenance stamp
# ---------------------------------------------------------------------------

def _checkpoint(all_records: list[dict], out_dir: Path) -> None:
    pd.DataFrame(all_records).to_parquet(out_dir / "records.checkpoint.parquet", index=False)
    logger.info("Checkpoint written (%d records so far)", len(all_records))


def save_results(
    all_records: list[dict],
    experiment_label: str,
    checksum: str,
    world_events: WorldEvents,
    specs: list[dict],
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

    # Provenance — V5 stamp
    backend = os.environ.get("BACKEND", "unknown")
    llm_df  = df[df.get("latency_ms", pd.Series(dtype=float)) > 0] if "latency_ms" in df.columns else pd.DataFrame()

    if not llm_df.empty:
        lat = llm_df["latency_ms"]
        latency_stats = {
            "n_calls":           int(len(llm_df)),
            "mean_ms":           round(float(lat.mean()), 1),
            "p50_ms":            round(float(np.percentile(lat, 50)), 1),
            "p95_ms":            round(float(np.percentile(lat, 95)), 1),
            "total_wall_time_s": round(float(lat.sum()) / 1000, 1),
        }
    else:
        latency_stats = {}

    v5_params = {s["label"]: s.get("params", {}) for s in specs}

    stamp = {
        "version":                "V5_ControlArch",
        "experiment":             experiment_label,
        "timestamp_utc":          timestamp,
        "demand_file":            str(DATA_FILE),
        "demand_checksum_sha256": checksum,
        "backend":                backend,
        "noise_cv":               NOISE_CV,
        "world_events_enabled":   list(world_events._enabled),
        "model_lightweight":      os.environ.get("MODEL_LIGHTWEIGHT", ""),
        "model_reasoning":        os.environ.get("MODEL_REASONING", ""),
        "v5_params":              v5_params,
        "run_stats":              run_stats or {},
        "latency_stats":          latency_stats,
        "platform":               platform.platform(),
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
    parser = argparse.ArgumentParser(description="Run V5 ControlArch Experiment")
    parser.add_argument("--experiments", nargs="+", default=["baselines"],
                        choices=list(EXPERIMENTS.keys()),
                        metavar="EXP")
    parser.add_argument("--runs",        type=int, default=None,
                        help="Override run count for all conditions. Omit to use per-spec defaults.")
    parser.add_argument("--env",         type=str, default=".env")
    parser.add_argument("--results-dir", type=str, default=None)
    parser.add_argument("--no-events",   action="store_true",
                        help="Disable all world events (global override)")
    args = parser.parse_args()

    load_dotenv(args.env)

    global RESULTS_DIR
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
            records, stats = run_condition(
                spec, demand_df, S, safety_stock, world_events, args.runs
            )
            all_records.extend(records)
            all_stats[spec["label"]] = stats
            _checkpoint(all_records, out_dir)

        save_results(all_records, exp_label, checksum, world_events, specs, all_stats, out_dir)
        logger.info("=== %s complete — results at %s ===", exp_label, out_dir)


if __name__ == "__main__":
    main()
