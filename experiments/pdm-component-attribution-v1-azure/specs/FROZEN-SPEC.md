# FROZEN-SPEC — pdm-component-attribution-v1-azure (v5, 2026-07-18)

Frozen companion to DESIGN r6; where DESIGN and this file disagree, this file wins — and
within this file, a block marked "sole normative rule" overrides any summary table cell
(round-5 fix). Everything here is fixed BEFORE any experiment code and before any model call;
later changes are reported protocol deviations. Seeds are arbitrary. Draw status: the Arm C
probe, label permutations, and repeat subset are **materialized** in §3; the answer-order
permutations and prior-random predictions are **fully specified and reproducible** (seed +
sorted population + stated RNG) and are materialized into the run config at the Data Gate,
before any call. v5 supersedes v4 per the round-6 findings (ledger `reviews/COVERAGE-r6.md`).

**Frozen-set rule (round-5 fix — no exclusion path exists):** the confirmatory eval set is
the 213 events, invariant. Data Gate audits run BEFORE any model call; ANY audit failure
STOPS the process — an implementation defect is fixed and the full gate rerun; an irreparable
data-intrinsic problem forces a documented design amendment with regenerated frozen
statistics (a new protocol version), never an ordinary exclusion from the declared 213. After
calls begin, no event is ever dropped: post-freeze anomalies quarantine the affected arm,
they never shrink the set. **Post-freeze anomaly rule (round-6 fix, uniform):** ANY
post-call anomaly that would have failed a pre-call audit (leak discovered in a render,
identity drift, duplicate detection, scoring defect) makes the affected subject-arm's
confirmatory claims UNEVALUABLE for this run — same terminal rule as retry-exhaustion (§9);
a rerun is a new protocol-versioned run. No discretionary release exists anywhere in this
spec.

## 1. Task-unit statistics (event unit)

Unit = unique (machine, T). 719 events; 42 multi-component excluded; **677 single-component
events over 98 machines**. Boundary: T < 2015-09-01 00:00 → train; else eval.

| Partition | events | machines | comp1 | comp2 | comp3 | comp4 | majority |
|---|---|---|---|---|---|---|---|
| Full | 677 | 98 | 172 | 232 | 118 | 155 | 34.27% (comp2) |
| Train | 464 | 98 | 127 | 149 | 82 | 106 | 32.11% (comp2) |
| Eval | 213 | 91 | 45 | 83 | 36 | 49 | 38.97% (comp2) |

Train prior vector p_train = (.2737, .3211, .1767, .2284) (comp1..4 order).
**Prior-random expected accuracy vs the fixed eval labels = Σ_c p_train,c · p_eval,c =
0.2654** (round-3 fix; the earlier Σp² = 0.2614 was the wrong quantity and is withdrawn).
Multi-component exclusion cross-tabs (both event-count and component-row denominators)
reported in FINDINGS. Window flags: 19 short-telemetry events; 3 recent-prior-failure events —
**flags are audit metadata only: excluded from the classifier predictors and from the render**
(round-3 fix: `flag_recent_failure` derives from the failure log and must never be a
predictor).

## 2. Seeds and RNG (round-3 fix: one generator, one draw, one seed)

Every draw uses a **fresh `numpy.random.default_rng(seed)`**, operates on a population sorted
by (machineID, T) (or the fixed label lists in their natural order), and its output is
materialized in this file or in the run config before calls. `random.Random` is not used.

| Draw | Seed | Status |
|---|---|---|
| Arm C machine sample | 20260718 | materialized §3 |
| Arm C label permutation | 20260719 | materialized §3 |
| Cluster bootstrap | 20260720 | protocol §6 |
| Prior-weighted random baseline | 20260721 | 213 predictions materialized + hashed at Data Gate |
| Label-shuffle permutation null (200 fits) | 20260722 + i, i=0..199 | protocol §8 |
| Repeat-call diagnostic subset | 20260727 | materialized §3 |
| Answer-option order | 20260728 | protocol below |

