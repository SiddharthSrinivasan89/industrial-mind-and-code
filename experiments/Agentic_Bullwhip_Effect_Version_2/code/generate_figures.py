#!/usr/bin/env python3
"""Generate all figures for the Agentic Bullwhip V2 experiment report.

Figures produced:
  fig1_ovar_stockouts.png   — OVAR vs Stockouts scatter with error bars
  fig2_tier_ovar_heatmap.png — Tier-level OVAR heatmap
  fig3_run_variance.png      — Box plots of per-run chain OVAR across 20 runs
  fig4_order_time_series.png — Order quantities vs demand over 25 periods

Run from the experiment root:
    python code/generate_figures.py
"""

import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent.parent  # …/Agentic_Bullwhip_Effect_Version_2/
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)

# ── Directory manifest (timestamp → key) ──────────────────────────────────
DIRS = {
    "baselines": RESULTS / "baselines" / "20260319T040819",
    "E1_azure":  RESULTS / "E1"        / "20260319T052904",
    "E1_local":  RESULTS / "E1"        / "20260319T055959",
    "E2_local":  RESULTS / "E2"        / "20260319T100459",
    "E2_azure":  RESULTS / "E2"        / "20260319T135556",
}

# ── Display labels ─────────────────────────────────────────────────────────
LABELS = {
    ("baselines", "exp_smoothing"):       "exp_smoothing",
    ("baselines", "naive_passthrough"):   "naive_passthrough",
    ("baselines", "order_up_to"):         "order_up_to",
    ("E1_azure",  "blind_lightweight"):   "L-Blind (Azure)\ngpt-4.1-mini",
    ("E1_azure",  "context_lightweight"): "L-Context (Azure)\ngpt-4.1-mini",
    ("E1_local",  "blind_lightweight"):   "L-Blind (Local)\nphi4:14b",
    ("E1_local",  "context_lightweight"): "L-Context (Local)\nphi4:14b",
    ("E2_local",  "blind_reasoning"):     "R-Blind (Local)\ngpt-oss:120b",
    ("E2_local",  "context_reasoning"):   "R-Context (Local)\ngpt-oss:120b",
    ("E2_azure",  "blind_reasoning"):     "R-Blind (Azure)\no4-mini",
    ("E2_azure",  "context_reasoning"):   "R-Context (Azure)\no4-mini",
}

HEURISTIC_CONDITIONS = {"exp_smoothing", "naive_passthrough", "order_up_to"}

# Colour palette for box plots / time series
PALETTE = {
    "L-Blind (Azure)\ngpt-4.1-mini":   "#1f77b4",
    "L-Context (Azure)\ngpt-4.1-mini": "#aec7e8",
    "L-Blind (Local)\nphi4:14b":       "#ff7f0e",
    "L-Context (Local)\nphi4:14b":     "#ffbb78",
    "R-Blind (Azure)\no4-mini":        "#9467bd",
    "R-Context (Azure)\no4-mini":      "#c5b0d5",
    "R-Blind (Local)\ngpt-oss:120b":   "#8c564b",
    "R-Context (Local)\ngpt-oss:120b": "#c49c94",
}

# ── Global style ───────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":     "serif",
    "font.size":       9,
    "axes.titlesize":  10,
    "axes.labelsize":  9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "savefig.dpi":     300,
    "savefig.bbox":    "tight",
})


# ══════════════════════════════════════════════════════════════════════════
# Data loading helpers
# ══════════════════════════════════════════════════════════════════════════

def load_all_summaries() -> pd.DataFrame:
    """Load every summary.json and return a flat DataFrame."""
    rows = []
    for key, d in DIRS.items():
        path = d / "summary.json"
        data = json.loads(path.read_text())
        for rec in data:
            cond = rec["condition"]
            label = LABELS.get((key, cond), f"{key}/{cond}")
            rows.append({
                "dir_key":        key,
                "condition":      cond,
                "label":          label,
                "is_heuristic":   cond in HEURISTIC_CONDITIONS,
                "chain_ovar_mean":   rec["chain_ovar"]["mean"],
                "chain_ovar_std":    rec["chain_ovar"]["std"] or 0.0,
                "stockouts_mean":    rec["chain_stockouts"]["mean"],
                "stockouts_std":     rec["chain_stockouts"]["std"] or 0.0,
                "oem_ovar_mean":     rec["tier_ovar"]["OEM"]["mean"],
                "anc_ovar_mean":     rec["tier_ovar"]["Ancillary"]["mean"],
                "comp_ovar_mean":    rec["tier_ovar"]["Component"]["mean"],
            })
    return pd.DataFrame(rows)


