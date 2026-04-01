# Publication Readiness Plan — Agentic Bullwhip Experiment

## 1) Objective
Convert the current exploratory study into a submission-ready paper with defensible causal claims, statistical rigor, and reproducibility.

## 2) Current Status (as of 2026-03-03)
- Parser fix is in code (`50_806` style numeric normalization).
- Historical raw artifacts still contain one contaminated run.
- `n=5` per condition is underpowered for high-variance reasoning-model behavior.
- Model-tier comparison is partially confounded by different operating regimes.

## 3) Go / No-Go Criteria
The paper is submission-ready only if all are true:
1. `parse_error_count_total == 0` for every tier and condition.
2. Hypotheses, primary endpoints, and analysis plan are pre-registered on OSF before any new runs.
3. Primary conclusions hold across robustness scenarios (not just one demand trace).
4. Key contrasts satisfy both:
   - statistical threshold: 95% CI excludes zero
   - practical threshold: pre-specified minimum practically relevant difference (MPRD)
5. Chain-level practical threshold for main claims: `|delta OVAR| >= 0.5`.
6. At least one LLM configuration shows statistically significant and practically meaningful OVAR difference versus every baseline policy.
7. Results are reproducible by an independent rerun from a clean environment.
8. Primary confirmatory contrasts are fixed before reruns (see §5.4); no post-hoc additions to the primary family.

## 4) Experimental Matrix (Required)
## 4.1 Core 2x2 Conditions
- `blind_lightweight`
- `context_lightweight`
- `blind_reasoning`
- `context_reasoning`

## 4.2 Baseline Policies (add)
- `baseline_naive_passthrough` (order equals received demand; lower-bound reference)
- `baseline_order_up_to`
- `baseline_exp_smoothing`

Baseline parameter lock (for preregistration):
- `baseline_order_up_to`:
  - policy form: `order_t = max(0, S - inventory_position_t)`
  - fixed target stock `S = 43,000` units (matches initial inventory level)
  - deterministic, no adaptive re-tuning during runs
- `baseline_exp_smoothing`:
  - demand forecast: `F_t = alpha * D_{t-1} + (1 - alpha) * F_{t-1}`
  - fixed `alpha = 0.30`
  - initialization: `F_1 = D_1`
  - order rule: order forecast plus backlog coverage, bounded below at 0

## 4.3 Robustness Axes
- Demand regimes:
  - seasonal (current profile)
  - seasonal + random noise
  - trend-up
  - trend-down
  - intermittent demand
  - shock scenario (step change)
- Lead times: deterministic `1`, `2`, `3` periods (no stochastic lead times in first-paper scope).

## 4.4 Replication Counts
- LLM conditions: minimum `n=20` runs per cell.
- Baselines: deterministic or `n=5` if stochastic implementation.
- Full planned matrix cost/time check (LLM only):
  - cells: `4 conditions x 6 demand regimes x 3 lead times = 72`
  - runs: `72 x 20 = 1,440`
  - calls: `1,440 x 36 calls/run = 51,840 API calls`
  - rough o1-only cost using current observed per-run rates: high three-figure to low four-figure USD range depending on token usage profile
  - rough runtime floor from inter-call delays alone is multi-day, excluding rate-limit backoff
- Scope option for initial submission if constrained:
  - Core 2x2 with `n=20`, deterministic lead time `1`, and one baseline (`order_up_to`)
  - treat full robustness matrix as revision/extension package

## 5) Statistical Analysis Plan
1. Pre-register on OSF before reruns. Archive preregistration ID in repo docs.
2. Primary endpoint: per-tier OVAR and chain-average OVAR.
3. Report:
   - mean, std, 95% CI
   - effect sizes:
     - absolute difference in mean OVAR
     - OVAR ratio (multiplicative framing)
   - adjusted p-values for multiple comparisons (Holm for primary family; BH for exploratory family)
