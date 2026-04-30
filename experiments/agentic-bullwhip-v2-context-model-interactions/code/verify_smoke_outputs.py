#!/usr/bin/env python3
"""Validate smoke-test outputs for baselines, E1, and E2.

Checks:
- Required experiments and conditions exist in the specified (or latest) run folder
- records.parquet exists and has the correct row count (n_conditions × n_periods × n_tiers)
- n_runs in summary matches what was requested
- chain_ovar values are not null
- pattern_score is null for baselines and non-null for E1/E2
- demand checksum is consistent across all experiments in the same run
- No bare NaN token appears in summary/provenance JSON files
- No order_clamped events occurred (warns if any found)

Usage:
    python verify_smoke_outputs.py --results-dir test_runs
    python verify_smoke_outputs.py --results-dir test_runs --run-dirs baselines=20260318T033153 E1=20260318T032928
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

REQUIRED = {
    "baselines": {"naive_passthrough", "order_up_to", "exp_smoothing"},
    "E1": {"blind_lightweight", "context_lightweight"},
    "E2": {"blind_reasoning", "context_reasoning"},
}

TIERS    = 3
PERIODS  = 25  # 24 active + 1 close-out


def latest_run_dir(root: Path, experiment: str) -> Path:
    exp_dir = root / experiment
    if not exp_dir.exists():
        raise FileNotFoundError(f"Missing experiment folder: {exp_dir}")
    runs = sorted([p for p in exp_dir.iterdir() if p.is_dir()])
    if not runs:
        raise FileNotFoundError(f"No runs found under: {exp_dir}")
    return runs[-1]


def assert_no_bare_nan(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "NaN" in text:
        raise AssertionError(f"Bare NaN token found in {path}")


def load_summary(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise AssertionError(f"Expected list summary in {path}")
    return data


def validate_experiment(
    root: Path,
    experiment: str,
    run_dir: Path | None = None,
    expected_runs: int = 1,
    expected_checksum: str | None = None,
) -> str:
    """Validate one experiment directory. Returns its demand checksum."""
    if run_dir is None:
        run_dir = latest_run_dir(root, experiment)

    summary_path    = run_dir / "summary.json"
    provenance_path = run_dir / "provenance.json"
    records_path    = run_dir / "records.parquet"

    # --- Required files ---
    for p in (summary_path, provenance_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing {p}")

    # --- No bare NaN ---
    assert_no_bare_nan(summary_path)
    assert_no_bare_nan(provenance_path)

    # --- Provenance checksum consistency ---
    with provenance_path.open() as f:
        prov = json.load(f)
    checksum = prov.get("demand_checksum_sha256", "")
    if expected_checksum and checksum != expected_checksum:
        raise AssertionError(
            f"{experiment}: demand checksum mismatch "
            f"(expected {expected_checksum[:12]}…, got {checksum[:12]}…)"
        )

    # --- records.parquet exists and has correct row count ---
    if not records_path.exists():
        raise FileNotFoundError(f"Missing records.parquet in {run_dir}")
    if HAS_PANDAS:
        df = pd.read_parquet(records_path)
        n_conditions = len(REQUIRED[experiment])
        expected_rows = n_conditions * expected_runs * PERIODS * TIERS
        if len(df) != expected_rows:
            raise AssertionError(
                f"{experiment}: expected {expected_rows} rows in records.parquet "
                f"({n_conditions} conditions × {expected_runs} runs × {PERIODS} periods × {TIERS} tiers), "
                f"got {len(df)}"
            )
        # Check for order clamp events
        if "order_clamped" in df.columns:
            clamped = df["order_clamped"].sum()
            if clamped > 0:
                print(
                    f"  WARNING {experiment}: {clamped} order_clamped events — "
                    f"review raw_order_quantity column before full run",
                    file=sys.stderr,
                )

    # --- Summary conditions and metrics ---
    summary    = load_summary(summary_path)
    by_cond    = {row.get("condition"): row for row in summary}
    missing    = REQUIRED[experiment] - set(by_cond)
    if missing:
        raise AssertionError(f"{experiment}: missing conditions {sorted(missing)}")

    for condition in REQUIRED[experiment]:
        row = by_cond[condition]

        # n_runs matches expected
        if row.get("n_runs") != expected_runs:
            raise AssertionError(
                f"{experiment}/{condition}: expected n_runs={expected_runs}, "
                f"got {row.get('n_runs')}"
            )

        if row.get("chain_ovar", {}).get("mean") is None:
            raise AssertionError(f"{experiment}/{condition}: chain_ovar.mean is null")

        pattern_mean = row.get("pattern_score", {}).get("mean")
        if experiment == "baselines":
            if pattern_mean is not None:
                raise AssertionError(
                    f"{experiment}/{condition}: expected null pattern_score.mean, got {pattern_mean}"
                )
        else:
            if pattern_mean is None:
                raise AssertionError(f"{experiment}/{condition}: pattern_score.mean is null")

    print(f"OK: {experiment} -> {run_dir.name}")
    return checksum


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="test_runs")
    parser.add_argument(
        "--run-dirs", nargs="*", metavar="EXP=TIMESTAMP",
        help="Pin specific run dirs, e.g. E1=20260318T032928 E2=20260318T040840",
    )
    parser.add_argument("--runs", type=int, default=1,
                        help="Expected number of runs per condition (default 1 for smoke)")
    args = parser.parse_args()

    root = Path(args.results_dir)

    # Parse pinned dirs
    pinned: dict[str, Path] = {}
    if args.run_dirs:
        for token in args.run_dirs:
            exp, ts = token.split("=", 1)
            pinned[exp] = root / exp / ts

    checksum = None
    for experiment in ("baselines", "E1", "E2"):
        run_dir = pinned.get(experiment)
        checksum = validate_experiment(
            root, experiment,
            run_dir=run_dir,
            expected_runs=args.runs,
            expected_checksum=checksum,
        )

    print("Smoke output validation passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
