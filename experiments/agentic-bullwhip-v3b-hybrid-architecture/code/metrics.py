"""
Metrics computation — V3b hybrid architecture.

Extends V2a metrics with three new hybrid-specific functions:
  compute_multiplier_stats()       — per-run × tier statistics on the ss_multiplier series
  compute_llm_compliance_rate()    — fraction of valid (not clamped, not fallback) periods
  compute_multiplier_pattern_score() — did the LLM set multiplier in the right direction?

All V2a functions are preserved unchanged:
  compute_ovar(), compute_chain_ovar(), compute_stockouts(),
  compute_excess_inventory(), compute_peak_overshoot(), compute_pattern_score()

summarise_condition() is extended to include hybrid metrics for hybrid policy rows.
"""

import numpy as np
import pandas as pd

TIERS = ["OEM", "Ancillary", "Component"]

# ---------------------------------------------------------------------------
# Seasonal event keyword table (unchanged from V2a)
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
# Utility
# ---------------------------------------------------------------------------

def _active_periods(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to the 24 active ordering periods (period < max)."""
    max_period = df["period"].max()
    return df[df["period"] < max_period].copy()


# ---------------------------------------------------------------------------
# OVAR — primary metric
# ---------------------------------------------------------------------------

def compute_ovar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Order Variance Ratio (OVAR) per run × tier.

    OVAR = Var(order_placed) / Var(demand_received), ddof=1, 24 active periods.
    OVAR > 1.0 → bullwhip. OVAR < 1.0 → dampening (desired).
    """
    active = _active_periods(df)
    rows = []
    for (run_id, tier), grp in active.groupby(["run_id", "tier"]):
        var_orders = grp["order_placed"].var(ddof=1)
        var_demand = grp["demand_received"].var(ddof=1)
        ovar = var_orders / var_demand if var_demand > 0 else np.nan
        rows.append({"run_id": run_id, "tier": tier, "ovar": ovar})
    return pd.DataFrame(rows)


def compute_chain_ovar(ovar_df: pd.DataFrame) -> pd.Series:
    """Chain-average OVAR per run: arithmetic mean across three tiers."""
    return ovar_df.groupby("run_id")["ovar"].mean().rename("chain_ovar")


# ---------------------------------------------------------------------------
# Stockouts — primary metric
# ---------------------------------------------------------------------------

def compute_stockouts(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Count stockout periods per run × tier, and chain totals per run.

    Returns (per_tier, chain). Runs with zero stockouts are explicitly set to
    0 via reindex() so they are not silently absent from the mean.
    """
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
# Supporting metrics (unchanged from V2a)
# ---------------------------------------------------------------------------

def compute_mean_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mean on-hand inventory per run × tier, over active periods.

    With adjustable safety stock, an LLM can "win" on stockouts simply by hoarding.
    Reporting mean on-hand alongside OVAR and stockouts prevents this from being
    masked — a low stockout count achieved via chronic over-stocking is a different
    failure mode, not a success.

    Returns DataFrame with columns: run_id, tier, mean_on_hand.
    """
    active = _active_periods(df)
    return (
        active.groupby(["run_id", "tier"])["on_hand_before_order"]
        .mean()
        .reset_index(name="mean_on_hand")
    )


def compute_excess_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """Sum of on_hand_before_order in surplus periods per run × tier."""
    active = _active_periods(df)
    surplus = active[active["backlog"] == 0]
    return (
        surplus.groupby(["run_id", "tier"])["on_hand_before_order"]
        .sum()
        .reset_index(name="excess_inventory")
    )


def compute_peak_overshoot(df: pd.DataFrame) -> pd.DataFrame:
    """Peak order / peak demand per run × tier. > 1.0 = panic ordering signature."""
    active = _active_periods(df)
    rows = []
    for (run_id, tier), grp in active.groupby(["run_id", "tier"]):
        max_order  = grp["order_placed"].max()
        max_demand = grp["demand_received"].max()
        peak = max_order / max_demand if max_demand > 0 else np.nan
        rows.append({"run_id": run_id, "tier": tier, "peak_overshoot": peak})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pattern score helpers (unchanged from V2a)
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


def _multiplier_elevation_score(multiplier: float, month_abbr: str) -> float:
    """
    Check whether the LLM's multiplier moved in the correct direction.

    Festive months (Oct, Nov, Dec, Jan, Feb, Mar, Apr, May): correct if multiplier > 1.10
    Monsoon dip months (Jun, Jul, Aug): correct if multiplier < 0.90

    This is a direct measure of whether the LLM correctly parameterised
    the safety stock adjustment, independent of whether the final order
    (after exp_smoothing) moved in the right direction.
    """
    if month_abbr in DIP_MONTHS:
        return 1.0 if multiplier < 0.90 else 0.0
    else:
        return 1.0 if multiplier > 1.10 else 0.0


# ---------------------------------------------------------------------------
# Order-level pattern score (V2a, extended to hybrid)
# ---------------------------------------------------------------------------

def compute_pattern_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Seasonal pattern score per run × tier — based on order_placed quantity.

    Extended from V2a to support hybrid policy rows in addition to llm rows.
    For hybrid: elevation_score measures whether the final order (after
    exp_smoothing with adjusted SS) moved in the right direction.

    Returns empty DataFrame for heuristic baselines (no rationale text).
    """
    policy = df["policy"].iloc[0]
    if policy not in ("llm", "hybrid"):
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
        rows.append({
            "run_id":          run_id,
            "tier":            tier,
            "keyword_score":   ks,
            "elevation_score": es,
            "pattern_score":   (ks + es) / 2,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# New V3b: multiplier-level pattern score
# ---------------------------------------------------------------------------

def compute_multiplier_pattern_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Seasonal pattern score per run × tier — based on ss_multiplier (not order_placed).

    This isolates whether the LLM's parameter adjustment was directionally correct,
    separate from whether the final exp_smoothing order moved correctly. A high
    multiplier_pattern_score with low order pattern_score would indicate the LLM
    parameterised correctly but the smoothing formula dominated the output.

    Only computed for hybrid policy rows. Returns empty DataFrame otherwise.

    Components:
      keyword_score     — same as compute_pattern_score() (rationale text check)
      mult_elevation    — did multiplier > 1.1 at festive months and < 0.9 at dip months?
      multiplier_pattern_score = (keyword_score + mult_elevation) / 2
    """
    policy = df["policy"].iloc[0] if not df.empty else None
    if policy != "hybrid" or "ss_multiplier" not in df.columns:
        return pd.DataFrame(columns=[
            "run_id", "tier", "keyword_score", "mult_elevation_score", "multiplier_pattern_score"
        ])

    event_months = set(EVENT_KEYWORDS.keys())
    active = _active_periods(df).copy()
    active["month_abbr"] = active["calendar_month"].apply(_extract_month_abbr)

    # Filter to rows that have a valid multiplier (hybrid active periods)
    active = active[active["ss_multiplier"].notna()].copy()
    event_rows = active[active["month_abbr"].isin(event_months)].copy()

    rows = []
    for (run_id, tier), grp in event_rows.groupby(["run_id", "tier"]):
        ks = grp.apply(lambda r: _keyword_score(r["rationale"], r["month_abbr"]), axis=1).mean()
        mes = grp.apply(lambda r: _multiplier_elevation_score(r["ss_multiplier"], r["month_abbr"]), axis=1).mean()
        rows.append({
            "run_id":                    run_id,
            "tier":                      tier,
            "keyword_score":             ks,
            "mult_elevation_score":      mes,
            "multiplier_pattern_score":  (ks + mes) / 2,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# New V3b: multiplier statistics
# ---------------------------------------------------------------------------

def compute_multiplier_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-run × tier statistics on the ss_multiplier time series.

    Covers 24 active periods × 3 tiers per run. Null rows (non-hybrid) are excluded.

    Returns DataFrame with columns:
      run_id, tier, mean_multiplier, std_multiplier, min_multiplier, max_multiplier,
      n_clamped, n_fallback
    """
    if "ss_multiplier" not in df.columns:
        return pd.DataFrame()

    active = _active_periods(df)
    active = active[active["ss_multiplier"].notna()].copy()
    if active.empty:
        return pd.DataFrame()

    rows = []
    for (run_id, tier), grp in active.groupby(["run_id", "tier"]):
        rows.append({
            "run_id":          run_id,
            "tier":            tier,
            "mean_multiplier": float(grp["ss_multiplier"].mean()),
            "std_multiplier":  float(grp["ss_multiplier"].std(ddof=1)),
            "min_multiplier":  float(grp["ss_multiplier"].min()),
            "max_multiplier":  float(grp["ss_multiplier"].max()),
            "n_clamped":       int(grp["ss_multiplier_clamped"].sum()),
            "n_fallback":      int(grp["llm_fallback"].sum()),
        })

    return pd.DataFrame(rows)


def compute_llm_compliance_rate(df: pd.DataFrame) -> dict:
    """
    Fraction of hybrid periods where the LLM returned a valid, in-bounds multiplier
    without clamping or fallback.

    compliance_rate = (rows where not clamped AND not fallback) / total active hybrid rows

    Returns {"mean": float, "std": float} across runs.
    A rate below 0.95 suggests the model is frequently producing invalid JSON or
    out-of-bounds values — worth investigating.
    """
    if "llm_fallback" not in df.columns:
        return {"mean": None, "std": None}

    active = _active_periods(df)
    active = active[active["ss_multiplier"].notna()].copy()
    if active.empty:
        return {"mean": None, "std": None}

    per_run = []
    for run_id, grp in active.groupby("run_id"):
        valid = (~grp["llm_fallback"]) & (~grp["ss_multiplier_clamped"])
        per_run.append(float(valid.mean()))

    s = pd.Series(per_run)
    return {
        "mean": float(s.mean()),
        "std":  float(s.std(ddof=1)) if len(s) > 1 else 0.0,
    }


# ---------------------------------------------------------------------------
# Condition summary
# ---------------------------------------------------------------------------

def summarise_condition(df: pd.DataFrame, condition_label: str) -> dict:
    """
    Compute and return all metrics for one condition.

    Extends V2a summarise_condition with hybrid-specific metrics
    (multiplier_stats, llm_compliance_rate, multiplier_pattern_score)
    when the condition uses policy == "hybrid".

    Standard structure (all conditions):
    {
        "condition":        "hybrid_context_local",
        "n_runs":           20,
        "chain_ovar":       {"mean": ..., "std": ...},
        "tier_ovar":        {"OEM": {...}, "Ancillary": {...}, "Component": {...}},
        "chain_stockouts":  {"mean": ..., "std": ...},
        "pattern_score":    {"mean": ..., "std": ...},
    }

    Additional keys for hybrid conditions:
        "multiplier_pattern_score": {"mean": ..., "std": ...},
        "multiplier_stats": {
            "mean_mean_multiplier": ...,
            "std_mean_multiplier":  ...,
            "mean_n_fallback":      ...,
            "mean_n_clamped":       ...,
        },
        "llm_compliance_rate": {"mean": ..., "std": ...},
    """
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

    # Chain mean on-hand: average across 3 tiers per run, then mean/std across runs.
    # Reported alongside OVAR and stockouts to detect inventory-hoarding "wins".
    chain_mean_on_hand = (
        inv_df.groupby("run_id")["mean_on_hand"]
        .mean()
        .reindex(all_run_ids)
    )

    policy = df["policy"].iloc[0] if not df.empty else None

    result = {
        "condition":        condition_label,
        "policy":           policy,
        "n_runs":           int(df["run_id"].nunique()),
        "chain_ovar":       ms(chain_ovar),
        "tier_ovar":        tier_ovar,
        "chain_stockouts":  ms(chain_stockouts.set_index("run_id")["chain_stockout_count"]),
        "mean_on_hand":     ms(chain_mean_on_hand),
        "pattern_score":    ms(chain_pattern),
    }

    # Hybrid-specific extensions
    if policy == "hybrid":
        # Multiplier-level pattern score
        mps_df = compute_multiplier_pattern_score(df)
        if mps_df.empty:
            chain_mps = pd.Series(np.nan, index=all_run_ids, name="multiplier_pattern_score")
        else:
            chain_mps = (
                mps_df.groupby("run_id")["multiplier_pattern_score"]
                .mean()
                .reindex(all_run_ids)
            )
        result["multiplier_pattern_score"] = ms(chain_mps)

        # Multiplier time series statistics
        mult_stats_df = compute_multiplier_stats(df)
        if not mult_stats_df.empty:
            result["multiplier_stats"] = {
                "mean_mean_multiplier": float(mult_stats_df["mean_multiplier"].mean()),
                "std_mean_multiplier":  float(mult_stats_df["mean_multiplier"].std(ddof=1)),
                "mean_n_fallback":      float(mult_stats_df["n_fallback"].mean()),
                "mean_n_clamped":       float(mult_stats_df["n_clamped"].mean()),
            }
        else:
            result["multiplier_stats"] = None

        # LLM compliance rate
        result["llm_compliance_rate"] = compute_llm_compliance_rate(df)

    return result
