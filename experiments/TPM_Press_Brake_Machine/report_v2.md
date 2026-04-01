# TPM Cross-Pillar Investigation Report

# Cross-Pillar Connection Report — PB-07

## Connection 1: Back Gauge Reference Block Mismatch Chain
**Pillars:** Focused Improvement (FI) → Administration (ADM) → Autonomous Maintenance (AM) → Quality Maintenance (QM)

**Chain:** FI-003 (stalled reference block procurement) → ADM-005 (BG-REF-02 stuck in approval queue) → AM logs (operators reporting "OK" with old BG-REF-01) → QM-006 (flange length variation ±0.6mm)

**Mechanism:** The new back gauge procedure was written and posted (Feb 8), but the reference block required for accurate measurement never arrived. Operators continued using old reference block BG-REF-01 while following "new" procedures. This creates a systematic measurement error that appears as "back gauge OK" in AM logs but produces consistent quality variation. The calibration PM (WO-0445) was deferred twice, allowing this configuration mismatch to persist for 3+ weeks.

**Consequence / Risk:** Flange length out of spec by up to 0.6mm (vs ±0.15mm spec). Parts shipped or scrapped without detection because operators believe their checks are valid. Customer complaints likely hidden in "under investigation" status.

**Confidence:** HIGH

---

## Connection 2: Training Gap → Safety Near-Miss Chain
**Pillars:** Training and Education (TE) → Safety, Health and Environment (SHE) → Autonomous Maintenance (AM)

