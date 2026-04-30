"""
Metrics for V5 ControlArch.

Extends V4 metrics with five new service/control metrics that reveal the
OVAR-service trade-off — the primary V5 analysis lens:

  compute_service_level(df)        mean fill rate per (run_id, tier)
  compute_avg_backlog(df)          mean backlog magnitude
  compute_max_backlog(df)          maximum backlog (gate criterion)
  compute_avg_on_hand(df)          mean on-hand inventory (holding proxy)
  compute_order_adj_variance(df)   Var(order_t - order_{t-1}) — second-order bullwhip

V4 metrics preserved unchanged:
  OVAR, stockouts, pattern score, excess inventory, peak overshoot,
  intent compliance, intent accuracy, intent entropy, intent distribution.

V4 change: summarise_condition() now runs intent-specific metrics for
policy in {"intent", "oracle_intent", "causal_intent"} so oracle and
causal ablation conditions get the same diagnostics as LLM conditions.

Ground-truth intent schedule, EVENT_KEYWORDS, and all V4 metric logic
are copied verbatim from V4 and must not be altered without updating
the hypothesis verdicts and provenance stamps.
"""

import logging
import math
from collections import Counter

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TIERS = ["OEM", "Ancillary", "Component"]

_INTENT_POLICIES = {"intent", "oracle_intent", "causal_intent"}

# ---------------------------------------------------------------------------
# Seasonal event keywords — V4 unchanged
# ---------------------------------------------------------------------------

EVENT_KEYWORDS = {
    "Jan": ["sankranti", "makar", "harvest", "festival", "wedding"],
    "Feb": ["budget", "union budget", "fiscal", "tax", "wedding"],
    "Mar": ["fy", "financial year", "year end", "quarter", "fy-end"],
    "Apr": ["wedding", "summer", "akshaya tritiya"],
    "May": ["wedding", "summer"],
    "Jun": ["monsoon", "rain", "slow", "dip"],
    "Jul": ["monsoon", "rain", "slow", "dip"],
    "Aug": ["monsoon", "rain", "slow", "dip"],
    "Oct": ["navratri", "dasara", "dussehra", "festive", "festival"],
    "Nov": ["diwali", "deepavali", "festive", "festival"],
    "Dec": ["year end", "year-end", "discount", "christmas", "wedding"],
}

DIP_MONTHS = {"Jun", "Jul", "Aug"}

# ---------------------------------------------------------------------------
# Ground-truth intent schedule — 36 periods (V4 unchanged)
# ---------------------------------------------------------------------------

GROUND_TRUTH_INTENT: dict[int, str] = {
    # 2025 — baseline seasonal (no world events in periods 1-6)
    1:  "NEUTRAL",
    2:  "MODERATE_DECREASE",
    3:  "STRONG_INCREASE",
    4:  "MODERATE_DECREASE",
    5:  "NEUTRAL",
    6:  "MODERATE_DECREASE",
    7:  "STRONG_DECREASE",    # pandemic_shock ×0.55
    8:  "STRONG_DECREASE",
    9:  "STRONG_DECREASE",
    10: "STRONG_INCREASE",    # pandemic_surge ×1.35
    11: "STRONG_INCREASE",
    12: "MODERATE_INCREASE",  # pandemic_recovery ×1.10
    # 2026 — conflict periods 19-21
    13: "NEUTRAL",
    14: "MODERATE_DECREASE",
    15: "STRONG_INCREASE",
    16: "NEUTRAL",
    17: "NEUTRAL",
    18: "MODERATE_DECREASE",
    19: "MODERATE_DECREASE",  # conflict ×0.95
    20: "MODERATE_DECREASE",  # conflict ×0.90
    21: "NEUTRAL",            # conflict ×0.90
    22: "STRONG_INCREASE",
    23: "STRONG_INCREASE",
    24: "MODERATE_INCREASE",
    # 2027 — port disruption periods 28-30
    25: "NEUTRAL",
    26: "MODERATE_DECREASE",
    27: "STRONG_INCREASE",
    28: "NEUTRAL",            # port: demand unaffected
    29: "NEUTRAL",
    30: "MODERATE_DECREASE",
    31: "STRONG_DECREASE",
    32: "MODERATE_DECREASE",
    33: "NEUTRAL",
    34: "STRONG_INCREASE",
    35: "STRONG_INCREASE",
    36: "MODERATE_INCREASE",
}