4. Define testing families:
   - primary family: fixed chain-average contrasts under seasonal regime, lead time `1`:
     - C1: `blind_lightweight` vs `context_lightweight` (context effect at lightweight tier)
     - C2: `blind_reasoning` vs `context_reasoning` (context effect at reasoning tier)
     - C3: `blind_lightweight` vs `blind_reasoning` (model effect under blind treatment)
     - C4: `context_lightweight` vs `context_reasoning` (model effect under context treatment)
     - C5: interaction contrast (difference-in-differences): `(C2 - C1)`
   - secondary family: tier-level and robustness-sweep contrasts (explicitly exploratory)
5. For high-CV conditions, add:
   - median, IQR
   - 10th/50th/90th percentiles
6. Sensitivity checks:
   - with/without outliers
   - with/without any run containing non-zero parse errors

## 6) Data Quality Gates
Hard fail any run if:
- JSON parse fails after retry budget.
- Required fields are missing.
- Non-finite metrics are produced.

Track and report:
- parse error counts
- retry counts
- dropped/invalid run counts

## 7) Implementation Worklist
1. Add model connection + format smoke test for each target model (`json_schema` / strict JSON path), including o1.
2. Enforce strict structured output mode in LLM calls.
3. Add bounded retry on parse failure (max 2 retries) with corrective retry prompt text:
   - "Previous response was invalid JSON. Return only one valid JSON object with integer order_quantity and string reasoning."
4. Add run-level quality gate that marks run invalid rather than coercing to zero.
5. Add replacement-run policy: automatically rerun until target valid `n` is reached; log invalid attempts separately.
6. Add baseline policy module (`naive_passthrough`, `order_up_to`, `exp_smoothing`) and integrate into orchestrator.
7. Add scenario generator for demand regime and deterministic lead-time sweeps.
8. Resolve model-tier confound (locked decision):
   - primary path: include token-budget-controlled ablation cells to estimate budget effects directly
   - fallback path (only if ablations are infeasible due to cost/runtime): explicitly reframe manuscript as deployment-configuration comparison in title/abstract, and demote pure capability claims
9. Add statistical reporting script that produces paper tables directly from raw data.

## 8) Deliverables for Submission
- `results/raw/` (all run logs)
- `results/aggregated/` (clean summaries)
- `results/tables/`:
  - primary effects table
  - robustness table
  - baseline comparison table
  - instability/risk table (percentiles)
- `results/figures/`:
  - OVAR by tier and condition
  - robustness heatmaps
  - distribution plots (box/violin) for high-variance conditions
- reproducibility bundle:
  - pinned dependency lockfile (`requirements.txt` with exact versions or equivalent lock format)
  - containerized environment (`Dockerfile` or `conda.yaml`)
  - one-command rerun script (`scripts/reproduce_all.sh` or equivalent)
- `docs/`:
  - OSF pre-registration record and exported snapshot
  - methods appendix
  - threat-to-validity section
  - reproducibility instructions
  - synthetic demand data provenance note (generation method, parameters, seed)
  - synthetic demand generation script used for paper runs

## 9) Suggested Timeline
Preferred (full matrix): 6 weeks
1. Week 1: quality-gated rerun pipeline, format tests, replacement-run policy.
2. Week 2: baseline module + confound-resolution ablation setup.
3. Week 3: demand/lead-time scenario generation and dry-run validation.
4. Week 4-5: full execution with monitoring and reruns for invalid attempts.
5. Week 6: statistical analysis, figures/tables, draft manuscript.

Scoped (fast-track): 4 weeks
1. Week 1: quality gates + rerun pipeline.
2. Week 2: core 2x2 + one baseline (`order_up_to`) at lead time `1`.
3. Week 3: execution (`n=20`) + analysis.
4. Week 4: draft manuscript with clear "limited robustness" framing.

## 10) Claim Discipline (for manuscript)
Use graded language:
- If CI excludes zero across robustness sweeps: "supported evidence".
- If directional but unstable/high-CV: "suggestive evidence".
- If result depends on single regime/scenario: "context-specific finding".
- If claim direction reverses in any robustness scenario: remove directional language from abstract and frame as context-dependent in main text.

