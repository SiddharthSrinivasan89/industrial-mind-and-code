# TPM Press Brake — Synthetic Dataset V2

**Machine:** PB-07 — AMADA HFE 100-ton Hydraulic Press Brake
**Floor:** Bay 3, Building A
**Period:** January 1 – March 7, 2024
**Note:** This dataset reflects realistic factory conditions. Records are incomplete, inconsistently logged, and sourced from multiple systems with no single owner. Some events were verbally reported and never formally entered. Some logs have gaps. Some entries are vague. Red herrings exist.

---

## Operators & Roles (Reference)

| Person | Role | Shift | Notes |
|---|---|---|---|
| Rajan M | Press Brake Op (Senior) | Night | 11 years experience. Logs sparingly. |
| Kavitha N | Press Brake Op | Day | Thorough logger. Raises issues formally. |
| Suresh D | Press Brake Op | Afternoon | Adequate logger. Tends to mark "OK" without detail. |
| Arjun P | Press Brake Op (New hire) | Night | Started Feb 12. Inducted verbally by Suresh D. No formal induction record. |
| Vijay R | Maintenance Tech | All (on-call) | Covers PB-07 and PB-04. Stretched thin. |
| Dinesh K | Shift Supervisor | Afternoon/Night | Keeps personal notebook. Does not always file formal reports. |
| Priya S | Quality Inspector | Day | Only covers day shift. Night/afternoon quality relies on operator self-check. |
| Binu O | Safety Rep | All | New to role as of Jan 1. Still learning the paperwork system. |

---

## 1. Shift Handover Notes (Raw — Dinesh K's log book, partial transcription)

> *These are informal. Not all shifts have entries. Transcribed by admin assistant on request — some entries illegible or abbreviated.*

**Jan 8 (Night → Day):**
"PB-07 ran fine. Rajan says hydraulic felt a bit sticky at startup but went away. Didn't log it. Back gauge homing slow — maybe 2 sec delay. Told Kavitha."

**Jan 15 (Day → Afternoon):**
"PM due today on PB-07 — Vijay says seal kit not in stock, deferred. Kavitha flagged bend angle issue on last 20 parts of B2204, put them aside for Priya. Not sure if they're scrap yet."

**Jan 19 (Night → Day):**
"[No entry — Dinesh on leave. No handover logged for Jan 16–19]"

**Jan 29 (Afternoon → Night):**
"Switched to new steel batch MS-447 this afternoon. Suresh noticed parts felt stiffer to bend but within spec so kept going. Rajan taking over."

**Jan 31 (Night → Day):**
"Die flew out during setup — Rajan was changing tooling with new quick-release. Nobody hurt but it landed about 2 meters away. Rajan reported to Dinesh verbally. Dinesh said he'd write it up."

**Feb 3 (Day → Afternoon):**
"PM finally happened today — Vijay was on it all morning. Machine back up at 1pm. Scrap rate this week has been bad, Priya flagged it. Not sure if related to the deferred PM or something else."

**Feb 8 (Afternoon → Night):**
"Back gauge procedure update from the Kaizen team — new reference sheet posted on the machine. Suresh showed Rajan and Arjun. Not sure Arjun understood it properly, he's still new."

**Feb 12 (Day → Afternoon):**
"Arjun P started today. Suresh walked him through startup and the AM checklist. Didn't have time to do full induction — told him to ask questions. No paperwork done yet."

**Feb 14 (Night → Day):**
"[No entry]"

**Feb 17 (Night → Day):**
"Arjun's shift. Parts from last night have some angle issues — put aside. Arjun said machine 'seemed fine'. Back gauge was set manually, not sure if he used the new reference sheet."

**Feb 18 (Afternoon → Night):**
"Dinesh here — Suresh mentioned something happened this afternoon, operator reached in near the tooling during a back gauge adjustment. No injury. Dinesh said he would file the near-miss form. [Note: form not found in safety system as of March]"

**Feb 21 (Afternoon → Night):**
"Near-miss — Arjun reached into die area. Filed formally by Binu O. Arjun was not wearing hearing protection either."

**Feb 28 (Day → Afternoon):**
"Back gauge still drifting. Kavitha re-zeroed it manually this morning. Vijay came by and said the calibration PM was still pending from Feb 15 — keeps getting pushed. Die set DS-118 still not here."