_DIRECTION = {
    "STRONG_INCREASE":   "increase",
    "MODERATE_INCREASE": "increase",
    "NEUTRAL":           "neutral",
    "MODERATE_DECREASE": "decrease",
    "STRONG_DECREASE":   "decrease",
}


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _active_periods(df: pd.DataFrame) -> pd.DataFrame:
    max_period = df["period"].max()
    return df[df["period"] < max_period].copy()


def _chain_mean(per_tier_df: pd.DataFrame, metric_col: str) -> pd.Series:
    """Mean of metric_col across tiers, per run_id."""
    return per_tier_df.groupby("run_id")[metric_col].mean().rename(f"chain_{metric_col}")


# ---------------------------------------------------------------------------
# OVAR — primary metric (V4 unchanged)
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
# Stockouts — secondary metric (V4 unchanged)
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
# Supporting metrics — V4 unchanged
# ---------------------------------------------------------------------------

def compute_excess_inventory(df: pd.DataFrame) -> pd.DataFrame:
    active = _active_periods(df)
    surplus = active[active["backlog"] == 0]
    return (
        surplus.groupby(["run_id", "tier"])["on_hand_before_order"]
        .sum()
        .reset_index(name="excess_inventory")
    )


def compute_peak_overshoot(df: pd.DataFrame) -> pd.DataFrame:
    active = _active_periods(df)
    rows = []
    for (run_id, tier), grp in active.groupby(["run_id", "tier"]):
        max_order  = grp["order_placed"].max()
        max_demand = grp["demand_received"].max()
        peak = max_order / max_demand if max_demand > 0 else np.nan
        rows.append({"run_id": run_id, "tier": tier, "peak_overshoot": peak})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pattern score — V4 unchanged
# ---------------------------------------------------------------------------

def _extract_month_abbr(calendar_month: str) -> str:
    return calendar_month.strip()[:3]


def _keyword_score(rationale: str, month_abbr: str) -> float:
    keywords = EVENT_KEYWORDS.get(month_abbr, [])
    if not keywords:
        return 0.0
    text = rationale.lower()
    return 1.0 if any(kw in text for kw in keywords) else 0.0


def _elevation_score(order: float, tier_baseline: float, month_abbr: str) -> float:
    if tier_baseline == 0:
        return 0.0
    ratio = order / tier_baseline
    if month_abbr in DIP_MONTHS:
        return 1.0 if ratio < 0.90 else 0.0
    else:
        return 1.0 if ratio > 1.10 else 0.0


def compute_pattern_score(df: pd.DataFrame) -> pd.DataFrame:
    if df["policy"].iloc[0] not in ("llm", "intent"):
        return pd.DataFrame(columns=["run_id", "tier", "keyword_score", "elevation_score", "pattern_score"])

    event_months = set(EVENT_KEYWORDS.keys())
    active = _active_periods(df).copy()
    active["month_abbr"] = active["calendar_month"].apply(_extract_month_abbr)

    baselines = (
        active.groupby(["run_id", "tier"])["order_placed"]
        .median()
        .rename("baseline")
        .reset_index()
    )
    active = active.merge(baselines, on=["run_id", "tier"])
    event_rows = active[active["month_abbr"].isin(event_months)].copy()

    rows = []
    for (run_id, tier), grp in event_rows.groupby(["run_id", "tier"]):
        ks = grp.apply(lambda r: _keyword_score(r["rationale"], r["month_abbr"]), axis=1).mean()
        es = grp.apply(lambda r: _elevation_score(r["order_placed"], r["baseline"], r["month_abbr"]), axis=1).mean()
        rows.append({"run_id": run_id, "tier": tier,
                     "keyword_score": ks, "elevation_score": es, "pattern_score": (ks + es) / 2})

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Intent compliance rate — V4 unchanged
# ---------------------------------------------------------------------------

