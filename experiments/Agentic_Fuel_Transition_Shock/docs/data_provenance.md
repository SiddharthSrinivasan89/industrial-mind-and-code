# Data Provenance — Agentic Fuel Transition Shock

**Last updated:** March 2026

---

## Source Data

**Publication:** Indian Passenger Car Market — Fuel Mix Analysis FY2025
**Source:** autopunditz.com
**URL:** https://www.autopunditz.com/post/indian-passenger-car-market-fuel-mix-analysis-fy2025
**Accessed:** March 2026

---

## Raw Market Data (FY2025)

### Sales Volume by OEM and Fuel Type

| Rank | OEM | Petrol | Diesel | CNG | Electric | Hybrid | FY2025 Total |
|---|---|---|---|---|---|---|---|
| 1 | Maruti Suzuki | 11,48,363 | 0 | 5,91,730 | 0 | 20,672 | 17,60,765 |
| 2 | Hyundai | 4,08,242 | 1,07,187 | 79,267 | 3,970 | 0 | 5,98,666 |
| 3 | Tata | 2,80,355 | 72,333 | 1,39,460 | 61,443 | 0 | 5,53,591 |
| 4 | Mahindra | 1,13,268 | 4,25,329 | 0 | 12,890 | 0 | 5,51,487 |
| 5 | Toyota | 1,19,415 | 79,156 | 28,089 | 0 | 82,848 | 3,09,508 |
| 6 | Kia | 1,69,976 | 84,403 | 0 | 828 | 0 | 2,55,207 |
| 7 | Honda | 64,645 | 0 | 0 | 0 | 1,280 | 65,925 |
| 8 | MG | 20,647 | 4,935 | 0 | 36,585 | 0 | 62,167 |
| 9 | Skoda | 44,862 | 0 | 0 | 0 | 0 | 44,862 |
| 10 | VW | 42,230 | 0 | 0 | 0 | 0 | 42,230 |
| 11 | Renault | 37,900 | 0 | 0 | 0 | 0 | 37,900 |
| 12 | Nissan | 27,921 | 0 | 0 | 0 | 0 | 27,921 |
| 13 | Citroen | 6,507 | 9 | 0 | 0 | 0 | 6,516 |
| 14 | Jeep | 0 | 3,951 | 0 | 0 | 0 | 3,951 |
| | **TOTAL** | **24,84,331** | **7,77,303** | **8,38,546** | **1,15,716** | **1,04,800** | **43,20,696** |

### Fuel Mix % by OEM

| Rank | OEM | Petrol% | Diesel% | CNG% | Electric% | Hybrid% |
|---|---|---|---|---|---|---|
| 1 | Maruti Suzuki | 65.2% | 0.0% | 33.6% | 0.0% | 1.2% |
| 2 | Hyundai | 68.2% | 17.9% | 13.2% | 0.7% | 0.0% |
| 3 | Tata | 50.6% | 13.1% | 25.2% | 11.1% | 0.0% |
| 4 | Mahindra | 20.5% | 77.1% | 0.0% | 2.3% | 0.0% |
| 5 | Toyota | 38.6% | 25.6% | 9.1% | 0.0% | 26.8% |
| 6 | Kia | 66.6% | 33.1% | 0.0% | 0.3% | 0.0% |
| 7 | Honda | 98.1% | 0.0% | 0.0% | 0.0% | 1.9% |
| 8 | MG | 33.2% | 7.9% | 0.0% | 58.8% | 0.0% |
| 9 | Skoda | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 10 | VW | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 11 | Renault | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 12 | Nissan | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 13 | Citroen | 99.9% | 0.1% | 0.0% | 0.0% | 0.0% |
| 14 | Jeep | 0.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| | **TOTAL** | **57.5%** | **18.0%** | **19.4%** | **2.7%** | **2.4%** |

---

## Derivation: Simulation Demand Series

### OEM Selection Rationale

The simulation models a **Mahindra-scale diesel-dependent OEM**. Mahindra is selected because:
- Highest absolute diesel volume: 4,25,329 units in FY2025
- Highest diesel dependency by mix: 77.1% of total volume
- Most representative of the supply chain risk scenario — a supplier whose primary customer is diesel-concentrated

### Monthly Run Rate Calculation

```
Annual diesel units (Mahindra): 4,25,329
Monthly baseline (÷12):          35,444 units/month
Rounded for simulation:           35,000 units/month
```

### Shock Trajectory

A 30% decline over 36 months starting Month 7:

```
Target end volume: 35,000 × (1 − 0.30) = 24,500 units/month
Total decline:     10,500 units/month over 24 months (Months 7–30)
Monthly step:      ~437.5 units/month reduction
```

| Phase | Months | Monthly Volume | Notes |
|---|---|---|---|
| Baseline | 1–6 | 35,000 | Pre-shock stable period |
| Decline Year 1 | 7–18 | 35,000 → 28,750 | −437.5/month, reaches −18% |
| Decline Year 2 | 19–30 | 28,750 → 24,500 | −437.5/month, reaches −30% |
| New Equilibrium | 31–36 | 24,500 | Stable at new lower level |
| Fulfilment only | 37 | 24,500 | No orders placed — simulation close-out |

### Seasonal Overlay (To Be Decided)

The raw monthly run rate is flat within each phase. An optional seasonal overlay can be applied using Indian automotive dispatch patterns (festive season peaks in Oct–Nov, budget effect in Feb–Mar, monsoon dip Jun–Aug). Decision: **hold flat for v1** to isolate the shock effect cleanly. Seasonal overlay is a v2 extension.

---

## Demand File Specification

**Filename:** `data/synthetic/diesel_transition_37m.csv`

**Columns:**

| Column | Type | Description |
|---|---|---|
| `period_number` | int | 1–37. Period 37 = fulfilment only, no orders. |
| `month_name` | str | e.g., "April", "May" |
| `year` | int | Calendar year (2025–2028) |
| `dispatches` | int | Monthly diesel dispatch target for the OEM tier |
| `phase` | str | "baseline", "decline_y1", "decline_y2", "equilibrium", "closeout" |
| `shock_active` | bool | False for periods 1–6, True from period 7 onward |

**Generation:** Script to be written at `src/generate_demand.py`. Random seed fixed and documented here once set.

---

## Notes and Caveats

1. **FY2025 data is annual.** Monthly figures are derived by division and may not capture intra-year seasonality. The simulation uses a flat monthly run rate — this is intentional to isolate the structural shock signal from seasonal noise.

2. **Mahindra's diesel mix may shift.** The 77.1% diesel figure is FY2025. Mahindra has announced EV expansion. The simulation holds the diesel share constant at the FY2025 baseline for the pre-shock period — the shock represents the projected external market decline, not OEM portfolio shifts.

3. **Market-level vs OEM-level shock.** The 30% decline is framed as a market-level projection. The simulation applies it uniformly to the single OEM's demand series. In reality, diesel share decline may be faster for smaller OEMs and slower for Mahindra (which has stronger diesel brand equity). This simplification is noted.

4. **No competitor dynamics.** The simulation does not model market share shifts between OEMs as diesel declines. Total addressable market for diesel shrinks; the OEM's share of that market is held constant.
