"""
Output verification — V6 StatelessSwing.

Runs post-hoc checks on a results directory. Use after dry-run or smoke-test runs
to confirm the pipeline produced correct output before launching production runs.

Usage
-----
    # Verify a specific output directory
    python verify_outputs.py --results-dir ../results/mini_adaptive/20260427T120000/

    # Verify all run directories under results/
    python verify_outputs.py --results-dir ../results/

Checks performed
----------------
1. records.parquet exists and has the expected shape (n_runs × 75 records)
2. No negative order quantities
3. alpha_chosen ∈ {0.1, 0.3, 0.5, 0.7} for all active periods (where not None)
4. alpha_fallback rate < 5% for adaptive_alpha conditions
5. Non-adaptive rows have alpha_fallback == False (not None, not True)
6. summary.json is valid JSON with finite chain_ovar mean per condition
7. Adaptive conditions have alpha_mean and alpha_fallback_rate keys in summary.json
8. Dry-run specific: all alpha_chosen == 0.3 (dry_run backend returns 0.3 every period)
9. Real-run specific: at least one adaptive row has latency_ms > 0

Exit code: 0 if all checks pass, 1 if any check fails.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import pandas as pd

VALID_ALPHAS = {0.1, 0.3, 0.5, 0.7}


def check(condition: bool, message: str) -> bool:
    if condition:
        print(f"  OK: {message}")
    else:
        print(f"  FAIL: {message}")
    return condition


def _read_dry_run_from_provenance(run_dir: Path) -> bool | None:
    prov_path = run_dir / "provenance.json"
    if not prov_path.exists():
        return None
    try:
        prov = json.loads(prov_path.read_text())
        if "dry_run" not in prov:
            return None
        return bool(prov["dry_run"])
    except Exception:
        return None


def verify_run_dir(run_dir: Path, is_dry_run: bool = False) -> bool:
    print(f"\n=== Verifying: {run_dir} ===")
    all_pass = True

    prov_dry_run = _read_dry_run_from_provenance(run_dir)
    if prov_dry_run is not None:
        if prov_dry_run != is_dry_run:
            print(
                f"  INFO: provenance.dry_run={prov_dry_run} overrides caller "
                f"is_dry_run={is_dry_run}"
            )
        is_dry_run = prov_dry_run
    else:
        print("  WARN: provenance.json missing or has no dry_run field — "
              "using caller-supplied is_dry_run flag")

    # --- records.parquet ---
    records_path = run_dir / "records.parquet"
    if not records_path.exists():
        print(f"  FAIL: records.parquet not found in {run_dir}")
        return False

    df = pd.read_parquet(records_path)
    n_runs = df["run_id"].nunique()
    n_conditions = df["condition_label"].nunique()
    print(f"  INFO: {len(df):,} records, {n_runs} run(s), {n_conditions} condition(s)")

    # Shape: each run must have exactly 75 records (25 periods × 3 tiers)
    for run_id, grp in df.groupby("run_id"):
        n = len(grp)
        all_pass &= check(n == 75, f"run {run_id}: {n} records (expected 75)")

    # No negative orders
    neg_orders = (df["order_placed"] < 0).sum()
    all_pass &= check(neg_orders == 0, f"No negative order quantities ({neg_orders} found)")

    # Active periods: period < max period (period 25 is fulfilment-only, alpha_chosen=None)
    max_period = df["period"].max()
    active_df = df[df["period"] < max_period].copy()

    # --- Alpha column checks (active periods) ---
    # alpha_chosen should be non-null for all active periods
    null_alpha = active_df["alpha_chosen"].isna().sum()
    all_pass &= check(null_alpha == 0, f"No null alpha_chosen in active periods ({null_alpha} found)")

    # alpha_chosen must be in valid set (where not null)
    valid_alpha_df = active_df[active_df["alpha_chosen"].notna()]
    if not valid_alpha_df.empty:
        invalid_alphas = valid_alpha_df[~valid_alpha_df["alpha_chosen"].isin(VALID_ALPHAS)]
        all_pass &= check(
            len(invalid_alphas) == 0,
            f"All alpha_chosen ∈ {{0.1, 0.3, 0.5, 0.7}} ({len(invalid_alphas)} invalid values found)",
        )

    # --- Adaptive-alpha condition checks ---
    adaptive_df = active_df[active_df["policy"] == "adaptive_alpha"].copy()
    if not adaptive_df.empty:
        # Fallback rate < 5%
        fallback_rate = float(adaptive_df["alpha_fallback"].mean())
        all_pass &= check(
            fallback_rate < 0.05,
            f"Adaptive alpha_fallback rate < 5% (actual: {fallback_rate:.1%})",
        )

        if is_dry_run:
            # Dry run: dry_run_backend returns 0.3 every period
            non_03 = (adaptive_df["alpha_chosen"] != 0.3).sum()
            all_pass &= check(
                non_03 == 0,
                f"Dry run: all adaptive alpha_chosen == 0.3 ({non_03} non-0.3 rows found)",
            )
        else:
            # Real run: at least some calls must have recorded latency
            n_live = (adaptive_df["latency_ms"] > 0).sum()
            all_pass &= check(
                n_live > 0,
                f"Real run: at least one adaptive row has latency_ms > 0 ({n_live} found)",
            )
            # All-fallback with blank rationales = dry-run-equivalent, not real evidence
            all_trivial = (
                (adaptive_df["alpha_chosen"] == 0.3).all()
                and (adaptive_df["alpha_fallback"].all())
            )
            all_pass &= check(
                not all_trivial,
                "Real run: not all alpha=0.3 fallbacks (would indicate dry-run-equivalent output)",
            )

    # --- Non-adaptive rows ---
    non_adaptive_active = active_df[active_df["policy"] != "adaptive_alpha"]
    if not non_adaptive_active.empty and "alpha_fallback" in non_adaptive_active.columns:
        bad_fallback = non_adaptive_active["alpha_fallback"].fillna(False).sum()
        all_pass &= check(
            bad_fallback == 0,
            f"Non-adaptive rows have alpha_fallback == False ({bad_fallback} non-False found)",
        )

    # Period 25 (fulfilment-only): alpha_chosen should be None/NaN
    period25 = df[df["period"] == max_period]
    if not period25.empty:
        non_null_p25 = period25["alpha_chosen"].notna().sum()
        all_pass &= check(
            non_null_p25 == 0,
            f"Period {max_period} alpha_chosen is null for all rows ({non_null_p25} non-null found)",
        )

    # --- summary.json ---
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        print("  FAIL: summary.json not found")
        all_pass = False
    else:
        try:
            summaries = json.loads(summary_path.read_text())
            all_pass &= check(isinstance(summaries, list), "summary.json is a list")
            all_pass &= check(len(summaries) > 0, f"summary.json has {len(summaries)} entries")

            for s in summaries:
                cond = s.get("condition", "unknown")

                # Finite chain_ovar mean
                ovar_entry = s.get("chain_ovar")
                if isinstance(ovar_entry, dict):
                    ovar_mean = ovar_entry.get("mean")
                    if ovar_mean is not None:
                        all_pass &= check(
                            math.isfinite(ovar_mean),
                            f"Condition '{cond}' chain_ovar mean is finite (got {ovar_mean})",
                        )

                # Adaptive conditions must have alpha summary keys
                if s.get("policy") == "adaptive_alpha":
                    for key in ("alpha_mean", "alpha_fallback_rate"):
                        all_pass &= check(
                            key in s,
                            f"Adaptive condition '{cond}' has '{key}' key in summary",
                        )

        except json.JSONDecodeError as e:
            print(f"  FAIL: summary.json is not valid JSON: {e}")
            all_pass = False

    return all_pass


def main():
    parser = argparse.ArgumentParser(description="Verify V6 StatelessSwing experiment outputs")
    parser.add_argument("--results-dir", type=str, required=True,
                        help="Directory to search for records.parquet files")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    caller_dry_run = os.environ.get("DRY_RUN", "").strip() == "1"
    if caller_dry_run:
        print("DRY_RUN=1 in environment — used as fallback for results without provenance stamp")

    run_dirs = sorted(p.parent for p in results_dir.rglob("records.parquet"))
    if not run_dirs:
        print(f"No records.parquet files found in {results_dir}")
        sys.exit(1)

    print(f"Found {len(run_dirs)} run directory(ies) to verify")

    all_pass = True
    for run_dir in run_dirs:
        all_pass &= verify_run_dir(run_dir, is_dry_run=caller_dry_run)

    print("\n" + ("=" * 50))
    if all_pass:
        print("ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED — review output above")
        sys.exit(1)


if __name__ == "__main__":
    main()