Answer-option order (AMENDED at prompt-gate r2 and r3, before any call — reviewers flagged
the shared-position rule, then partial per-position coincidence, as Arm C positional
channels): Arm A/B — rng(20260728), one rank permutation of {0,1,2,3} per event (events
sorted machineID, T), applied to sorted comp1..comp4. Arm C — an INDEPENDENT stream
rng(20260731), rejection-sampled per event until the option list is an **elementwise
derangement** of the mapped A/B order (no position holds the same underlying component in
both arms), applied to sorted unitA..unitD. Automated test over all 213 events: 0
per-position correspondences. Position effects are mean-zero across events within each arm;
pair-cancellation was traded away for channel elimination.

## 3. Materialized draws (2026-07-18)

- **Arm C probe (whole-machine draw, seed 20260718): 22 machines, 51 events, max cluster 5.**
  Machines: 4, 11, 22, 23, 30, 39, 40, 42, 47, 56, 58, 61, 63, 64, 68, 73, 74, 75, 80, 81,
  88, 98. Class counts: comp2 23, comp3 12, comp1 8, comp4 8. H2b is scoped to this
  sampled-machine population.
- **Label permutation (seed 20260719):** comp1→unitD, comp2→unitB, comp3→unitC, comp4→unitA;
  error1→codeB, error2→codeE, error3→codeC, error4→codeD, error5→codeA. One permutation only
  (stated limitation).
- **Repeat-call diagnostic subset (seed 20260727): 30 eval events, 25 machines**, class
  counts comp4 9 / comp2 9 / comp3 8 / comp1 4. Materialized (machine@timestamp):
  1@2015-09-02, 17@2015-11-27, 21@2015-12-04, 24@2015-11-13, 25@2015-10-31, 30@2015-12-05,
  37@2015-09-16, 37@2015-10-01, 37@2015-11-15, 43@2015-11-17, 45@2015-10-19, 49@2015-11-11,
  50@2015-09-12, 57@2015-11-04, 63@2015-11-09, 64@2015-09-17, 71@2015-09-23, 74@2015-10-20,
  78@2015-09-03, 78@2015-11-02, 84@2015-10-02, 87@2015-12-23, 88@2015-12-30, 90@2015-10-02,
  90@2015-11-01, 94@2015-10-20, 95@2015-09-17, 95@2015-10-17, 97@2015-09-06, 99@2015-11-29
  (all 06:00).
- **Audit policy:** governed by the frozen-set rule in the header — pre-call failures stop
  and rerun the gate; post-call anomalies quarantine, never drop.
- Arm C interpretation (unchanged from v1): label-renaming invariance probe; "consistent
  with", never a direct memorization measurement.

## 4. Canonical feature dictionary and projections

All aggregation windows right-open, ending at T. Blocks: d3 = [T−72h, T−48h), d2 = [T−48h,
T−24h), f24 = [T−24h, T). **Rounding is applied to the dictionary values themselves**
(telemetry 1 decimal, hours/days integers) and both projections consume the rounded values —
no precision asymmetry (round-3 fix). Telemetry std = sample std (ddof=1; 0.0 if <2 rows).
Error events sorted (hours-before-T asc, then code asc) BEFORE the 20-row cap; dropped-row
count recorded. sklearn/pandas/numpy versions recorded at Step-0.

| Field | Type | Definition | Predictor? | Rendered? |
|---|---|---|---|---|
| model | cat | PdM_machines | yes (one-hot) | yes |
| age | int | PdM_machines | yes | yes |
| tele_{ch}_{blk}_{mean,std,min,max} | float | ch ∈ 4 channels; blk ∈ {d3,d2,f24} | yes | yes |
| tele_{ch}_delta1 | float | f24 mean − d2 mean | yes | yes |
| tele_{ch}_delta2 | float | d2 mean − d3 mean | yes | yes |
| tele_missing_{blk} | bool | block has no telemetry rows | yes (indicator) | yes ("no data") |
| err_count_{e} | int | occurrences of e in [T−168h, T) | yes | yes |
| err_recent_code | cat | most recent code, 'none' | yes (one-hot) | yes |
| err_recent_hours | float | hours to T; 168 if none | yes | yes |
| err_events | list ≤20 | (code, hours) recent-first | no (represented above) | yes (table) |
| maint_days_{c} | float | days since last replacement; **NaN if censored** | yes | yes / "no prior record" |
| maint_censored_{c} | bool | no replacement record before T | yes | yes (implied by "no prior record") |
| maint_count90_{c} | int | replacements in [T−90d, T) | yes | yes |
| flag_short_tele | bool | lookback < 72h | **no — metadata** | no (visible as "no data") |
| flag_recent_failure | bool | failure-log derived | **no — metadata** | no |

