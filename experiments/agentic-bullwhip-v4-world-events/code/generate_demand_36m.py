"""
Generate 36-month demand series for V3 simulation.

Extends the V2 25-month Tatva Motors Vecta series to 36 months (Jan 2025 -- Dec 2027).
- 2025 baseline: same as V2
- 2026: +5% YoY (already in V2 series for periods 13-25)
- 2027: +5% YoY on top of 2026

Demand noise is NOT baked into this CSV -- it is applied at runtime per-run in
simulation.py so that each of the 20 Monte Carlo runs sees a different realisation
of the same underlying seasonal pattern.

World event labels are annotated in the CSV for human reference. The simulation
reads them from WorldEvents, not from this file.

Run from the code/ directory:
    python generate_demand_36m.py
"""

import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# 2025 baseline monthly demand (same as V2 tatva_monthly_dispatches_25m.csv)
# ---------------------------------------------------------------------------
BASELINE_2025 = {
    "January":   37_200,
    "February":  36_200,
    "March":     43_500,   # FY-end peak
    "April":     36_200,
    "May":       37_200,
    "June":      34_300,   # monsoon
    "July":      33_700,   # monsoon trough
    "August":    35_100,
    "September": 37_200,
    "October":   40_400,   # Navratri/Dasara
    "November":  41_600,   # Diwali peak
    "December":  37_700,
}

MONTHS_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

YOY_GROWTH = 0.05   # 5% applied each year

EVENT_LABELS = {
    # 2025
    1:  ("Makar Sankranti",         "Minor festive uplift; modestly above 2025 baseline"),
    2:  ("Union Budget",            "Budget announcement; sentiment uplift, demand broadly flat"),
    3:  ("FY-end peak",             "Highest demand month; OEM and dealer push to close Indian FY"),
    4:  ("Wedding season onset",    "Post-FY dip; mild wedding-season elevation"),
    5:  ("Wedding season",          "Modest wedding-season lift"),
    6:  ("Monsoon dip",             "Three-month monsoon trough begins"),
    7:  ("Monsoon trough",          "Lowest demand month; monsoon at peak intensity"),
    8:  ("Monsoon exit",            "Partial recovery toward pre-festive build"),
    9:  ("Pre-festive build",       "Inventory build-up; demand returns to baseline"),
    10: ("Navratri / Dasara",       "First festive peak; auspicious buying window"),
    11: ("Diwali",                  "Largest single-month demand spike (cycle 1)"),
    12: ("Year-end / post-Diwali",  "Year-end dealer push; elevated vs non-festive months"),
    # 2026
    13: ("Makar Sankranti",         "Same driver as Jan 2025; +5% YoY growth base"),
    14: ("Union Budget",            "Budget period; +5% YoY"),
    15: ("FY-end peak",             "Structural annual maximum; +5% YoY"),
    16: ("Wedding season onset",    "Post-FY dip; mirrors April 2025 at 2026 base"),
    17: ("Wedding season",          "Modest lift; +5% YoY"),
    18: ("Monsoon dip",             "Monsoon trough; ~6% below 2026 annual mean"),
    19: ("Monsoon trough — CONFLICT", "Monsoon trough + geopolitical supply shock begins"),
    20: ("Monsoon exit — CONFLICT", "Partial demand recovery; supply chain disrupted by conflict"),
    21: ("Pre-festive build — CONFLICT", "Festive build hampered by sustained conflict disruption"),
    22: ("Navratri / Dasara",       "Festive cycle 2; +5% YoY on Oct 2025 peak"),
    23: ("Diwali",                  "Peak demand month of entire series; Diwali cycle 2"),
    24: ("Year-end / post-Diwali",  "Year-end push; +5% YoY"),
    # 2027
    25: ("Makar Sankranti",         "+10% YoY from 2025; post-conflict recovery"),
    26: ("Union Budget",            "+10% YoY from 2025"),
    27: ("FY-end peak",             "+10% YoY; largest FY-end in series"),
    28: ("Wedding season onset — PORT DISRUPTION", "Post-FY dip; port/logistics disruption begins"),
    29: ("Wedding season — PORT DISRUPTION",       "Port disruption peaks; lead times spike"),
    30: ("Monsoon dip — PORT DISRUPTION",          "Monsoon + tail of port disruption"),
    31: ("Monsoon trough",          "Monsoon trough 2027; disruption cleared"),
    32: ("Monsoon exit",            "Partial recovery; normal operations resuming"),
    33: ("Pre-festive build",       "Festive inventory build; logistics normalised"),
    34: ("Navratri / Dasara",       "Festive cycle 3; +10% YoY on Oct 2025"),
    35: ("Diwali",                  "Diwali cycle 3; highest festive demand in series"),
    36: ("Year-end",                "Year-end close; +10% YoY"),
}

PHASES = {
    # 2025
    1: "baseline", 2: "baseline", 3: "baseline", 4: "baseline",
    5: "baseline", 6: "baseline", 7: "baseline", 8: "baseline",
    9: "baseline", 10: "festive", 11: "festive", 12: "baseline",
    # 2026
    13: "baseline", 14: "baseline", 15: "baseline", 16: "baseline",
    17: "baseline", 18: "baseline",
    19: "conflict", 20: "conflict", 21: "conflict",
    22: "festive", 23: "festive", 24: "baseline",
    # 2027
    25: "baseline", 26: "baseline", 27: "baseline",
    28: "port_disruption", 29: "port_disruption", 30: "port_disruption",
    31: "baseline", 32: "baseline", 33: "baseline",
    34: "festive", 35: "festive", 36: "baseline",
}


def build_series() -> list[dict]:
    rows = []
    period = 1

    for year_idx, year in enumerate([2025, 2026, 2027]):
        growth = (1 + YOY_GROWTH) ** year_idx
        for month in MONTHS_ORDER:
            baseline = round(BASELINE_2025[month] * growth)
            label, note = EVENT_LABELS.get(period, ("", ""))
            phase = PHASES.get(period, "baseline")
            calendar_month = f"{month[:3]} {year}"

            rows.append({
                "period":         period,
                "calendar_month": calendar_month,
                "year":           year,
                "month":          month,
                "retail_demand":  baseline,
                "phase":          phase,
                "event_label":    label,
                "event_note":     note,
            })
            period += 1

    return rows


def main():
    out_dir = Path(__file__).parent / "data" / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = build_series()

    fields = ["period", "calendar_month", "year", "month",
              "retail_demand", "phase", "event_label", "event_note"]

    # Raw CSV (used by simulation.py)
    raw_path = out_dir / "tatva_monthly_dispatches_36m.csv"
    with open(raw_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # Annotated copy (human-readable, same content)
    ann_path = out_dir / "tatva_monthly_dispatches_36m_annotated.csv"
    with open(ann_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Generated {len(rows)} periods")
    print(f"  Raw:       {raw_path}")
    print(f"  Annotated: {ann_path}")
    print()
    print(f"{'Per':>4}  {'Month':<12}  {'Demand':>8}  {'Phase':<18}  Event")
    print("-" * 80)
    for r in rows:
        print(f"{r['period']:>4}  {r['calendar_month']:<12}  {r['retail_demand']:>8,}  "
              f"{r['phase']:<18}  {r['event_label']}")


if __name__ == "__main__":
    main()
