"""
Output verification — V3b hybrid architecture.

Runs post-hoc checks on a results directory. Use after dry-run or smoke-test runs
to confirm the pipeline produced correct output before launching production runs.

Usage
-----
    # Verify the most recent experiment output
    python verify_outputs.py --results-dir ../results/H1/20260327T123456/

    # Verify all runs in a results directory
    python verify_outputs.py --results-dir ../results/

Checks performed
----------------
1. records.parquet exists and has the expected shape (n_runs × 75 records)
2. ss_multiplier is within [0.5, 3.0] for all hybrid rows (after clamping)
3. llm_fallback rate < 5% (LLM is returning valid JSON)
4. Non-hybrid rows have ss_multiplier = null
5. summary.json is valid JSON and contains multiplier_stats for hybrid conditions
6. No negative order quantities
7. OVAR values are finite (no NaN from division by zero)
8. Dry-run specific: all ss_multiplier == 1.0 if DRY_RUN=1

Exit code: 0 if all checks pass, 1 if any check fails.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd


def check(condition: bool, message: str) -> bool:
    if condition:
        print(f"  OK: {message}")
    else:
        print(f"  FAIL: {message}")
    return condition


def _read_dry_run_from_provenance(run_dir: Path) -> bool | None:
    """
    Read dry_run flag from provenance.json.
    Returns True/False if stamped, None if provenance is missing or field absent.
    """
    prov_path = run_dir / "provenance.json"
    if not prov_path.exists():
        return None
    try:
        prov = json.loads(prov_path.read_text())
        # If the key is absent (legacy provenance), return None — unknown, not False.
        # Defaulting to False would silently treat old dry-run results as real runs.
        if "dry_run" not in prov:
            return None
        return bool(prov["dry_run"])
    except Exception:
        return None


def verify_run_dir(run_dir: Path, is_dry_run: bool = False) -> bool:
    print(f"\n=== Verifying: {run_dir} ===")
    all_pass = True

    # Read dry_run from provenance (authoritative) — fall back to caller's flag
    # if provenance is absent (legacy results without the stamp).
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
    print(f"  INFO: {len(df):,} records, {df['run_id'].nunique()} runs, "
          f"{df['condition_label'].nunique()} conditions")

    # Shape check: each run should have exactly 75 records (25 × 3)
    for run_id, grp in df.groupby("run_id"):
        n = len(grp)
        all_pass &= check(n == 75, f"run {run_id}: {n} records (expected 75)")

    # No negative orders
    neg_orders = (df["order_placed"] < 0).sum()
    all_pass &= check(neg_orders == 0, f"No negative order quantities ({neg_orders} found)")

    # Hybrid-specific checks
    hybrid_df = df[df["policy"] == "hybrid"].copy()
    if not hybrid_df.empty:
        active_hybrid = hybrid_df[hybrid_df["ss_multiplier"].notna()]

        # Multiplier in bounds after clamping
        out_of_bounds = active_hybrid[
            (active_hybrid["ss_multiplier"] < 0.5) | (active_hybrid["ss_multiplier"] > 3.0)
        ]
        all_pass &= check(
            len(out_of_bounds) == 0,
            f"All clamped ss_multiplier in [0.5, 3.0] ({len(out_of_bounds)} violations)",
        )

        # Fallback rate
        fallback_rate = float(active_hybrid["llm_fallback"].mean())
        all_pass &= check(
            fallback_rate < 0.05,
            f"LLM fallback rate < 5% (actual: {fallback_rate:.1%})",
        )

        if is_dry_run:
            # Dry run: all multipliers should be exactly 1.0 (neutral).
            non_neutral = (active_hybrid["ss_multiplier"] != 1.0).sum()
            all_pass &= check(
                non_neutral == 0,
                f"Dry run: all ss_multiplier == 1.0 ({non_neutral} non-neutral rows)",
            )
            # Dry run hybrid OVAR must match hybrid_control exactly (both use
            # multiplier=1.0 with the same OUT-style formula). Divergence means
            # a formula bug, not an LLM issue.
            from metrics import compute_ovar, compute_chain_ovar
            dry_ovar_series = compute_chain_ovar(compute_ovar(active_hybrid))
            ctrl_df = df[df["policy"] == "hybrid_control"]
            if not dry_ovar_series.empty and not ctrl_df.empty:
                ctrl_ovar_series = compute_chain_ovar(compute_ovar(ctrl_df))
                ctrl_ovar = float(ctrl_ovar_series.mean()) if not ctrl_ovar_series.empty else None
                dry_ovar_mean = float(dry_ovar_series.mean())
                if ctrl_ovar is not None:
                    delta = abs(dry_ovar_mean - ctrl_ovar)
                    all_pass &= check(
                        delta < 0.01,
                        f"Dry run hybrid OVAR ({dry_ovar_mean:.4f}) matches hybrid_control "
                        f"({ctrl_ovar:.4f}), delta={delta:.4f} (must be < 0.01)",
                    )
                else:
                    print("  SKIP: hybrid_control OVAR could not be computed — no data")
            else:
                print("  SKIP: dry-run OVAR equivalence check — missing hybrid or hybrid_control rows")
        else:
            # Real run: require evidence of actual LLM calls.
            # A run where every hybrid row has latency_ms=0 is indistinguishable
            # from a dry run and must not be treated as experimental evidence.
            n_live_calls = (active_hybrid["latency_ms"] > 0).sum()
            all_pass &= check(
                n_live_calls > 0,
                f"Real run: at least one hybrid row has latency_ms > 0 ({n_live_calls} found)",
            )
            # A run where every multiplier is exactly 1.0 AND every rationale is
            # blank is dry-run-equivalent regardless of the dry_run stamp.
            all_trivial = (
                (active_hybrid["ss_multiplier"] == 1.0).all()
                and (active_hybrid["rationale"].fillna("").str.strip() == "").all()
            )
            all_pass &= check(
                not all_trivial,
                "Real run: not all multipliers=1.0 with blank rationales (would indicate dry-run-equivalent output)",
            )

    # Non-hybrid rows should have null ss_multiplier
    non_hybrid = df[df["policy"] != "hybrid"]
    if not non_hybrid.empty and "ss_multiplier" in non_hybrid.columns:
        non_null = non_hybrid["ss_multiplier"].notna().sum()
        all_pass &= check(
            non_null == 0,
            f"Non-hybrid rows have null ss_multiplier ({non_null} non-null found)",
        )

    # --- summary.json ---
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        print(f"  FAIL: summary.json not found")
        all_pass = False
    else:
        try:
            summaries = json.loads(summary_path.read_text())
            all_pass &= check(isinstance(summaries, list), "summary.json is a list")
            all_pass &= check(len(summaries) > 0, f"summary.json has {len(summaries)} entries")

            # Finite OVAR check: any NaN/Inf OVAR indicates division-by-zero
            # (zero-variance demand or order series — a data or formula bug).
            # chain_ovar is written as {"mean": float, "std": float} by metrics.py.
            import math
            for s in summaries:
                ovar_entry = s.get("chain_ovar")
                if isinstance(ovar_entry, dict):
                    ovar_mean = ovar_entry.get("mean")
                    if ovar_mean is not None:
                        all_pass &= check(
                            math.isfinite(ovar_mean),
                            f"Condition '{s.get('condition')}' chain_ovar mean is finite (got {ovar_mean})",
                        )

            # Live hybrid conditions (policy == "hybrid", not hybrid_control)
            # should have multiplier_stats and llm_compliance_rate.
            # Use policy field from summary, not condition name substring match.
            for s in summaries:
                if s.get("policy") == "hybrid":
                    cond_label = s.get("condition", "unknown")
                    has_mult_stats = "multiplier_stats" in s
                    all_pass &= check(
                        has_mult_stats,
                        f"Hybrid condition '{cond_label}' has multiplier_stats key",
                    )
                    has_compliance = "llm_compliance_rate" in s
                    all_pass &= check(
                        has_compliance,
                        f"Hybrid condition '{cond_label}' has llm_compliance_rate key",
                    )

        except json.JSONDecodeError as e:
            print(f"  FAIL: summary.json is not valid JSON: {e}")
            all_pass = False

    return all_pass


def main():
    parser = argparse.ArgumentParser(description="Verify V3b experiment outputs")
    parser.add_argument("--results-dir", type=str, required=True,
                        help="Directory to search for records.parquet files")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    # Caller-supplied dry_run flag is used only as a fallback for results that
    # predate the provenance dry_run stamp. verify_run_dir() always prefers the
    # value read from provenance.json when it is present.
    caller_dry_run = os.environ.get("DRY_RUN", "").strip() == "1"
    if caller_dry_run:
        print("DRY_RUN=1 in environment — used as fallback for results without provenance stamp")

    # Find all run directories (contain records.parquet)
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