## 11) Execution Tracker
Use this as the operational checklist. Update `Status`, `Owner`, and `Evidence` as work completes.

Status legend:
- `TODO`
- `IN_PROGRESS`
- `DONE`
- `BLOCKED`

| ID | Work Item | Section Link | Status | Owner | Evidence / Artifact |
|---|---|---|---|---|---|
| T01 | Register OSF preregistration before new runs | §3, §5, §8 | TODO | Unassigned | OSF URL + timestamp + exported snapshot |
| T02 | Add strict JSON schema response mode for all target models | §6, §7 | TODO | Unassigned | PR/commit touching `src/base_agent.py` + test logs |
| T03 | Add model format smoke tests (including o1) | §7 | TODO | Unassigned | `tests/` output or `results/format_smoke_test.log` |
| T04 | Implement bounded retry with corrective prompt text | §6, §7 | TODO | Unassigned | Code diff + run logs with retry metadata |
| T05 | Implement invalid-run replacement policy to preserve valid `n` | §6, §7 | TODO | Unassigned | Orchestrator logs showing replacement runs |
| T06 | Regenerate clean raw and aggregated outputs with zero parse errors | §3, §6 | TODO | Unassigned | `results/raw/*`, `results/aggregated/*` with `parse_error_count_total == 0` |
| T07 | Add `baseline_naive_passthrough` policy | §4.2, §7 | TODO | Unassigned | Baseline module + sample output table |
| T08 | Add `baseline_order_up_to` policy | §4.2, §7 | TODO | Unassigned | Baseline module + sample output table |
| T09 | Add `baseline_exp_smoothing` policy | §4.2, §7 | TODO | Unassigned | Baseline module + sample output table |
| T10 | Add deterministic lead-time sweep support (1,2,3) | §4.3, §7 | TODO | Unassigned | Config + run manifest |
| T11 | Add demand-regime generator (6 regimes) | §4.3, §7, §8 | TODO | Unassigned | Generation script + provenance note |
| T12 | Decide confound strategy (ablation vs deployment framing) | §7 | TODO | Unassigned | Decision note in `docs/` |
| T13 | If ablation chosen: add token-budget-controlled ablation cells | §7 | TODO | Unassigned | Config updates + results table |
| T14 | Define and codify test families (primary vs exploratory) in analysis script | §5 | TODO | Unassigned | Statistical script + methods text |
| T15 | Add analysis outputs: CI, delta OVAR, OVAR ratio, adjusted p-values | §5 | TODO | Unassigned | `results/tables/primary_effects.csv` |
| T16 | Add high-CV distribution summaries (median/IQR/p10/p50/p90) | §5 | TODO | Unassigned | `results/tables/instability_metrics.csv` |
| T17 | Add outlier and parse-contamination sensitivity analyses | §5 | TODO | Unassigned | `results/tables/sensitivity_checks.csv` |
| T18 | Produce reproducibility bundle (locked deps + container + one-command rerun) | §8 | TODO | Unassigned | `requirements.txt` lock, `Dockerfile`/`conda.yaml`, `scripts/reproduce_all.sh` |
| T19 | Create methods appendix + threats to validity + reproducibility instructions | §8 | TODO | Unassigned | `docs/methods_appendix.md` etc. |
| T20 | Run Go/No-Go audit against criteria and sign-off | §3 | TODO | Unassigned | `docs/go_no_go_audit.md` |

### 11.1 Fast-Track Scope Tracker (4-week option)
If using the scoped path in §9, mark these as minimum required for submission draft:
- `T01`, `T02`, `T03`, `T04`, `T05`, `T06`, `T08`, `T12`, `T14`, `T15`, `T18`, `T20`

### 11.2 Full-Matrix Scope Tracker (6-week option)
For full claim strength, all tracker items (`T01`-`T20`) are required.
