# Run 1 Report — Reasoning Model Degradation on the Gas Turbine Set

**Experiment:** FailureSensorIQ, edge-deployed fault diagnosis
**Model:** phi4-mini-reasoning (ollama, version `3ca8c2865ce91b6be85`)
**Asset:** industrial gas turbine (240 single-answer questions)
**Settings:** temperature 0.3, top_p 0.95, top_k 50, seed 42, num_ctx 8192, num_predict 16384
**Run:** 2026-06-24, 09:03–11:07 UTC, single sequential pass, local DGX Spark (Kratos)

---

## 1. What I set out to test

The reasoning model had returned roughly 80% garbage on this asset at the vendor-recommended temperature of 0.8. The question for Run 1 was narrow: does lowering the temperature to 0.3 — the correct setting for a one-right-answer task — clean that up, or does it just trade the high-temperature garbage for the low-temperature failure mode (the model looping forever and never finishing)?

The answer turned out to be neither, and the reason is more important than the temperature question.

## 2. Headline result

The model's diagnostic knowledge is sound. When it actually commits to an answer, it scores **49.3%** on this asset — inside the expert band (human experts sit near 60%, the guessing floor is 27.5%). That is a genuinely capable result for a model small enough to run on an 8 GB edge box.

But the model only stayed usable for the first part of the run. After about 120 sequential calls it stopped producing readable output and never recovered. Across the full 240 questions, **40% of all answers came back as unusable garbage**, which dragged the headline accuracy down to **29.6%** — barely above blind guessing. The low score is a serving failure, not a knowledge failure.

| Metric | Value |
|---|---|
| Accuracy, all 240 | 29.6% (71/240) |
| Accuracy, committed answers only | **49.3% (71/144)** |
| Unusable (fallback) rate | 40.0% (96/240) |
| Structured-output reliability (SOR) | 0.600 (target ≥ 0.95) |
| Truncations (ran out of tokens) | 2 |

## 3. The failure is positional, and the cliff is sharp

The garbage is not spread evenly. The first 120 calls were almost perfect; then output collapsed and stayed collapsed.

| Run position | Unusable rate | Median output length | Median time |
|---|---|---|---|
| q0–119 | **1 / 120 (≈1%)** | 1,258 tokens | 21 s |
| q120–239 | **95 / 120 (≈79%)** | 734 tokens | 12 s |

In the back half the model produced shorter responses, faster, almost all of them junk. Same machine, same model, same settings, same asset — only the position in the run changed.

## 4. What the garbage actually is

This is the part that tells us the cause. The failures are not the model thoughtfully declining to answer, and they are not the infinite-loop failure that low temperature causes in reasoning models. The responses finish normally — 93 of the 96 failures ended with a clean stop signal, not a truncation. They have simply decayed into incoherent text. Real examples from the collapse zone:

- *"Your name is called after effect ... athoffili"*
- *"A your other is=C899I'mCom query is=M898-Tus calledDis nameyour=Ahem"*
- *"the name of an AI math expert from the given options: A) vibration, B) exhaust temperature ..."* — the model hallucinated a name-guessing task laid over the turbine answer options.

This is word salad and wrong-task hallucination. The model is not reasoning poorly about turbines; it has lost the thread of what it is being asked entirely.

## 5. Ruling out the obvious explanations

Before blaming the serving layer I checked whether the questions themselves explain the cliff. They do not.

**It is not harder input.** The prompt size is identical on both sides of the cliff — median 73 input tokens in the clean zone and 73 in the collapse zone. The late questions are no longer or more complex than the early ones.

**It is not question difficulty.** Using the frozen difficulty labels, easy ("clear") questions fail at 44% — exactly the same rate as "confusing" ones (44%). If content drove the failure, the easy questions would survive. They do not.

**The decisive check.** Among the easy "clear" questions that happen to fall *in the collapse zone*, 44 of 52 (85%) failed. The same trivial question type that scored near-zero failure in the first 120 calls fails 85% of the time later in the run, purely because of where it sits. Position, not content, is the variable.

**It is not temperature, and it is not truncation.** Temperature was fixed at 0.3 throughout, so it cannot explain a change that happens mid-run. Only 2 of 240 calls ran out of tokens, so the model was not being cut off.

## 6. Why would the model degenerate?

The model weights are fixed and each request is an independent, stateless HTTP call — the client sends one prompt, gets one answer, and shares nothing between calls. So nothing in *my* code carries state from question to question. The only thing that persists across all 240 sequential calls is the **serving process's own internal state on the GPU**. That is where the degradation has to live.

The signature — a sharp onset after a fixed number of calls, a persistent bad state that never self-corrects, and output that decays into token salad rather than wrong-but-coherent answers — is consistent with corrupted internal generation state, not with anything about the questions. The most likely mechanisms, in order of how well they fit the evidence:

