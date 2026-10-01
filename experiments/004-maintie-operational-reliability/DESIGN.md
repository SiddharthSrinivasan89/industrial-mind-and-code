# IMC-EXP-004 — MaintIE: Operational Reliability of Consistency Across Repeated Runs

**Design status:** Draft; human expert ledger frozen; pre-production freeze/review pending  
**Inference status:** Not authorized and not started  
**Expert-ledger status:** Human-approved and frozen at SHA-256 `01ce3e5045c22e093d0da1d85b324ed0bb36687a8ed6a585ce7a4164e70e630a`

## Purpose and questions

EXP-004 is a prospective repeated-run replication of EXP-003 plus a blinded Industrial Engineering interpretation layer.

Primary question: Does the relationship between LLM consistency and classification correctness observed in EXP-003 remain stable across repeated model realizations?

Industrial Engineering question: Does the usefulness of consistency as a reliability signal depend on the operational characteristics of the maintenance record?

Expert-reasoning question: What missing context, ambiguity, failure mechanisms, operational effects, and assumptions characterize records where models fail or are consistently wrong?

The first pass reconstructs and reviews human annotations only. It does not analyze model outcomes.

## Authority and baseline

Repository facts follow root `AGENTS.md`. EXP-003 remains immutable. Exact baseline paths, hashes, production-manifest bindings, model identities, the minimum-evidence rule, and the accepted result review are recorded in `data/exp003-baseline-binding.json`.

The higher-authority EXP-003 tracker completion events and `reviews/CHECKER-STATUS.md` establish that production, deterministic analysis, and independent result review are complete at grade B / `CHECK_GO`. Several locked status surfaces disagree: EXP-003 `README.md`, `DESIGN.md`, the `RESULTS.md` status line, `run-config.json`, and one trailing tracker sentence retain pre-review or pre-production wording. EXP-004 records this discrepancy in its baseline binding and does not modify EXP-003.

The authoritative evaluation-input census is 108 records from source indices 968–1075. EXP-004 intends to reuse the exact evaluation inputs, gold, label space, hierarchy, and A/B/C prompt templates after the expert ledger is frozen and the prospective design passes review.

## Mandatory annotation blinding

The expert annotation ledger is reconstructed from `handoffs/004-maintie-operational-reliability/CHAT-TRANSCRIPT.md` before any outcome join. During reconstruction, no model responses, correctness values, consistency labels, repeated-question agreement, model-specific errors, or EXP-003 outcome analyses may be read or exposed.

The reconstruction uses exact string matching to `evaluation-inputs.jsonl`; it never uses conversational numbering as record identity and never uses fuzzy matching to force a record assignment. Identical surfaced text remains separate evidence and receives a transcript-text group; only an authoritative mapped record may receive the EXP-003 duplicate group.

The transcript itself records an assistant giving Sid aggregate EXP-003 results before the expert annotation session. No record-level answers or correctness were used during reconstruction, but the human layer is therefore not fully outcome-blind. It may be described only as record-level outcome-blind with documented prior aggregate exposure unless Sid adopts a scientifically appropriate alternative. This limitation must be resolved in the human freeze decision and preserved in any later claims.

## Expert annotation model

Each record has three layers:

1. Structured judgments: context sufficiency, operational consequence, and specificity required, each using low/medium/high where applicable (`context_sufficiency` instead uses sufficient/partial/insufficient).
2. Sid's raw rationale, preserved as transcript evidence.
3. Conservative normalized rationale, controlled qualitative themes, explicit assumptions, actionability, revisions, conditionality, and hazard/risk-noted flags.

`operational_consequence` is Sid's operational judgment. It is not formal FMEA severity, certified safety risk, measured plant consequence, or universal criticality. Null values are retained where Sid did not provide a controlled categorical judgment.