---

## 2. Autonomous Maintenance Log — PB-07

> *Logged on paper checklist. Transcribed weekly into shared drive. Night shift logging is sparse. Some weeks missing entirely.*

| Date | Operator | Shift | Hydraulic Oil | Back Gauge | Ram Parallelism | Tooling Inspect | Notes |
|---|---|---|---|---|---|---|---|
| Jan 2 | Kavitha N | Day | OK (measured 87%) | OK | OK | OK | — |
| Jan 3 | Suresh D | Afternoon | OK | OK | — | OK | Skipped parallelism — was busy |
| Jan 4 | Rajan M | Night | OK | OK | — | — | — |
| Jan 5 | Rajan M | Night | OK | — | — | — | — |
| Jan 8 | Kavitha N | Day | OK (measured 84%) | Slow homing ~2s | OK | OK | Flagged slow homing to Dinesh |
| Jan 9 | Suresh D | Afternoon | OK | OK | — | OK | — |
| Jan 10 | Rajan M | Night | OK | OK | — | — | — |
| Jan 11 | Rajan M | Night | — | — | — | — | [NO ENTRY] |
| Jan 12 | Rajan M | Night | — | — | — | — | [NO ENTRY] |
| Jan 15 | Kavitha N | Day | OK (measured 81%) | OK | OK | OK | Oil low-ish, mentioned to Vijay |
| Jan 16–19 | — | — | — | — | — | — | [4-DAY GAP — no logs filed] |
| Jan 22 | Kavitha N | Day | OK | Drift noted +0.3mm | OK | OK | Back gauge drift — told Priya |
| Jan 23 | Suresh D | Afternoon | OK | OK | — | OK | — |
| Jan 24 | Rajan M | Night | OK | — | — | — | — |
| Jan 25 | Rajan M | Night | — | — | — | — | [NO ENTRY] |
| Jan 29 | Suresh D | Afternoon | OK | OK | — | OK | New batch MS-447 loaded |
| Jan 30 | Rajan M | Night | OK | — | — | — | — |
| Jan 31 | Rajan M | Night | — | — | — | — | [NO ENTRY — die incident this shift] |
| Feb 3 | Kavitha N | Day | OK (measured 89% post-PM) | OK | OK | OK | Post PM. Machine better. |
| Feb 5 | Suresh D | Afternoon | OK | OK | — | OK | — |
| Feb 7 | Rajan M | Night | OK | — | — | — | — |
| Feb 8 | Suresh D | Afternoon | OK | OK | — | OK | New back gauge procedure posted |
| Feb 12 | Suresh D | Afternoon | OK | OK | — | OK | Arjun started today |
| Feb 13 | Rajan M | Night | OK | — | — | — | — |
| Feb 14 | Arjun P | Night | — | — | — | — | [NO ENTRY] |
| Feb 15 | Arjun P | Night | OK | OK | — | — | — |
| Feb 16 | Arjun P | Night | OK | OK | — | — | — |
| Feb 17 | Arjun P | Night | OK | — | — | — | machine seemed fine |
| Feb 18 | Suresh D | Afternoon | OK | OK | — | OK | — |
| Feb 19 | Arjun P | Night | OK | — | — | — | — |
| Feb 20 | Kavitha N | Day | OK | Drift +0.5mm | OK | OK | Back gauge worse. Re-zeroed. |
| Feb 21 | Arjun P | Night | — | — | — | — | [NO ENTRY] |
| Feb 22 | Kavitha N | Day | OK | OK (after re-zero) | OK | Wear on Die #3 | Die #3 edge wear unusual — told Vijay |
| Feb 26 | Suresh D | Afternoon | OK | OK | — | OK | — |
| Feb 27 | Rajan M | Night | OK | — | — | — | — |
| Feb 28 | Kavitha N | Day | OK | Drift again +0.4mm | OK | OK | Back gauge can't hold zero |
| Mar 1 | Vijay R | Day | — | CALIBRATED | — | — | Calibration PM done. Back gauge stable. |
| Mar 5 | Kavitha N | Day | OK | OK | OK | OK | — |

---

## 3. Maintenance Work Orders