**Chain:** TE-006 (Jordan's induction incomplete, no formal record) → Jordan's AM log gaps (Feb 14, Feb 21) → SHE-004 (Jordan reached into die area during setup) + SHE-003 (Dave's shift similar incident)

**Mechanism:** Jordan started Feb 12 with only verbal induction. No formal documentation of safety procedures for quick-change system or back gauge adjustments. AM logs show gaps on nights where Jordan worked. The pattern shows inexperienced operators performing tasks without documented safety training. Combined with unlogged near-miss from Jan 31 (SHE-001), this suggests a systemic issue: safety incidents not formally reported → no corrective action → repeat incidents.

**Consequence / Risk:** Potential for serious injury if operator reaches into die area during power-on or quick-change. Current guard configuration changed by FI-001 not documented in training. Regulatory and insurance implications if incident escalates.

**Confidence:** HIGH

---

## Connection 3: Maintenance Resource Strain Chain
**Pillars:** Equipment Engineering & Maintenance (EEM) → Focused Improvement (FI) → Administration (ADM) → Quality Maintenance (QM)

**Chain:** WO-0432 (PB-04 breakdown Jan 15) → Ray pulled off PB-07 work → WO-0431 deferred (hydraulic PM) + WO-0433 never closed (back gauge homing) → QM-002/QM-004/QM-005 (quality degradation Feb 1–26)

**Mechanism:** Single technician covering multiple machines creates cascading deferrals. PB-04 breakdown required Ray's immediate attention, leaving PB-07 without dedicated maintenance coverage for 4+ days. This explains AM log gaps Jan 16–19. However, quality issues in that period are within spec (red herring). The real impact: deferred PMs allow hydraulic degradation and back gauge drift to compound. WO-0433 never closed because Ray was stretched thin across multiple machines.

**Consequence / Risk:** Accumulated maintenance debt → equipment reliability decline → unplanned downtime risk increases. Hydraulic system operating above design limits (see Connection 7) with deferred PMs compounds failure probability.

**Confidence:** HIGH

---

## Connection 4: Material Change Without ECN Chain
**Pillars:** Administration (ADM) → Quality Maintenance (QM) → Training and Education (TE)

**Chain:** ADM-002 (HSLA added to supplier list without ECN) + ADM-003 (MS-447 batch loaded Jan 29, not documented in TPM systems) → TE-003 (night shift procedure change not confirmed read) + no HSLA training for night shift → QM-005 (Feb 17-19 quality issues with MS-447)

**Mechanism:** Higher-tensile material (380 MPa vs 310 MPa) introduced without engineering change notification. Night shift operators never trained on HSLA springback characteristics. Jordan ran MS-447 Feb 17–19 with no awareness of material properties. Material is within machine spec but amplifies existing problems (back gauge drift, hydraulic issues). Dave's informal note "stiffer feel" was never formalized or acted upon.

**Consequence / Risk:** Quality variation amplified by untrained operators on unfamiliar material. Springback characteristics different from baseline → bend angle compensation needed. If not documented, future batches will repeat issue. Partial red herring: material alone within spec but interaction with other problems creates quality impact.

**Confidence:** MEDIUM (partial red herring as noted in V2-D)

---

## Connection 5: Hydraulic System Degradation Chain
**Pillars:** Equipment Engineering & Maintenance (EEM) → Quality Maintenance (QM) → Safety, Health and Environment (SHE)

**Chain:** WO-0431 deferred (hydraulic seal kit out of stock, ADM-001) + FI-002 (stroke speed increased to 11mm/s above 8mm/s frame rating) + hydraulic pressure spikes noted informally → QM-004/QM-005 (scrap rate spike Feb 3–26) + latent structural risk

**Mechanism:** Hydraulic system operating above design limits with deferred PMs. Pressure spikes cause seal wear, contamination ingress, and inconsistent ram force. Back gauge drift compounds this: ram position less accurate → bend angle variation. Safety risk: hydraulic leaks or failure could cause pinch points or uncontrolled movement. No formal pressure logging means degradation goes unnoticed until quality impact appears.

**Consequence / Risk:** Hydraulic system failure → unplanned downtime + potential safety incident. Seal kit stock at zero (ADM-001) means no buffer for reordering lead time of 21 days.

**Confidence:** HIGH

---

## Connection 6: Safety System Gaps Chain
**Pillars:** Safety, Health and Environment (SHE) → Focused Improvement (FI) → Quality Maintenance (QM)

**Chain:** SHE-001 (die ejected Jan 31, unlogged near-miss) + FI-001 (quick-change system installed without safety review) + locking torque spec not communicated → SHE-003/SHE-004 (repeat incidents Feb 18/21)

**Mechanism:** Safety incident not formally reported to central system → no corrective action taken. Quick-change system guard configuration changed but not documented in training or procedure. Locking torque specification never communicated to operators. Two more near-misses occurred without formal reporting, suggesting safety culture issue where incidents are "too minor" to log.

**Consequence / Risk:** Regulatory compliance risk if incident escalates to injury. Insurance premiums may increase. Safety culture degradation → higher likelihood of serious incident.

**Confidence:** HIGH

---

## Red Herrings Investigated

| ID | Pattern | Why It's a Red Herring |
|---|---|---|
| V2-D | MS-447 material change (ADM-003) | Material within machine spec. Causes subtle variation but is not root cause alone. Amplifies other problems (back gauge drift, hydraulic issues) but doesn't explain quality issues before Jan 29. QM-005 can be explained by back gauge + training gaps without material change. |
| V2-G | PB-04 operator reassignment (staffing) | AM log gap Jan 16–19 is real and explained by Ray's availability. However, PB-07 quality issues in that period are within spec (no QM record). Staffing explains maintenance deferrals but not the Feb quality degradation which stems from other causes. |
| V2-F | Die wear signal (AM Feb 22) | Single informal observation without formal wear rate calculation. Die replacement request logged as "routine" masks root cause (HSLA above design spec). Signal exists but requires cross-pillar analysis to be actionable. |

---

## Priority Actions

**1. Approve BG-REF-02 Reference Block Immediately (ADM-005)**
- **Impact:** Breaks Connection 1 (back gauge drift) and Connection 3 (maintenance deferral chain)
- **Rationale:** This is the single most direct fix for QM-006 flange variation. Without correct reference block, all back gauge checks are invalid. Engineering sign-off needed but can be expedited if framed as "quality risk" not "routine procurement."
- **Timeline:** 3–5 days to approve + 1 week delivery

**2. Complete Jordan P Training Documentation & Safety Review (TE-006 + SHE-004)**
- **Impact:** Breaks Connection 2 (training gap) and Connection 6 (safety system gaps)
- **Rationale:** Jordan represents the most immediate safety risk. Formalize induction, complete all required training modules, and document guard configuration changes from FI-001. If Jordan continues without documentation, consider reassignment pending completion.
- **Timeline:** 1–2 weeks to complete + immediate safety review

**3. Address Hydraulic Seal Kit Stock & WC-0431 PM Deferral (ADM-001 + WO-0431)**
- **Impact:** Breaks Connection 5 (hydraulic degradation) and Connection 3 (maintenance resource strain)
- **Rationale:** Set reorder point at minimum 1 kit (lead time 21 days). Complete deferred PM before next production cycle. This prevents hydraulic failure cascade that compounds all other issues.
- **Timeline:** Immediate procurement + schedule PM within 48 hours

**Secondary Priority:** Close WO-0433 back gauge homing investigation and document FI-001 guard configuration changes in both training and safety systems.
