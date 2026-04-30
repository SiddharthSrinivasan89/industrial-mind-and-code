"""
Metrics — V4 Intent Classifier (25-month V3b demand series).

Standard metrics (all conditions):
  OVAR, stockouts, mean_on_hand, pattern_score

Intent-specific metrics (policy=="intent" only):
  intent_compliance_rate, intent_accuracy, intent_direction_accuracy,
  intent_entropy, intent_distribution

Ground-truth intent schedule
-----------------------------
Derived from the 25-month V3b demand series (periods 1-24 active).
Deviation bands relative to 24-period mean (~38,446 units):
  STRONG_INCREASE   > +10%
  MODERATE_INCREASE  +3% to +10%
  NEUTRAL            -5% to +3%
  MODERATE_DECREASE  -5% to -10%
  STRONG_DECREASE   < -10%

Source: V4 IntentClassifier design doc §3.3.
"""

import logging
import math
from collections import Counter

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TIERS = ["OEM", "Ancillary", "Component"]

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
# Ground-truth intent schedule — 24 active ordering periods
# From V4 IntentClassifier design doc §3.3 (deviation-band classification)
# ---------------------------------------------------------------------------

GROUND_TRUTH_INTENT: dict[int, str] = {
    1:  "NEUTRAL",           # Jan 2025: 37,200  −3.2%
    2:  "MODERATE_DECREASE", # Feb 2025: 36,200  −5.8%
    3:  "STRONG_INCREASE",   # Mar 2025: 43,500  +13.1%  FY-end
    4:  "MODERATE_DECREASE", # Apr 2025: 36,200  −5.8%
    5:  "NEUTRAL",           # May 2025: 37,200  −3.2%
    6:  "STRONG_DECREASE",   # Jun 2025: 34,300  −10.8%  peak monsoon
    7:  "STRONG_DECREASE",   # Jul 2025: 33,700  −12.3%  peak monsoon
    8:  "MODERATE_DECREASE", # Aug 2025: 35,100  −8.7%   monsoon exit
    9:  "NEUTRAL",           # Sep 2025: 37,200  −3.2%
    10: "MODERATE_INCREASE", # Oct 2025: 40,400  +5.1%   Navratri/Dasara
    11: "MODERATE_INCREASE", # Nov 2025: 41,600  +8.2%   Diwali (deviation-band)
    12: "NEUTRAL",           # Dec 2025: 37,700  −1.9%
    13: "NEUTRAL",           # Jan 2026: 39,000  +1.4%
    14: "NEUTRAL",           # Feb 2026: 38,000  −1.2%
    15: "STRONG_INCREASE",   # Mar 2026: 45,600  +18.6%  FY-end
    16: "NEUTRAL",           # Apr 2026: 38,000  −1.2%
    17: "NEUTRAL",           # May 2026: 39,000  +1.4%
    18: "MODERATE_DECREASE", # Jun 2026: 36,000  −6.4%   early monsoon
    19: "MODERATE_DECREASE", # Jul 2026: 35,400  −7.9%   monsoon
    20: "NEUTRAL",           # Aug 2026: 36,800  −4.3%   within neutral band
    21: "NEUTRAL",           # Sep 2026: 39,000  +1.4%
    22: "STRONG_INCREASE",   # Oct 2026: 42,400  +10.3%  Navratri/Dasara
    23: "STRONG_INCREASE",   # Nov 2026: 43,600  +13.4%  Diwali
    24: "MODERATE_INCREASE", # Dec 2026: 39,600  +3.0%
}

# Note on period 11 (Nov 2025, +8.2%): classified MODERATE_INCREASE by deviation band.
# Context-informed ground truth would be STRONG_INCREASE (Diwali). Both are tracked in
# accuracy metrics: full_accuracy uses deviation-band ground truth (above);
# direction_accuracy gives partial credit for correct direction regardless of intensity.

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
# Pattern score (rationale keyword + order elevation check)
# ---------------------------------------------------------------------------

def _extract_month_abbr(calendar_month: str) -> str:
    return calendar_month.strip()[:3]


def _keyword_score(rationale: str, month_abbr: str) -> float:
    keywords = EVENT_KEYWORDS.get(month_abbr, [])
    if not keywords:
        return 0.0
    return 1.0 if any(kw in rationale.lower() for kw in keywords) else 0.0


