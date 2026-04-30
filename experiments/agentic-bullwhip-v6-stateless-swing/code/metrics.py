"""
Metrics — V6 StatelessSwing (25-month V3b demand series).

Standard metrics (all conditions):
  OVAR, stockouts, mean_on_hand

Alpha-specific metrics (policy=="adaptive_alpha" only):
  alpha_distribution, alpha_entropy, alpha_fallback_rate, alpha_mean
"""

import logging
import math
from collections import Counter

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TIERS = ["OEM", "Ancillary", "Component"]


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _active_periods(df: pd.DataFrame) -> pd.DataFrame:
    max_period = df["period"].max()
    return df[df["period"] < max_period].copy()


# ---------------------------------------------------------------------------
# OVAR
# ---------------------------------------------------------------------------

def compute_ovar(df: pd.DataFrame) -> pd.DataFrame:
    active = _active_periods(df)
    rows = []
    for (run_id, tier), grp in active.groupby(["run_id", "tier"]):
        var_orders = grp["order_placed"].var(ddof=1)
        var_demand = grp["demand_received"].var(ddof=1)
        ovar = var_orders / var_demand if var_demand > 0 else np.nan
        rows.append({"run_id": run_id, "tier": tier, "ovar": ovar})
    return pd.DataFrame(rows)


def compute_chain_ovar(ovar_df: pd.DataFrame) -> pd.Series:
    return ovar_df.groupby("run_id")["ovar"].mean().rename("chain_ovar")


# ---------------------------------------------------------------------------
# Stockouts
# ---------------------------------------------------------------------------

def compute_stockouts(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_run_ids = df["run_id"].unique()
    per_tier = (
        df[df["stockout"]]
        .groupby(["run_id", "tier"])
        .size()
        .reset_index(name="stockout_count")
    )
    chain = (
        df[df["stockout"]]
        .groupby("run_id")
        .size()
        .reindex(all_run_ids, fill_value=0)
        .reset_index(name="chain_stockout_count")
    )
    return per_tier, chain


# ---------------------------------------------------------------------------
# Supporting metrics
# ---------------------------------------------------------------------------

def compute_mean_inventory(df: pd.DataFrame) -> pd.DataFrame:
    active = _active_periods(df)
    return (
        active.groupby(["run_id", "tier"])["on_hand_before_order"]
        .mean()
        .reset_index(name="mean_on_hand")
    )


# ---------------------------------------------------------------------------
# Alpha-specific metrics
# ---------------------------------------------------------------------------

def compute_alpha_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-run alpha metrics at OEM tier (active periods only).

    Returns DataFrame: run_id, alpha_mean, alpha_entropy, alpha_fallback_rate,
                       alpha_distribution
    """
    active = _active_periods(df)
    alpha_rows = active[(active["policy"] == "adaptive_alpha") & (active["tier"] == "OEM")].copy()
    if alpha_rows.empty:
        return pd.DataFrame(columns=["run_id", "alpha_mean", "alpha_entropy",
                                     "alpha_fallback_rate", "alpha_distribution"])

    def _entropy(series: pd.Series) -> float:
        counts = Counter(series.dropna())
        total  = sum(counts.values())
        if total == 0:
            return 0.0
        return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)

    rows = []
    for run_id, grp in alpha_rows.groupby("run_id"):
        alphas = grp["alpha_chosen"].dropna()
        fb     = grp["alpha_fallback"].dropna()
        rows.append({
            "run_id":              run_id,
            "alpha_mean":          float(alphas.mean()) if len(alphas) > 0 else np.nan,
            "alpha_entropy":       _entropy(alphas),
            "alpha_fallback_rate": float(fb.mean()) if len(fb) > 0 else np.nan,
            "alpha_distribution":  dict(Counter(alphas.astype(str))),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Condition summary
# ---------------------------------------------------------------------------

def summarise_condition(df: pd.DataFrame, condition_label: str) -> dict:
    ovar_df            = compute_ovar(df)
    chain_ovar         = compute_chain_ovar(ovar_df)
    _, chain_stockouts = compute_stockouts(df)
    inv_df             = compute_mean_inventory(df)

    all_run_ids = df["run_id"].unique()

    def ms(series: pd.Series) -> dict:
        s = series.reindex(all_run_ids)
        return {"mean": float(s.mean()), "std": float(s.std(ddof=1))}

    tier_ovar = {}
    for tier in TIERS:
        tier_series = (
            ovar_df[ovar_df["tier"] == tier]
            .set_index("run_id")["ovar"]
            .reindex(all_run_ids)
        )
        tier_ovar[tier] = ms(tier_series)

    chain_mean_on_hand = (
        inv_df.groupby("run_id")["mean_on_hand"]
        .mean()
        .reindex(all_run_ids)
    )

    policy = df["policy"].iloc[0] if not df.empty else None

    result = {
        "condition":       condition_label,
        "policy":          policy,
        "n_runs":          int(df["run_id"].nunique()),
        "chain_ovar":      ms(chain_ovar),
        "tier_ovar":       tier_ovar,
        "chain_stockouts": ms(chain_stockouts.set_index("run_id")["chain_stockout_count"]),
        "mean_on_hand":    ms(chain_mean_on_hand),
    }

    if policy == "adaptive_alpha":
        alpha_df = compute_alpha_metrics(df)
        if not alpha_df.empty:
            ai = alpha_df.set_index("run_id")
            result["alpha_mean"]          = ms(ai["alpha_mean"].reindex(all_run_ids))
            result["alpha_entropy"]        = ms(ai["alpha_entropy"].reindex(all_run_ids))
            result["alpha_fallback_rate"]  = ms(ai["alpha_fallback_rate"].reindex(all_run_ids))
            result["alpha_distribution"]   = {
                str(rid): row for rid, row in
                alpha_df[["run_id", "alpha_distribution"]].set_index("run_id")["alpha_distribution"].items()
            }
        else:
            result["alpha_mean"]         = None
            result["alpha_entropy"]      = None
            result["alpha_fallback_rate"] = None
            result["alpha_distribution"] = {}

    return result
