# FailureSensorIQ — Findings

Small language models for industrial fault diagnosis: a baseline characterisation of four 4B-class
models on IBM's FailureSensorIQ, run locally under an integration-hygiene discipline. This document
consolidates the design, methodology, results, findings, the runtime-degradation case, and the
limitations. The plain-language version is on the site:
[industrialmindandcode.ai](https://www.industrialmindandcode.ai/blog/small-language-models-fault-diagnosis.html).

## Abstract

I tested four small (≤4B-parameter) language models on IBM's **FailureSensorIQ** benchmark — 2,667
single-answer fault-diagnosis questions across ten industrial asset classes — to characterise what an
edge-deployable model can and cannot do on industrial fault reasoning. Accuracy and output reliability
were scored as separate axes. Best clean full-set result: **Nemotron-3 Nano 4B at 51.8%** with clean,
machine-readable output on all 2,667 calls — above the ~27.5% blind-guessing floor, below the ~60.2%
human-expert mean. The two most practical lessons sit outside the ranking: sampling **temperature** and
**serving reliability** often decide whether a small model's output is usable at all. This is a baseline
to inform a deployment, not a deployment.

## Design & methodology

- **Benchmark.** FailureSensorIQ (IBM Research): 2,667 single-answer multiple-choice fault-diagnosis
  questions across ten asset classes (gas turbines, transformers, motors, pumps, compressors, fans,
  generators, reciprocating engines, and more). A public, named benchmark — checkable and comparable.
- **Two axes, scored separately.** Each call is scored for *correctness* (right answer) and for
  *integration reliability* (well-formed, machine-readable output). They are independent: a model can be
  wired correctly but wrong, or knowledgeable but unreliable. Per-call telemetry — parse status, finish
  reason, empty/refusal, attempts, token counts, sampling settings, and the model version — is recorded
  for every question (the integration-hygiene discipline).
- **Temperature as an explicit variable, where a clean comparison was available.** Non-reasoning models
  were run at low temperature and, where relevant, at vendor default; Phi-4-mini gives the clearest
  same-model contrast. Nemotron ran at its provider setting of 0.6.
- **Full-run endurance.** The entire 2,667-question set was scored in a single run rather than a short
  sample, specifically to expose degradation that only appears over a long sequential run.
- **Reliability gate.** A 5% unusable-output threshold was used as the gate for further consideration.
- **Reference yardsticks** (from the benchmark): blind guessing ≈ 27.5%, always-answer-A ≈ 28.2%,
  human-expert mean ≈ 60.2%, best expert ≈ 66.2%.

## Models & results

Clean full-set runs (all 2,667 questions). Full per-call metrics are in [`results/`](results/).

| Model | Type | Temp | Accuracy | Output reliability | Unusable |
|---|---|---|---|---|---|
| Nemotron-3 Nano 4B | reasoning | 0.6 (provider) | **51.8%** | 1.000 | 0.0% |
| Gemma 3 4B | non-reasoning | 0.3 | 42.1% | 1.000 | 0.0% |
| Gemma 3 4B | non-reasoning | 1.0 (default) | 41.9% | 1.000 | 0.0% |
| Phi-4-mini | non-reasoning | 0.3 | 36.6% | 0.951 | 4.9% |
| Phi-4-mini | non-reasoning | 0.8 (default) | 30.7% | 0.933 | 6.7% |

**Phi-4-mini-reasoning is excluded from the leaderboard** because it produced no clean full-set run (see
the runtime-degradation section). Its default-temperature run broke; a 240-question single-asset
diagnostic at temperature 0.3 degraded badly (40% unusable) — an operational warning, not a model score.

## Findings

1. **The best clean result is a capable assistant, not a decision-maker.** Nemotron-3 Nano 4B at 51.8%
   is a real lift over guessing with perfectly clean output, but sits ~8 points below the expert mean —
   a reasoning layer for an engineer to confirm, not an unsupervised maintenance authority.
2. **Temperature is not a detail (directional, single-model contrast).** Phi-4-mini rose from 30.7% at
   its 0.8 default to 36.6% at 0.3 on the same weights, and its unusable rate fell from 6.7% to 4.9%,
   crossing the 5% reliability gate. The vendor default is tuned for open-ended generation, not for a
   one-right-answer task.
3. **Temperature-insensitivity is its own robustness.** Gemma 3 4B scored 41.9% / 42.1% across
   temperatures 1.0 and 0.3, clean on every call at both — easier to commission and trust.
4. **Two reasoning models, opposite ends.** Nemotron-reasoning topped the clean leaderboard;
   Phi-4-mini-reasoning produced no clean full-set result. "Reasoning model" is not itself a verdict.
5. **Clean output and a correct answer are different axes.** Early "wrong" answers were often the parser
   failing to read a correctly-given answer in an unexpected format. On a small model the glue code can
   cost as many points as the model's knowledge — it is a first-class part of the result.
6. **Capability varies sharply per asset.** The same headline average hid assets where models behaved
   very differently. Commission per asset, not from one aggregate score.

## Runtime degradation case (Phi-4-mini-reasoning)

Phi-4-mini-reasoning's output degraded during a long sequential run. This was a **serving-runtime
issue, not the model**:

- the input was identical across the point where output began degrading;
- question difficulty did not predict failure;
- questions that produced garbage late in the run answered cleanly when re-sent to a freshly loaded model.

The cause is cumulative serving-state degradation in the runtime. The **leading hypothesis is the KV
cache** — the runtime's reusable working memory — but the exact mechanism is **not confirmed**. What is
settled is the *location*: the runtime's (Ollama's) state, not the model's weights, and not the model
maker. (Nemotron's Mamba-hybrid architecture carries far less of that growing cache and stayed clean
throughout; whether the architecture is the reason is a plausible but unproven hypothesis.) The
operational lesson: monitor output reliability continuously and reload the serving runtime on a schedule
— a pilot can fail because the serving setup ages over a long run, even when the model is fine.

## Limitations

- **Edge-deployability is footprint-only.** At 2.8 GB the top model fits an 8 GB box, but runs were on a
  workstation, not constrained edge hardware. Footprint evidence, not a validated edge deployment.
- **The top score is not good enough for autonomous action.** 51.8% is ~8 points below the expert mean;
  the deployed use case needs a grounding/scaffolding layer (reference data, retrieval, tools) or a
  human sign-off above the bare model.
- **The temperature result is a single-model contrast** — directional, not a general law.
- **Phi-4-mini-reasoning has no clean full-set result.** Its degraded number is from a 240-question
  single-asset diagnostic (40% unusable); a re-run with adequate runtime headroom is pending before any
  reasoning-model comparison is treated as valid.
- **The architecture-explains-endurance link is a hypothesis** the two-model comparison cannot prove.
- Hypotheses were not pre-registered.

## What this informs

**1. What the model is for — an assistant, not the decision-maker.** Model and setting are settled:
Nemotron-3 Nano (reasoning) as primary, Gemma 3 4B at low temperature as the non-reasoning fallback. A
51.8% top score means the bare model cannot make the call; the system has to put a grounding layer above
it, or keep a human in the loop. The model proposes; the system or the engineer decides.

**2. How to run it reliably.** Set the sampling temperature for the task; score reliability separately
from accuracy; monitor serving health over long runs and reload the runtime before degradation becomes
invisible; commission per asset rather than with one general prompt; and check the decision is genuinely
judgement-shaped before using a model at all — fixed thresholds and lookups belong in plain code.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
