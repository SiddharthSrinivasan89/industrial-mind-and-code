# TPM Press Brake — Synthetic Issue Dataset

**Machine:** PB-07 — AMADA HFE 100-ton Hydraulic Press Brake
**Period:** January 1 – March 7, 2024
**Purpose:** Synthetic ground truth for cross-pillar agentic reasoning experiment

---

## Pillar 1 — Autonomous Maintenance

| ID | Date | Operator | Shift | Observation |
|---|---|---|---|---|
| AM-001 | Jan 3 – Jan 31 | Mike T | Night | Ram parallelism check skipped on 14 of 20 shifts |
| AM-002 | Jan 5 – Feb 10 | Mike T | Night | Hydraulic oil level logged as "OK" without measurement on 8 occasions |
| AM-003 | Feb 7 | Sarah K | Day | Back gauge calibration drift noted — gauge returning to position 0.4mm off target |
| AM-004 | Feb 3 | Dave R | Day | Tooling inspection skipped — high-volume run, pressure to clear batch #B2211 |

---

## Pillar 2 — Focused Improvement

| ID | Date | Event | Target | Outcome |
|---|---|---|---|---|
| FI-001 | Jan 10 | Kaizen — Die Setup | Reduce setup time 20% | Quick-change die system installed. No safety or validation review conducted before deployment |
| FI-002 | Feb 5 | Kaizen — Cycle Time | Reduce cycle time on bracket family | Stroke speed increased from 8mm/s to 11mm/s. Hydraulic pressure spikes observed post-event |
| FI-003 | Feb 20 | OEE Review | Identify bottleneck | Back gauge positioning identified as primary availability loss — no action taken yet |

---

## Pillar 3 — Planned Maintenance

| ID | Scheduled | Completed | Status | Notes |
|---|---|---|---|---|
| PM-001 | Jan 15 | Feb 3 | Deferred 19 days | Hydraulic seal kit (part #HYD-4721) out of stock — waited on procurement |
| PM-002 | Feb 10 | Feb 17 | Deferred 7 days | Die set #DS-118 not available — procurement approval delay |
| PM-003 | Jan 8 | Jan 8 | On time | Back gauge servo motor lubrication — no issues |
| PM-004 | Feb 15 | Mar 1 | Deferred 14 days | Ram parallelism calibration — technician assigned to breakdown elsewhere |

---

## Pillar 4 — Quality Maintenance

| ID | Date | Batch | Material | Issue | Metric |
|---|---|---|---|---|---|
| QM-001 | Jan 28–30 | B2204 | HSLA 550 MPa | Bend angle variation | ±0.8° (spec: ±0.2°) — night shift production |
| QM-002 | Feb 4–6 | B2208 | HSLA 550 MPa | Springback inconsistency | Compensation setting not adjusted for material grade |
| QM-003 | Feb 20 | B2215 | Mild steel | Flange length variation | ±0.6mm (spec: ±0.15mm) — back gauge suspected |
| QM-004 | Feb 3–7 | Mixed | Mixed | Scrap rate spike | 4.2% (baseline: 1.1%) |

---

## Pillar 5 — Early Equipment Management

| ID | Category | Detail |
|---|---|---|
| EEM-001 | Material spec | Machine rated for mild steel, max tensile 400 MPa. No engineering restriction in procurement spec — HSLA at 550 MPa now being run |
| EEM-002 | Design tolerance | Back gauge design accuracy: ±0.1mm. Actual positioning accuracy at install: ±0.3mm — known deviation, never formally addressed |
| EEM-003 | Die design life | Die set rated 500,000 cycles at 250 MPa material. No cycle-life adjustment formula exists for higher-grade materials |
| EEM-004 | Stroke speed | Machine frame rated continuous operation at 8mm/s stroke. Kaizen FI-002 increased to 11mm/s — no structural review |

---

## Pillar 6 — Training and Education

| ID | Date | Person | Event | Detail |
|---|---|---|---|---|
| TE-001 | Dec 28 | Mike T | AM recertification completed | New checklist format introduced as part of recertification |
| TE-002 | Dec 28 | — | Checklist revision | Ram parallelism check removed from night shift AM checklist — oversight during format change |
| TE-003 | Feb 1 | Sarah K | Bend allowance / springback training | Material-specific springback tables covered. Attendance: day shift only |
| TE-004 | — | Night shift operators | No training | HSLA material introduced to production — no operator training on material behavior differences |

---

## Pillar 7 — Safety, Health and Environment

| ID | Date | Type | Description |
|---|---|---|---|
| SHE-001 | Jan 31 | Near-miss | Die ejected during quick-change procedure — new system installed Jan 10, locking mechanism not properly torqued. Reported by Mike T |
| SHE-002 | Feb 18 | Near-miss | Operator reached into die area during back gauge manual adjustment — guarding gap identified |
| SHE-003 | Jan–Feb | Ergonomic | 3 reports of shoulder strain during die changes — heavy tooling, no lift assist for quick-change system |
| SHE-004 | Feb 10 | Noise | 87 dB measured during HSLA bending (threshold: 85 dB) — no PPE upgrade issued |

---

## Pillar 8 — Administration and Office TPM

| ID | Date | Type | Detail |
|---|---|---|---|
| ADM-001 | Ongoing | Inventory policy | Part #HYD-4721 (hydraulic seal kit) — reorder point set at 0 stock. Lead time: 21 days. Has caused 3 PM deferrals in 12 months |
| ADM-002 | Jan 15 | Work order | WO-0431 raised for PM-001 — closed as "deferred" after 4 weeks with no resolution tracking or escalation |
| ADM-003 | Feb 1–12 | Procurement | Die set #DS-118 approval cycle: 11 days. Request to approval blocked at engineering sign-off queue |
| ADM-004 | Nov 2023 | Change control | HSLA steel added to approved supplier list — no engineering change notification issued to maintenance or production engineering |

---

## Embedded Cross-Pillar Connections (Hidden — Agent Must Discover)

These connections are not labeled anywhere in the data above. They exist across pillars.

| Connection | Pillars | Chain |
|---|---|---|
| A | TE-002 → AM-001 → QM-001 | Checklist revision removed parallelism check → Mike T skipped it 14 nights → bend angle variation on night shift batches Jan 28–30 |
| B | ADM-004 → EEM-001 → QM-001 + QM-002 + SHE-004 | HSLA approved in procurement with no engineering notification → machine running out-of-spec material → quality drift + noise breach |
| C | FI-001 → SHE-001 | Quick-change die system installed with no safety validation → die ejected 21 days later |
| D | ADM-001 → PM-001 → QM-004 | Seal kit always out of stock → PM deferred 19 days → hydraulic degradation → scrap spike week of Feb 3–7 |
| E | EEM-002 + PM-004 → QM-003 | Back gauge accuracy degraded below design spec + calibration deferred 14 days → flange length variation Feb 20 |
| F | FI-002 → EEM-004 | Stroke speed raised above machine rating with no structural review — latent risk, no event yet |
| G | TE-004 + ADM-004 → QM-002 | Night shift operators not trained on HSLA springback behavior, and no one knew HSLA had been introduced → compensation never set |
