# pdm-component-attribution-v1-azure — DESIGN

The design was hardened through several rounds of adversarial review before any data or model
run, then frozen. All quantitative and procedural commitments — task definition, evaluation
arms, baselines, decision rules, and random seeds — are frozen in
[specs/FROZEN-SPEC.md](specs/FROZEN-SPEC.md); where this document and the frozen spec disagree,
the frozen spec governs.

**Lineage:** the evaluation harness (blind rendering with the answer stripped, subject fan-out,
deterministic baselines, exact-match scoring) was reused from an earlier diagnostic study on a
different task, to test whether the runner transfers to a materially different problem without a
rewrite.

## 1. What this experiment is

I take the Microsoft Azure Predictive Maintenance sample dataset — simulated by Microsoft,
failure-prediction-shaped, tabular/sensor-heavy — and run a **failure-component classification**
evaluation on it using the DER discipline (role separation, truth isolation, deterministic
baselines). Two questions:

- **Capability question:** conditional on a known machine failure, can LLMs classify which of
  four components failed, from pre-failure evidence only, better than deterministic baselines —
  and how does that change when they receive the same train-period statistical context the
  classical baselines learn from?
- **Framework question:** which parts of DER transfer to a materially different task unchanged,
  and which need a rewrite — scored against the pre-declared predictions in §11 under the
  operational definitions in §11.1.

Naming note: the task was renamed from "component attribution" to **failure-component
classification conditional on a known failure** after round-1 triage (a Codex High finding:
"attribution" overclaims causal root-cause). The folder name keeps the original label as an
admin identifier only; no document claims root-cause identification.

## 2. The dataset (verified at fetch, 2026-07-18 — full profile in data/DATA.md)

100 simulated machines, calendar 2015: hourly telemetry (876,100 rows: volt/rotate/pressure/
vibration), 3,919 error events (error1–5), 3,286 maintenance records (comp1–4, history from
2014-06), 100 machine rows (model1–4, age 0–20), 761 failure rows → 719 unique (machine, T)
events, of which 42 are multi-component (excluded, §5) → **677 single-component events over 98
machines** (two machines have none). All class statistics are at the event unit (round-2 fix —
the failure-row counts overstated them): full 677 = comp2 232 / comp1 172 / comp4 155 /
comp3 118, majority 34.27%; train 464 events (majority 32.11%); eval 213 events over 91
machines (majority 38.97%). Full partition table, priors, and window flags (19 short-telemetry
events, 3 with a recent prior failure) are frozen in FROZEN-SPEC §1. 743/761 failure rows have
a same-timestamp maint row naming the failed component (the confirmed label leak, §6).
Failures cluster at 06:00 (743) and 03:00 (18) — a simulator batch artifact treated as a leak
surface, not a feature (§6).

The data is Microsoft-simulated ("synthesis of multiple real-world business problems") and is
described as such everywhere — never as real plant data. It remains a real *external* test for
DER: I did not generate it, its shape was not designed for my runner, and its ground truth is
independent of my pipeline.

## 3. License Gate (§0) — DEFERRED by Sid's override

Working determination (full record in [data/DATA.md](data/DATA.md)): acquisition from the
Microsoft-owned repo microsoft/sqlworkshops (MIT, pinned commit e836f4e8, SHA-256 per file in
PROVENANCE.json); original Azure AI Gallery publication point retired; Kaggle mirror not used.
Sid authorized the fetch on 2026-07-18 with the license ruling deferred. **No public use of
results or excerpts until the ruling.**

## 4. The task — exact statement and estimand

**Primary task: failure-component classification conditional on a known failure.**
For each single-component failure event (machine m, timestamp T, failed component c*), the
subject receives a text-rendered evidence window drawn strictly from `[T − window, T)` and is
told a failure occurred; it must answer which one of comp1–comp4 failed. Output is JSON with a
single component choice plus a short rationale. Truth is c* from `PdM_failures.csv`, hidden
from the subject.

**Estimand:** classification performance over single-component failure events on *this fleet of
100 simulated machines* in the eval period. Explicitly out of scope: causal root-cause
identification, failure detection/timing, deployment performance, and generalization to unseen
machines (the time split does not estimate it — §6.4).

