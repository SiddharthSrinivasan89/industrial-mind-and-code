"""
Metrics computation.

Pure computation — no LLM calls, no file I/O, no side effects.
Input:  DataFrame of simulation records produced by simulation.run_simulation().
Output: Scalar summaries stored in dicts, returned by summarise_condition().

All functions operate on a DataFrame that may contain multiple runs of the same
condition. They group by run_id (and tier where relevant) so each run contributes
equally to the mean/std reported in the summary.

Primary metric:  OVAR  = Var(orders) / Var(demand)  per run × tier
                         OVAR > 1.0 → bullwhip amplification
                         OVAR < 1.0 → dampening (agent smooths demand noise)
Secondary:       Stockout count per run (chain total across all three tiers)
Supporting:      Pattern score — did the agent recognise seasonal demand events?
"""

import numpy as np
import pandas as pd

TIERS = ["OEM", "Ancillary", "Component"]

# ---------------------------------------------------------------------------
# Seasonal event keyword table
# ---------------------------------------------------------------------------
# Used by keyword_score: if the agent's rationale text for a given calendar month
# contains any of these words, the agent gets credit for seasonal awareness.
#
# Only months with a named demand event are listed. Sep and months not in this
# dict return an empty keyword list, scoring 0 automatically.
#
# These keywords are derived from real Indian automotive demand patterns:
#   Jan  — Makar Sankranti / harvest festival / wedding season start
#   Feb  — Union Budget (affects commercial vehicle / fleet purchases)
#   Mar  — Financial year-end (fleet managers clear budgets)
#   Apr  — Wedding season peak; Akshaya Tritiya (auspicious buying day)
#   May  — Late wedding season; summer purchases
#   Jun–Aug — Monsoon demand dip (poor roads, delayed deliveries, low sentiment)
#   Oct  — Navratri/Dasara pre-festive spike
#   Nov  — Diwali peak (largest single month for Indian auto retail)
#   Dec  — Year-end discounts; year-end fleet purchases; wedding season resumes

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