1. **KV-cache / context-slot corruption in the serving runtime (most likely).** ollama keeps a reusable key/value cache for the loaded model and reuses memory slots across requests. A small reasoning model emits long (~1,200–2,000 token) traces every call, so the cache is heavily churned. If that cache or its slot bookkeeping drifts into a bad state after enough long generations, the model's attention reads corrupted history and the output collapses into salad. This fits the sharp onset, the persistence (a poisoned slot stays poisoned until the model is reloaded), and the incoherent-text signature better than anything else.

2. **GPU memory pressure or a slow leak over the run.** Sustained back-to-back generation can fragment or exhaust working memory; once allocations start failing or overlapping, the math feeding the sampler produces nonsense. This also fits a cumulative, position-driven onset.

3. **Numerical fragility of the small quantized reasoning model under sustained load.** phi4-mini-reasoning is heavily compressed and generates long autoregressive chains. Such models have thin numerical margins; under continuous load on this hardware those margins may be crossed, tipping the sampler into degenerate territory. This is plausible but weaker — it does not by itself explain why the failure is so persistent once it starts.

What the evidence does **not** support: a model-knowledge problem (it scores 49% when it commits), a content or difficulty problem (ruled out in Section 5), or a temperature problem (fixed throughout). The cause is the serving layer degrading over a long sequential batch, not the model being wrong.

I am not claiming which of the three runtime mechanisms it is — distinguishing them needs the controlled test in Section 8. But the class of cause is clear: cumulative serving-state degradation.

## 7. What this changes

**The earlier "the garbage is asset-driven" read was wrong.** Within a single asset, with everything else fixed, position alone produced the failure. The real variable was the number of sequential calls, not which machine the question was about.

**The model-selection verdict gets stronger.** A small reasoning model is not merely a poor temperature match for a deterministic task — on this box it cannot be served reliably across a long batch. Gemma 3 4B ran the full 2,667-question set clean. For an edge box that must answer continuously, that reliability is the deciding factor, not peak per-question cleverness.

**This is an integration-hygiene finding, not just a model finding.** A short preflight — even a generous 100-call one — would have *passed* this model, because the first 120 calls were spotless. It would then fail in production once the box had been answering for a while. This is the strongest case yet for a rolling gate that samples across the *full* run length rather than only the head, and for monitoring output reliability continuously in deployment, not just at commissioning.

## 8. Verification — confirmed by a fresh-load test

The isolation check has now been run, and it confirms the diagnosis directly.

Six questions that produced pure garbage late in Run 1 (positions 122–136) were re-sent to a **freshly loaded** model, with identical settings (temperature 0.3, top_p 0.95, top_k 50, seed 42, num_ctx 8192). Because the model had unloaded itself after Run 1, the first call loaded it fresh — a clean serving state. **All six recovered.**

| ID | Run 1 (position 120+, degraded state) | Fresh load |
|---|---|---|
| 1197 | "I'm not very well gifted…" — 92-token salad | coherent reasoning, 1,649 tokens, committed |
| 2073 | "&lt;think]&lt;/strong&gt;" salad — 56 tokens | coherent, 3,753 tokens, committed |
| 1167 | "Your name is Phi. What is your name?" — 11 tokens | coherent, 910 tokens, committed |
| 1202 | Chinese-character salad — 265 tokens | coherent, 1,006 tokens, committed |
| 624 | "The question is about Turbine…" — 11 tokens | full reasoning, 6,033 tokens, **correct** |
| 2077 | "Your name is ? ? ? ?" — truncated salad | coherent, 834 tokens, **correct** |

**6 / 6 now parse cleanly.** Same questions, same settings, same machine, same model version — the only thing that changed is that the serving state was fresh rather than ~120 calls deep. This rules out the questions and the model weights beyond any residual doubt: the failure lived in the runtime's accumulated state, exactly as Section 6 argued. It is an ollama (0.18.0) / llama.cpp runtime behaviour, not a phi4 or a data problem.

**Deployment mitigation (now justified, worth validating at scale):** cap the number of calls per loaded session and reload the model periodically during long batches, so the serving state never ages into the failure zone. This is a serving-configuration fix, not a model swap. A full re-order run (same 240 in a different shuffle) would further quantify exactly how many calls the runtime survives before degrading; the fresh-load test already settles the *cause*.

## 9. Bottom line

phi4-mini-reasoning can diagnose gas-turbine faults at roughly expert level — when it answers at all. On this hardware it degrades into unusable output after about 120 continuous calls, for reasons that sit in the serving layer rather than the model's knowledge or the questions. For an always-on edge deployment that is disqualifying, and it points back to the same conclusion the temperature work reached from a different direction: the deployable choice here is a small non-reasoning model (Gemma 3 4B), run at a low deterministic temperature, with reliability watched continuously rather than only at commissioning.