def compute_intent_compliance(df: pd.DataFrame) -> pd.Series:
    if "intent_fallback" not in df.columns:
        return pd.Series(dtype=float)

    active  = _active_periods(df)
    intent_rows = active[active["policy"].isin(_INTENT_POLICIES)]
    if intent_rows.empty:
        return pd.Series(dtype=float)

    result = (
        intent_rows.groupby("run_id")["intent_fallback"]
        .apply(lambda s: 1.0 - s.mean())
    ).rename("intent_compliance")
    return result


# ---------------------------------------------------------------------------
# Intent accuracy — V4 unchanged
# ---------------------------------------------------------------------------

def compute_intent_accuracy(df: pd.DataFrame, world_events_on: bool = True) -> pd.DataFrame:
    if not world_events_on:
        logger.info("compute_intent_accuracy: skipped — world events off, no ground truth defined")
        return pd.DataFrame(columns=["run_id", "full_accuracy", "direction_accuracy", "event_periods_evaluated"])

    if "intent_class" not in df.columns:
        return pd.DataFrame(columns=["run_id", "full_accuracy", "direction_accuracy", "event_periods_evaluated"])

    active      = _active_periods(df)
    intent_rows = active[active["policy"].isin(_INTENT_POLICIES)].copy()
    if intent_rows.empty:
        return pd.DataFrame(columns=["run_id", "full_accuracy", "direction_accuracy", "event_periods_evaluated"])

    intent_rows = intent_rows[intent_rows["tier"] == "OEM"].copy()
    intent_rows["ground_truth"] = intent_rows["period"].map(GROUND_TRUTH_INTENT)

    event_rows = intent_rows[intent_rows["ground_truth"] != "NEUTRAL"].copy()

    rows = []
    for run_id, grp in event_rows.groupby("run_id"):
        n = len(grp)
        if n == 0:
            continue
        full_acc = (grp["intent_class"] == grp["ground_truth"]).mean()
        dir_acc  = grp.apply(
            lambda r: _DIRECTION.get(r["intent_class"], "") == _DIRECTION.get(r["ground_truth"], ""),
            axis=1,
        ).mean()
        rows.append({"run_id": run_id, "full_accuracy": full_acc,
                     "direction_accuracy": dir_acc, "event_periods_evaluated": n})

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Intent entropy — V4 unchanged
# ---------------------------------------------------------------------------

def compute_intent_entropy(df: pd.DataFrame) -> pd.Series:
    if "intent_class" not in df.columns:
        return pd.Series(dtype=float)

    active      = _active_periods(df)
    intent_rows = active[active["policy"].isin(_INTENT_POLICIES) & (active["tier"] == "OEM")].copy()
    if intent_rows.empty:
        return pd.Series(dtype=float)

    def _entropy(series: pd.Series) -> float:
        counts = Counter(series.dropna())
        total  = sum(counts.values())
        if total == 0:
            return 0.0
        return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)

    return (
        intent_rows.groupby("run_id")["intent_class"]
        .apply(_entropy)
        .rename("intent_entropy")
    )


# ---------------------------------------------------------------------------
# Intent distribution — V4 unchanged
# ---------------------------------------------------------------------------

