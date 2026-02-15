#!/usr/bin/env python3
"""
Bullwhip Experiment Runner v3 — Tatva Motors Monthly Dispatches
================================================================

Usage:
    # Validate with 1 run on cheapest model
    python run_experiment.py --category blind --model lightweight --runs 1

    # Run single config
    python run_experiment.py --category context --model lightweight --runs 3

    # Run ALL configs (full experiment: 2 categories x 2 models x 3 runs = 12)
    python run_experiment.py --all

    # Analyze existing results only (no API calls)
    python run_experiment.py --analyze

Run from: dev/bullwhip-effect/src/
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Local imports
from blind_agent import BlindAgent
from context_agent import ContextAgent
from foundry_client import FoundryClient
from inventory_manager import InventoryManager
from supply_chain import SupplyChain

# =============================================================================
# Paths (relative to dev/bullwhip-effect/)
# =============================================================================
BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "experiment_config.yaml"
DATA_PATH = BASE_DIR / "data" / "tatva_monthly_dispatches.csv"
RESULTS_DIR = BASE_DIR / "results"
RAW_DIR = RESULTS_DIR / "raw"
AGG_DIR = RESULTS_DIR / "aggregated"
FIGURES_DIR = RESULTS_DIR / "figures"


# =============================================================================
# Logging
# =============================================================================
def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(RESULTS_DIR / "experiment.log", mode="a"),
        ],
    )


# =============================================================================
# Config
# =============================================================================
def expand_env_vars(config):
    """Recursively expand ${VAR_NAME} environment variables in config."""
    if isinstance(config, dict):
        return {k: expand_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [expand_env_vars(item) for item in config]
    elif isinstance(config, str):
        pattern = r'\$\{([^}]+)\}'
        def replacer(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        return re.sub(pattern, replacer, config)
    else:
        return config

def load_config(path=None):
    p = path or CONFIG_PATH
    with open(p, "r") as f:
        config = yaml.safe_load(f)
    return expand_env_vars(config)


# =============================================================================
# Single run execution
# =============================================================================
def execute_run(config, category, model_tier, run_number, demand_data):
    """Execute one simulation run. Returns result dict."""
    exp = config.get("experiment", {})
    costs = config.get("costs", {})
    initial_inv = exp.get("initial_inventory", 180000)
    time_unit = exp.get("time_unit", "month")

    lead_time = exp.get("lead_time_periods",
                        exp.get("lead_time_weeks", 1))
    ordering_periods = exp.get("ordering_periods",
                               exp.get("ordering_weeks", 13))

    client = FoundryClient(config)

    chain = SupplyChain(
        agent_category=category,
        initial_inventory=initial_inv,
        lead_time_periods=lead_time,
        time_unit=time_unit,
        holding_cost=costs.get("holding_per_unit", 100),
        backlog_cost=costs.get("backlog_per_unit", 1000),
    )

    start = time.time()
    result = chain.run(
        demand_data=demand_data,
        client=client,
        model_tier=model_tier,
        ordering_periods=ordering_periods,
    )
    elapsed = time.time() - start

    result["run_metadata"] = {
        "run_number": run_number,
        "agent_category": category,
        "model_tier": model_tier,
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    result["costs_config"] = costs
    result["api_usage"] = client.get_usage_summary()

    return result, client


# =============================================================================
# Metrics
# =============================================================================
def compute_ovar(orders, demands):
    """Order Variance Amplification Ratio."""
    vo = np.var(orders)
    vd = np.var(demands)
    return float(vo / vd) if vd > 0 else 0.0


def compute_tier_metrics(tier_data, holding_cost=100, backlog_cost=1000):
    orders = tier_data["orders_placed"]
    demands = tier_data["incoming_demands"]
    inventory = tier_data["inventory_levels"]
    stockouts = tier_data.get("stockout_periods", tier_data.get("stockout_weeks", []))

    # Financial impact from period records
    records = tier_data.get("period_records", [])
    total_holding = sum(r.get("inventory_after", 0) * holding_cost for r in records)
    total_backlog = sum(r.get("backlog", 0) * backlog_cost for r in records)

    # Clamp event tracking
    clamp_count = sum(1 for r in records if r.get("was_clamped", False))

    return {
        "ovar": compute_ovar(orders, demands),
        "peak_overshoot": float(max(orders) / max(max(demands), 1)) if orders else 0,
        "excess_inventory": int(sum(max(0, i - d) for i, d in zip(inventory, demands))),
        "stockout_count": len(stockouts),
        "clamp_count": clamp_count,
        "mean_order": float(np.mean(orders)),
        "std_order": float(np.std(orders)),
        "mean_demand": float(np.mean(demands)),
        "std_demand": float(np.std(demands)),
        "max_order": int(max(orders)) if orders else 0,
        "max_demand": int(max(demands)) if demands else 0,
        "total_ordered": int(sum(orders)),
        "total_demand": int(sum(demands)),
        "holding_cost_inr": total_holding,
        "backlog_cost_inr": total_backlog,
        "total_cost_inr": total_holding + total_backlog,
    }


def compute_run_metrics(result, holding_cost=100, backlog_cost=1000):
    metrics = {}
    for tier in ["oem", "ancillary", "ancillary_supplier"]:
        metrics[tier] = compute_tier_metrics(
            result["tiers"][tier], holding_cost, backlog_cost
        )

    metrics["cascade"] = {
        "ovar_oem": metrics["oem"]["ovar"],
        "ovar_ancillary": metrics["ancillary"]["ovar"],
        "ovar_ancillary_supplier": metrics["ancillary_supplier"]["ovar"],
        "total_stockouts": sum(metrics[t]["stockout_count"] for t in ["oem", "ancillary", "ancillary_supplier"]),
        "total_excess_inventory": sum(metrics[t]["excess_inventory"] for t in ["oem", "ancillary", "ancillary_supplier"]),
        "total_cost_inr": sum(metrics[t]["total_cost_inr"] for t in ["oem", "ancillary", "ancillary_supplier"]),
        "total_holding_inr": sum(metrics[t]["holding_cost_inr"] for t in ["oem", "ancillary", "ancillary_supplier"]),
        "total_backlog_inr": sum(metrics[t]["backlog_cost_inr"] for t in ["oem", "ancillary", "ancillary_supplier"]),
    }
    return metrics


def aggregate_metrics(metrics_list):
    """Mean/std across runs."""
    if not metrics_list:
        return {}
    agg = {}
    for tier in ["oem", "ancillary", "ancillary_supplier"]:
        agg[tier] = {}
        for key in ["ovar", "peak_overshoot", "excess_inventory", "stockout_count",
                     "clamp_count", "mean_order", "std_order", "max_order", "total_ordered",
                     "holding_cost_inr", "backlog_cost_inr", "total_cost_inr"]:
            vals = [m[tier][key] for m in metrics_list if tier in m and key in m[tier]]
            if vals:
                agg[tier][key] = {
                    "mean": float(np.mean(vals)),
                    "std": float(np.std(vals)),
                    "min": float(np.min(vals)),
                    "max": float(np.max(vals)),
                    "per_run": [float(v) for v in vals],
                }
    return agg


# =============================================================================
# Visualization
# =============================================================================
TIER_LABELS = {
    "oem": "OEM (Tatva Motors)",
    "ancillary": "Lighting Mfr",
    "ancillary_supplier": "LED/Component Supplier",
}


def plot_cascade(result, title, path):
    """Order cascade chart."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    consumer = result["consumer_demand"]
    time_unit = result.get("metadata", {}).get("time_unit", "month")
    periods = list(range(1, len(consumer) + 1))

    fig, ax = plt.subplots(figsize=(16, 7))
    ax.plot(periods, consumer, color="#6b7280", linewidth=1.5,
            label="Demand (Dispatches)", alpha=0.7, linestyle="--")
    ax.plot(periods, result["tiers"]["oem"]["orders_placed"],
            color="#2563eb", linewidth=1.2, label=TIER_LABELS["oem"], alpha=0.85)
    ax.plot(periods, result["tiers"]["ancillary"]["orders_placed"],
            color="#d97706", linewidth=1.2, label=TIER_LABELS["ancillary"], alpha=0.85)
    ax.plot(periods, result["tiers"]["ancillary_supplier"]["orders_placed"],
            color="#dc2626", linewidth=1.2, label=TIER_LABELS["ancillary_supplier"], alpha=0.85)

    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel(time_unit.title(), fontsize=11)
    ax.set_ylabel("Order Quantity (units)", fontsize=11)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_comparison(blind_result, context_result, model, path):
    """Side-by-side cascade: Blind vs Context."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 7), sharey=True)

    for ax, result, label in [
        (ax1, blind_result, f"Blind ({model})"),
        (ax2, context_result, f"Context ({model})"),
    ]:
        consumer = result["consumer_demand"]
        time_unit = result.get("metadata", {}).get("time_unit", "month")
        periods = list(range(1, len(consumer) + 1))
        ax.plot(periods, consumer, color="#6b7280", linewidth=1.5,
                label="Demand", alpha=0.7, linestyle="--")
        ax.plot(periods, result["tiers"]["oem"]["orders_placed"],
                color="#2563eb", linewidth=1.2, label=TIER_LABELS["oem"], alpha=0.85)
        ax.plot(periods, result["tiers"]["ancillary"]["orders_placed"],
                color="#d97706", linewidth=1.2, label=TIER_LABELS["ancillary"], alpha=0.85)
        ax.plot(periods, result["tiers"]["ancillary_supplier"]["orders_placed"],
                color="#dc2626", linewidth=1.2, label=TIER_LABELS["ancillary_supplier"], alpha=0.85)
        ax.set_title(label, fontsize=12, fontweight="bold")
        ax.set_xlabel(time_unit.title())
        ax.set_ylabel("Units")
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

    plt.suptitle(f"Bullwhip: Blind vs Context — {model}",
                 fontsize=15, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_ovar_bars(blind_agg, context_agg, model, path):
    """OVAR bar chart."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    tiers = ["oem", "ancillary", "ancillary_supplier"]
    labels = [TIER_LABELS[t] for t in tiers]

    b_vals = [blind_agg[t]["ovar"]["mean"] for t in tiers]
    c_vals = [context_agg[t]["ovar"]["mean"] for t in tiers]
    b_err = [blind_agg[t]["ovar"]["std"] for t in tiers]
    c_err = [context_agg[t]["ovar"]["std"] for t in tiers]

    x = np.arange(len(tiers))
    w = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - w/2, b_vals, w, yerr=b_err, label="Blind",
           color="#ef4444", alpha=0.8, capsize=4)
    ax.bar(x + w/2, c_vals, w, yerr=c_err, label="Context",
           color="#22c55e", alpha=0.8, capsize=4)
    ax.axhline(y=1.0, color="#94a3b8", linestyle="--", alpha=0.7,
               label="No Amplification")
    ax.set_title(f"OVAR — {model}", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("OVAR (higher = worse)")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def plot_cost_bars(all_agg, path):
    """Total cost bar chart across all configs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    configs = sorted(all_agg.keys())
    if not configs:
        return

    tiers = ["oem", "ancillary", "ancillary_supplier"]
    holding_vals = []
    backlog_vals = []
    labels = []

    for ck in configs:
        agg = all_agg[ck]
        h = sum(agg[t].get("holding_cost_inr", {}).get("mean", 0) for t in tiers)
        b = sum(agg[t].get("backlog_cost_inr", {}).get("mean", 0) for t in tiers)
        holding_vals.append(h / 1e6)  # Convert to millions
        backlog_vals.append(b / 1e6)
        labels.append(ck.replace("_", "\n"))

    x = np.arange(len(configs))
    w = 0.5

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x, holding_vals, w, label="Holding Cost", color="#3b82f6", alpha=0.8)
    ax.bar(x, backlog_vals, w, bottom=holding_vals, label="Backlog Cost",
           color="#ef4444", alpha=0.8)
    ax.set_title("Total Simulation Cost by Configuration", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Cost (₹ millions)")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


# =============================================================================
# Pattern scoring (context agents only)
# =============================================================================
PATTERN_KEYWORDS = {
    "navratri_diwali": (["navratri", "diwali", "deepavali", "festival of lights", "festive season"], 3),
    "monsoon": (["monsoon", "rainy", "rain", "monsoon dip"], 2),
    "wedding": (["wedding", "marriage", "shaadi"], 2),
    "fy_end_march": (["march", "financial year", "year-end", "fy end", "fiscal", "depreciation"], 2),
    "sankranti_pongal": (["sankranti", "pongal", "makar", "harvest"], 1),
    "promotional": (["promo", "promotion", "launch", "new model", "discount", "offer", "clearance"], 2),
    "seasonal": (["seasonal", "cyclical", "annual", "recurring"], 1),
    "growth": (["growth", "trend", "increasing", "upward"], 1),
}


def score_patterns(decisions):
    """Score pattern detection from context agent decisions."""
    all_analyses = " ".join(
        d.get("pattern_analysis", "") or "" for d in decisions
    ).lower()

    if not all_analyses.strip():
        return {}

    results = {}
    total = 0
    max_score = sum(w for _, w in PATTERN_KEYWORDS.values())

    for name, (keywords, weight) in PATTERN_KEYWORDS.items():
        found = [k for k in keywords if k in all_analyses]
        detected = len(found) > 0
        if detected:
            total += weight
        results[name] = {"detected": detected, "keywords_matched": found, "weight": weight}

    results["_summary"] = {
        "score": total,
        "max_score": max_score,
        "detection_rate": round(total / max_score, 2) if max_score > 0 else 0,
    }
    return results


# =============================================================================
# Reasoning audit (o1 blind vs context)
# =============================================================================
def reasoning_audit(all_results):
    """Compare reasoning quality between blind and context for reasoning model."""
    bk = "blind_reasoning"
    ck = "context_reasoning"

    if bk not in all_results or ck not in all_results:
        return

    print(f"\n{'='*55}")
    print("REASONING AUDIT (o1: Blind vs Context)")
    print(f"{'='*55}")

    for tier in ["oem", "ancillary", "ancillary_supplier"]:
        print(f"\n  {TIER_LABELS.get(tier, tier)}:")

        # Sample from first run, periods 1, 6, 12 (early, mid, late)
        blind_run = all_results[bk][0]
        context_run = all_results[ck][0]

        b_decisions = blind_run["tiers"][tier]["decisions"]
        c_decisions = context_run["tiers"][tier]["decisions"]

        sample_periods = [0, 5, 11]  # 0-indexed
        for idx in sample_periods:
            if idx >= len(b_decisions) or idx >= len(c_decisions):
                continue

            b_dec = b_decisions[idx]
            c_dec = c_decisions[idx]
            period = b_dec.get("period", idx + 1)

            print(f"\n    Period {period}:")
            print(f"      Blind  → order={b_dec.get('order_quantity', '?'):,}  "
                  f"clamped={b_dec.get('was_clamped', '?')}")
            b_reasoning = b_dec.get("reasoning", "")
            if b_reasoning:
                # Truncate to 120 chars
                print(f"               \"{b_reasoning[:120]}{'...' if len(b_reasoning) > 120 else ''}\"")

            print(f"      Context → order={c_dec.get('order_quantity', '?'):,}  "
                  f"clamped={c_dec.get('was_clamped', '?')}")
            c_reasoning = c_dec.get("reasoning", "")
            if c_reasoning:
                print(f"               \"{c_reasoning[:120]}{'...' if len(c_reasoning) > 120 else ''}\"")

            c_pattern = c_dec.get("pattern_analysis", "")
            if c_pattern:
                print(f"               patterns: \"{c_pattern[:120]}{'...' if len(c_pattern) > 120 else ''}\"")

    # Summary: count how often blind vs context was clamped
    print(f"\n  Clamp summary (reasoning model):")
    for tier in ["oem", "ancillary", "ancillary_supplier"]:
        b_clamps = sum(
            1 for run in all_results[bk]
            for d in run["tiers"][tier]["decisions"]
            if d.get("was_clamped", False)
        )
        c_clamps = sum(
            1 for run in all_results[ck]
            for d in run["tiers"][tier]["decisions"]
            if d.get("was_clamped", False)
        )
        b_total = sum(len(run["tiers"][tier]["decisions"]) for run in all_results[bk])
        c_total = sum(len(run["tiers"][tier]["decisions"]) for run in all_results[ck])
        print(f"    {TIER_LABELS.get(tier, tier):>25}: "
              f"Blind={b_clamps}/{b_total}  Context={c_clamps}/{c_total}")


# =============================================================================
# Analysis pipeline
# =============================================================================
def analyze_all():
    """Analyze all raw results."""
    if not RAW_DIR.exists():
        print(f"No results in {RAW_DIR}")
        return

    os.makedirs(AGG_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    # Discover configs
    config_keys = set()
    for fn in sorted(os.listdir(RAW_DIR)):
        if fn.endswith(".json"):
            parts = fn.rsplit("_run", 1)
            if parts:
                config_keys.add(parts[0])

    print(f"Found: {sorted(config_keys)}\n")

    all_agg = {}
    all_results = {}
    skipped_files = []
    required_tiers = {"oem", "ancillary", "ancillary_supplier"}

    for ck in sorted(config_keys):
        runs = []
        for fn in sorted(os.listdir(RAW_DIR)):
            if fn.startswith(ck + "_run") and fn.endswith(".json"):
                with open(RAW_DIR / fn) as f:
                    data = json.load(f)
                    if "error" in data:
                        skipped_files.append((fn, "error payload"))
                        continue

                    tiers = data.get("tiers", {})
                    if not required_tiers.issubset(set(tiers.keys())):
                        missing = sorted(required_tiers - set(tiers.keys()))
                        skipped_files.append(
                            (fn, f"incompatible schema (missing tiers: {', '.join(missing)})")
                        )
                        continue

                    runs.append(data)

        if not runs:
            continue

        all_results[ck] = runs
        metrics_list = [
            compute_run_metrics(
                r,
                r.get("costs_config", {}).get("holding_per_unit", 100),
                r.get("costs_config", {}).get("backlog_per_unit", 1000),
            )
            for r in runs
        ]
        agg = aggregate_metrics(metrics_list)
        all_agg[ck] = agg

        with open(AGG_DIR / f"{ck}_aggregated.json", "w") as f:
            json.dump(agg, f, indent=2)

        print(f"{ck}: {len(runs)} runs")
        for tier in ["oem", "ancillary", "ancillary_supplier"]:
            ovar = agg[tier].get("ovar", {})
            cost = agg[tier].get("total_cost_inr", {})
            print(f"  {TIER_LABELS.get(tier, tier):>25}: "
                  f"OVAR = {ovar.get('mean', 0):.3f} +/- {ovar.get('std', 0):.3f}  "
                  f"Cost = ₹{cost.get('mean', 0):,.0f}")

        # Cascade chart (first run)
        plot_cascade(
            runs[0],
            f"Cascade — {ck.replace('_', ' ').title()}",
            str(FIGURES_DIR / f"cascade_{ck}.png"),
        )

        # Pattern scoring for context
        if ck.startswith("context_"):
            for run in runs:
                for tier in ["oem", "ancillary", "ancillary_supplier"]:
                    decisions = run["tiers"][tier]["decisions"]
                    scores = score_patterns(decisions)
                    if scores:
                        summary = scores.get("_summary", {})
                        print(f"  {TIER_LABELS.get(tier, tier):>25} patterns: "
                              f"{summary.get('score', 0)}/{summary.get('max_score', 0)}")
                break  # Score first run only for display

    # =========================================================================
    # Blind vs Context comparison
    # =========================================================================
    models = set()
    for ck in config_keys:
        parts = ck.split("_", 1)
        if len(parts) == 2:
            models.add(parts[1])

    print(f"\n{'='*55}")
    print("BLIND vs CONTEXT")
    print(f"{'='*55}")

    for model in sorted(models):
        bk = f"blind_{model}"
        ck = f"context_{model}"

        if bk in all_agg and ck in all_agg:
            print(f"\n  {model}:")
            for tier in ["oem", "ancillary", "ancillary_supplier"]:
                b_ovar = all_agg[bk][tier]["ovar"]["mean"]
                c_ovar = all_agg[ck][tier]["ovar"]["mean"]
                reduction = ((b_ovar - c_ovar) / max(b_ovar, 0.001)) * 100
                print(f"    {TIER_LABELS.get(tier, tier):>25}: "
                      f"Blind={b_ovar:.3f}  Context={c_ovar:.3f}  D={reduction:+.1f}%")

            # Comparison chart
            if bk in all_results and ck in all_results:
                plot_comparison(
                    all_results[bk][0], all_results[ck][0], model,
                    str(FIGURES_DIR / f"comparison_{model}.png"),
                )

            # OVAR bar chart
            plot_ovar_bars(
                all_agg[bk], all_agg[ck], model,
                str(FIGURES_DIR / f"ovar_{model}.png"),
            )

    # =========================================================================
    # Financial impact summary
    # =========================================================================
    print(f"\n{'='*55}")
    print("FINANCIAL IMPACT (INR)")
    print(f"{'='*55}")

    tiers = ["oem", "ancillary", "ancillary_supplier"]
    for ck in sorted(all_agg.keys()):
        agg = all_agg[ck]
        total_h = sum(agg[t].get("holding_cost_inr", {}).get("mean", 0) for t in tiers)
        total_b = sum(agg[t].get("backlog_cost_inr", {}).get("mean", 0) for t in tiers)
        total = total_h + total_b
        print(f"  {ck:>25}: Holding=₹{total_h:>12,.0f}  "
              f"Backlog=₹{total_b:>12,.0f}  Total=₹{total:>12,.0f}")

    # Cost bar chart
    if len(all_agg) > 1:
        plot_cost_bars(all_agg, str(FIGURES_DIR / "cost_comparison.png"))

    # =========================================================================
    # Stability check (cross-run variance)
    # =========================================================================
    if any(len(runs) > 1 for runs in all_results.values()):
        print(f"\n{'='*55}")
        print("STABILITY CHECK (cross-run variance)")
        print(f"{'='*55}")

        for ck in sorted(all_agg.keys()):
            agg = all_agg[ck]
            num_runs = len(all_results.get(ck, []))
            if num_runs < 2:
                continue
            print(f"\n  {ck} ({num_runs} runs):")
            for tier in ["oem", "ancillary", "ancillary_supplier"]:
                ovar_data = agg[tier].get("ovar", {})
                per_run = ovar_data.get("per_run", [])
                cv = (ovar_data["std"] / ovar_data["mean"] * 100) if ovar_data.get("mean", 0) > 0 else 0
                run_str = ", ".join(f"{v:.2f}" for v in per_run)
                print(f"    {TIER_LABELS.get(tier, tier):>25}: "
                      f"OVAR=[{run_str}]  CV={cv:.1f}%")

    # =========================================================================
    # Reasoning audit
    # =========================================================================
    reasoning_audit(all_results)

    if skipped_files:
        print(f"\nSkipped {len(skipped_files)} file(s) with incompatible schema:")
        for fn, reason in skipped_files:
            print(f"  - {fn}: {reason}")

    print(f"\nFigures saved to {FIGURES_DIR}/")


# =============================================================================
# Main
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Bullwhip Experiment Runner v3")
    parser.add_argument("--config", type=str, help="Config YAML path")
    parser.add_argument("--category", choices=["blind", "context"])
    parser.add_argument("--model", choices=["lightweight", "reasoning"])
    parser.add_argument("--runs", type=int, help="Number of runs")
    parser.add_argument("--all", action="store_true", help="Run ALL configurations")
    parser.add_argument("--analyze", action="store_true", help="Analyze only (no API calls)")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    # Create directories
    for d in [RESULTS_DIR, RAW_DIR, AGG_DIR, FIGURES_DIR]:
        os.makedirs(d, exist_ok=True)

    setup_logging(args.verbose)

    if args.analyze:
        analyze_all()
        return

    # Load config
    config = load_config(args.config)
    exp = config.get("experiment", {})
    time_unit = exp.get("time_unit", "month")

    # Load demand data
    data_path = config.get("paths", {}).get("demand_data") or str(DATA_PATH)
    if not os.path.exists(data_path):
        data_path = str(BASE_DIR / data_path)
    demand_data = SupplyChain.load_demand_data(data_path)
    print(f"Loaded {len(demand_data)} {time_unit}s of demand data from {data_path}")

    costs = config.get("costs", {})
    run_holding = costs.get("holding_per_unit", 100)
    run_backlog = costs.get("backlog_per_unit", 1000)

    if args.all:
        categories = ["blind", "context"]
        model_tiers = list(config["models"].keys())
        runs_per = exp.get("runs_per_config", 3)
        total = len(categories) * len(model_tiers) * runs_per

        print(f"\nFULL EXPERIMENT: {len(categories)} categories x "
              f"{len(model_tiers)} models x {runs_per} runs = {total} total\n")

        all_logs = []
        run_count = 0

        for cat in categories:
            for model in model_tiers:
                ck = f"{cat}_{model}"
                print(f"\n{'='*55}")
                print(f"  {ck}")
                print(f"{'='*55}")

                for r in range(1, runs_per + 1):
                    run_count += 1
                    print(f"  Run {r}/{runs_per} ({run_count}/{total})")

                    try:
                        result, client = execute_run(
                            config, cat, model, r, demand_data
                        )
                        path = RAW_DIR / f"{ck}_run{r:02d}.json"
                        with open(path, "w") as f:
                            json.dump(result, f, indent=2)
                        print(f"    Saved: {path}")

                        m = compute_run_metrics(result, run_holding, run_backlog)
                        print(f"    OVAR: OEM={m['oem']['ovar']:.2f} "
                              f"Anc={m['ancillary']['ovar']:.2f} "
                              f"Sup={m['ancillary_supplier']['ovar']:.2f}  "
                              f"Cost=₹{m['cascade']['total_cost_inr']:,.0f}")

                        all_logs.extend([vars(l) if hasattr(l, '__dict__') else l
                                        for l in client.call_log])

                    except Exception as e:
                        logging.error(f"    FAILED: {e}")

        # Save all API logs
        with open(RESULTS_DIR / "api_logs.json", "w") as f:
            json.dump([{k: str(v) for k, v in l.items()} if isinstance(l, dict) else str(l)
                       for l in all_logs], f, indent=2)

    elif args.category and args.model:
        runs = args.runs or exp.get("runs_per_config", 3)
        ck = f"{args.category}_{args.model}"

        print(f"\nSINGLE CONFIG: {ck} x {runs} runs\n")

        for r in range(1, runs + 1):
            print(f"Run {r}/{runs}")
            try:
                result, client = execute_run(
                    config, args.category, args.model, r, demand_data
                )
                path = RAW_DIR / f"{ck}_run{r:02d}.json"
                with open(path, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"  Saved: {path}")

                m = compute_run_metrics(result, run_holding, run_backlog)
                print(f"  OVAR: OEM={m['oem']['ovar']:.2f} "
                      f"Anc={m['ancillary']['ovar']:.2f} "
                      f"Sup={m['ancillary_supplier']['ovar']:.2f}  "
                      f"Cost=₹{m['cascade']['total_cost_inr']:,.0f}")

                client.export_logs(str(RESULTS_DIR / f"api_logs_{ck}_run{r:02d}.json"))

                usage = client.get_usage_summary()
                print(f"  Tokens: {usage['total_tokens']:,} | "
                      f"Calls: {usage['successful']}/{usage['total_calls']} | "
                      f"Avg latency: {usage['avg_latency_ms']:.0f}ms")

            except Exception as e:
                logging.error(f"  FAILED: {e}")

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python run_experiment.py --category blind --model lightweight --runs 1")
        print("  python run_experiment.py --all")
        print("  python run_experiment.py --analyze")
        return

    # Auto-analyze after experiment
    print(f"\n{'='*55}")
    print("ANALYSIS")
    print(f"{'='*55}\n")
    analyze_all()


if __name__ == "__main__":
    main()