# Months where the correct agent response is to ORDER LESS than the baseline,
# not more. elevation_score checks for a dip (ratio < 0.90) in these months,
# and a spike (ratio > 1.10) in all other event months.
DIP_MONTHS = {"Jun", "Jul", "Aug"}


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _active_periods(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter to the 24 active ordering periods only.

    The 25th period is a fulfilment-only close-out with order_placed = 0 for
    every tier by design. Including it in OVAR would deflate order variance
    (artificially adding a 0 to every tier's order series) and understate the
    bullwhip effect.

    We filter by period number (period < max), NOT by order_placed > 0. Filtering
    by order quantity would silently drop legitimate zero orders that agents or
    heuristics might place in slack periods — that would be a bug.
    """
    max_period = df["period"].max()
    return df[df["period"] < max_period].copy()


# ---------------------------------------------------------------------------
# OVAR — primary metric
# ---------------------------------------------------------------------------

def compute_ovar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Order Variance Ratio (OVAR) per run × tier.

    Formula:  OVAR = Var(order_placed) / Var(demand_received)
              using sample variance (ddof=1) over the 24 active periods.

    Why ddof=1?  We have a finite sample (24 periods) and want an unbiased
    estimate of the true variance, not the population variance of the sample.

    Returns a DataFrame with columns: run_id, tier, ovar.
    NaN is returned for a tier+run combination if demand variance is zero
    (i.e. perfectly flat demand for the entire run — should not happen with
    the synthetic dataset but guarded against to avoid ZeroDivisionError).

    Interpretation:
      OVAR = 1.0 — agent passes demand through exactly (like naive_passthrough)
      OVAR > 1.0 — agent amplifies demand noise (bullwhip)
      OVAR < 1.0 — agent dampens demand noise (desirable)
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
    """
    Chain-average OVAR per run: arithmetic mean of OVAR across the three tiers.

    A single chain_ovar number summarises bullwhip behaviour for one run.
    This is the primary outcome variable for H1–H6 hypothesis tests.

    Input: the DataFrame returned by compute_ovar().
    Output: Series indexed by run_id, named "chain_ovar".
    """
    return ovar_df.groupby("run_id")["ovar"].mean().rename("chain_ovar")


# ---------------------------------------------------------------------------
# Stockouts — secondary metric
# ---------------------------------------------------------------------------

def compute_stockouts(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Count stockout periods per run × tier, and chain totals per run.

    A stockout is recorded in the simulation whenever shortfall > 0 (the tier
    could not fully serve demand + backlog from available on-hand inventory).
    This function counts how many periods each tier experienced a stockout.

    Returns
    -------
    per_tier : DataFrame with columns (run_id, tier, stockout_count)
               Only run × tier pairs that had at least one stockout appear here.

    chain    : DataFrame with columns (run_id, chain_stockout_count)
               All run_ids are present, including runs with zero stockouts.
               Runs with zero stockouts are explicitly set to 0 via reindex()
               so they are not silently absent from the mean calculation.
               Without reindex, the mean would be inflated (averaging only
               the runs that had at least one stockout).

    Note: stockouts in the final period (period 25) ARE included here because
    they represent real unserved demand from backlog carried out of period 24.
    _active_periods() is NOT applied to stockout counting.
    """
    all_run_ids = df["run_id"].unique()

    # per_tier: group stockout rows by run+tier, count them
    per_tier = (
        df[df["stockout"]]
        .groupby(["run_id", "tier"])
        .size()
        .reset_index(name="stockout_count")
    )

    # chain: group stockout rows by run, count them, then reindex to ALL run_ids
    # so runs with zero stockouts get count=0 rather than being absent
    chain = (
        df[df["stockout"]]
        .groupby("run_id")
        .size()
        .reindex(all_run_ids, fill_value=0)   # ← key: zero-stockout runs contribute 0
        .reset_index(name="chain_stockout_count")
    )

    return per_tier, chain


# ---------------------------------------------------------------------------
# Supporting metrics
# ---------------------------------------------------------------------------

def compute_excess_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sum of on_hand_before_order in surplus periods per run × tier.

    "Surplus period" is any active period where backlog == 0 (all demand was met
    and no carry-forward obligation). In these periods, on_hand_before_order is
    pure excess — stock sitting idle that could have been avoided.

    High excess_inventory combined with low OVAR suggests the agent is playing
    it safe with large buffer orders rather than genuinely smoothing demand.
    """
    active = _active_periods(df)
    surplus = active[active["backlog"] == 0]  # only periods without unfulfilled backlog
    return (
        surplus.groupby(["run_id", "tier"])["on_hand_before_order"]
        .sum()
        .reset_index(name="excess_inventory")
    )


def compute_peak_overshoot(df: pd.DataFrame) -> pd.DataFrame:
    """
    Peak order overshoot per run × tier.

    Formula: max(order_placed) / max(demand_received) over the 24 active periods.

    A ratio > 1.0 means the agent placed an order larger than any demand it ever
    received in the same run. This is the classic "panic ordering" signature of
    the bullwhip effect. Values close to 1.0 indicate disciplined ordering.

    Used as a supporting diagnostic, not a primary hypothesis test variable.
    """
    active = _active_periods(df)
    rows = []
    for (run_id, tier), grp in active.groupby(["run_id", "tier"]):
        max_order = grp["order_placed"].max()
        max_demand = grp["demand_received"].max()
        peak = max_order / max_demand if max_demand > 0 else np.nan
        rows.append({"run_id": run_id, "tier": tier, "peak_overshoot": peak})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pattern score helpers
# ---------------------------------------------------------------------------

def _extract_month_abbr(calendar_month: str) -> str:
    """
    Extract the 3-letter month abbreviation from a calendar_month string.

    Examples:
      "Nov 2025" → "Nov"
      "Jan 2026" → "Jan"
      "Aug 2026" → "Aug"

    The first 3 characters after stripping whitespace give the abbreviated
    month name, which is the key used in EVENT_KEYWORDS.
    """
    return calendar_month.strip()[:3]


def _keyword_score(rationale: str, month_abbr: str) -> float:
    """
    Check whether the agent's rationale mentions a relevant seasonal keyword.

    Returns 1.0 if the rationale text (lowercased) contains any keyword from
    EVENT_KEYWORDS[month_abbr], 0.0 otherwise.

    Returns 0.0 if month_abbr is not in EVENT_KEYWORDS (no event expected
    in that month, so no credit to give).

    This score measures semantic awareness: did the agent mention WHY demand
    is high/low, not just THAT it is high/low?
    """
    keywords = EVENT_KEYWORDS.get(month_abbr, [])
    if not keywords:
        return 0.0          # no expected event this month — nothing to score
    text = rationale.lower()
    return 1.0 if any(kw in text for kw in keywords) else 0.0


def _elevation_score(order: float, tier_baseline: float, month_abbr: str) -> float:
    """
    Check whether the agent's order quantity moves in the right direction for the event.

    Threshold logic:
      Festival months (Oct, Nov, Dec, Jan, Feb, Mar, Apr, May):
        Score 1.0 if order > 1.10 × baseline  (agent pre-stocks for demand spike)
      Monsoon dip months (Jun, Jul, Aug):
        Score 1.0 if order < 0.90 × baseline  (agent orders less during slow season)

    tier_baseline is the median order for that run × tier across all 24 active
    periods. Using the median (not mean) avoids distortion from extreme outlier
    orders in panic-buying periods.

    Returns 0.0 if baseline is zero (can't compute a meaningful ratio).
    """
    if tier_baseline == 0:
        return 0.0
    ratio = order / tier_baseline
    if month_abbr in DIP_MONTHS:
        return 1.0 if ratio < 0.90 else 0.0   # correct response: order less
    else:
        return 1.0 if ratio > 1.10 else 0.0   # correct response: order more


# ---------------------------------------------------------------------------
# Pattern score — main function
# ---------------------------------------------------------------------------

def compute_pattern_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Seasonal pattern score per run × tier.

    Pattern score = average of keyword_score and elevation_score at event periods.
    A score of 1.0 means the agent consistently mentioned the right seasonal
    keywords AND placed orders in the right direction at every event month.

    Steps
    -----
    1. Filter to active periods and annotate each row with its 3-letter month abbr.
    2. Compute the per-(run, tier) median order as the baseline for elevation_score.
    3. Filter to event months only (rows where month_abbr is a key in EVENT_KEYWORDS).
    4. For each (run, tier) group, compute:
         keyword_score  — fraction of event rows where rationale mentioned keywords
         elevation_score — fraction of event rows where order moved the right way
         pattern_score  — simple average of the two

    Why calendar month, not period number?
      The demand dataset spans two calendar years (2025–2026). The same calendar
      month (e.g. "Nov") appears twice (Nov 2025 and Nov 2026). Joining on
      calendar_month abbreviation naturally captures both Diwali cycles.
      Hard-coding period numbers (e.g. period 11 = Nov 2025) would miss the
      second cycle and need updating if the demand dataset changes.

    Returns a DataFrame with columns: run_id, tier, keyword_score, elevation_score, pattern_score.
    Rows exist only for (run, tier) pairs that had at least one event-month observation.
    """
    # Pattern score is only meaningful for LLM conditions.
    # Heuristics have empty rationale — computing elevation_score without
    # semantic awareness conflates quantity shape with seasonal reasoning.
    if df["policy"].iloc[0] != "llm":
        return pd.DataFrame(columns=["run_id", "tier", "keyword_score", "elevation_score", "pattern_score"])

    event_months = set(EVENT_KEYWORDS.keys())
    active = _active_periods(df).copy()
    active["month_abbr"] = active["calendar_month"].apply(_extract_month_abbr)

    # Compute per-(run, tier) median order — this is the baseline for elevation_score.
    # Median is more robust than mean when a few panic orders are very large.
    baselines = (
        active.groupby(["run_id", "tier"])["order_placed"]
        .median()
        .rename("baseline")
        .reset_index()
    )
    active = active.merge(baselines, on=["run_id", "tier"])

    # Keep only rows where the calendar month is an event month
    event_rows = active[active["month_abbr"].isin(event_months)].copy()

    rows = []
    for (run_id, tier), grp in event_rows.groupby(["run_id", "tier"]):
        # Average keyword_score across all event periods for this run × tier
        ks = grp.apply(
            lambda r: _keyword_score(r["rationale"], r["month_abbr"]), axis=1
        ).mean()
        # Average elevation_score across all event periods for this run × tier
        es = grp.apply(
            lambda r: _elevation_score(r["order_placed"], r["baseline"], r["month_abbr"]), axis=1
        ).mean()
        rows.append({
            "run_id": run_id,
            "tier": tier,
            "keyword_score":   ks,
            "elevation_score": es,
            "pattern_score":   (ks + es) / 2,   # equal weight on text and quantity
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Condition summary — called by run_experiment.py for each condition label
# ---------------------------------------------------------------------------

def summarise_condition(df: pd.DataFrame, condition_label: str) -> dict:
    """
    Compute and return all primary metrics for one condition.

    Called by save_results() in run_experiment.py once per condition_label.
    The input df should already be filtered to a single condition_label
    (this is done by the df.groupby("condition_label") in save_results).

    Returns a dict with the following structure:
    {
        "condition":        "context_lightweight",   # the condition label
        "n_runs":           20,                      # how many runs contributed
        "chain_ovar":       {"mean": 1.23, "std": 0.18},
        "chain_stockouts":  {"mean": 2.40, "std": 1.10},
        "pattern_score":    {"mean": 0.55, "std": 0.12},
    }

    The ms() helper reindexes each Series to all run_ids before computing
    mean/std. Without reindexing, runs that had no pattern-score rows
    (e.g. no event months in their output) would be silently excluded from
    the mean, inflating it.

    Pattern score is reported as NaN for heuristic baselines because the metric
    is defined for LLM rationale+ordering behaviour, not for deterministic
    non-semantic rules.
    """
    ovar_df       = compute_ovar(df)
    chain_ovar    = compute_chain_ovar(ovar_df)
    _, chain_stockouts = compute_stockouts(df)
    pattern_df    = compute_pattern_score(df)

    all_run_ids = df["run_id"].unique()

    def ms(series: pd.Series) -> dict:
        """
        Mean and std of a per-run Series, reindexed to all run_ids.

        Reindexing to all_run_ids ensures runs that produced no rows in an
        intermediate groupby still contribute NaN (which pandas mean/std skip
        by default with skipna=True). Without reindex, those runs would be
        entirely absent from the calculation — a silent exclusion bug.
        """
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

    # Tier-wise OVAR: mean and std per tier across all runs.
    # Reported alongside the chain average so divergent behaviour (e.g. low OVAR
    # at OEM but high OVAR at Component) is not masked by averaging.
    tier_ovar = {}
    for tier in TIERS:
        tier_series = (
            ovar_df[ovar_df["tier"] == tier]
            .set_index("run_id")["ovar"]
            .reindex(all_run_ids)
        )
        tier_ovar[tier] = ms(tier_series)

    return {
        "condition":       condition_label,
        "n_runs":          int(df["run_id"].nunique()),
        "chain_ovar":      ms(chain_ovar),
        "tier_ovar":       tier_ovar,
        "chain_stockouts": ms(chain_stockouts.set_index("run_id")["chain_stockout_count"]),
        "pattern_score":   ms(chain_pattern),
    }