The predictor set is EXACTLY the rows marked "yes" — no "every numeric field" clause
(round-3 fix). **The canonical dictionary retains NaN** for missing telemetry and censored
maintenance (round-4 fix — imputation is a model-pipeline step, §7, never a dictionary
step, so no tune leakage and no cross-candidate contradiction). Censored maintenance renders
as "no prior record" with **no day count** (round-3 fix). Rounding = numpy round-half-even to
the stated decimals, applied to non-NaN dictionary values, consumed by both projections.

**Attempt-2 granularity schema (complete — round-4 fix):** if the ladder's attempt 1 fails,
the telemetry fields are replaced by tele_{ch}_h6{k}_{mean,std} for k = 1..8 (successive 6h
blocks over [T−48h, T), k=8 latest; min/max dropped), deltas replaced by tele_{ch}_delta1 =
h68 mean − h64 mean and delta2 = h64 mean − h61 mean, missing indicators per 6h block; render
table columns become the 8 blocks; classifier matrix analogous; every other field, rule, and
rounding unchanged.

**Render projection:** fixed-schema markdown tables (machine block; telemetry table with the
three blocks + deltas; error table from err_events + per-code counts; maintenance table).
Relative time only; no absolute dates, no machineID, no time-of-day.

**Arm B context block (frozen formulas — round-3 fix):** computed once from the 464 train
events, SHA-256 recorded at the Data Gate. (a) Error→component table: cell (e, c) = number of
train events with label c whose [T−168h, T) window contains ≥1 occurrence of e (event-level
co-occurrence; denominators = train class counts, shown). (b) Class counts: the §1 train row.
(c) Wear statistic per component: mean days from previous replacement to failure over
**uncensored intervals only** (a prior replacement record exists); "N/A" if a component has
no uncensored train interval (round-3 fix: censored spans would import the arbitrary dataset
start date). Counts integer; means integer days.

**Granularity acceptance (finite ladder — round-3 fix):** attempt 1 = the block scheme above;
attempt 2 (only if the gate fails) = 6-hourly mean/std blocks over [T−48h, T) (8 blocks,
same stats). Gate: champion candidates must beat the no-evidence control by ≥5 macro-F1
points on the tune split. Max 2 attempts, both scored on the same tune split, choice logged;
if both fail, STOP and escalate to Sid as a design amendment. No other adaptation path.

## 5. Comparison registry (confirmatory; all else exploratory)

Primary subjects S = {gpt-5.4, gpt-oss:120b}, frozen; unavailable/Cost-Gate-failed primary →
its hypotheses are NOT RUN.

| ID | Family | Comparison | Metric | Decision rule |
|---|---|---|---|---|
| R1–R3 | H1 | gpt-5.4 Arm A vs B2, B3, B4 | macro-F1 | raw one-sided p's feed the subject IUT below |
| R4–R6 | H1 | gpt-oss:120b Arm A vs B2, B3, B4 | macro-F1 | raw one-sided p's feed the subject IUT below |
| R7–R8 | H2 | champion vs each primary's Arm B | macro-F1 | both raw p < 0.05 (IUT, no Holm) |
| R9–R10 | H2b | Arm B vs Arm C per primary, probe set | accuracy gap | **descriptive + cap rule** |

