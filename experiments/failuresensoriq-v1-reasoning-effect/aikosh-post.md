<!-- Rung-0 atom · AIKosh article (manual paste) · checker-revised light rewrite 2026-06-29 · grounded in WHAT-WE-LEARNED.md · F-007/F-008 VETTED, F-009 runtime-confounded · status: ready to paste -->
<!-- SHORT DESCRIPTION (for the AIKosh summary field):
A baseline test of four small (4B-class) language models on IBM's FailureSensorIQ fault-diagnosis
benchmark — 2,667 questions across ten industrial asset classes. The best, Nemotron-3 Nano 4B,
reached 51.8% with perfectly clean output: a plausible local assistant, but short of a human expert.
The practical lessons sit outside the ranking — sampling temperature and serving reliability often
decide whether a small model's output is usable at all. -->


# Small Language Models for Industrial Fault Diagnosis: A Baseline on IBM's FailureSensorIQ

By Siddharth Srinivasan · Industrial Mind and Code (industrialmindandcode.ai)

The practical question was simple: can a language model small enough to run locally near industrial equipment help with fault diagnosis, without sending data to the cloud?

I tested that question on IBM's **FailureSensorIQ** benchmark — 2,667 single-answer fault-diagnosis questions across ten industrial asset classes. I treated the run as more than a leaderboard exercise: each model was scored both for accuracy and for whether its output was clean enough for software to read reliably — two separate things.

The best clean full-set result came from **Nemotron-3 Nano 4B: 51.8% accuracy with structured output on all 2,667 calls.** That is well above blind guessing (~27.5%), but below the ~60.2% human-expert mean. So the right conclusion is not "autonomous diagnosis" — it is "plausible local assistant, with engineering guardrails." And the two lessons that matter most for anyone trying this are not in the ranking at all: the sampling **temperature** and the **serving reliability** often decide whether you get a usable answer in the first place.

## Models tested — clean full-set runs

Across the clean full-set runs — all 2,667 questions — Nemotron-3 Nano 4B (a reasoning model, run at its provider setting of temperature 0.6) led with **51.8%** accuracy and perfectly clean output: every one of its answers was well-formed and machine-readable. Gemma 3 4B followed at 42.1% (temperature 0.3) and 41.9% (its 1.0 default), also clean on every single call at both settings. Phi-4-mini scored lower and less reliably — 36.6% at temperature 0.3, with 4.9% of its outputs unreadable, and 30.7% at its 0.8 default, with 6.7% unreadable. ("Reliability" here is the share of calls returning well-formed structured output; "unusable" is the share the parser could not read.)

For reference, the benchmark's own yardsticks are blind guessing ≈ 27.5%, always-answer-A ≈ 28.2%, human-expert mean ≈ 60.2%, and best expert ≈ 66.2%.

A sixth model, **Phi-4-mini-reasoning, is excluded from the leaderboard because it produced no clean full-set run.** Its default-temperature run broke, and a 240-question single-asset diagnostic degraded badly (40% unusable). I discuss it below as a runtime failure case, not as a model score.

## Methodology

**Benchmark.** FailureSensorIQ (IBM): 2,667 single-answer multiple-choice fault-diagnosis questions across ten industrial asset classes. A public, named benchmark matters — the result is checkable and directly comparable to other models.

**Two axes, scored separately.** Each call was scored for *correctness* (did it pick the right answer) and for *integration reliability* (did it return well-formed, machine-readable output). These are independent: a model can be wired correctly but wrong, or knowledgeable but unreliable. Per-call telemetry (parse status, finish reason, empty/refusal, token counts, settings) was recorded for every question.

**Temperature as an explicit variable, where a clean comparison was available.** The non-reasoning models were run at low temperature and, where relevant, at vendor default; Phi-4-mini gives the clearest same-model contrast. Nemotron was run at its provider setting of 0.6.

**Full-run endurance.** I scored the entire 2,667-question set in a single run rather than a short sample, specifically to expose any degradation that only appears over a long sequential run.

**Reliability gate.** For this baseline I used a 5% unusable-output threshold as the reliability gate for further consideration.

## Findings

**1. Leaderboard.** Every clean full-set run cleared the guessing floor; none reached the human-expert mean. Nemotron-3 Nano led at 51.8% with clean output on every call, ahead of Gemma 3 4B (42.1%) and Phi-4-mini (36.6%).