| WO# | Raised | Machine | Task | Assigned | Completed | Status | Notes |
|---|---|---|---|---|---|---|---|
| WO-0431 | Jan 15 | PB-07 | Hydraulic PM (seal kit) | Vijay R | Feb 3 | Closed | Deferred — HYD-4721 out of stock. Closed 19 days late. |
| WO-0432 | Jan 15 | **PB-04** | Hydraulic cylinder leak | Vijay R | Jan 22 | Closed | Urgent — PB-04 down. Vijay pulled from PB-07 work to cover. |
| WO-0433 | Jan 22 | PB-07 | Back gauge homing investigation | Vijay R | — | **OPEN** | Vijay looked at it briefly Jan 23, said "probably software, will revisit". Never closed. |
| WO-0441 | Feb 1 | PB-07 | Die set DS-118 replacement | Vijay R | Feb 17 | Closed | Die arrived Feb 15. Vijay replaced Feb 17. |
| WO-0445 | Feb 15 | PB-07 | Ram parallelism calibration | Vijay R | Mar 1 | Closed | Deferred twice — Vijay on PB-04 breakdown Feb 20, then parts issue. |
| WO-0447 | Feb 20 | **PB-04** | Servo motor failure | Vijay R | Feb 27 | Closed | Second PB-04 breakdown in 2 months. Vijay fully occupied Feb 20–25. |
| WO-0452 | Feb 22 | PB-07 | Die #3 wear inspection | Vijay R | — | **OPEN** | Kavitha raised it. Vijay hasn't looked yet. |

---

## 4. Quality Records

> *Day shift records are complete — Priya inspects formally. Afternoon and night shift relies on operator self-check. Results less reliable.*

| Ref | Date | Batch | Material | Shift | Inspector | Defect | Metric | Notes |
|---|---|---|---|---|---|---|---|---|
| QM-001 | Jan 15 | B2204 | Mild steel MS-441 | Day | Priya S | Bend angle variation | ±0.6° (spec ±0.2°) | Last 20 parts of shift. Held for review. |
| QM-002 | Jan 28–30 | B2208 | HSLA 550 MPa | Night | Self-check | Bend angle variation | ±0.8° reported by Rajan | Rajan noted it but didn't stop production. Priya reviewed on Jan 31 — confirmed scrap. |
| QM-003 | Jan 30–31 | B2209 | Mild steel MS-447 | Afternoon/Night | Self-check | "Parts feel different, angles within spec" | — | Suresh's note. No formal defect raised. Priya unaware. |
| QM-004 | Feb 3–7 | Mixed | Mixed | Mixed | Priya S | Scrap rate spike | 4.2% (baseline 1.1%) | Priya flagged. Cause listed as "under investigation". Never formally closed. |
| QM-005 | Feb 17–19 | B2213 | Mild steel MS-447 | Night | Self-check | Bend angle issues | "Not sure — some parts off" | Arjun's note. No measurement recorded. Parts set aside but no formal rejection. |
| QM-006 | Feb 20–26 | B2215 | Mild steel | Day/Afternoon | Priya S | Flange length variation | ±0.6mm (spec ±0.15mm) | Back gauge suspected. Multiple batches affected. |
| QM-007 | Mar 1–5 | B2220 | Mild steel | Day | Priya S | Within spec | — | Post-calibration PM. Quality recovered. |

---

## 5. Safety Incident Log

> *Binu O is new to the role. Formal reports incomplete. Some incidents exist only in shift handover notes or verbal accounts.*