**LLM arms (per subject):**
- **Arm A — zero-shot:** the evidence window only. Claim scope: zero-shot LLM vs supervised
  baselines — an asymmetric comparison, labeled as such wherever reported.
- **Arm B — train-summary context:** the same window plus a frozen, mechanically derived
  train-only context block: the error→component contingency table (counts, train failures
  only), per-component failure counts, and per-component wear statistics (train-period mean
  days from last replacement to failure). One fixed block for all events, generated once from
  the train split, shown verbatim at the Prompt Gate (round-1 F1 fix; Sid ruled 2026-07-18:
  adopt). Scope, stated wherever H2 is reported: this narrows but does not close the
  information asymmetry — the classical champion learns from labeled examples over the full
  joint feature distribution, Arm B receives aggregate marginals only. H2 is never described
  as a "same-information" or fully fair comparison (round-2 fix).
- **Arm C — label-renaming invariance probe (subset, primary subjects only):** as Arm B, but
  component and error labels bijectively remapped in window, context block, and answer set
  alike (one fixed seeded permutation — FROZEN-SPEC §3). Information content is identical, so
  an Arm B − Arm C gap on the same events is *consistent with* reliance on memorized label
  conventions; it is not a direct memorization measurement, since arbitrary-symbol grounding
  cost can contribute (round-2 fix). Runs on a frozen cluster-preserving subset: whole eval
  machines sampled until ≥50 events (FROZEN-SPEC §3), so the machine-cluster bootstrap
  remains valid. Decision rule: FROZEN-SPEC §5 — descriptive gap + CI with a pre-declared cap
  rule; a power simulation showed equivalence testing is infeasible at this probe size, so no
  "no contamination" verdict exists in this design (a failed difference test is never
  reported as evidence of no contamination).

**Secondary task (phase 2, optional, separate go from Sid): failure detection** — same render,
windows from pre-failure and matched no-failure periods, "does any component fail within 24h",
precision/recall/PR-AUC with time censoring. Specified so the renderer is designed once; not
run in phase 1.

## 5. Ground truth, unit, and exclusions

Unit = unique (machine, T). The 42 multi-component events are excluded from the single-answer
task; because inclusion is determined using contemporaneous truth, the exclusion is published
as cross-tabs (by component, month, machine model, hour) so the narrowing is visible, and every
conclusion is scoped to single-component events. There is NO other exclusion path: an audit
failure before calls stops the process per the frozen-set rule (FROZEN-SPEC header — fix the
defect and rerun the gate, or amend the design with regenerated statistics); after calls
begin nothing is ever dropped (round-6 reconciliation).

## 6. Evidence window, canonical features, rendering, and leakage prevention

**6.0 Canonical feature table first.** One typed per-event feature dictionary is computed from
`[T − window, T)` data; the **markdown-table render** and the **classifier matrix** are both
deterministic projections of it and of nothing else (round-1 F6/F15 fix; a classifier win must
not be a representation win). The full typed dictionary — fields, block boundaries with no
day−1/final-24h overlap, list caps, missing-data encodings, rounding, and both projection
definitions — is frozen in FROZEN-SPEC §4, together with the train-only granularity acceptance
criterion (champion candidates must beat the no-evidence control by ≥5 macro-F1 points on the
tune split before any eval contact).

**6.1 Censoring — one rule, all modalities.** Every join and aggregation reads from
`[T − window, T)` — right-open, strictly before T — for telemetry, errors, maintenance, and
every derived feature. Fail-closed audits, run before any model call: no record of any
modality at ≥ T in any window; interval endpoints checked; incomplete windows (events too
early for a full 72h/7d/90d lookback) flagged and handled by an explicit missing-data policy
(rendered as "no data", never imputed); a duplicate window is an implementation defect —
STOP and rerun the gate per the frozen-set rule, never an exclusion.

**6.2 The maintenance-log trap (confirmed):** 743/761 failure rows have a same-timestamp maint
row naming the failed component. Covered by 6.1's strict boundary; the audit asserts zero maint
records at T in any render.