**2. Temperature is not a detail (directional, single-model contrast).** Phi-4-mini scored 30.7% at its vendor default of 0.8 and 36.6% at 0.3 — same model, same weights, six points from one setting. Its unusable rate also fell from 6.7% to 4.9%, moving it from failing the reliability gate to passing it. The default is tuned for open-ended generation, not for one-right-answer work. I treat this as directional because it is one model, but the direction is consistent with the task.

**3. Temperature-insensitivity is its own robustness.** Gemma 3 4B scored 41.9% and 42.1% across temperatures 1.0 and 0.3, clean on all 2,667 calls at both. A model that does not wobble when the setting changes is easier to commission and trust.

**4. Two reasoning models, opposite ends.** Nemotron-reasoning topped the clean leaderboard; Phi-4-mini-reasoning produced no clean full-set result at all. "Reasoning model" is therefore not itself a verdict — the two diverged sharply, and the difference is the story.

**5. The Phi-4-mini-reasoning failure was a serving-runtime issue, not the model.** I isolated it: the input was identical across the point where output began degrading, question difficulty did not predict failure, and questions that produced garbage late in the run answered cleanly when re-sent to a freshly loaded model. The cause is cumulative serving-state degradation in the runtime. The leading hypothesis is the KV cache — the runtime's reusable working memory — but the exact mechanism is **not confirmed**. What is settled is the *location*: the runtime's (Ollama's) state, not the model's weights, and not the model maker. (Nemotron's Mamba-hybrid architecture carries far less of that growing cache and stayed clean throughout; whether the architecture is the reason is a plausible but unproven hypothesis.) A vendor benchmark will never warn you about this, because it is a property of how the model is served.

**6. Clean output and a correct answer are different axes.** Early in the work, a large share of "wrong" answers were actually the parser failing to read a correct answer returned in an unexpected format. On a small model, the glue code between model and system can cost as many points as the model's knowledge — so it is a first-class part of the result, not an afterthought.

**7. Capability varies sharply per asset.** Per-asset behaviour varied sharply — the same headline average hid assets where models behaved very differently. That is the deployment lesson: commission per asset, not from one aggregate score.

## Limitations

- **Edge-deployability is footprint-only.** At 2.8 GB the top model fits an 8 GB box, but these runs were on a workstation, not constrained edge hardware. Treat it as a footprint result, not a validated edge deployment.
- **The top score is a reasoning layer, not a decision-maker.** 51.8% is ~8 points below the expert mean (~60.2%) and ~14 below the best expert — useful for surfacing likely causes for an engineer to confirm, not for an unsupervised maintenance call.
- **The temperature result is a single-model contrast** — directional, not a general law.
- **Phi-4-mini-reasoning has no clean full-set result.** Its degraded number is from a 240-question single-asset diagnostic (40% unusable). A re-run with adequate runtime headroom is pending before any reasoning-model comparison is treated as valid.
- **Why Nemotron stayed clean is not proven.** Its different internal design may be why it didn't degrade over the long run — but I only compared two models, which is not enough to prove the architecture is the cause rather than some other difference (size, training, runtime settings). It stays a hypothesis.
- Hypotheses were not pre-registered.

## What this informs

The value of a baseline is the design inputs it produces, not the score. Two inferences follow.

**1. What the model is for — an assistant, not the decision-maker.** The model and setting are settled: Nemotron-3 Nano (reasoning) as the primary, with Gemma 3 4B at low temperature as the non-reasoning fallback. But a 51.8% top score sits well below an expert, so the bare model cannot be the one making the call. The deployed system has to put a grounding layer above it — reference data, retrieval, or tools — or keep a human in the loop to confirm. The model proposes; the system or the engineer decides.

**2. How to run it reliably — three operating rules.** First, monitor output reliability continuously and reload the model on a schedule: the serving setup can degrade over a long run even when the model itself is fine. Second, commission per asset rather than with one general prompt, because capability varies sharply from one asset to another. Third, check the decision is genuinely judgement-shaped before using a model at all — fixed thresholds and lookups belong in plain code, not a 4B model.

If you are working on small or local models for maintenance, diagnostics, or the shop floor, I would be glad to compare notes — more of this work is at industrialmindandcode.ai.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