Sequences 1–7 used a legacy ambiguity schema. Sid confirmed sequences 1–3 directly. On 2026-09-12 he then authorized Codex to resolve remaining missing categories from his preserved rationale without repeating the transcript. Those completions are explicitly marked as derived under Sid's authorization in provenance and revision history. Same-as-prior statements preserve their reference; structured values may be inherited under the recorded resolution, never as a falsely restated rationale.

## Reconstruction finding and human gate

The transcript contains 49 human annotation events for a target of 50. Sequences 1–15 map exactly to evaluation records `maintie-gold-0968` through `maintie-gold-0982`. The transcript then surfaces `repair fire suppression system`, whereas authoritative source index 983 is `repair door frame`. Sequences 16–27 and 29–50 have no exact match anywhere in the EXP-003 evaluation-input artifact. A complete exact-text audit of the pinned upstream MaintIE gold and silver releases found sequence 16 only at silver index 55 and sequence 23 only at silver index 2546; the other 32 later phrases occur in neither release. Sequence 28 has neither a surfaced record nor a Sid response. Sequence 45 also refers to a feed cylinder while its surfaced text names a propel motor. The audit evidence and hashes are frozen in `data/transcript-source-audit.json`.

Sid approved the fail-closed disposition on 2026-09-12. The frozen ledger preserves all 49 recovered rationales while allowing outcome-stratified analysis only for the 15 exact EXP-003 evaluation matches. Silver-only and unreleased/transcript-variant records are not force-mapped and are ineligible for an outcome join; sequence 28 remains missing and sequence 45's mismatch remains explicit. The joinable 15-record expert subset is too small for confirmatory subgroup claims, so its IE analyses remain descriptive/exploratory unless a separately authorized, prospectively annotated expansion is completed. The authoritative human freeze is `expert/expert-annotations-final.lock.json`; no transcript repetition is required.

## Prospective repeated-run design after expert freeze

For Qwen and Gemma separately:

> Cross-level-consistent detailed classifications will have higher exact-match correctness than cross-level-inconsistent detailed classifications across repeated model realizations.

`Delta_AB = accuracy(A | parent(A)=B) - accuracy(A | parent(A)!=B)`.

Correctness is only A against authoritative detailed MaintIE gold. B correctness never defines correctness. Five new complete runs per model are planned; EXP-003 does not count as one. Local settings are temperature 0.2 and seeds 4101–4105. Astra receives five fresh provider-managed realizations with only supported EXP-003-compatible controls. No model substitution is allowed.

The frozen panel is Qwen `qwen3.5:122b` digest `8b9d11d807c57feb1e2ecb0d6cbf40334c37dcc3523bed5540af4f927f112a37`, Gemma `gemma4:31b` digest `6316f0629137b426c9d9b853ffc4c8209589f30ee39aebede6285096c0ff47e7`, both through Ollama 0.32.5 with 32,768 context, 2,048 output cap, thinking disabled, concurrency one, temperature 0.2, and run seeds 4101–4105. Gemma additionally uses Ollama JSON format. Astra is deployment/model `gpt-6-astra`, version `2026-09-03`, GlobalStandard, medium reasoning effort, 2,048 output cap; seed and temperature are omitted because they are unsupported for this task route. Live identities were read-only verified on 2026-09-12 and must be reverified at execution.

Every record retains three isolated one-turn tasks: A fresh detailed classification, B fresh broad classification, and C independently worded fresh detailed classification. Calls see the record and supplied spans, but no other answer, gold, history, retrieval, browsing, or tools.

Replication for Qwen or Gemma requires all of:

- at least four of five runs individually estimable under the frozen EXP-003 minimum-evidence rule;
- at least four of five runs with `Delta_AB > 0`;
- the predeclared crossed run/record bootstrap 95% interval for mean `Delta_AB` wholly above zero.

Panel replication requires both local models. Astra is a prespecified heterogeneity/stability comparison and is not predeclared null.

## Repeated-question and operational analyses

On the common valid A/B/C item set:

