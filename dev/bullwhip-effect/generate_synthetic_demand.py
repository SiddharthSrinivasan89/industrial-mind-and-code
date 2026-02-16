#!/usr/bin/env python3
"""
Synthetic Demand Data Generator
================================
Generates 24-month weekly demand for light bulbs in India.
Patterns embedded: Diwali, wedding seasons, monsoon dip,
Sankranti/Pongal, promo spikes, annual growth, noise.

Run:
    python generate_synthetic_demand.py

Output in: /home/sid/industrial-mind-and-code/dev/data/synthetic/
"""

import json
import os
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# =============================================================================
# Config
# =============================================================================
OUTPUT_DIR = "/home/sid/industrial-mind-and-code/dev/data/synthetic"
BASE_DEMAND = 1000          # units/week
START_DATE = datetime(2024, 1, 1)
TOTAL_WEEKS = 104           # 24 months
SEED = 42
NOISE_STD = 0.12            # +/-12% weekly noise


# =============================================================================
# Helpers
# =============================================================================
def week_date(w):
    return START_DATE + timedelta(weeks=w)

def week_month(w):
    return week_date(w).month


# =============================================================================
# Pattern application functions
# =============================================================================
def apply_annual_growth(demand, rng):
    """5-8% compound annual growth."""
    rate = rng.uniform(1.05, 1.08)
    weekly = rate ** (1 / 52)
    factors = np.array([weekly ** w for w in range(len(demand))])
    info = {
        "name": "Year-over-Year Growth",
        "type": "trend",
        "annual_rate": f"{(rate-1)*100:.1f}%",
        "weekly_rate": float(weekly),
        "weeks": "0-103",
    }
    return demand * factors, info


def apply_diwali(demand, rng):
    """Diwali spike: 3-4x for ~3 weeks in Oct/Nov."""
    mult = np.ones(len(demand))
    centers = [43, 94]  # Diwali 2024 (~Nov 1), Diwali 2025 (~Oct 20)
    info_list = []

    for c in centers:
        peak = rng.uniform(3.0, 4.0)
        for offset, factor in [(-1, 0.5), (0, 1.0), (1, 0.6)]:
            w = c + offset
            if 0 <= w < len(demand):
                mult[w] = max(mult[w], 1.0 + (peak - 1.0) * factor)
        info_list.append({
            "center_week": c,
            "peak": float(f"{peak:.2f}"),
            "date": week_date(c).strftime("%Y-%m-%d"),
            "weeks": f"{max(0,c-1)}-{min(len(demand)-1,c+1)}",
        })

    return demand * mult, {
        "name": "Diwali Spike",
        "type": "cultural",
        "multiplier": "3.0-4.0x",
        "duration": "3 weeks",
        "recurring": True,
        "occurrences": info_list,
    }


def apply_wedding_winter(demand, rng):
    """Winter wedding season: 1.4-1.6x Nov-Feb."""
    mult = np.ones(len(demand))
    val = rng.uniform(1.4, 1.6)
    weeks_applied = []
    for w in range(len(demand)):
        if week_month(w) in [11, 12, 1, 2]:
            mult[w] = val
            weeks_applied.append(w)

    return demand * mult, {
        "name": "Winter Wedding Season",
        "type": "seasonal",
        "multiplier": float(f"{val:.2f}"),
        "months": [11, 12, 1, 2],
        "weeks": f"{weeks_applied[0]}-{weeks_applied[-1]}" if weeks_applied else "",
        "recurring": True,
    }


def apply_wedding_summer(demand, rng):
    """Summer wedding season: 1.3-1.5x Apr-May."""
    mult = np.ones(len(demand))
    val = rng.uniform(1.3, 1.5)
    weeks_applied = []
    for w in range(len(demand)):
        if week_month(w) in [4, 5]:
            mult[w] = val
            weeks_applied.append(w)

    return demand * mult, {
        "name": "Summer Wedding Season",
        "type": "seasonal",
        "multiplier": float(f"{val:.2f}"),
        "months": [4, 5],
        "weeks": f"{weeks_applied[0]}-{weeks_applied[-1]}" if weeks_applied else "",
        "recurring": True,
    }