def compute_intent_distribution(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    if "intent_class" not in df.columns:
        return {}

    active      = _active_periods(df)
    intent_rows = active[active["policy"].isin(_INTENT_POLICIES) & (active["tier"] == "OEM")]
    result = {}
    for run_id, grp in intent_rows.groupby("run_id"):
        result[run_id] = dict(Counter(grp["intent_class"].dropna()))
    return result


# ---------------------------------------------------------------------------
# V5 new metrics — service level, backlog, on-hand, order adjustment variance
# ---------------------------------------------------------------------------

def compute_service_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per (run_id, tier): mean(fulfilled / (fulfilled + shortfall)).

    Denominates against total obligation (current demand + carried backlog),
    so accumulated backlog from world events makes this metric structurally low.
    Treat as a diagnostic for backlog pressure, not as the gate metric.
    Use demand_fill_rate for the Phase 2 gate.
    """
    active = _active_periods(df)
    rows = []
    for (run_id, tier), grp in active.groupby(["run_id", "tier"]):
        total = grp["fulfilled"] + grp["shortfall"]
        sl = np.where(total > 0, grp["fulfilled"] / total, 1.0)
        rows.append({"run_id": run_id, "tier": tier, "service_level": float(sl.mean())})
    return pd.DataFrame(rows)


def compute_demand_fill_rate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per (run_id, tier): mean(min(1.0, fulfilled / demand_received)).

    Measures what fraction of current-period demand was fulfilled, capped at 1.0
    (clearing old backlog doesn't count as extra credit). Periods with zero demand
    contribute 1.0. This is the recommended Phase 2 gate metric — achievable values
    are in a sensible range regardless of accumulated backlog.
    """
    active = _active_periods(df)
    rows = []
    for (run_id, tier), grp in active.groupby(["run_id", "tier"]):
        dr   = grp["demand_received"].values.astype(float)
        fl   = grp["fulfilled"].values.astype(float)
        rate = np.where(dr > 0, np.minimum(1.0, fl / dr), 1.0)
        rows.append({"run_id": run_id, "tier": tier, "demand_fill_rate": float(rate.mean())})
    return pd.DataFrame(rows)


def compute_avg_backlog(df: pd.DataFrame) -> pd.DataFrame:
    """Mean backlog over active periods per (run_id, tier)."""
    active = _active_periods(df)
    return (
        active.groupby(["run_id", "tier"])["backlog"]
        .mean()
        .reset_index(name="avg_backlog")
    )


def compute_max_backlog(df: pd.DataFrame) -> pd.DataFrame:
    """Max backlog over active periods per (run_id, tier)."""
    active = _active_periods(df)
    return (
        active.groupby(["run_id", "tier"])["backlog"]
        .max()
        .reset_index(name="max_backlog")
    )


def compute_avg_on_hand(df: pd.DataFrame) -> pd.DataFrame:
    """Mean on_hand_before_order over active periods per (run_id, tier)."""
    active = _active_periods(df)
    return (
        active.groupby(["run_id", "tier"])["on_hand_before_order"]
        .mean()
        .reset_index(name="avg_on_hand")
    )


def compute_order_adj_variance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Second-order bullwhip signal: Var(order_t - order_{t-1}, ddof=1) per (run_id, tier).

    Periods are sorted by period number before differencing. Runs with fewer
    than 2 active periods return NaN (edge case; should not occur in 36-period sims).
    """
    active = _active_periods(df)
    rows = []
    for (run_id, tier), grp in active.groupby(["run_id", "tier"]):
        orders = grp.sort_values("period")["order_placed"]
        diffs  = orders.diff().dropna()
        oav    = float(diffs.var(ddof=1)) if len(diffs) >= 1 else np.nan
        rows.append({"run_id": run_id, "tier": tier, "order_adj_variance": oav})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Condition summary
# ---------------------------------------------------------------------------

def summarise_condition(df: pd.DataFrame, condition_label: str) -> dict:
    """Compute all metrics for one condition. Called once per condition_label."""
    ovar_df           = compute_ovar(df)
    chain_ovar        = compute_chain_ovar(ovar_df)
    _, chain_stockouts = compute_stockouts(df)
    pattern_df        = compute_pattern_score(df)

    all_run_ids = df["run_id"].unique()

    def ms(series: pd.Series) -> dict:
        s = series.reindex(all_run_ids)
        return {"mean": float(s.mean()), "std": float(s.std(ddof=1))}

    if pattern_df.empty:
        chain_pattern = pd.Series(np.nan, index=all_run_ids, name="pattern_score")
    else:
        chain_pattern = (
            pattern_df.groupby("run_id")["pattern_score"]
            .mean()
            .reindex(all_run_ids)
        )

    tier_ovar = {}
    for tier in TIERS:
        tier_series = (
            ovar_df[ovar_df["tier"] == tier]
            .set_index("run_id")["ovar"]
            .reindex(all_run_ids)
        )
        tier_ovar[tier] = ms(tier_series)

    # V5 new metrics
    sl_df      = compute_service_level(df)
    dfr_df     = compute_demand_fill_rate(df)
    ab_df      = compute_avg_backlog(df)
    mb_df      = compute_max_backlog(df)
    oh_df      = compute_avg_on_hand(df)
    oav_df     = compute_order_adj_variance(df)

    chain_sl   = _chain_mean(sl_df,  "service_level")
    chain_dfr  = _chain_mean(dfr_df, "demand_fill_rate")
    chain_ab   = _chain_mean(ab_df,  "avg_backlog")
    chain_mb   = _chain_mean(mb_df,  "max_backlog")
    chain_oh   = _chain_mean(oh_df,  "avg_on_hand")
    chain_oav  = _chain_mean(oav_df, "order_adj_variance")

    tier_sl = {}
    tier_dfr = {}
    for tier in TIERS:
        t_series = (
            sl_df[sl_df["tier"] == tier]
            .set_index("run_id")["service_level"]
            .reindex(all_run_ids)
        )
        tier_sl[tier] = ms(t_series)
        t_dfr = (
            dfr_df[dfr_df["tier"] == tier]
            .set_index("run_id")["demand_fill_rate"]
            .reindex(all_run_ids)
        )
        tier_dfr[tier] = ms(t_dfr)

    summary = {
        "condition":              condition_label,
        "n_runs":                 int(df["run_id"].nunique()),
        "chain_ovar":             ms(chain_ovar),
        "tier_ovar":              tier_ovar,
        "chain_stockouts":        ms(chain_stockouts.set_index("run_id")["chain_stockout_count"]),
        "pattern_score":          ms(chain_pattern),
        # V5 service / control metrics
        # demand_fill_rate: gate metric (current-period demand only, capped at 1.0)
        # service_level: diagnostic (denominates against total obligation incl. carried backlog)
        "demand_fill_rate":       ms(chain_dfr.reindex(all_run_ids)),
        "tier_demand_fill_rate":  tier_dfr,
        "service_level":          ms(chain_sl.reindex(all_run_ids)),
        "tier_service_level":     tier_sl,
        "avg_backlog":            ms(chain_ab.reindex(all_run_ids)),
        "max_backlog":            ms(chain_mb.reindex(all_run_ids)),
        "avg_on_hand":            ms(chain_oh.reindex(all_run_ids)),
        "order_adj_variance":     ms(chain_oav.reindex(all_run_ids)),
    }

    # Intent-specific metrics — V4 gate updated to include oracle_intent and causal_intent
    policy_val = df["policy"].iloc[0] if len(df) > 0 else ""
    if policy_val in _INTENT_POLICIES:
        compliance = compute_intent_compliance(df)
        we_on = bool(df["world_event"].notna().any()) if "world_event" in df.columns else True
        accuracy_df = compute_intent_accuracy(df, world_events_on=we_on)
        entropy = compute_intent_entropy(df)

        summary["intent_compliance"] = ms(compliance.reindex(all_run_ids))

        if not accuracy_df.empty:
            acc_idx = accuracy_df.set_index("run_id")
            summary["intent_accuracy"] = {
                "full":      ms(acc_idx["full_accuracy"].reindex(all_run_ids)),
                "direction": ms(acc_idx["direction_accuracy"].reindex(all_run_ids)),
                "n_event_periods": int(acc_idx["event_periods_evaluated"].mean()) if len(acc_idx) > 0 else 0,
            }
        else:
            summary["intent_accuracy"] = None

        summary["intent_entropy"]      = ms(entropy.reindex(all_run_ids))
        summary["intent_distribution"] = compute_intent_distribution(df)

    return summary
