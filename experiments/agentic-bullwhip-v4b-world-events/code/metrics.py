"""
Metrics for V4 WorldEvents.

Extends V3 metrics with intent-classification-specific metrics:
  - intent_compliance_rate : fraction of valid (non-fallback) intent decisions
  - intent_accuracy        : match rate vs ground-truth deviation-band labels
  - intent_direction_accuracy : correct direction regardless of intensity
  - intent_entropy         : distribution entropy across the 5 intent classes

V3 metrics preserved unchanged:
  - OVAR (primary)
  - Stockout count (secondary)
  - Pattern score (semantic seasonal awareness; LLM conditions only)
  - Excess inventory, peak overshoot (supporting diagnostics)

Ground-truth intent schedule
-----------------------------
Derived from V3's 36-month demand series using V4's deviation bands:
  STRONG_INCREASE   > +10% above period mean
  MODERATE_INCREASE +3% to +10%
  NEUTRAL           -5% to +3%
  MODERATE_DECREASE -5% to -10%
  STRONG_DECREASE   < -10%

World-event-adjusted ground truths: during pandemic_shock (demand -45%) the
ground truth is STRONG_DECREASE; during pandemic_surge (+35%) it is STRONG_INCREASE.
The schedule below reflects demand_multiplier × baseline, not raw baseline alone.
"""

import logging
import math
from collections import Counter

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TIERS = ["OEM", "Ancillary", "Component"]

# ---------------------------------------------------------------------------
# Seasonal event keywords — V3 unchanged
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
# Ground-truth intent schedule — 36 periods
# ---------------------------------------------------------------------------
# Derived from world_events-adjusted demand: during event periods, the effective
# demand = baseline × demand_multiplier (e.g. pandemic_shock × 0.55).
# Mean computed over all 36 periods of the world-events-on series.
#
# Deviation bands relative to the 36-period series mean:
#   STRONG_INCREASE   > +10%
#   MODERATE_INCREASE  +3% to +10%
#   NEUTRAL            -5% to +3%
#   MODERATE_DECREASE  -5% to -10%
#   STRONG_DECREASE   < -10%

GROUND_TRUTH_INTENT: dict[int, str] = {
    # 2025 — baseline seasonal (no world events in periods 1-6)
    1:  "NEUTRAL",           # Jan 2025:  37,200 — mild above mean
    2:  "MODERATE_DECREASE", # Feb 2025:  36,200 — -5.8% below mean
    3:  "STRONG_INCREASE",   # Mar 2025:  43,500 — FY-end peak (+13%)
    4:  "MODERATE_DECREASE", # Apr 2025:  36,200 — -5.8%
    5:  "NEUTRAL",           # May 2025:  37,200 — -3.2%
    6:  "MODERATE_DECREASE", # Jun 2025:  34,300 — monsoon dip, no world event (pandemic starts period 7)
    7:  "STRONG_DECREASE",   # Jul 2025:  33,700 → pandemic_shock ×0.55 → effective ~18,535
    8:  "STRONG_DECREASE",   # Aug 2025:  35,100 → pandemic_shock ×0.55 → effective ~19,305
    9:  "STRONG_DECREASE",   # Sep 2025:  37,200 → pandemic_shock ×0.55 → effective ~20,460
    10: "STRONG_INCREASE",   # Oct 2025:  40,400 → pandemic_surge ×1.35 → effective ~54,540
    11: "STRONG_INCREASE",   # Nov 2025:  41,600 → pandemic_surge ×1.35 → effective ~56,160
    12: "MODERATE_INCREASE", # Dec 2025:  37,700 → pandemic_recovery ×1.10 → effective ~41,470
    # 2026 — conflict periods 19-21
    13: "NEUTRAL",           # Jan 2026:  39,000 (+5% YoY) — mild above mean
    14: "MODERATE_DECREASE", # Feb 2026:  38,000 — mild below mean
    15: "STRONG_INCREASE",   # Mar 2026:  45,600 — FY-end (+19%)
    16: "NEUTRAL",           # Apr 2026:  38,000 — mild below mean
    17: "NEUTRAL",           # May 2026:  39,000 — at mean
    18: "MODERATE_DECREASE", # Jun 2026:  36,000 — monsoon dip
    19: "MODERATE_DECREASE", # Jul 2026:  35,400 → conflict demand ×0.95 → effective ~33,630
    20: "MODERATE_DECREASE", # Aug 2026:  36,800 → conflict demand ×0.90 → effective ~33,120
    21: "NEUTRAL",           # Sep 2026:  39,000 → conflict demand ×0.90 → effective ~35,100
    22: "STRONG_INCREASE",   # Oct 2026:  42,400 — Navratri/Dasara (+10%)
    23: "STRONG_INCREASE",   # Nov 2026:  43,600 — Diwali (+13%)
    24: "MODERATE_INCREASE", # Dec 2026:  39,600 — year-end push
    # 2027 — port disruption periods 28-30
    25: "NEUTRAL",           # Jan 2027:  39,060 (+10% YoY from 2025)
    26: "MODERATE_DECREASE", # Feb 2027:  38,010
    27: "STRONG_INCREASE",   # Mar 2027:  45,675 — FY-end peak (+10%)
    28: "NEUTRAL",           # Apr 2027:  38,010 → port demand ×1.00 → demand unaffected
    29: "NEUTRAL",           # May 2027:  39,060 → port demand ×1.00
    30: "MODERATE_DECREASE", # Jun 2027:  36,015 → port demand ×1.00 + monsoon dip
    31: "STRONG_DECREASE",   # Jul 2027:  35,385 — monsoon trough
    32: "MODERATE_DECREASE", # Aug 2027:  36,855 — monsoon exit
    33: "NEUTRAL",           # Sep 2027:  39,060 — pre-festive
    34: "STRONG_INCREASE",   # Oct 2027:  42,420 — Navratri/Dasara (+10%)
    35: "STRONG_INCREASE",   # Nov 2027:  43,680 — Diwali (+10%)
    36: "MODERATE_INCREASE", # Dec 2027:  39,585 — year-end
}