def apply_monsoon(demand, rng):
    """Monsoon dip: 0.7-0.8x Jul-Aug."""
    mult = np.ones(len(demand))
    val = rng.uniform(0.7, 0.8)
    weeks_applied = []
    for w in range(len(demand)):
        if week_month(w) in [7, 8]:
            mult[w] = val
            weeks_applied.append(w)

    return demand * mult, {
        "name": "Monsoon Demand Dip",
        "type": "seasonal",
        "multiplier": float(f"{val:.2f}"),
        "months": [7, 8],
        "weeks": f"{weeks_applied[0]}-{weeks_applied[-1]}" if weeks_applied else "",
        "recurring": True,
    }


def apply_sankranti(demand, rng):
    """Sankranti/Pongal: 1.5-1.8x mid-January, 2 weeks."""
    mult = np.ones(len(demand))
    centers = [2, 54]  # Week 3 of 2024 and 2025
    info_list = []

    for c in centers:
        peak = rng.uniform(1.5, 1.8)
        for offset in range(2):
            w = c + offset
            if 0 <= w < len(demand):
                mult[w] = peak
        info_list.append({
            "center_week": c,
            "peak": float(f"{peak:.2f}"),
            "date": week_date(c).strftime("%Y-%m-%d"),
            "weeks": f"{c}-{c+1}",
        })

    return demand * mult, {
        "name": "Makar Sankranti / Pongal",
        "type": "cultural",
        "multiplier": "1.5-1.8x",
        "duration": "2 weeks",
        "recurring": True,
        "occurrences": info_list,
    }


def apply_promo(demand, rng, week, name):
    """One-time promo spike: 2.0-2.5x for 1 week."""
    mult = np.ones(len(demand))
    val = rng.uniform(2.0, 2.5)
    if 0 <= week < len(demand):
        mult[week] = val

    return demand * mult, {
        "name": name,
        "type": "promotional",
        "multiplier": float(f"{val:.2f}"),
        "week": week,
        "date": week_date(week).strftime("%Y-%m-%d"),
        "recurring": False,
    }


def apply_noise(demand, rng):
    """Random weekly noise +/-12%."""
    noise = rng.normal(1.0, NOISE_STD, size=len(demand))
    noise = np.clip(noise, 0.7, 1.3)
    return demand * noise


# =============================================================================
# Main generation
# =============================================================================
def generate():
    rng = np.random.default_rng(SEED)
    demand = np.full(TOTAL_WEEKS, BASE_DEMAND, dtype=float)
    ground_truth = []

    # Layer patterns (order matters: multiplicative)
    demand, info = apply_annual_growth(demand, rng)
    ground_truth.append(info)

    demand, info = apply_diwali(demand, rng)
    ground_truth.append(info)

    demand, info = apply_wedding_winter(demand, rng)
    ground_truth.append(info)

    demand, info = apply_wedding_summer(demand, rng)
    ground_truth.append(info)

    demand, info = apply_monsoon(demand, rng)
    ground_truth.append(info)

    demand, info = apply_sankranti(demand, rng)
    ground_truth.append(info)

    demand, info = apply_promo(demand, rng, 17, "Promotional Spike 1 (One-time)")
    ground_truth.append(info)

    demand, info = apply_promo(demand, rng, 66, "Promotional Spike 2 (One-time)")
    ground_truth.append(info)

    # Noise last
    demand = apply_noise(demand, rng)
    demand = np.round(demand).astype(int)

    # Build metadata
    metadata = []
    for w in range(TOTAL_WEEKS):
        dt = week_date(w)
        metadata.append({
            "week_number": w + 1,
            "date": dt.strftime("%Y-%m-%d"),
            "year": dt.year,
            "month": dt.month,
            "month_name": dt.strftime("%B"),
            "week_of_year": dt.isocalendar()[1],
        })

    return demand, metadata, ground_truth


