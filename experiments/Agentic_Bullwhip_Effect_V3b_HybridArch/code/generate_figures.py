"""
Figure generation — V3b hybrid architecture.

Generates 6 figures from the experiment results:

  fig1_ovar_stockouts.png    — OVAR vs stockout scatter (hybrid + V2 reference cluster)
  fig2_tier_heatmap.png      — Tier × condition OVAR heatmap
  fig3_run_variance.png      — Box plots of chain OVAR per condition (success zone band)
  fig4_multiplier_series.png — ss_multiplier time series per tier (seasonal event bands)
  fig5_order_series.png      — Order qty vs demand: exp_smoothing vs best hybrid
  fig6_compliance.png        — LLM compliance rate bars + multiplier distribution violin

Usage
-----
    # From the code/ directory, after running experiments:
    python generate_figures.py --results-dir ../results

    # Specify specific experiment directories:
    python generate_figures.py --results-dir ../results/H2/20260327T*/
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

FIGURES_DIR = Path("../figures")

# Condition display labels for plots
CONDITION_LABELS = {
    "naive_passthrough":    "Naive passthrough",
    "exp_smoothing":        "Exp smoothing (V2 benchmark)",
    "hybrid_blind_local":   "H-Blind / local",
    "hybrid_blind_azure":   "H-Blind / Azure",
    "hybrid_context_local": "H-Context / local",
    "hybrid_context_azure": "H-Context / Azure",
    "hybrid_stateful_local": "H-Stateful / local",
    "hybrid_stateful_azure": "H-Stateful / Azure",
}

# Colours
C_BENCHMARK  = "#2ca02c"   # green — exp_smoothing
C_HYBRID     = "#1f77b4"   # blue  — hybrid conditions
C_V2_REF     = "#aec7e8"   # light blue — V2 autonomous LLM cluster (reference)
C_NAIVE      = "#ff7f0e"   # orange — naive passthrough
C_AZURE      = "#9467bd"   # purple — Azure conditions
C_LOCAL      = "#1f77b4"   # blue — local conditions

# Seasonal event bands (period index, label, is_dip)
SEASONAL_EVENTS = [
    (1,  "Jan\nSankranti", False),
    (2,  "Feb\nBudget",    False),
    (3,  "Mar\nFY-end",    False),
    (4,  "Apr\nWedding",   False),
    (6,  "Jun\nMonsoon",   True),
    (7,  "Jul",            True),
    (8,  "Aug",            True),
    (10, "Oct\nNavratri",  False),
    (11, "Nov\nDiwali",    False),
    (12, "Dec\nYear-end",  False),
    (13, "Jan\nSankranti", False),
    (14, "Feb\nBudget",    False),
    (15, "Mar\nFY-end",    False),
    (16, "Apr\nWedding",   False),
    (18, "Jun\nMonsoon",   True),
    (19, "Jul",            True),
    (20, "Aug",            True),
    (22, "Oct\nNavratri",  False),
    (23, "Nov\nDiwali",    False),
    (24, "Dec\nYear-end",  False),
]

# V2 autonomous LLM OVAR reference values (from V2/V2a results for annotation)
V2_LLM_OVAR_RANGE = (4.33, 6.35)


def _load_results(results_dir: Path) -> tuple[pd.DataFrame, list[dict]]:
    """Load all records.parquet and summary.json files from a results directory."""
    all_records = []
    all_summaries = []

    for parquet_path in sorted(results_dir.rglob("records.parquet")):
        df = pd.read_parquet(parquet_path)
        all_records.append(df)

    for summary_path in sorted(results_dir.rglob("summary.json")):
        summaries = json.loads(summary_path.read_text())
        all_summaries.extend(summaries)

    if not all_records:
        print(f"No records.parquet files found in {results_dir}")
        sys.exit(1)

    return pd.concat(all_records, ignore_index=True), all_summaries


def _get_condition_stats(summaries: list[dict]) -> dict:
    """Index summaries by condition label for easy lookup."""
    return {s["condition"]: s for s in summaries}


# ---------------------------------------------------------------------------
# Figure 1: OVAR vs Stockouts scatter
# ---------------------------------------------------------------------------

def fig1_ovar_stockouts(summaries: list[dict], out_dir: Path) -> None:
    """
    Joint OVAR vs stockout scatter. Key question: did hybrid beat autonomous LLM?
    Includes V2 reference cluster (grey shaded region) for context.
    """
    fig, ax = plt.subplots(figsize=(10, 7))
    stats = _get_condition_stats(summaries)

    # V2 autonomous LLM reference region (grey background band)
    ax.axvspan(37, 44, alpha=0.08, color="grey", label="V2 autonomous LLM range\n(37–43 stockouts, OVAR 4.33–6.35)")
    ax.axhspan(V2_LLM_OVAR_RANGE[0], V2_LLM_OVAR_RANGE[1], alpha=0.04, color="grey")

    # Success zone: below exp_smoothing benchmark
    bench_ovar = stats.get("exp_smoothing", {}).get("chain_ovar", {}).get("mean", 0.54)
    bench_sto  = stats.get("exp_smoothing", {}).get("chain_stockouts", {}).get("mean", 5.0)
    ax.axhline(bench_ovar, color=C_BENCHMARK, linestyle="--", alpha=0.7, linewidth=1.5)
    ax.axvline(bench_sto,  color=C_BENCHMARK, linestyle="--", alpha=0.7, linewidth=1.5)
    ax.fill_between(
        [0, bench_sto], 0, bench_ovar,
        alpha=0.07, color=C_BENCHMARK,
        label=f"Success zone (OVAR ≤ {bench_ovar:.2f}, stockouts ≤ {bench_sto:.0f})",
    )

    # Plot each condition
    markers = {
        "naive_passthrough":     ("D", C_NAIVE,     "Naive passthrough"),
        "exp_smoothing":         ("^", C_BENCHMARK, "Exp smoothing (benchmark)"),
        "hybrid_blind_local":    ("o", C_LOCAL,     "H-Blind / local (gpt-oss:120b)"),
        "hybrid_blind_azure":    ("s", C_AZURE,     "H-Blind / Azure (gpt-4.1-mini)"),
        "hybrid_context_local":  ("o", C_LOCAL,     "H-Context / local"),
        "hybrid_context_azure":  ("s", C_AZURE,     "H-Context / Azure"),
        "hybrid_stateful_local": ("o", C_LOCAL,     "H-Stateful / local"),
        "hybrid_stateful_azure": ("s", C_AZURE,     "H-Stateful / Azure"),
    }
    fill_styles = {
        "hybrid_blind_local":    "none",
        "hybrid_blind_azure":    "none",
        "hybrid_context_local":  "full",
        "hybrid_context_azure":  "full",
        "hybrid_stateful_local": "left",
        "hybrid_stateful_azure": "left",
    }

    plotted_labels = set()
    for cond_label, s in stats.items():
        if cond_label not in markers:
            continue
        marker, color, label = markers[cond_label]
        ovar_mean  = s["chain_ovar"]["mean"]
        ovar_std   = s["chain_ovar"]["std"]
        sto_mean   = s["chain_stockouts"]["mean"]
        sto_std    = s["chain_stockouts"]["std"]

        # Deduplicate legend entries for local/azure that share label prefix
        plot_label = label if label not in plotted_labels else None
        plotted_labels.add(label)

        ax.errorbar(
            sto_mean, ovar_mean,
            xerr=sto_std, yerr=ovar_std,
            fmt=marker, color=color,
            markersize=10, capsize=4, linewidth=1.5,
            fillstyle=fill_styles.get(cond_label, "full"),
            label=plot_label,
        )
        ax.annotate(
            CONDITION_LABELS.get(cond_label, cond_label).split(" /")[0].split("\n")[0],
            (sto_mean, ovar_mean),
            textcoords="offset points", xytext=(6, 4),
            fontsize=7, alpha=0.8,
        )

    ax.set_xlabel("Chain stockout count (mean ± std across 20 runs)", fontsize=11)
    ax.set_ylabel("Chain OVAR (mean ± std)", fontsize=11)
    ax.set_title("V3b Hybrid Architecture: OVAR vs Stockout count\n(lower-left = better)", fontsize=12)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.set_ylim(bottom=0)
    ax.set_xlim(left=0)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    path = out_dir / "fig1_ovar_stockouts.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Figure 2: Tier × Condition OVAR heatmap
# ---------------------------------------------------------------------------

def fig2_tier_heatmap(summaries: list[dict], out_dir: Path) -> None:
    """Tier-level OVAR heatmap. Shows which tier benefited most from hybrid."""
    stats = _get_condition_stats(summaries)
    conditions = [c for c in CONDITION_LABELS if c in stats]

    if not conditions:
        print("fig2: no matching conditions found — skipping")
        return

    data = []
    for cond in conditions:
        row = []
        for tier in ["OEM", "Ancillary", "Component"]:
            row.append(stats[cond].get("tier_ovar", {}).get(tier, {}).get("mean", np.nan))
        data.append(row)

    data_arr = np.array(data, dtype=float)
    labels_y = [CONDITION_LABELS.get(c, c) for c in conditions]

    fig, ax = plt.subplots(figsize=(8, max(4, len(conditions) * 0.8 + 1.5)))
    im = ax.imshow(data_arr, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=max(5.0, float(np.nanmax(data_arr))))

    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["OEM", "Ancillary", "Component"], fontsize=11)
    ax.set_yticks(range(len(conditions)))
    ax.set_yticklabels(labels_y, fontsize=9)

    for i in range(len(conditions)):
        for j in range(3):
            val = data_arr[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=9, color="black" if val < 3.0 else "white")

    plt.colorbar(im, ax=ax, label="OVAR (lower = better)")
    ax.set_title("Tier-level OVAR by condition\n(green < 1.0 = dampening; red > 3.0 = bullwhip)", fontsize=11)
    fig.tight_layout()
    path = out_dir / "fig2_tier_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Figure 3: Run variance box plots
# ---------------------------------------------------------------------------

def fig3_run_variance(records_df: pd.DataFrame, out_dir: Path) -> None:
    """
    Box plots of chain OVAR across 20 runs per condition.
    Includes success zone band and V2 reference lines.
    """
    from metrics import compute_ovar, compute_chain_ovar, _active_periods

    conditions_ordered = [
        "exp_smoothing",
        "hybrid_blind_local", "hybrid_blind_azure",
        "hybrid_context_local", "hybrid_context_azure",
        "hybrid_stateful_local", "hybrid_stateful_azure",
    ]

    data_by_cond = {}
    for cond in conditions_ordered:
        grp = records_df[records_df["condition_label"] == cond]
        if grp.empty:
            continue
        ovar_df = compute_ovar(grp)
        chain   = compute_chain_ovar(ovar_df)
        data_by_cond[cond] = chain.values

    if not data_by_cond:
        print("fig3: no data found — skipping")
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    # V2 autonomous LLM OVAR range (grey band)
    ax.axhspan(V2_LLM_OVAR_RANGE[0], V2_LLM_OVAR_RANGE[1],
               alpha=0.10, color="grey", label="V2 autonomous LLM OVAR range (4.33–6.35)")

    cond_list = [c for c in conditions_ordered if c in data_by_cond]
    box_data  = [data_by_cond[c] for c in cond_list]
    labels    = [CONDITION_LABELS.get(c, c).replace(" / ", "\n") for c in cond_list]

    colors = []
    for c in cond_list:
        if c == "exp_smoothing":
            colors.append(C_BENCHMARK)
        elif "azure" in c:
            colors.append(C_AZURE)
        else:
            colors.append(C_LOCAL)

    bp = ax.boxplot(box_data, patch_artist=True, medianprops=dict(color="black", linewidth=2))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    # exp_smoothing benchmark line
    if "exp_smoothing" in data_by_cond:
        bench_val = float(np.median(data_by_cond["exp_smoothing"]))
        ax.axhline(bench_val, color=C_BENCHMARK, linestyle="--", linewidth=1.5, alpha=0.8,
                   label=f"Exp smoothing OVAR = {bench_val:.2f}")
        # Success zone shading
        ax.axhspan(0, bench_val, alpha=0.06, color=C_BENCHMARK, label="Success zone (OVAR ≤ benchmark)")

    ax.set_xticks(range(1, len(cond_list) + 1))
    ax.set_xticklabels(labels, fontsize=9, rotation=20, ha="right")
    ax.set_ylabel("Chain OVAR", fontsize=11)
    ax.set_title("Chain OVAR distribution across 20 runs per condition\n(lower = better; green band = success zone)", fontsize=11)
    ax.legend(fontsize=9, loc="upper right")
    ax.set_ylim(bottom=0)
    ax.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    path = out_dir / "fig3_run_variance.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Figure 4: Safety stock multiplier time series
# ---------------------------------------------------------------------------

def fig4_multiplier_series(records_df: pd.DataFrame, out_dir: Path) -> None:
    """
    ss_multiplier over time per tier (median-OVAR run).
    Shows whether LLM raises multiplier at seasonal events.
    """
    from metrics import compute_ovar, compute_chain_ovar

    # Find the median-OVAR run for each hybrid context condition
    hybrid_records = records_df[records_df["policy"] == "hybrid"].copy()
    if hybrid_records.empty:
        print("fig4: no hybrid records found — skipping")
        return

    # Pick the best condition (H-Context local as primary, fall back to whatever exists)
    preferred = ["hybrid_context_local", "hybrid_context_azure",
                 "hybrid_stateful_local", "hybrid_blind_local"]
    cond_to_plot = None
    for pref in preferred:
        if pref in hybrid_records["condition_label"].values:
            cond_to_plot = pref
            break
    if cond_to_plot is None:
        cond_to_plot = hybrid_records["condition_label"].iloc[0]

    grp = hybrid_records[hybrid_records["condition_label"] == cond_to_plot].copy()
    ovar_df = compute_ovar(grp)
    chain   = compute_chain_ovar(ovar_df)
    median_run = chain.abs().sub(chain.median()).abs().idxmin()

    run_df = grp[grp["run_id"] == median_run].copy()
    active = run_df[run_df["period"] < run_df["period"].max()]

    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    fig.suptitle(
        f"Safety Stock Multiplier per Period — {CONDITION_LABELS.get(cond_to_plot, cond_to_plot)}\n"
        f"(median-OVAR run; seasonal event bands shaded)",
        fontsize=11,
    )

    for ax_i, tier in enumerate(["OEM", "Ancillary", "Component"]):
        ax = axes[ax_i]
        tier_df = active[active["tier"] == tier].sort_values("period")

        # Seasonal event bands
        for period_num, _, is_dip in SEASONAL_EVENTS:
            color = "#aec7e8" if is_dip else "#ffbb78"
            ax.axvspan(period_num - 0.4, period_num + 0.4, alpha=0.25, color=color)

        multiplier = tier_df["ss_multiplier"].values
        periods    = tier_df["period"].values

        ax.plot(periods, multiplier, "b-o", markersize=4, linewidth=1.5, label="ss_multiplier")
        ax.axhline(1.0, color="grey", linestyle="--", linewidth=1, alpha=0.7, label="Neutral (1.0)")
        ax.axhline(1.1, color="orange", linestyle=":", linewidth=0.8, alpha=0.6)
        ax.axhline(0.9, color="orange", linestyle=":", linewidth=0.8, alpha=0.6)

        ax.set_ylabel(f"{tier}\nmultiplier", fontsize=9)
        ax.set_ylim(0.3, 3.3)
        ax.grid(True, alpha=0.3)

        if ax_i == 0:
            ax.legend(fontsize=8, loc="upper right")

    axes[-1].set_xlabel("Period", fontsize=10)

    # Add event labels on top plot
    ax = axes[0]
    for period_num, label, is_dip in SEASONAL_EVENTS:
        if period_num <= active["period"].max():
            ax.text(period_num, 3.1, label, ha="center", va="bottom",
                    fontsize=5.5, rotation=45, color="grey")

    fig.tight_layout()
    path = out_dir / "fig4_multiplier_series.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Figure 5: Order time series comparison
# ---------------------------------------------------------------------------

def fig5_order_series(records_df: pd.DataFrame, out_dir: Path) -> None:
    """
    Order quantities over 24 periods: exp_smoothing baseline vs best hybrid condition.
    Three subplots, one per tier. Shows how much the hybrid closes the V2 gap.
    """
    from metrics import compute_ovar, compute_chain_ovar

    # Select the baseline run
    baseline = records_df[records_df["condition_label"] == "exp_smoothing"]
    if baseline.empty:
        baseline = records_df[records_df["policy"] == "exp_smoothing"]

    # Select the best hybrid condition (lowest mean OVAR)
    hybrid = records_df[records_df["policy"] == "hybrid"]
    if hybrid.empty:
        print("fig5: no hybrid records found — skipping")
        return

    best_hybrid_cond = None
    best_ovar = float("inf")
    for cond, grp in hybrid.groupby("condition_label"):
        ovar_df = compute_ovar(grp)
        chain   = compute_chain_ovar(ovar_df)
        mean_ovar = float(chain.mean())
        if mean_ovar < best_ovar:
            best_ovar = mean_ovar
            best_hybrid_cond = cond

    hybrid_grp = hybrid[hybrid["condition_label"] == best_hybrid_cond]
    hybrid_ovar_df = compute_ovar(hybrid_grp)
    hybrid_chain   = compute_chain_ovar(hybrid_ovar_df)
    median_hybrid_run = hybrid_chain.abs().sub(hybrid_chain.median()).abs().idxmin()

    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    fig.suptitle(
        f"Order quantities over time\nExp smoothing vs {CONDITION_LABELS.get(best_hybrid_cond, best_hybrid_cond)} "
        f"(OVAR={best_ovar:.2f})",
        fontsize=11,
    )

    for ax_i, tier in enumerate(["OEM", "Ancillary", "Component"]):
        ax = axes[ax_i]

        # Seasonal event bands
        for period_num, _, is_dip in SEASONAL_EVENTS:
            color = "#aec7e8" if is_dip else "#ffbb78"
            ax.axvspan(period_num - 0.4, period_num + 0.4, alpha=0.20, color=color)

        # Baseline run (single deterministic run)
        if not baseline.empty:
            b_tier = baseline[baseline["tier"] == tier].sort_values("period")
            b_tier = b_tier[b_tier["period"] < b_tier["period"].max()]
            ax.plot(b_tier["period"], b_tier["order_placed"], "-",
                    color=C_BENCHMARK, linewidth=2, label="Exp smoothing")
            ax.plot(b_tier["period"], b_tier["demand_received"], "k--",
                    linewidth=1, alpha=0.5, label="Demand received")

        # Best hybrid (median run)
        h_tier = hybrid_grp[
            (hybrid_grp["tier"] == tier) & (hybrid_grp["run_id"] == median_hybrid_run)
        ].sort_values("period")
        h_tier = h_tier[h_tier["period"] < h_tier["period"].max()]
        ax.plot(h_tier["period"], h_tier["order_placed"], "-",
                color=C_HYBRID, linewidth=1.5, alpha=0.9, label=f"Best hybrid (median run)")

        ax.set_ylabel(f"{tier}\norder qty", fontsize=9)
        ax.grid(True, alpha=0.3)
        if ax_i == 0:
            ax.legend(fontsize=8, loc="upper right")

    axes[-1].set_xlabel("Period", fontsize=10)
    fig.tight_layout()
    path = out_dir / "fig5_order_series.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Figure 6: LLM compliance + multiplier distribution
# ---------------------------------------------------------------------------

def fig6_compliance(summaries: list[dict], records_df: pd.DataFrame, out_dir: Path) -> None:
    """
    Two panels:
      Left:  Bar chart of LLM compliance rate per hybrid condition.
      Right: Violin plot of ss_multiplier distribution per hybrid condition.
    """
    hybrid_records = records_df[records_df["policy"] == "hybrid"].copy()
    if hybrid_records.empty:
        print("fig6: no hybrid records — skipping")
        return

    hybrid_conditions = sorted(hybrid_records["condition_label"].unique())
    stats = _get_condition_stats(summaries)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # --- Left: compliance rate bars ---
    compliance_rates = []
    bar_labels = []
    for cond in hybrid_conditions:
        s = stats.get(cond, {})
        rate = s.get("llm_compliance_rate", {}).get("mean", None)
        compliance_rates.append(rate if rate is not None else 0.0)
        bar_labels.append(CONDITION_LABELS.get(cond, cond).replace(" / ", "\n"))

    colors = [C_AZURE if "azure" in c else C_LOCAL for c in hybrid_conditions]
    bars = ax1.bar(range(len(hybrid_conditions)), compliance_rates, color=colors, alpha=0.7)
    ax1.axhline(0.95, color="red", linestyle="--", linewidth=1.5, label="95% threshold")
    ax1.set_xticks(range(len(hybrid_conditions)))
    ax1.set_xticklabels(bar_labels, fontsize=8, rotation=15, ha="right")
    ax1.set_ylabel("LLM compliance rate\n(no clamp + no fallback)", fontsize=9)
    ax1.set_ylim(0, 1.05)
    ax1.set_title("LLM output quality\n(compliance = valid multiplier, no clamping)", fontsize=10)
    ax1.legend(fontsize=9)
    ax1.grid(True, axis="y", alpha=0.3)

    # Add value labels on bars
    for bar, val in zip(bars, compliance_rates):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + 0.01,
                 f"{val:.2%}", ha="center", va="bottom", fontsize=8)

    # --- Right: multiplier distribution violin ---
    active = hybrid_records[hybrid_records["period"] < hybrid_records["period"].max()].copy()
    active = active[active["ss_multiplier"].notna()]

    violin_data  = []
    violin_labels = []
    for cond in hybrid_conditions:
        grp = active[active["condition_label"] == cond]["ss_multiplier"]
        if not grp.empty:
            violin_data.append(grp.values)
            violin_labels.append(CONDITION_LABELS.get(cond, cond).replace(" / ", "\n"))

    if violin_data:
        parts = ax2.violinplot(violin_data, positions=range(len(violin_data)),
                               showmedians=True, showextrema=True)
        for pc in parts["bodies"]:
            pc.set_alpha(0.5)

        ax2.axhline(1.0, color="grey", linestyle="--", linewidth=1.5, label="Neutral (1.0)", alpha=0.8)
        ax2.axhline(1.1, color="orange", linestyle=":", linewidth=1, alpha=0.6)
        ax2.axhline(0.9, color="orange", linestyle=":", linewidth=1, alpha=0.6, label="Threshold (±10%)")
        ax2.set_xticks(range(len(violin_labels)))
        ax2.set_xticklabels(violin_labels, fontsize=8, rotation=15, ha="right")
        ax2.set_ylabel("ss_multiplier value", fontsize=9)
        ax2.set_ylim(0.3, 3.3)
        ax2.set_title("Safety stock multiplier distribution\n(all active periods, all runs)", fontsize=10)
        ax2.legend(fontsize=9)
        ax2.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    path = out_dir / "fig6_compliance.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate V3b figures")
    parser.add_argument("--results-dir", type=str, default="../results",
                        help="Root results directory to scan for records.parquet files")
    parser.add_argument("--figures-dir", type=str, default=None,
                        help="Output directory for figures (default: ../figures)")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    out_dir = Path(args.figures_dir) if args.figures_dir else FIGURES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading results from: {results_dir}")
    records_df, summaries = _load_results(results_dir)
    print(f"Loaded {len(records_df):,} records, {len(summaries)} condition summaries")

    fig1_ovar_stockouts(summaries, out_dir)
    fig2_tier_heatmap(summaries, out_dir)
    fig3_run_variance(records_df, out_dir)
    fig4_multiplier_series(records_df, out_dir)
    fig5_order_series(records_df, out_dir)
    fig6_compliance(summaries, records_df, out_dir)

    print(f"\nAll figures saved to: {out_dir}")


if __name__ == "__main__":
    main()