def load_records(dir_key: str) -> pd.DataFrame:
    """Load records.parquet for a given dir_key."""
    path = DIRS[dir_key] / "records.parquet"
    return pd.read_parquet(path)


def compute_run_ovar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a records DataFrame, compute chain OVAR per run.
    Excludes period 25 (close-out, orders=0).
    Returns a DataFrame with columns: run_id, condition, label, chain_ovar.
    """
    df = df[df["period"] <= 24].copy()
    rows = []
    for (run_id, condition, tier), grp in df.groupby(["run_id", "condition_label", "tier"]):
        var_order  = grp["order_placed"].var(ddof=1)
        var_demand = grp["demand_received"].var(ddof=1)
        ovar = var_order / var_demand if var_demand > 0 else np.nan
        rows.append({"run_id": run_id, "condition": condition, "tier": tier, "tier_ovar": ovar})
    tier_df = pd.DataFrame(rows)
    chain = tier_df.groupby(["run_id", "condition"])["tier_ovar"].mean().reset_index()
    chain.columns = ["run_id", "condition", "chain_ovar"]
    return chain


# ══════════════════════════════════════════════════════════════════════════
# Figure 1 — OVAR vs Stockouts scatter
# ══════════════════════════════════════════════════════════════════════════

def fig1_ovar_stockouts(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))

    heuristics = df[df["is_heuristic"]]
    llms       = df[~df["is_heuristic"]]

    # LLMs — coloured circles
    for _, row in llms.iterrows():
        color = PALETTE.get(row["label"], "#888888")
        ax.errorbar(
            row["chain_ovar_mean"], row["stockouts_mean"],
            xerr=row["chain_ovar_std"], yerr=row["stockouts_std"],
            fmt="o", color=color, markersize=7, capsize=3,
            elinewidth=1, markeredgewidth=0.5, markeredgecolor="white",
            zorder=3,
        )
        short = row["label"].replace("\n", " ")
        ax.annotate(
            short,
            (row["chain_ovar_mean"], row["stockouts_mean"]),
            textcoords="offset points", xytext=(5, 3),
            fontsize=6.5, color=color,
        )

    # Heuristics — triangles
    heuristic_colors = {
        "exp_smoothing":    "#2ca02c",
        "naive_passthrough":"#7f7f7f",
        "order_up_to":      "#bcbd22",
    }
    for _, row in heuristics.iterrows():
        color = heuristic_colors.get(row["condition"], "#333333")
        ax.plot(
            row["chain_ovar_mean"], row["stockouts_mean"],
            "^", color=color, markersize=10, zorder=4,
            markeredgewidth=0.5, markeredgecolor="white",
        )
        ax.annotate(
            row["condition"],
            (row["chain_ovar_mean"], row["stockouts_mean"]),
            textcoords="offset points", xytext=(5, -8),
            fontsize=7.5, color=color, fontweight="bold",
        )

    ax.set_xlabel("Chain-average OVAR (mean ± std)")
    ax.set_ylabel("Chain stockout count (mean ± std)")
    ax.set_title("Figure 1: OVAR vs Stockout Performance — All Conditions")

    # Legend entries
    legend_handles = [
        mpatches.Patch(color="#2ca02c", label="Heuristic baselines (▲)"),
        mpatches.Patch(color="#1f77b4", label="LLM conditions (●)"),
    ]
    ax.legend(handles=legend_handles, fontsize=7.5, framealpha=0.7)
    ax.set_xlim(left=-0.2)
    ax.set_ylim(bottom=-2)

    fig.tight_layout()
    fig.savefig(FIGURES / "fig1_ovar_stockouts.png")
    plt.close(fig)
    print("✓ fig1_ovar_stockouts.png")


# ══════════════════════════════════════════════════════════════════════════
# Figure 2 — Tier-level OVAR heatmap
# ══════════════════════════════════════════════════════════════════════════

def fig2_tier_ovar_heatmap(df: pd.DataFrame) -> None:
    # Build a matrix: rows = conditions, columns = tiers
    # Sort by chain OVAR ascending (best at top)
    df_sorted = df.sort_values("chain_ovar_mean")

    labels = df_sorted["label"].str.replace("\n", " ")
    data = df_sorted[["oem_ovar_mean", "anc_ovar_mean", "comp_ovar_mean"]].values

    fig, ax = plt.subplots(figsize=(5.5, 5))
    im = sns.heatmap(
        data,
        ax=ax,
        annot=True, fmt=".2f", annot_kws={"size": 8},
        xticklabels=["OEM", "Ancillary", "Component"],
        yticklabels=labels.tolist(),
        cmap="YlOrRd",
        linewidths=0.3,
        linecolor="white",
        cbar_kws={"label": "OVAR", "shrink": 0.7},
    )
    ax.set_title("Figure 2: Tier-Level OVAR by Condition\n(sorted by chain-average OVAR, ascending)")
    ax.set_ylabel("")
    ax.tick_params(axis="y", labelsize=8)

    fig.tight_layout()
    fig.savefig(FIGURES / "fig2_tier_ovar_heatmap.png")
    plt.close(fig)
    print("✓ fig2_tier_ovar_heatmap.png")


# ══════════════════════════════════════════════════════════════════════════
# Figure 3 — Run variance box plots
# ══════════════════════════════════════════════════════════════════════════

def fig3_run_variance() -> None:
    frames = []
    for key in ("E1_azure", "E1_local", "E2_azure", "E2_local"):
        rec = load_records(key)
        run_ovar = compute_run_ovar(rec)
        # Attach display labels
        run_ovar["label"] = run_ovar["condition"].map(
            lambda c, k=key: LABELS.get((k, c), c)
        )
        frames.append(run_ovar)

    all_runs = pd.concat(frames, ignore_index=True)

    # Order: E1 Azure blind, E1 Azure context, E1 Local blind, E1 Local context,
    #        E2 Azure blind, E2 Azure context, E2 Local blind, E2 Local context
    order = [
        "L-Blind (Azure)\ngpt-4.1-mini",
        "L-Context (Azure)\ngpt-4.1-mini",
        "L-Blind (Local)\nphi4:14b",
        "L-Context (Local)\nphi4:14b",
        "R-Blind (Azure)\no4-mini",
        "R-Context (Azure)\no4-mini",
        "R-Blind (Local)\ngpt-oss:120b",
        "R-Context (Local)\ngpt-oss:120b",
    ]
    # Filter to labels that actually exist
    order = [o for o in order if o in all_runs["label"].values]

    colors = [PALETTE.get(o, "#888888") for o in order]

    fig, ax = plt.subplots(figsize=(9, 4.5))

    bp = ax.boxplot(
        [all_runs[all_runs["label"] == o]["chain_ovar"].values for o in order],
        patch_artist=True,
        medianprops={"color": "black", "linewidth": 1.5},
        whiskerprops={"linewidth": 1},
        capprops={"linewidth": 1},
        flierprops={"marker": ".", "markersize": 4, "alpha": 0.5},
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.8)

    # Reference lines
    ax.axhline(0.5445, color="#2ca02c", linestyle="--", linewidth=1.2,
               label="exp_smoothing (0.54)", zorder=2)
    ax.axhline(1.00, color="#7f7f7f", linestyle=":", linewidth=1.2,
               label="naive_passthrough (1.00)", zorder=2)

    short_labels = [o.replace("\n", "\n") for o in order]
    ax.set_xticks(range(1, len(order) + 1))
    ax.set_xticklabels(short_labels, fontsize=7.5)
    ax.set_ylabel("Chain OVAR (per run)")
    ax.set_title("Figure 3: Distribution of Chain OVAR Across 20 Independent Runs per LLM Condition")
    ax.legend(fontsize=7.5, framealpha=0.7)

    # Vertical separator between E1 and E2 groups
    if len(order) >= 5:
        ax.axvline(4.5, color="#cccccc", linewidth=1, linestyle="-")
        ax.text(2.5, ax.get_ylim()[1] * 0.97, "E1 — Lightweight models",
                ha="center", fontsize=7.5, color="#555555")
        ax.text(6.5, ax.get_ylim()[1] * 0.97, "E2 — Reasoning models",
                ha="center", fontsize=7.5, color="#555555")

    fig.tight_layout()
    fig.savefig(FIGURES / "fig3_run_variance.png")
    plt.close(fig)
    print("✓ fig3_run_variance.png")


# ══════════════════════════════════════════════════════════════════════════
# Figure 4 — Order time series
# ══════════════════════════════════════════════════════════════════════════

ELEVATION_MONTHS = {"Jan", "Feb", "Mar", "Apr", "May", "Oct", "Nov", "Dec"}
DIP_MONTHS       = {"Jun", "Jul", "Aug"}


def _month_abbr(calendar_month: str) -> str:
    return calendar_month.split()[0]  # "Nov 2025" → "Nov"


def fig4_order_time_series() -> None:
    # ── Load baselines (exp_smoothing) ────────────────────────────────────
    base_rec = load_records("baselines")
    exp = (
        base_rec[base_rec["policy"] == "exp_smoothing"]
        .sort_values(["tier", "period"])
        .copy()
    )

    # ── Load E1 Azure — find median-OVAR run for blind_lightweight ────────
    e1_az = load_records("E1_azure")
    blind_lw = e1_az[e1_az["condition_label"] == "blind_lightweight"].copy()
    run_ovar = compute_run_ovar(blind_lw)
    median_ovar = run_ovar["chain_ovar"].median()
    # Pick run closest to median
    run_ovar["dist"] = (run_ovar["chain_ovar"] - median_ovar).abs()
    best_run = run_ovar.loc[run_ovar["dist"].idxmin(), "run_id"]
    llm_run = blind_lw[blind_lw["run_id"] == best_run].sort_values(["tier", "period"]).copy()

    tiers = ["OEM", "Ancillary", "Component"]
    fig, axes = plt.subplots(3, 1, figsize=(9, 7), sharex=True)

    # Calendar month labels from period (same across conditions)
    periods = sorted(exp["period"].unique())
    cal_months = (
        exp[exp["tier"] == "OEM"]
        .sort_values("period")["calendar_month"]
        .tolist()
    )

    for i, (ax, tier) in enumerate(zip(axes, tiers)):
        exp_tier = exp[exp["tier"] == tier].sort_values("period")
        llm_tier = llm_run[llm_run["tier"] == tier].sort_values("period")

        # Shade seasonal bands
        for p, cal in enumerate(cal_months, start=1):
            abbr = _month_abbr(cal)
            if abbr in ELEVATION_MONTHS:
                ax.axvspan(p - 0.5, p + 0.5, alpha=0.06, color="#ffd700", zorder=0)
            elif abbr in DIP_MONTHS:
                ax.axvspan(p - 0.5, p + 0.5, alpha=0.08, color="#87ceeb", zorder=0)

        # Demand line (grey, behind)
        ax.plot(
            exp_tier["period"], exp_tier["demand_received"],
            color="#aaaaaa", linewidth=1.2, linestyle="-",
            label="Demand" if i == 0 else "_nolegend_", zorder=1,
        )
        # exp_smoothing
        ax.plot(
            exp_tier["period"], exp_tier["order_placed"],
            color="#2ca02c", linewidth=1.5, linestyle="-",
            label="exp_smoothing" if i == 0 else "_nolegend_", zorder=2,
        )
        # LLM blind
        ax.plot(
            llm_tier["period"], llm_tier["order_placed"],
            color="#d62728", linewidth=1.2, linestyle="-", alpha=0.85,
            label="L-Blind (Azure) — gpt-4.1-mini" if i == 0 else "_nolegend_", zorder=3,
        )

        ax.set_ylabel(f"{tier}\nOrder qty", fontsize=8)
        ax.set_ylim(bottom=0)

    # X-axis tick labels: every period, rotated
    axes[-1].set_xticks(periods)
    axes[-1].set_xticklabels(cal_months, rotation=45, ha="right", fontsize=7)
    axes[-1].set_xlabel("Period (calendar month)")

    # Legend on top panel
    axes[0].legend(fontsize=7.5, framealpha=0.7, loc="upper right")

    # Seasonal band legend as text annotation
    axes[0].annotate(
        "■ elevation event   ■ monsoon dip",
        xy=(0.01, 0.92), xycoords="axes fraction",
        fontsize=6.5, color="#888888",
    )

    fig.suptitle(
        "Figure 4: Order Quantities vs Demand over 25 Periods\n"
        "(exp_smoothing vs L-Blind Azure, median-OVAR run)",
        fontsize=10, y=1.01,
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "fig4_order_time_series.png")
    plt.close(fig)
    print("✓ fig4_order_time_series.png")


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("Loading summaries…")
    df = load_all_summaries()

    print("Generating Figure 1…")
    fig1_ovar_stockouts(df)

    print("Generating Figure 2…")
    fig2_tier_ovar_heatmap(df)

    print("Generating Figure 3…")
    fig3_run_variance()

    print("Generating Figure 4…")
    fig4_order_time_series()

    print(f"\nAll figures saved to {FIGURES}/")


if __name__ == "__main__":
    main()