**6.3 Timestamp and identity hygiene (contamination + shortcut defenses, all arms):** the
render uses **relative time only** ("T−26h", "day −2") — no absolute dates, no time-of-day, no
machineID. This blocks the 06:00/03:00 batch artifact, calendar shortcuts, and memorized-row
lookup by timestamp. A rendered-text scan asserts no absolute timestamp, machine ID, or
failure-log content survives. Fixed schema, fixed numeric precision, deterministic truncation
policy; component answer-option order shuffled per event with the permutation recorded.

**6.4 Split.** Boundary frozen: train = events with T < **2015-09-01 00:00** (464 events),
eval = T ≥ boundary (**213 events, 91 machines** — corrected to the event unit, round-2 fix).
All fitting — error→component mapping, classifier training and selection,
aggregation-granularity choice, context-block statistics — uses train-period data only, with
the frozen tune sub-split (fit < 2015-07-01, tune Jul–Aug; FROZEN-SPEC §7). Machines appear on
both sides: the estimand is same-fleet future events (§4); machine-disjoint splitting is a
robustness check at most, not a phase-1 arm. **Eval set = all 213 single-component eval-period
events** (Sid ruled 2026-07-18: all events, not a subsample). No reserve, no reseed: samples,
seeds, exclusions, and stopping rules are frozen in FROZEN-SPEC §§2–3 before the first call;
the round-1 "targeted reseed if close" language is withdrawn (optional stopping). Flagged
windows (19 short-telemetry, 3 recent-prior-failure) stay included, flagged, with an
exploratory sensitivity analysis excluding them.

**6.5 Ablations (analysis stage, train-only fitting):** feature-group ablations of the
classifier over the groups actually present in the canonical dictionary — telemetry, errors,
maintenance, machine metadata (round-2 fix: the earlier timestamp/row-count groups referenced
fields the canonical table does not carry) — to show where the recoverable signal lives,
reported next to the LLM results as context for what the window contains.

## 7. Baselines (all from the canonical feature table)

- **B1 — prior-weighted random (control):** prediction sampled from the train prior vector
  (FROZEN-SPEC §1), fixed seed; realized draw reported next to its analytic expectation.
- **B2 — no-evidence control:** train majority class (comp2) for every event (prior-only).
- **B3 — oldest component:** longest time since replacement at T; tie rules frozen in
  FROZEN-SPEC §7.
- **B4 — recent-error mapping:** most recent error code in the window mapped via the
  train-only contingency argmax; no-error fallback = B2; tie rules frozen in FROZEN-SPEC §7.
- **B5 — classical champion:** logistic regression vs HistGradientBoosting, trained on the 464
  train-period failure-event windows only; grids, tune boundary (fit < 2015-07-01, tune
  Jul–Aug), selection metric, tie rule, and refit policy frozen in FROZEN-SPEC §7; **one
  champion selected inside train, then frozen** before any eval contact. Both candidates' eval
  numbers reported; only the champion is confirmatory for H2.
- **Label-shuffle plumbing gate (not a baseline):** a 200-iteration y-scrambling permutation
  test on the frozen representation (FROZEN-SPEC §8 is the sole normative rule), fail-closed,
  run before eval.

The "three deterministic baselines" referenced by H1 are exactly **B2, B3, B4** (round-2 fix
of the ambiguous "3–6" reference).

