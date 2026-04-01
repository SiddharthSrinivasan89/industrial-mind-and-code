# TPM Cross-Pillar Investigation Report

## Cross-Pillar Connection Report — PB-07

**Investigator:** Senior TPM Lead
**Subject:** Cross-Pillar Root Cause Analysis (Jan 1 – Mar 7, 2024)
**Machine:** PB-07 Press Brake

---

### Connection 1: Checklist Integrity & Autonomous Maintenance Drift
**Pillars:** Training and Education → Autonomous Maintenance → Quality Maintenance
**Chain:** TE-002 → AM-001 → QM-001
**Mechanism:** A revision to the Autonomous Maintenance checklist (TE-002) inadvertently removed the "Ram parallelism check" from the night shift procedure. Consequently, Operator Mike T did not perform this critical check on 14 of 20 shifts (AM-001). The lack of verification allowed hydraulic ram alignment drift to go undetected, directly resulting in bend angle variation defects during night shift production batches (QM-001).
**Consequence / Risk:** Unvalidated process changes degrade operator adherence. A checklist update intended to streamline work inadvertently compromised machine precision, causing scrap and customer complaints without triggering a single pillar alarm.
**Confidence:** HIGH

### Connection 2: Procurement Silence & Out-of-Spec Material Usage
**Pillars:** Administration and Office TPM → Early Equipment Management → Quality Maintenance + Safety Health and Environment
**Chain:** ADM-004 → EEM-001 → QM-001 / QM-002 / SHE-004
**Mechanism:** HSLA steel was added to the approved supplier list via a procurement action (ADM-004) without issuing an Engineering Change Notification (ECN). This bypassed Early Equipment Management design limits (EEM-001), which rate the machine for mild steel only. Operators ran HSLA 550 MPa material, causing quality drift (QM-001/QM-002) and exceeding noise thresholds due to higher tensile strength dynamics (SHE-004).
**Consequence / Risk:** Procurement decisions made in isolation override machine design constraints. The lack of an ECN means maintenance teams, engineers, and safety officers are unaware of material changes until defects or noise breaches occur.
**Confidence:** HIGH

### Connection 3: Kaizen Safety Validation Gap
**Pillars:** Focused Improvement → Safety, Health and Environment
**Chain:** FI-001 → SHE-001
**Mechanism:** A Kaizen event (FI-001) installed a new quick-change die system to reduce setup time without conducting a safety or validation review. Approximately 21 days later, the locking mechanism on this unvalidated system failed during a procedure, causing a near-miss where a die was ejected (SHE-001).
**Consequence / Risk:** Speed improvements (OEE) cannot be implemented without verifying that new hardware maintains safety integrity. The "Kaizen" mindset focused on time savings while ignoring the physical validation of new mechanical interfaces.
**Confidence:** HIGH

### Connection 4: Inventory Policy Impact on Maintenance & Quality
**Pillars:** Administration and Office TPM → Planned Maintenance → Quality Maintenance
**Chain:** ADM-001 → PM-001 → QM-004
**Mechanism:** The inventory policy for hydraulic seal kits (ADM-001) set the reorder point at zero stock. When a scheduled maintenance event occurred (PM-001), the kit was unavailable, forcing a 19-day deferral. This extended degradation period allowed hydraulic fluid loss to reach critical levels during the subsequent production window, triggering a scrap rate spike (QM-004).
**Consequence / Risk:** Administrative inventory policies directly drive machine reliability and quality stability. "Just-in-Time" logic applied to critical consumables creates unacceptable risk windows where equipment performance degrades without immediate repair capability.
**Confidence:** HIGH

### Connection 5: Design Tolerance vs. Maintenance Deferral
**Pillars:** Early Equipment Management → Planned Maintenance → Quality Maintenance
**Chain:** EEM-002 + PM-004 → QM-003
**Mechanism:** The back gauge was installed with a known accuracy deviation (±0.3mm) versus design spec (±0.1mm) (EEM-002). When the scheduled calibration maintenance (PM-004) was deferred by 14 days due to technician availability, this latent defect manifested as flange length variation on batch B2215 (QM-003).
**Consequence / Risk:** Design tolerances that are already out of spec rely entirely on perfect maintenance execution. When maintenance is delayed (due to staffing or parts), the machine operates outside its design safety/quality envelope immediately.
**Confidence:** HIGH

### Connection 6: Process Improvement vs. Machine Design Limits
**Pillars:** Focused Improvement → Early Equipment Management
**Chain:** FI-002 → EEM-004
**Mechanism:** A Kaizen initiative (FI-002) increased stroke speed from 8mm/s to 11mm/s to reduce cycle time. However, the machine frame is rated for continuous operation at only 8mm/s (EEM-004). No structural review was conducted before this change.
**Consequence / Risk:** This creates a latent failure risk. While no breakdown has occurred yet (unlike QM defects), the machine is operating in an unverified fatigue regime. Future hydraulic spikes or frame cracking could occur if speed increases continue without engineering validation.
**Confidence:** MEDIUM

### Connection 7: Training Gaps & Material Change Management
**Pillars:** Administration and Office TPM → Training and Education → Quality Maintenance
**Chain:** ADM-004 + TE-004 → QM-002
**Mechanism:** HSLA material was introduced via procurement (ADM-004) without notifying engineering or production. Consequently, night shift operators received no specific training on the different springback behavior of HSLA compared to mild steel (TE-004). When running this material, operators used standard compensation settings derived for mild steel, resulting in springback inconsistency (QM-002).
**Consequence / Risk:** Material changes require synchronized updates to training and process parameters. The lack of notification meant the "new" material was treated as "old" material by the production team until a defect was identified.
**Confidence:** HIGH

---

## Priority Actions

1.  **Implement Engineering Change Notification (ECN) Protocol**
    *   **Targets:** Addresses Connection 2, Connection 7, and partially Connection D.
    *   **Action:** Mandate that any material or supplier change (ADM) triggers a mandatory review in Early Equipment Management (EEM) and Training (TE) before production begins. No HSLA runs without updated springback tables and operator training logs.

2.  **Establish Kaizen Safety Gatekeeping**
    *   **Targets:** Addresses Connection 3, Connection 6, and partially Connection C.
    *   **Action:** Require a Safety Health and Environment (SHE) sign-off for all Focused Improvement (FI) hardware or speed changes. Specifically, revert stroke speed to rated limits (8mm/s) pending structural analysis of the frame at 11mm/s.

3.  **Restore Critical Spares & Lock Checklist Integrity**
    *   **Targets:** Addresses Connection 4, Connection 1, and partially Connection E.
    *   **Action:** Increase reorder point for hydraulic seal kits (ADM-001) to cover minimum 2-week lead time + buffer. Freeze checklist revisions (TE) until they are validated on a pilot shift; revert TE-002 changes immediately to reinstate parallelism checks.