# Intent direction map: direction for partial-credit accuracy
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
# OVAR — primary metric (V3 unchanged)
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
# Stockouts — secondary metric (V3 unchanged)
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
# Supporting metrics — V3 unchanged
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
# Pattern score — V3 unchanged
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
# Intent compliance rate — V4 addition
# ---------------------------------------------------------------------------

def compute_intent_compliance(df: pd.DataFrame) -> pd.Series:
    """
    Fraction of active intent-policy periods that returned a valid (non-fallback)
    classification. Only meaningful for policy=="intent" runs.

    Returns a Series indexed by run_id.
    """
    if "intent_fallback" not in df.columns:
        return pd.Series(dtype=float)

    active  = _active_periods(df)
    intent_rows = active[active["policy"] == "intent"]
    if intent_rows.empty:
        return pd.Series(dtype=float)

    result = (
        intent_rows.groupby("run_id")["intent_fallback"]
        .apply(lambda s: 1.0 - s.mean())   # compliance = 1 - fallback_rate
    ).rename("intent_compliance")
    return result


# ---------------------------------------------------------------------------
# Intent accuracy — V4 addition
# ---------------------------------------------------------------------------

def compute_intent_accuracy(df: pd.DataFrame, world_events_on: bool = True) -> pd.DataFrame:
    """
    Per-run intent accuracy metrics against GROUND_TRUTH_INTENT.

    Only computed for policy=="intent" runs with world events enabled.
    Pass world_events_on=False for E3_IC (no-events ablation) runs — no ground
    truth schedule exists for the events-off world, so accuracy is not defined.

    Returns a DataFrame with columns:
      run_id, full_accuracy, direction_accuracy, event_periods_evaluated
    """
    if not world_events_on:
        logger.info("compute_intent_accuracy: skipped — world events off, no ground truth defined")
        return pd.DataFrame(columns=["run_id", "full_accuracy", "direction_accuracy", "event_periods_evaluated"])

    if "intent_class" not in df.columns:
        return pd.DataFrame(columns=["run_id", "full_accuracy", "direction_accuracy", "event_periods_evaluated"])

    active      = _active_periods(df)
    intent_rows = active[active["policy"] == "intent"].copy()
    if intent_rows.empty:
        return pd.DataFrame(columns=["run_id", "full_accuracy", "direction_accuracy", "event_periods_evaluated"])

    intent_rows = intent_rows[intent_rows["tier"] == "OEM"].copy()   # evaluate at OEM (retail demand driver)
    intent_rows["ground_truth"] = intent_rows["period"].map(GROUND_TRUTH_INTENT)

    # Only evaluate non-neutral ground-truth periods (event periods)
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
# Intent entropy — V4 addition
# ---------------------------------------------------------------------------

def compute_intent_entropy(df: pd.DataFrame) -> pd.Series:
    """
    Shannon entropy of the intent distribution per run (OEM tier only).
    High entropy = the model uses multiple classes. Low entropy = collapse to one class.

    Returns a Series indexed by run_id.
    """
    if "intent_class" not in df.columns:
        return pd.Series(dtype=float)

    active      = _active_periods(df)
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
# Intent distribution — V4 addition
# ---------------------------------------------------------------------------

def compute_intent_distribution(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """
    Raw count of each intent class per run (OEM tier only).
    Returns dict keyed by run_id → dict of class → count.
    """
    if "intent_class" not in df.columns:
        return {}

    active      = _active_periods(df)
    intent_rows = active[(active["policy"] == "intent") & (active["tier"] == "OEM")]
    result = {}
    for run_id, grp in intent_rows.groupby("run_id"):
        result[run_id] = dict(Counter(grp["intent_class"].dropna()))
    return result


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

    summary = {
        "condition":       condition_label,
        "n_runs":          int(df["run_id"].nunique()),
        "chain_ovar":      ms(chain_ovar),
        "tier_ovar":       tier_ovar,
        "chain_stockouts": ms(chain_stockouts.set_index("run_id")["chain_stockout_count"]),
        "pattern_score":   ms(chain_pattern),
    }

    # Intent-specific metrics — only populated for intent policy conditions
    if df.get("policy", pd.Series(dtype=str)).iloc[0] == "intent" if len(df) > 0 else False:
        compliance = compute_intent_compliance(df)
        # Infer whether world events were active: any non-None world_event value means events on.
        # Conditions with no_events=True produce all-None world_event columns.
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

        summary["intent_entropy"] = ms(entropy.reindex(all_run_ids))
        summary["intent_distribution"] = compute_intent_distribution(df)

    return summary