# =============================================================================
# Output
# =============================================================================
def save_csv(demand, metadata, out_dir):
    path = os.path.join(out_dir, "synthetic_demand_weekly_24m.csv")
    with open(path, "w") as f:
        f.write("week_number,date,year,month,week_of_year,demand_units\n")
        for w in range(len(demand)):
            m = metadata[w]
            f.write(f"{m['week_number']},{m['date']},{m['year']},"
                    f"{m['month']},{m['week_of_year']},{demand[w]}\n")
    print(f"  CSV:          {path}")


def save_ground_truth(ground_truth, out_dir):
    path = os.path.join(out_dir, "synthetic_demand_truth_labels.json")
    doc = {
        "description": (
            "Ground truth patterns embedded in the synthetic demand data. "
            "The CSV contains NO labels - only numbers and dates. "
            "These patterns exist for context agents to discover."
        ),
        "product": "Light bulbs",
        "market": "India (mid-sized urban market)",
        "base_demand": BASE_DEMAND,
        "seed": SEED,
        "total_weeks": TOTAL_WEEKS,
        "start_date": START_DATE.strftime("%Y-%m-%d"),
        "patterns": ground_truth,
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)
    print(f"  Ground truth: {path}")


def save_visualization(demand, metadata, ground_truth, out_dir):
    path = os.path.join(out_dir, "synthetic_demand_plot.png")
    dates = [datetime.strptime(m["date"], "%Y-%m-%d") for m in metadata]

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.plot(dates, demand, color="#2563eb", linewidth=1.2, alpha=0.9)
    ax.fill_between(dates, demand, alpha=0.1, color="#2563eb")

    # Growth trend baseline
    growth_info = ground_truth[0]
    base_trend = [BASE_DEMAND * (growth_info["weekly_rate"] ** w) for w in range(len(demand))]
    ax.plot(dates, base_trend, color="#94a3b8", linewidth=1,
            linestyle="--", label="Base + Growth Trend", alpha=0.7)

    # Annotate Diwali
    diwali_info = ground_truth[1]
    for occ in diwali_info["occurrences"]:
        c = occ["center_week"]
        ax.annotate("Diwali", xy=(dates[c], demand[c]),
                    xytext=(0, 25), textcoords="offset points",
                    fontsize=9, color="#dc2626", fontweight="bold", ha="center",
                    arrowprops=dict(arrowstyle="->", color="#dc2626"))

    # Annotate Sankranti
    sankranti_info = ground_truth[5]
    for occ in sankranti_info["occurrences"]:
        c = occ["center_week"]
        ax.annotate("Sankranti", xy=(dates[c], demand[c]),
                    xytext=(0, 20), textcoords="offset points",
                    fontsize=8, color="#ea580c", ha="center",
                    arrowprops=dict(arrowstyle="->", color="#ea580c"))

    # Annotate promos
    for idx in [6, 7]:
        p = ground_truth[idx]
        w = p["week"]
        ax.annotate("Promo", xy=(dates[w], demand[w]),
                    xytext=(0, 20), textcoords="offset points",
                    fontsize=8, color="#7c3aed", ha="center",
                    arrowprops=dict(arrowstyle="->", color="#7c3aed"))

    ax.set_title("Synthetic Light Bulb Demand — Indian Market (24 Months)",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Weekly Demand (units)", fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=45)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Chart:        {path}")


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Generating synthetic demand data (seed={SEED})...")
    print(f"Output: {OUTPUT_DIR}\n")

    demand, metadata, ground_truth = generate()

    save_csv(demand, metadata, OUTPUT_DIR)
    save_ground_truth(ground_truth, OUTPUT_DIR)
    save_visualization(demand, metadata, ground_truth, OUTPUT_DIR)

    print(f"\n{'='*50}")
    print(f"  Weeks:       {len(demand)}")
    print(f"  Mean:        {demand.mean():.0f} units/week")
    print(f"  Min:         {demand.min()} (week {demand.argmin()+1})")
    print(f"  Max:         {demand.max()} (week {demand.argmax()+1})")
    print(f"  Std:         {demand.std():.0f}")
    print(f"  Total:       {demand.sum():,} units")
    print(f"{'='*50}")
    print(f"\nDone. Seed: {SEED}")
