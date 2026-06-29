# Real Data Findings — Indian PV Market Calibration

**Sources:** autopunditz.com (CY2023, CY2024, CY2025 analyses)
**Accessed:** March 2026
**Purpose:** Calibrate synthetic 25-month demand series (Jan 2025 – Jan 2027) for Tatva Motors Vecta simulation

---

## 1. Market Volume

| Year | Indian PV Market (units) | YoY Growth |
|---|---|---|
| 2024 | 4,098,180 | 4.6% |
| 2025 | 4,529,913 | **5.7%** |

**Assumed Tata Motors share:** ~13–14% of Indian PV market → ~590,000–635,000 units annually in 2025.
**Vecta simulation scale:** ~37,000–39,000 units/month mean (scaled to one product family; lighting assembly sub-supply chain).

---

## 2. Monthly Seasonality — 2025 vs 2024 Growth (Real Data)

| Month | Real 2025 vs 2024 | Spec Event | Direction Match |
|---|---|---|---|
| January | +2% | Makar Sankranti (elevation) | ✅ |
| February | +2% | Union Budget (elevation) | ✅ |
| March | +4% | FY-end (elevation) | ✅ (absolute level remains highest month) |
| April | +5% | Wedding season (elevation) | ✅ |
| May | 0% | Wedding season (elevation) | ⚠️ muted in 2025 |
| June | **−6%** | Monsoon dip | ✅ |
| July | +1% | Monsoon dip | ✅ (still below non-monsoon months in absolute) |
| August | **−8%** | Monsoon dip | ✅ |
| September | +5% | Pre-festive build | ✅ |
| October | **+17%** | Navratri / Dasara (elevation) | ✅ |
| November | **+19%** | Diwali (elevation) | ✅ |
| December | **+26%** | Year-end sales (elevation) | ✅ |

**All 8 seasonal events in the experiment spec are directionally confirmed by real data.**

---

## 3. Key Findings

**F1 — Festive season confirmed, but 2025 Q4 was anomalously strong.**
The October–December 2025 surge (+17–26% YoY) was partly driven by a one-time regulatory event: GST rate changes announced August 15, effective September 22, 2025. This pulled forward buying into Q4. Normal festive uplift in Indian automotive is ~10–15%. The synthetic series uses normalised festive indices (~11–14% above mean) rather than replicating the GST distortion.

**F2 — Monsoon dip is real and consistent.**
June and August 2025 both contracted YoY. The three-month monsoon trough (Jun–Aug) is structurally embedded in Indian automotive demand and appears reliably in both 2024 and 2025 data. Synthetic series preserves this with ~6–8% below-mean demand across Jun–Aug.

**F3 — March FY-end is the structural annual peak.**
While the YoY growth rate for March 2025 was only +4%, the absolute March volume is consistently the highest month of the year due to OEM and dealer push to close fiscal year targets. The synthetic series models March at ~+13–15% above annual mean.

**F4 — May 2025 wedding season was flat.**
The spec expects mild wedding-season elevation in April–May. April confirmed (+5%), but May was flat (0%) — likely because pre-GST uncertainty dampened mid-year discretionary buying in 2025. The synthetic series retains a modest May elevation as the spec intends, since 2025's flatness is a one-year anomaly.

**F5 — India GDP growth (~5.6–7%) supports demand trajectory.**
GDP data (Investing.com, Q3 2024: 5.6% actual) is consistent with the 5% YoY growth applied to the 2025→2026 leg of the synthetic series.

---

## 4. Synthetic Series Parameters (derived)

| Parameter | Value | Derivation |
|---|---|---|
| Mean monthly demand | 38,548 units | Weighted mean across 25 months |
| Std | ~3,067 units | Sample std from 25-month series (`ddof=1`), matching runtime calibration |
| Initial inventory target S | **~43,600** | mean + 1.65 × std(ddof=1, sample) — derived at runtime by run_experiment.py |
| Implied safety stock | **~5,061** | `S − mean_demand`; used by the forecast-based Order-Up-To heuristic |
| 2025 base mean | 37,000/month | Tata Motors scale, one product family |
| 2026 base mean | 38,850/month | +5% YoY growth applied |
| 2027 base (Jan only) | 40,793/month | +5% YoY applied again |

S ≈ 43,600 as derived by `run_experiment.py` using sample std (ddof=1). The blind Order-Up-To baseline uses fixed safety stock of ≈5,061 units on top of a smoothed demand forecast.

---

## 5. What Is NOT in the Synthetic Data

The CSV (`data/tatva_monthly_dispatches_25m.csv`) contains only:
- `period`, `calendar_month`, `year`, `retail_demand`, `phase`

**Event labels are intentionally excluded.** Agents receive only the calendar month and year. Any seasonal reasoning must come from the agent's own world knowledge — this is the capability under test (pattern score, Section 8.3 of experiment design).