| Ref | Date | Type | Formal Report? | Description |
|---|---|---|---|---|
| SHE-001 | Jan 31 | Near-miss | **NO** | Die ejected during quick-change setup. Rajan M reported verbally to Dinesh K. Dinesh said "I'll write it up." No formal report filed. Mentioned in handover note only. |
| SHE-002 | Feb 10 | Noise measurement | YES (partial) | 87 dB during HSLA bending. Binu O noted it but did not issue PPE upgrade or formal action. Threshold is 85 dB. Form filed, no follow-up. |
| SHE-003 | Feb 18 | Near-miss | **NO** | Operator (Suresh D's shift) reached into die area during back gauge adjustment. Dinesh K noted in personal notebook — "Suresh said someone reached in, I'll file tomorrow." Form never filed. |
| SHE-004 | Feb 21 | Near-miss | YES | Arjun P reached into die area during setup. Binu O filed report. Arjun not wearing hearing protection. Corrective action: verbal warning. |
| SHE-005 | Feb 22 | Ergonomic | YES (partial) | Kavitha N filed ergonomic complaint — shoulder strain during die changes. Binu O acknowledged. No action yet. |

---

## 6. Focused Improvement Tracker

> *Maintained as a shared Excel spreadsheet. Ownership unclear. Last column ("Outcome") often blank.*

| ID | Start | Initiated By | Target | Status | Outcome / Notes |
|---|---|---|---|---|---|
| FI-001 | Jan 10 | Suresh D + Dinesh K | Reduce die setup time 20% | Complete | Quick-change die system installed. No safety review. Locking torque spec not communicated to night shift. |
| FI-002 | Feb 5 | Dinesh K | Reduce bracket family cycle time | Complete | Stroke speed increased 8→11mm/s. Machine engineering limits not checked. Hydraulic pressure spikes noted post-change but not formally recorded. |
| FI-003 | Feb 8 | Priya S + Suresh D | Reduce back gauge positioning errors | **In Progress — STALLED** | New reference procedure written and posted. Reference block (part #BG-REF-02) not yet procured — PO raised Feb 9, still in approval. Operators using new procedure sheet but old reference block. |
| FI-004 | Feb 15 | Kavitha N | Standardise die change ergonomics | **Not Started** | Raised after SHE-005. No owner assigned. Sitting in the tracker. |

---

## 7. Early Equipment Management (Machine Specs)

> *Static document. Rarely referenced. Last updated at machine installation (2019).*

- **Frame rated stroke speed:** 8mm/s continuous
- **Material spec:** Mild steel, max tensile 400 MPa
- **Back gauge design accuracy:** ±0.1mm
- **Back gauge actual accuracy at install:** ±0.3mm — noted as "acceptable deviation, monitor" in install report. No formal deviation record raised.
- **Die design life:** 500,000 cycles at 250 MPa. No formula for higher-tensile materials.
- **Back gauge reference block:** Part #BG-REF-01 (original). Procedure references this part.

---

## 8. Training Records

> *No central training system. Records are a mix of sign-off sheets in a binder, email confirmations, and verbal confirmations. The following is reconstructed from available sources.*

| ID | Date | Person | Training | Format | Verified |
|---|---|---|---|---|---|
| TE-001 | Dec 28 | Rajan M | AM recertification — new checklist format | Classroom | Sign-off sheet (in binder) |
| TE-002 | Dec 28 | Suresh D | AM recertification — new checklist format | Classroom | Sign-off sheet (in binder) |
| TE-003 | Dec 28 | — | Checklist revision: ram parallelism check removed from night shift procedure | Internal memo | Memo filed. Not confirmed read by operators. |
| TE-004 | Feb 1 | Kavitha N | Bend allowance / HSLA springback | External course | Certificate on file |
| TE-005 | Feb 8 | Suresh D, Rajan M | New back gauge procedure (FI-003) | Walkthrough by Suresh D | **No sign-off. Verbal only.** |
| TE-006 | Feb 12 | Arjun P | Machine induction | Verbal walkthrough by Suresh D, ~1 hour | **No record. Not in system.** |
| — | — | Arjun P | AM checklist procedure | — | **No record.** |
| — | — | Arjun P | New back gauge procedure | — | **No record.** |
| — | — | Night shift operators | HSLA material behavior / springback | — | **No training conducted.** |

---

## 9. Administration and Office TPM

| ID | Date | Type | Detail |
|---|---|---|---|
| ADM-001 | Ongoing | Inventory policy | Part #HYD-4721 (hydraulic seal kit) — reorder point set at 0. Lead time 21 days. Out of stock when WO-0431 raised. Has caused 3 PM deferrals in 12 months. |
| ADM-002 | Nov 2023 | Change control | HSLA 550 MPa added to approved supplier list by procurement. No Engineering Change Notification issued. Maintenance, production engineering, and training unaware. |
| ADM-003 | Jan 29 | Material batch | Steel batch changed from MS-441 to MS-447 (different mill, same grade). Tensile strength MS-447: 380 MPa vs MS-441: 310 MPa. Batch change recorded in production schedule only — not in TPM or quality systems. |
| ADM-004 | Feb 1 | Procurement | Die set DS-118 requested — reason logged as "routine replacement". Actual cause (accelerated wear from HSLA running) not documented. Approved Feb 12, 11-day cycle. |
| ADM-005 | Feb 9 | Procurement | Reference block BG-REF-02 requested for FI-003. Requires engineering sign-off. Sitting in approval queue. Not yet approved as of Mar 7. |
| ADM-006 | Feb 12 | HR / Onboarding | Arjun P employment start. Standard induction pack issued. Press brake specific training marked "to be completed" — not followed up by supervisor. |

---

## Hidden Cross-Pillar Connections — V2

> *These connections are embedded in the data above but require the agent to reason across incomplete, inconsistent, and fragmented sources. Some require inference under uncertainty. One is a red herring.*

| ID | Pillars | Chain | Why it's hard to find |
|---|---|---|---|
| V2-A | TE → AM → QM | TE-006 (no induction record for Arjun) → Arjun's AM log gaps (Feb 14, 21) + vague entries → QM-005 (unmeasured "parts off" night shift) | Arjun's name doesn't appear in QM records. Quality issue logged as "night shift", cause unknown. |
| V2-B | FI-003 + ADM-005 → AM → QM | FI-003 stalled (no reference block) → operators using new procedure + old block (BG-REF-01) → systematic back gauge offset → QM-006 flange variation | AM logs say "back gauge OK" — operators think they're checking correctly. The error is in what they're checking against. |
| V2-C | WO-0432 (PB-04) → Vijay R availability → PM-deferral chain | PB-04 breakdown Jan 15 pulled Vijay off PB-07 → WO-0431 deferred, WO-0433 never actioned → hydraulic degradation and back gauge drift unresolved | The PB-04 link is only visible in WO-0432. The PM deferral reasons say "parts" and "technician" — not "other machine". |
| V2-D | ADM-003 → QM-003/QM-005 | Material batch MS-447 (380 MPa) loaded Jan 29 → "stiffer" feel noted by Suresh (not a defect, no formal record) → Arjun running same batch Feb 17–19 with no awareness of material change → QM-005 | This is a **partial red herring** — MS-447 causes subtle variation but is within machine spec. It amplifies other problems (back gauge drift) but is not the root cause alone. Agent must distinguish this from the HSLA issue. |
| V2-E | SHE-001 (unlogged) + FI-001 → SHE-003/SHE-004 | Die ejected Jan 31 (near-miss, not formally reported) due to FI-001 locking torque not communicated → no corrective action taken → guard configuration changed by FI-001 not documented → two more near-misses Feb 18 (also unlogged) and Feb 21 | The Jan 31 and Feb 18 near-misses don't exist in the formal safety system — only in shift notes and Dinesh's notebook. |
| V2-F | ADM-002 → EEM-001 → AM-die wear → ADM-004 | HSLA introduced without ECN → running above machine material spec → die wearing at ~1.4x design rate → Kavitha notices "unusual edge wear" Feb 22 → die replacement request ADM-004 raised as "routine" — root cause never captured | The die wear signal (AM Feb 22) is a single informal observation. The wear rate calculation requires comparing EEM design life against actual cycle count — no one has done this. |
| V2-G | **RED HERRING** — PB-04 operator reassignment | PB-04 breakdown in Jan → 2 operators temporarily moved to assist PB-04 → PB-07 short-staffed Jan 16–19 (explains 4-day AM log gap) → *looks like* staffing caused quality issues | AM gap Jan 16–19 is real. But PB-07 quality issues in that period are within spec (no QM record). The agent should note this as a possible factor but mark it as unsupported — the quality issues come later and from other causes. |
| V2-H | FI-002 → EEM (stroke speed) + hydraulic pressure | Stroke speed raised to 11mm/s (above 8mm/s frame rating) → hydraulic pressure spikes noted informally post-FI-002 but not formally recorded → WO-0433 (back gauge homing) never resolved → latent structural risk | Hydraulic pressure spikes mentioned in handover notes but no formal log. WO-0433 is open but Vijay dismissed it as "probably software". |