def _elevation_score(order: float, tier_baseline: float, month_abbr: str) -> float:
    if tier_baseline == 0:
        return 0.0
    ratio = order / tier_baseline
    if month_abbr in DIP_MONTHS:
        return 1.0 if ratio < 0.90 else 0.0
    return 1.0 if ratio > 1.10 else 0.0


def compute_pattern_score(df: pd.DataFrame) -> pd.DataFrame:
    policy = df["policy"].iloc[0] if not df.empty else None
    if policy not in ("intent",):
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
                     "keyword_score": ks, "elevation_score": es,
                     "pattern_score": (ks + es) / 2})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Intent compliance
# ---------------------------------------------------------------------------

def compute_intent_compliance(df: pd.DataFrame) -> pd.Series:
    if "intent_fallback" not in df.columns:
        return pd.Series(dtype=float)
    active = _active_periods(df)
    intent_rows = active[active["policy"] == "intent"]
    if intent_rows.empty:
        return pd.Series(dtype=float)
    return (
        intent_rows.groupby("run_id")["intent_fallback"]
        .apply(lambda s: 1.0 - s.mean())
        .rename("intent_compliance")
    )


# ---------------------------------------------------------------------------
# Intent accuracy
# ---------------------------------------------------------------------------

def compute_intent_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-run intent accuracy against GROUND_TRUTH_INTENT (24-period deviation-band schedule).
    Evaluated at OEM tier only (retail demand driver).

    Returns DataFrame: run_id, full_accuracy, direction_accuracy, event_periods_evaluated
    """
    if "intent_class" not in df.columns:
        return pd.DataFrame(columns=["run_id", "full_accuracy", "direction_accuracy", "event_periods_evaluated"])

    active = _active_periods(df)
    intent_rows = active[(active["policy"] == "intent") & (active["tier"] == "OEM")].copy()
    if intent_rows.empty:
        return pd.DataFrame(columns=["run_id", "full_accuracy", "direction_accuracy", "event_periods_evaluated"])

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
# Intent entropy
# ---------------------------------------------------------------------------

def compute_intent_entropy(df: pd.DataFrame) -> pd.Series:
    if "intent_class" not in df.columns:
        return pd.Series(dtype=float)
    active = _active_periods(df)
    intent_rows = active[(active["policy"] == "intent") & (active["tier"] == "OEM")].copy()
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
# Intent distribution
# ---------------------------------------------------------------------------

def compute_intent_distribution(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    if "intent_class" not in df.columns:
        return {}
    active = _active_periods(df)
    intent_rows = active[(active["policy"] == "intent") & (active["tier"] == "OEM")]
    result = {}
    for run_id, grp in intent_rows.groupby("run_id"):
        result[run_id] = dict(Counter(grp["intent_class"].dropna()))
    return result


# ---------------------------------------------------------------------------
# Condition summary
# ---------------------------------------------------------------------------

def summarise_condition(df: pd.DataFrame, condition_label: str) -> dict:
    ovar_df            = compute_ovar(df)
    chain_ovar         = compute_chain_ovar(ovar_df)
    _, chain_stockouts = compute_stockouts(df)
    pattern_df         = compute_pattern_score(df)
    inv_df             = compute_mean_inventory(df)

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
        "pattern_score":   ms(chain_pattern),
    }

    if policy == "intent":
        compliance  = compute_intent_compliance(df)
        accuracy_df = compute_intent_accuracy(df)
        entropy     = compute_intent_entropy(df)

        result["intent_compliance"] = ms(compliance.reindex(all_run_ids))

        if not accuracy_df.empty:
            acc_idx = accuracy_df.set_index("run_id")
            result["intent_accuracy"] = {
                "full":              ms(acc_idx["full_accuracy"].reindex(all_run_ids)),
                "direction":         ms(acc_idx["direction_accuracy"].reindex(all_run_ids)),
                "n_event_periods":   int(acc_idx["event_periods_evaluated"].mean()) if len(acc_idx) > 0 else 0,
            }
        else:
            result["intent_accuracy"] = None

        result["intent_entropy"]      = ms(entropy.reindex(all_run_ids))
        result["intent_distribution"] = compute_intent_distribution(df)

    return result