- `Delta_AC = accuracy(A | A=C) - accuracy(A | A!=C)`;
- `MethodGap = Delta_AB - Delta_AC`.

A negative MethodGap means repeated-question agreement has a larger accuracy separation. It does not by itself establish a better or safer screen. Coverage and accepted-set accuracy must always be reported.

After expert freeze and before outcome unblinding, theme frequencies will be inspected without model outcomes and sparse strata will be designated descriptive. The prespecified questions are:

- IE-Q1: whether errors and consistent-but-wrong predictions are more common on partial/insufficient-context records;
- IE-Q2: whether consistency remains informative among high-consequence records;
- IE-Q3: whether high-specificity-required records are harder to classify correctly;
- IE-Q4: which frozen missing-information, ambiguity, and failure-mechanism themes are associated with errors or consistent-but-wrong predictions.

The outcome-blind frequency inspection is frozen in `data/expert-analysis-plan.json`. Quantitative exploratory comparisons are limited to high versus non-high consequence (6 versus 9 records), high versus medium specificity (10 versus 5), and missing-machine-identity present versus absent (8 versus 7). Context sufficiency and every other qualitative theme are descriptive only. No expert-subgroup result may be presented as confirmatory, and categories may not be merged after outcomes are observed.

Expert labels are record-level. Span/entity outcomes may inherit record strata but are not independent expert observations. Uncertainty must cluster by record/exact-duplicate group.

The descriptive high-consequence metric is:

`HighConsequence_CBW = consistent-and-wrong valid predictions / all valid cross-level-consistent predictions`, restricted to expert-rated high-consequence records. It is not measured plant or safety risk.

## Outputs, uncertainty, and execution controls

Per model/run, report overall A accuracy and coverage; valid A/B consistency, stratum accuracies, `Delta_AB`, and consistent-but-wrong; valid A/C agreement, stratum accuracies, and `Delta_AC`; common A/B/C count and MethodGap; accepted coverage/accuracy; invalid outputs; and terminal failures.

Within-run uncertainty uses 10,000 record/duplicate-group bootstrap draws with seed 4004 (seed 4005 for repeated-question estimates and 4006 for MethodGap). Across-run uncertainty uses 10,000 crossed resamples of run IDs and record/duplicate groups with seed 4005. Implementations require synthetic-fixture tests. Within-run uncertainty, between-run stochasticity, and between-model heterogeneity remain distinct.

The fixed production census is 15 runs and 4,860 logical calls: 324 calls per run and 1,620 per model. Retries preserve the same logical observation and never become statistical replicates. The runner records every attempt, honors Retry-After, uses exponential backoff with jitter without an agent-defined retry-count cap, checkpoints each completed logical observation, resumes only an exact unique prefix, preserves terminal failures, and rechecks model identity. Local responses additionally require verified 100% GPU placement at the frozen context; a placement failure is checkpointed and stops the affected run without duplicating that observation.

Any future runner must distinguish transient provider failures from permanent failures and valid negative outcomes; honor Retry-After; use exponential backoff with jitter; checkpoint; resume idempotently; preserve attempts; and apply no agent-defined retry count. A retry is not a statistical replicate. Production monitoring is operational only, with no adaptive stopping or mid-run scientific inspection.

Before inference: freeze the resolved expert ledger, design, hashes, models/configuration, five-run plan, scoring, subgroup rules, qualitative analysis plan, uncertainty, and interpretation rules; create a candidate lock; complete Maker self-review; and obtain the root-AGENTS independent Checker `CHECK_GO`. Before paid Astra work, report deployment/version, logical calls, projected tokens, current sourced cost estimate, lock, and verdict, then obtain Sid's explicit authorization.

## Current stop condition

The human-review gate is complete. No model inference, result analysis, pre-production candidate lock, or independent EXP-004 Checker review has been performed. The next stage is prospective pre-production completion and review, not inference.
