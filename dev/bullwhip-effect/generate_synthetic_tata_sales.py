#!/usr/bin/env python3
"""
Synthetic Data Generator — Tata Car Sales (India)
===================================================
Generates 24-month weekly car sales data calibrated against
real-world Tata Motors domestic sales patterns.

Patterns embedded:
  - Navratri/Diwali surge (Oct)
  - Year-end push (Nov-Dec)
  - Wedding season winter (Nov-Feb)
  - Wedding season summer (Apr-May)
  - Monsoon dip (Jul-Aug)
  - Akshaya Tritiya (Apr-May)
  - Makar Sankranti / Pongal (Jan)
  - Month-end wholesale push
  - Annual growth trend
  - One-time promo spikes
  - Weekly noise

Calibration source: Real Tata Motors sales Dec-24 to Dec-25
  Monthly range: ~38,000 to ~61,000 units
  Base monthly: ~45,000 units (~11,250/week)

Run:
    python generate_synthetic_tata_sales.py

Output: /home/sid/industrial-mind-and-code/dev/data/synthetic/
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
BASE_WEEKLY_SALES = 11250     # ~45,000/month (Tata baseline from real data)
START_DATE = datetime(2024, 1, 1)
TOTAL_WEEKS = 104             # 24 months
SEED = 42
NOISE_STD = 0.08              # +/-8% weekly noise (cars are less volatile than FMCG)


# =============================================================================
# Helpers
# =============================================================================
def week_date(w):
    return START_DATE + timedelta(weeks=w)

def week_month(w):
    return week_date(w).month

def week_day_of_month(w):
    return week_date(w).day


# =============================================================================
# Pattern functions
# =============================================================================
def apply_annual_growth(demand, rng):
    """8-12% compound annual growth (Tata has been growing aggressively)."""
    rate = rng.uniform(1.08, 1.12)
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


def apply_navratri_diwali(demand, rng):
    """
    Navratri + Diwali surge: 1.5-1.8x for ~4 weeks in Sep-Oct.
    This is THE biggest period for Indian car sales.
    Navratri 2024: Oct 3-12. Diwali 2024: Nov 1.
    Navratri 2025: Sep 22-Oct 2. Diwali 2025: Oct 20.
    """
    mult = np.ones(len(demand))
    # Navratri-Diwali windows (approximate week indices)
    # 2024: weeks 39-43 (late Sep to early Nov)
    # 2025: weeks 91-95 (late Sep to late Oct)
    windows = [
        {"start": 39, "peak": 41, "end": 43},
        {"start": 90, "peak": 93, "end": 95},
    ]
    info_list = []

    for win in windows:
        peak = rng.uniform(1.5, 1.8)
        for w in range(win["start"], min(win["end"] + 1, len(demand))):
            if w == win["peak"]:
                mult[w] = peak
            elif w == win["peak"] - 1 or w == win["peak"] + 1:
                mult[w] = 1.0 + (peak - 1.0) * 0.8
            else:
                mult[w] = 1.0 + (peak - 1.0) * 0.5

        info_list.append({
            "weeks": f"{win['start']}-{win['end']}",
            "peak_week": win["peak"],
            "peak_multiplier": float(f"{peak:.2f}"),
            "date_range": f"{week_date(win['start']).strftime('%Y-%m-%d')} to {week_date(win['end']).strftime('%Y-%m-%d')}",
        })

    return demand * mult, {
        "name": "Navratri + Diwali Surge",
        "type": "cultural",
        "multiplier": "1.5-1.8x",
        "duration": "4-5 weeks",
        "recurring": True,
        "description": "Peak car buying season in India. Auspicious period for major purchases.",
        "occurrences": info_list,
    }


def apply_year_end_push(demand, rng):
    """
    Year-end wholesale push: 1.15-1.25x in Nov-Dec.
    Dealers push inventory to meet annual targets.
    """
    mult = np.ones(len(demand))
    val = rng.uniform(1.15, 1.25)
    weeks_applied = []
    for w in range(len(demand)):
        if week_month(w) in [11, 12]:
            mult[w] = val
            weeks_applied.append(w)

    return demand * mult, {
        "name": "Year-End Wholesale Push",
        "type": "seasonal",
        "multiplier": float(f"{val:.2f}"),
        "months": [11, 12],
        "recurring": True,
        "description": "Dealers push stock to meet annual sales targets.",
    }


def apply_wedding_winter(demand, rng):
    """Winter wedding season: 1.08-1.15x Dec-Feb. Cars as gifts/family purchases."""
    mult = np.ones(len(demand))
    val = rng.uniform(1.08, 1.15)
    for w in range(len(demand)):
        if week_month(w) in [12, 1, 2]:
            mult[w] = val

    return demand * mult, {
        "name": "Winter Wedding Season",
        "type": "seasonal",
        "multiplier": float(f"{val:.2f}"),
        "months": [12, 1, 2],
        "recurring": True,
        "description": "Elevated car purchases during wedding season.",
    }


def apply_wedding_summer(demand, rng):
    """Summer wedding season + Akshaya Tritiya: 1.08-1.12x Apr-May."""
    mult = np.ones(len(demand))
    val = rng.uniform(1.08, 1.12)
    for w in range(len(demand)):
        if week_month(w) in [4, 5]:
            mult[w] = val

    return demand * mult, {
        "name": "Summer Wedding Season + Akshaya Tritiya",
        "type": "seasonal",
        "multiplier": float(f"{val:.2f}"),
        "months": [4, 5],
        "recurring": True,
        "description": "Akshaya Tritiya is considered auspicious for buying vehicles.",
    }


def apply_monsoon_dip(demand, rng):
    """Monsoon dip: 0.80-0.88x Jul-Aug. Fewer showroom visits, flooding concerns."""
    mult = np.ones(len(demand))
    val = rng.uniform(0.80, 0.88)
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
        "recurring": True,
        "description": "Reduced showroom footfall during monsoon. Flood/waterlogging concerns delay purchases.",
    }


def apply_sankranti(demand, rng):
    """Makar Sankranti / Pongal: 1.10-1.20x mid-January, 2 weeks."""
    mult = np.ones(len(demand))
    centers = [2, 54]
    info_list = []

    for c in centers:
        peak = rng.uniform(1.10, 1.20)
        for offset in range(2):
            w = c + offset
            if 0 <= w < len(demand):
                mult[w] = peak
        info_list.append({
            "center_week": c,
            "peak": float(f"{peak:.2f}"),
            "date": week_date(c).strftime("%Y-%m-%d"),
        })

    return demand * mult, {
        "name": "Makar Sankranti / Pongal",
        "type": "cultural",
        "multiplier": "1.10-1.20x",
        "duration": "2 weeks",
        "recurring": True,
        "occurrences": info_list,
    }


def apply_march_surge(demand, rng):
    """
    March financial year-end: 1.20-1.30x.
    Massive push — dealers clear inventory, corporate fleet purchases,
    depreciation benefit before March 31.
    """
    mult = np.ones(len(demand))
    val = rng.uniform(1.20, 1.30)
    for w in range(len(demand)):
        if week_month(w) == 3:
            mult[w] = val

    return demand * mult, {
        "name": "March Financial Year-End Push",
        "type": "seasonal",
        "multiplier": float(f"{val:.2f}"),
        "months": [3],
        "recurring": True,
        "description": "Dealers and corporates rush purchases before financial year-end (March 31). Depreciation benefits drive fleet sales.",
    }


def apply_new_model_launch(demand, rng):
    """One-time spike from a new model launch. ~1.15-1.25x for 3 weeks."""
    mult = np.ones(len(demand))
    week_start = 22  # ~early June 2024
    val = rng.uniform(1.15, 1.25)
    for w in range(week_start, min(week_start + 3, len(demand))):
        mult[w] = val

    return demand * mult, {
        "name": "New Model Launch Spike",
        "type": "promotional",
        "multiplier": float(f"{val:.2f}"),
        "weeks": f"{week_start}-{week_start+2}",
        "date": week_date(week_start).strftime("%Y-%m-%d"),
        "duration": "3 weeks",
        "recurring": False,
        "description": "One-time demand spike from a new model/facelift launch.",
    }


def apply_promo_spike(demand, rng):
    """One-time promotional/discount event. 1 week spike."""
    mult = np.ones(len(demand))
    week = 70  # ~mid-May 2025
    val = rng.uniform(1.15, 1.25)
    if 0 <= week < len(demand):
        mult[week] = val

    return demand * mult, {
        "name": "Promotional Discount Event",
        "type": "promotional",
        "multiplier": float(f"{val:.2f}"),
        "week": week,
        "date": week_date(week).strftime("%Y-%m-%d"),
        "recurring": False,
        "description": "One-time clearance/exchange offer event.",
    }


def apply_month_end_pattern(demand, rng):
    """
    Subtle month-end push: weeks containing 25th-31st get a small bump.
    Dealers push registrations at month-end for targets.
    """
    mult = np.ones(len(demand))
    bump = rng.uniform(1.03, 1.06)
    for w in range(len(demand)):
        if week_day_of_month(w) >= 22:
            mult[w] = bump

    return demand * mult, {
        "name": "Month-End Wholesale Push",
        "type": "operational",
        "multiplier": float(f"{bump:.2f}"),
        "recurring": True,
        "description": "Dealers push dispatches in last week of month to meet monthly targets.",
    }


def apply_noise(demand, rng):
    """Random weekly noise +/-8%."""
    noise = rng.normal(1.0, NOISE_STD, size=len(demand))
    noise = np.clip(noise, 0.8, 1.2)
    return demand * noise


# =============================================================================
# Main generation
# =============================================================================
def generate():
    rng = np.random.default_rng(SEED)
    demand = np.full(TOTAL_WEEKS, BASE_WEEKLY_SALES, dtype=float)
    ground_truth = []

    demand, info = apply_annual_growth(demand, rng)
    ground_truth.append(info)

    demand, info = apply_navratri_diwali(demand, rng)
    ground_truth.append(info)

    demand, info = apply_year_end_push(demand, rng)
    ground_truth.append(info)

    demand, info = apply_wedding_winter(demand, rng)
    ground_truth.append(info)

    demand, info = apply_wedding_summer(demand, rng)
    ground_truth.append(info)

    demand, info = apply_monsoon_dip(demand, rng)
    ground_truth.append(info)

    demand, info = apply_sankranti(demand, rng)
    ground_truth.append(info)

    demand, info = apply_march_surge(demand, rng)
    ground_truth.append(info)

    demand, info = apply_new_model_launch(demand, rng)
    ground_truth.append(info)

    demand, info = apply_promo_spike(demand, rng)
    ground_truth.append(info)

    demand, info = apply_month_end_pattern(demand, rng)
    ground_truth.append(info)

    # Noise last
    demand = apply_noise(demand, rng)
    demand = np.round(demand).astype(int)

    # Metadata
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
    path = os.path.join(out_dir, "synthetic_tata_sales_weekly_24m.csv")
    with open(path, "w") as f:
        f.write("week_number,date,year,month,week_of_year,sales_units\n")
        for w in range(len(demand)):
            m = metadata[w]
            f.write(f"{m['week_number']},{m['date']},{m['year']},"
                    f"{m['month']},{m['week_of_year']},{demand[w]}\n")
    print(f"  CSV:          {path}")


def save_ground_truth(ground_truth, out_dir):
    path = os.path.join(out_dir, "synthetic_tata_sales_truth_labels.json")
    doc = {
        "description": (
            "Ground truth patterns embedded in synthetic Tata car sales data. "
            "The CSV contains NO labels - only numbers and dates. "
            "These patterns exist for context agents to discover."
        ),
        "product": "Passenger vehicles (Tata Motors)",
        "market": "India (domestic sales)",
        "base_weekly_sales": BASE_WEEKLY_SALES,
        "base_monthly_sales": BASE_WEEKLY_SALES * 4,
        "calibration_source": "Real Tata Motors monthly sales Dec-24 to Dec-25 (publicly available)",
        "seed": SEED,
        "total_weeks": TOTAL_WEEKS,
        "start_date": START_DATE.strftime("%Y-%m-%d"),
        "patterns": ground_truth,
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)
    print(f"  Ground truth: {path}")


def save_visualization(demand, metadata, ground_truth, out_dir):
    path = os.path.join(out_dir, "synthetic_tata_sales_plot.png")
    dates = [datetime.strptime(m["date"], "%Y-%m-%d") for m in metadata]

    fig, ax = plt.subplots(figsize=(16, 7))
    ax.plot(dates, demand, color="#1a56db", linewidth=1.3, alpha=0.9)
    ax.fill_between(dates, demand, alpha=0.08, color="#1a56db")

    # Growth baseline
    growth_info = ground_truth[0]
    base_trend = [BASE_WEEKLY_SALES * (growth_info["weekly_rate"] ** w) for w in range(len(demand))]
    ax.plot(dates, base_trend, color="#94a3b8", linewidth=1,
            linestyle="--", label="Base + Growth Trend", alpha=0.7)

    # Annotate Navratri/Diwali
    nav_info = ground_truth[1]
    for occ in nav_info["occurrences"]:
        pk = occ["peak_week"]
        if pk < len(demand):
            ax.annotate("Navratri/\nDiwali", xy=(dates[pk], demand[pk]),
                        xytext=(0, 30), textcoords="offset points",
                        fontsize=8, color="#dc2626", fontweight="bold", ha="center",
                        arrowprops=dict(arrowstyle="->", color="#dc2626"))

    # Annotate March surge
    for w in range(len(demand)):
        if week_month(w) == 3 and week_day_of_month(w) <= 7:
            ax.annotate("FY-End\nPush", xy=(dates[w], demand[w]),
                        xytext=(0, 25), textcoords="offset points",
                        fontsize=8, color="#ea580c", ha="center",
                        arrowprops=dict(arrowstyle="->", color="#ea580c"))
            break

    # Annotate monsoon
    monsoon_weeks = [w for w in range(len(demand)) if week_month(w) == 7]
    if monsoon_weeks:
        mid = monsoon_weeks[len(monsoon_weeks)//2]
        ax.annotate("Monsoon\nDip", xy=(dates[mid], demand[mid]),
                    xytext=(0, -35), textcoords="offset points",
                    fontsize=8, color="#0ea5e9", ha="center",
                    arrowprops=dict(arrowstyle="->", color="#0ea5e9"))

    # Annotate new model launch
    launch_info = ground_truth[8]
    lw = int(launch_info["weeks"].split("-")[0])
    if lw < len(demand):
        ax.annotate("New Model\nLaunch", xy=(dates[lw], demand[lw]),
                    xytext=(0, 25), textcoords="offset points",
                    fontsize=8, color="#7c3aed", ha="center",
                    arrowprops=dict(arrowstyle="->", color="#7c3aed"))

    ax.set_title("Synthetic Tata Motors Weekly Sales — India (24 Months)",
                 fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Weekly Sales (units)", fontsize=11)
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
# Monthly aggregation check (sanity vs real data)
# =============================================================================
def print_monthly_check(demand, metadata):
    """Aggregate to monthly and compare against real Tata data range."""
    monthly = {}
    for w in range(len(demand)):
        key = f"{metadata[w]['year']}-{metadata[w]['month']:02d}"
        if key not in monthly:
            monthly[key] = 0
        monthly[key] += demand[w]

    print(f"\n  Monthly aggregation (sanity check vs real ~38K-61K range):")
    for key in sorted(monthly.keys()):
        val = monthly[key]
        flag = "" if 30000 <= val <= 75000 else " ⚠️ outside expected range"
        print(f"    {key}: {val:>8,}{flag}")


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Generating synthetic Tata car sales data (seed={SEED})...")
    print(f"Output: {OUTPUT_DIR}\n")

    demand, metadata, ground_truth = generate()

    save_csv(demand, metadata, OUTPUT_DIR)
    save_ground_truth(ground_truth, OUTPUT_DIR)
    save_visualization(demand, metadata, ground_truth, OUTPUT_DIR)

    print(f"\n{'='*55}")
    print(f"  WEEKLY STATS")
    print(f"  Weeks:        {len(demand)}")
    print(f"  Mean:         {demand.mean():,.0f} units/week")
    print(f"  Min:          {demand.min():,} (week {demand.argmin()+1})")
    print(f"  Max:          {demand.max():,} (week {demand.argmax()+1})")
    print(f"  Std:          {demand.std():,.0f}")
    print(f"  Total:        {demand.sum():,} units over 24 months")
    print(f"{'='*55}")

    print_monthly_check(demand, metadata)

    print(f"\nSeed: {SEED} | Done.")