**Frozen algorithm, R1–R8 — the SOLE normative rule (round-5 fix; the table cells above are
pointers to this block, never an independent procedure):** metric = macro-F1 over the fixed
4-class set (absent class → F1 = 0; no metric switching). Paired difference per bootstrap
replicate (§6); one-sided raw p = (1 + #{replicates with diff ≤ 0}) / (B + 1).
- **H1** ("at least one subject beats all three"): per subject, intersection p_S =
  max(p of its three rows); Holm over {p_S(gpt-5.4), p_S(gpt-oss:120b)} at α = 0.05. H1
  supported iff any adjusted p_S < 0.05; that subject's H1 verdict is supported.
- **H2** ("champion beats both primaries", pure intersection): supported iff BOTH raw
  p_R7 < 0.05 and p_R8 < 0.05 — no Holm (IUT needs none).
- **Missing-primary handling (round-5 fix — asymmetric by design):** H2 is UNEVALUABLE
  unless both its rows exist. H1 with one primary missing: if the remaining subject's p_S <
  0.05 (singleton Holm), H1 is **supported** (an existential claim needs one witness); if it
  fails, H1 is **unevaluable** — never refuted, because the missing subject is unknown.
  Missing rows are never imputed or substituted.

**H2b (round-3 change, evidence-driven):** a cluster-aware power simulation on the
materialized probe (Gaussian-copula paired outcomes, ρ = 0.6, a_B = 0.5; banked in
`specs/power-sim-notes.md`) gives TOST-at-δ=0.10 power ≈ **0.01 even at true gap 0** — the
51-event probe cannot support an equivalence verdict, and enlarging it would exceed Sid's
ruled probe scope. R9–R10 are therefore **descriptive**: report the paired accuracy gap with
its 90% cluster-bootstrap CI and the simulation-based MDE; no "equivalent" verdict is
available at this design. Pre-declared **cap rule** (superiority-style, feasible at n=51):
if gap > 0.10 AND the 90% CI excludes 0, capability claims for that subject are capped at
Arm C performance. "No contamination detected" may never be claimed from a non-significant
gap. **Cap semantics (round-4 fix):** H2b receives no supported/refuted verdict — its output
is "estimate reported; cap triggered / not triggered" per subject. If triggered for subject
s: s's Arm A and Arm B results are reported with s's Arm C probe accuracy quoted first and
every claim tagged "label-convention-dependent"; any H1/H2 verdict involving s carries the
same tag; untagged capability language about s is prohibited.

Wording rule: Arm B = train-summary context; the champion learns the joint distribution,
Arm B gets marginals; H2 is never "same-information".

## 6. Cluster bootstrap protocol

Resample machines with replacement (91 for eval arms; the 22 probe machines for R9–R10),
keeping all their events; B = 10,000; per-row child generators per the stream-allocation
rule below (round-6 fix — no sequential consumption, no stream shift on missing rows);
percentile CIs (95% two-sided for
reporting; 90% for the H2b cap rule); paired differences within replicate; macro-F1 per §5's
fixed-class convention. **MDE procedure (round-6 fix, deterministic):** for R9–R10 (paired
accuracy) the copula model of specs/power-sim-notes.md at the observed marginal accuracy and
discordance. For R1–R8 (macro-F1), algorithm, exactly: (1) real event truths stay fixed —
nothing samples truth. (2) From the actual run, tabulate per true class c the conditional
joint table J[c](s, k) = frequency of (subject-prediction s, comparator-prediction k) among
events with truth c, both pooled (J_pool) and per machine (J_m). "Subject" = the LLM primary
of the row; "comparator" = the baseline (R1–R6) or the champion (R7–R8); directions per §5.
(3) Per simulation (generator: default_rng(20260729 + sim_index)): for each event with truth
c on machine m, draw the prediction pair from the mixture table 0.5·J_pool[c] +
0.5·J_m[c] (J_m computed from m's own events; if m has <3 events of class c, use J_pool[c]
alone). (4) Effect injection at level π: after drawing, replace the subject prediction with
the true class with probability π (one Bernoulli per event, same generator); π runs over
{0, 0.02, …, 0.40}; report the achieved macro-F1 delta per π. (5) 1,000 simulations per π;
apply the §5 family decisions jointly (H1's max-p + Holm over all six rows; H2 over both
rows). MDE = smallest achieved macro-F1 delta detected in ≥80% of simulations; Monte-Carlo
standard error reported. Reported per registry family before interpretation.

**Bootstrap stream allocation (round-6 fix):** each registry row uses its own child
generator, default_rng(20260720 + row_number) (R1→20260721 … R10→20260730 — the overlap with
other seed constants is inert; generators are per-purpose). Missing rows consume nothing;
no stream shifts when a primary is absent.

## 7. Classical champion selection (train-only, frozen)

Fit < 2015-07-01, tune Jul–Aug. The canonical dictionary keeps NaN (§4); **imputation lives
inside each candidate pipeline and is fit on the fit partition only during selection, then
refit on all 464 train events for the frozen champion** (round-4 fix — no tune leakage, no
§4/§7 contradiction). Candidates: (a) multinomial logistic regression — pipeline:
median imputer (numeric) → StandardScaler + OneHotEncoder(handle_unknown='ignore') (cat),
class_weight='balanced', C ∈ {0.01, 0.1, 1, 10}, lbfgs, max_iter 2000; (b)
HistGradientBoostingClassifier — native NaN handling (no imputer), one-hot for cats,
learning_rate ∈ {0.05, 0.1}, max_depth ∈ {2, 3}, max_iter ∈ {100, 300}, balanced sample
weights. Library versions recorded at Step-0. Selection: highest tune macro-F1; exact tie →
logistic regression. Champion refit on all 464 train events; frozen. Both candidates' eval
numbers reported; champion only is confirmatory.

**B4 — single executable definition (round-5 fix; this paragraph is the only normative B4
rule):** M[e, c] = count of train events with err_recent_code = e AND label = c (a 6×4 table:
5 codes + 'none'). For an eval event with err_recent_code = e: if e = 'none' → predict comp2
(B2 fallback); else predict argmax_c M[e, c]; ties → higher train failure count → fixed order
comp1<comp2<comp3<comp4. The §4 any-occurrence co-occurrence table serves Arm B's context
block ONLY and is never used by B4.

**B3 (oldest component) — round-5 fix (censored = oldest, matching the heuristic's physical
meaning):** a censored component (no replacement record before T) is treated as OLDER than
every component with a known age. One censored → predict it. Multiple censored → they tie
among themselves → higher train failure count → fixed order comp1<comp2<comp3<comp4. No
censored components → argmax of maint_days; ties → same tiebreak chain.

## 8. Label-shuffle plumbing gate (round-3 fix: permutation-calibrated, not analytic)

Ordering (round-5 fix — representation frozen first): the §4 granularity ladder runs to
completion FIRST (attempt 1 → gate → at most attempt 2 → representation frozen). The
permutation gate then runs on the frozen representation. 200 iterations (seeds 20260722+i);
each: permute the fit-split labels **across rows (y-scrambling — destroys the feature-target
relationship; NOT the Arm C bijective renaming)**, rerun the complete §7 candidate selection
(both candidates, full grids, tune-split selection) on the scrambled data, record the
selected pipeline's tune macro-F1. PASS iff the real selection's tune macro-F1 strictly
exceeds ALL 200 null values (permutation p = 1/201 < 0.01). Fail → fail closed, investigate
before eval. **Scope disclosure:** this gate calibrates candidate-selection optimism only;
the label-dependent ladder choice is NOT inside the null — that optimism is bounded by the
2-attempt limit and disclosed wherever the gate is reported. The v1 analytic band is
withdrawn.

## 9. Subjects, decoding, transport

| Subject | Surface | Decoding | Max tokens |
|---|---|---|---|
| gpt-5.4 (primary) | Azure, metered | reasoning surface — no temperature sent | max_completion_tokens 4096 |
| gpt-oss:120b (primary) | Ollama kratos | temp 1.0, top_p 1.0 (provider defaults) | 8192, ctx 8192 |
| qwen3.5-122b | native /api/chat, think=true | per experiments/CLAUDE.md | 16384, ctx 32768 |
| nemotron-3-super | Ollama, THINK_MODE=false | provider defaults | 4096 |
| qwen3:4b | Ollama | provider defaults | 4096 |

Decoding values transmitted (frozen; "provider defaults" resolved to concrete numbers —
round-4 fix): gpt-oss:120b temp 1.0 / top_p 1.0; qwen3.5-122b temp 0.6 / top_p 0.95, think
true, num_ctx 32768, num_predict 16384 (values copied here, no external doc dependency);
nemotron-3-super temp 0.7 / top_p 0.95, THINK_MODE=false; qwen3:4b temp 0.6 / top_p 0.95;
gpt-5.4 no sampling params (reasoning surface). Every transmitted parameter and relevant
server setting is materialized in the run config, hashed at preflight Step-0; drift aborts.

Identity pinning: Ollama model digests and the Azure deployment name + api-version are
recorded at IHF preflight Step-0 and frozen; any mid-run resolution change aborts the batch
(runner rule). Transport: exponential backoff, 10 retries, cap 60s, retry only on transport
errors (timeouts, 5xx, 429) — never on parseable-but-wrong content. "First call" = first
transport-successful response; it is canonical. **Retry-exhausted events score invalid =
incorrect on the fixed event set — never dropped** (round-4 fix: exclusions would give each
subject its own eval sample); if exhausted events exceed 2% for any subject-arm, that
subject-arm's confirmatory claims are automatically **UNEVALUABLE for this run** — no
discretionary release; a rerun is a new protocol-versioned run requiring fresh preflight
(round-5 fix). Unparseable output per the §13 frozen
parse policy scores incorrect — never repaired, never resampled. Repeat-call diagnostics (3
extra calls, §3 subset, primaries only) never enter confirmatory inference.

## 10. Adapter contract (H3), pinned, bypass-proof

Pinned: commit **9a44c726fc66a872a376b24add1000420f8d0930**,
`experiments/tpm-cross-pillar-v1-grounded/pipeline-v2/`.

| DER component (DESIGN §11 row) | Entry point(s) | Refuted by |
|---|---|---|
| Blind render + truth-strip assertion | `runner.py` envelope assertion path | editing that path, or scanning scope defined by the artifact under test |
| Subject fan-out | `local_solve.py` / `blind_solve.py` shells | editing the invocation loop (adapter config excepted) |
| Baseline layer | `baselines_extra.py` harness | editing the harness (new baseline *functions* are adapters) |
| Exclusions table | `aggregate.py` exclusion reporting | editing it |
| Judge (predicted NOT to transfer) | `judge_score.py`, `score_compare.py`, `compare_strict.py` | confirmed by adapter-level replacement; refuted only if exact-match runs through the judge plumbing unchanged |
| Solvability filter / pre-gate (predicted N/A) | `generate_scenario.py`, `pregate.py` | n/a on real ground truth |

Allowed adapter hooks: event renderer, exact-match scorer, subject API adapter, event schema.
**Bypass rules (round-3 fix):** each core file must be imported AND executed in the real run
(runtime log evidence required); a new module or wrapper that reimplements a core file's
responsibility scores that row as **core rewrite**, exactly as if the file were edited; a
core file left unchanged but unused scores its row **did not transfer**; monkey-patching core
symbols = core rewrite. File hashes at the pinned commit recorded in the run config.
Reclassification after implementation = reported protocol deviation.
**Behavior fixtures (round-5 fix — one per core transfer row, execution must be real):** at
preflight, (i) truth-injection: a render with the failure row deliberately inserted must be
REJECTED by the pinned envelope-assertion path; (ii) exclusion-flow: a synthetic excluded
event must appear, with reason, in the pinned aggregation output; (iii) fan-out: one smoke
event must traverse BOTH pinned invocation shells (`local_solve.py` to a local subject,
`blind_solve.py` to the frontier surface); (iv) baseline harness: a known-input event with a
hand-computed expected prediction for each of B1–B4 must produce exactly those predictions
through the pinned `baselines_extra.py` harness. All recorded in the preflight report; a core
row may claim "transfers unchanged" only with its fixture passing through the pinned code.

## 11. Data Gate rendering evidence (round-3 fix: edge cases, not one sample)

Golden renders frozen at the Data Gate for: (a) a normal event; (b) a short-telemetry event
(of the 19); (c) a censored-maintenance event; (d) an event with simultaneous same-hour
errors; (e) an error-cap truncation event if any window exceeds 20 error rows (else recorded
as none); (f) a recent-prior-failure event (of the 3); plus one Arm B and one Arm C render.
Full-table invariant counts (audit pass/fail totals over all 677 windows) reported alongside.

## 12. Cost arithmetic inputs (for the Cost Gate)

gpt-5.4 calls = 213 (Arm A) + 213 (Arm B) + 51 (Arm C) + 3×30 (repeat diagnostics) + ~25
(preflight) ≈ **592**; per-call prompt ≈ render + context block (measured at Data Gate),
completion ≤ 4096. Exact token arithmetic × current rates presented at the Cost Gate
**before the FIRST metered call of any kind — the ~25-call Azure preflight included**
(round-6 fix); nothing metered fires pre-approval. Local subjects: same call counts,
unmetered, no cost approval needed.


## 13. Frozen parse policy (round-4 fix)

Subject output contract: a JSON object containing key `"component"` whose value must
exact-match one of the four presented answer labels (after trimming whitespace and
casefolding); optional `"rationale"` string; extra fields ignored. Every prompt instructs:
respond with ONLY a raw JSON object, no other text (round-5 fix).

Parser (single pass, no retries — round-5 fix, string-aware): (1) remove all markdown fence
marker lines (lines whose stripped content starts with ```); (2) scan left-to-right with a
brace-depth counter that IGNORES braces inside JSON string literals (tracking `"` delimiters
and `\` escapes) and collect every balanced top-level `{…}` block; (3) take the FIRST block
whose parsed content (`json.loads`; duplicate keys → last value, the Python default)
contains the key `"component"` — blocks appearing in reasoning preamble without that key are
skipped (round-5 fix for chain-of-thought braces); (4) validate the value against the
presented label set. No candidate block, unparseable candidates, or a value outside the
presented set → **incorrect** (`parse_status=fallback`). No other repair. Parser module
hashed at preflight. Golden cases frozen with it: ACCEPT — plain JSON; fenced JSON; JSON
after a prose/CoT preamble containing `{mean: 10.5}`-style braces; JSON whose rationale
string contains `{`, `}`, and `\"` escapes; label with trailing space or different case;
multiple fenced blocks where only the second contains `"component"`. REJECT (scored
incorrect) — prose answer with no `"component"`-bearing JSON block; label not in the
presented set (e.g. unpermuted `comp2` in Arm C); `"component"` present but non-string or
array-valued; empty output.

## Amendment A1 — nemotron-3-super promoted to primary (2026-07-19, post-hoc)

Sid directed that `nemotron-3-super:120b` be treated as primary/confirmatory data alongside
gpt-5.4 and gpt-oss:120b. **This is a post-hoc change made after its Arm A/B results were
visible** — it relaxes the multiplicity control the round-2 triage froze (primaries fixed
before results). Recorded honestly rather than presented as pre-specified.

Impact on verdicts: none directional. nemotron zero-shot Arm A ≈ 0.36 macro-F1 (at floor, fails
H1 like the others); champion still beats nemotron Arm B. The third subject reinforces H1
(not-supported) and H2 (supported), and adds an H2b probe point. H1 Holm family widens to 3
subjects; H2 IUT now requires the champion to beat all three Arm B's. nemotron gets Arm C probe
+ repeats so its primary treatment matches the other two. Any reader may discount it to
exploratory without changing a conclusion.