No credible ceiling exists for this dataset (the generator's internals are not published);
that absence is documented rather than implying the boosted tree is the ceiling.

## 8. Model panel (proposal — Sid picks the final panel)

- **Local ladder (kratos, unmetered, serial, 45/15 run/cooldown):** gpt-oss:120b, qwen3.5-122b
  (native `/api/chat`, thinking budgets per experiments/CLAUDE.md), nemotron-3-super
  (THINK_MODE=false), qwen3:4b as ladder floor.
- **Frontier arm (metered — real Azure cost):** gpt-5.4, ≈592 calls total (213 Arm A + 213
  Arm B + 51 Arm C + 90 repeat diagnostics + ~25 preflight; FROZEN-SPEC §12). Fires only
  after Cost Gate arithmetic (measured tokens × rate vs remaining credit) is announced and
  approved. No Codex-hosted subjects (ruling 2026-07-13).
- **Primary subjects (confirmatory, frozen):** gpt-5.4 and gpt-oss:120b. If a primary subject
  is unavailable or its Cost Gate fails, its hypotheses are **not run** — no substitution
  (round-2 fix). All other subjects are exploratory (multiplicity control, §9). Arm C runs on
  primary subjects only.

Decoding, token budgets, and context settings are frozen per subject in FROZEN-SPEC §9 —
never a silent default. Canonical score = first call; repeat-call variance is measured on a
frozen 30-event subset for primary subjects as diagnostics only, never entering confirmatory
inference (round-2 fix).

## 9. Metrics and statistics

- Primary metrics: accuracy and macro-F1; per-component recall reported.
- **Cluster-aware inference:** events cluster within machines (213 eval events, 91 machines).
  All CIs and paired comparisons use the machine-level cluster bootstrap protocol frozen in
  FROZEN-SPEC §6 (B=10,000, seeded, percentile CIs, declared handling of class-sparse
  replicates); event and machine counts reported for every arm; MDE at the frozen sizes
  reported before interpretation.
- **Confirmatory tests = the comparison registry, FROZEN-SPEC §5, verbatim** (round-2 fix of
  the internally inconsistent §9/§10): H1 per primary subject, Arm A vs B2/B3/B4, Holm within
  subject; H2, champion vs each primary subject's Arm B; H2b, descriptive gap + cap rule on
  the materialized probe (equivalence testing shown infeasible at n=51 —
  specs/power-sim-notes.md). Everything else — including Arm A vs champion and all
  non-primary subjects — exploratory and labelled as such.
- Unparseable or invalid output after the IHF-standard parse policy is scored **incorrect**,
  never repaired into a valid answer; parse/truncation/choice-position rates reported per
  model and per true class.
- No LLM judge anywhere; scoring is deterministic exact match. IHF §4.4 telemetry on every
  call; attribution gate (GATES.md §5) before any capability conclusion in either direction.

## 10. Hypotheses (stated now, not pre-registered)

- **H1:** at least one primary subject in Arm A (zero-shot) beats all three deterministic
  baselines B2/B3/B4 on macro-F1 (registry rows R1–R6; intersection-union structure — per
  subject p = max of its three raw bootstrap p-values, Holm over the two subject-level
  p-values; FROZEN-SPEC §5).
- **H1b (exploratory):** Arm B (train-summary context) improves each subject over its own
  Arm A.
- **H2:** the classical champion beats both primary subjects on macro-F1 in Arm B (registry
  rows R7–R8). Arm B narrows but does not close the information asymmetry (§4); H2 is
  reported with that scope, never as a "same-information" comparison. Arm A versions are
  exploratory.
- **H2b (label-renaming invariance, primary subjects — descriptive):** the paired B−C
  accuracy gap on the materialized 51-event probe, reported with its 90% cluster-bootstrap CI
  and MDE (registry R9–R10). A power simulation (specs/power-sim-notes.md) shows equivalence
  testing is infeasible at this size, so **no equivalence verdict exists**; a
  non-significant gap is never evidence of no contamination. Pre-declared cap rule: gap
  > 0.10 with the 90% CI excluding zero → capability claims for that subject capped at Arm C
  performance.
- **H3 (framework), split per component with refutation conditions in §11.1:** the harness
  components predicted to transfer do so under the adapter contract; the scoring interface
  does not transfer (exact-match replaces judge+gold-statement).

## 11. DER transfer accounting

| DER component | Prediction |
|---|---|
| Blind render + truth-stripping assertion | transfers unchanged |
| Subject fan-out (frontier + local ladder) | transfers unchanged |
| Deterministic baseline layer | transfers; heuristics re-derived per domain |
| Independent judge, strict/lenient rubrics | does NOT transfer — replaced by exact match |
| Solvability filter | does NOT transfer — no generator, truth from logs |
| Synthetic pre-gate | not applicable — no generated bundles |
| Exclusions table with reasons | transfers unchanged |

**11.1 Adapter contract (operational definitions — the round-1 falsifiability fix).** The
pipeline-v2 runner is pinned NOW at commit `9a44c726` with a file-level core/interface
inventory frozen in FROZEN-SPEC §10 (round-2 fix — pinning promised is not pinning done);
reclassifying a file after implementation difficulty is observed is a reported protocol
deviation. Outcomes are scored as: **config-only reuse** (core and interface run with configuration
changes only), **adapter reuse** (new renderer/scorer adapters; core unchanged), or **core
rewrite** (any core module modified). Per-row refutation: a "transfers unchanged" row is
refuted if its mechanism requires core-module modification; the H3 scoring-interface row is
*confirmed* by an adapter-level replacement and would be *refuted* only if exact-match scoring
worked through the existing judge plumbing unchanged. Honest framing carried into FINDINGS
(round-1 Gemini fix): replacing the judge, solvability filter, and pre-gate strips DER's
free-text-specific machinery — the result is evidence about which layer of DER is general
(the discipline) and which is task-bound (the scoring stack), not a claim that "DER
generalizes."

## 12. Success criteria

Successful when: (a) canonical results exist for the approved panel (Arms A/B, plus C on
primaries) and all baselines/controls on the same frozen eval set with IHF-valid telemetry;
(b) H1 and H2 get supported/refuted/unevaluable verdicts under FROZEN-SPEC §5, and H2b gets
its defined output — estimate reported, cap triggered or not (no hypothesis verdict exists
for H2b — round-4 fix); (c) the §11 table is scored under the §11.1 contract with the
pinned-commit and fixture evidence; (d) exclusions, audits, and ablations are documented.
Every LLM losing to the champion is a fully successful outcome.

## 13. Gates and run plan (in firing order, each waits for Sid)

1. **License Gate (§0)** — DEFERRED by override; must be ruled before publication.
2. **Data Gate (§1)** — canonical feature table spec + golden renders for the frozen
   edge-case set (normal, short-telemetry, censored-maintenance, simultaneous-errors,
   truncation, recent-prior-failure, plus Arm B and Arm C renders — FROZEN-SPEC §11), the Arm
   B context block verbatim with its hash, audit outputs over all 677 windows (censoring,
   label-by-hour, absolute-timestamp scan), split counts, exclusion cross-tabs. Wait.
3. **Prompt Gate (§2)** — system + user prompts verbatim for every arm; mechanics-only labels;
   shuffled answer-order policy shown. Wait.
4. **Cost Gate (§6)** — frontier arithmetic covering EVERY metered call, including the
   ~25-call Azure preflight, presented and approved BEFORE the first metered call of any kind
   (round-6 fix: no metered preflight before cost approval). Local preflights need no cost
   approval.
5. **IHF Preflight (§3)** — ~20 calls per subject at exact settings **plus the longest/densest
   eligible renders**; rolling gate over first 10%. Azure preflight fires only after gate 4.
6. Runs: dry → 1-event smoke → baselines/controls → local ladder (serial, tmux+nohup,
   checkpointed, filtered monitor) → frontier arms. Every step announced first.

## 14. Not claimed / known limitations

- Microsoft-simulated data; no claim about real plant performance.
- Conditional classification, not root-cause analysis, not detection; no deployment claims.
- Same-fleet estimand; nothing about unseen machines.
- At best DER moves from one worked task to two; "general" is not claimable.
- Window lengths (72h/7d/90d) are design choices; sensitivity out of scope for v1.
- Arm C is a single-permutation label-renaming invariance probe: a B−C gap is consistent with
  label-convention memorization but confounded with arbitrary-symbol grounding cost, and even
  a clean Arm C cannot rule out deeper structural memorization of the simulator's dynamics.
  Stated as residual risks wherever contamination is discussed.
- The cap-rule threshold of 10 accuracy points is pre-declared but arbitrary; the probe can
  only ever catch large invariance failures (power-sim MDE reported at analysis) — H2b bounds
  gross contamination, nothing finer.
