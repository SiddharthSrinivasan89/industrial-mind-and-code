# What I Learned — FailureSensorIQ Baseline Capability Test

## What this experiment was for

This was always a **baseline test**, not the product. I ran the full FailureSensorIQ set —
2,667 single-answer fault-diagnosis questions across 10 industrial assets — to find out what a
small, edge-deployable model can and cannot do on industrial fault reasoning, and to do it under
an integration-hygiene discipline rather than as a one-off accuracy number. The point was to
characterise the models. The actual LLM use case gets designed *on top of* what this baseline tells
us — so the value here is the learnings, not the score.

The target deployment it informs: a small model running on a box next to the machines, no cloud,
reading the sensor feed and acting as the reasoning layer over the existing monitoring system.

## The numbers (verified, full 2,667-question set unless noted)

Reference points from the benchmark: blind guessing ≈ 27.5%, always-answer-A ≈ 28.2%, human
expert mean ≈ 60.2% (best expert ≈ 66.2%).

| Model | Temp | n | Accuracy | Structured-output reliability | Unusable rate |
|---|---|---|---|---|---|
| nemotron-3-nano:4b (reasoning) | 0.6 | 2,667 | **51.8%** | 1.000 | 0.0% |
| gemma3:4b | 0.3 | 2,667 | 42.1% | 1.000 | 0.0% |
| gemma3:4b | 1.0 (default) | 2,667 | 41.9% | 1.000 | 0.0% |
| phi4-mini | 0.3 | 2,667 | 36.6% | 0.951 | 4.9% |
| phi4-mini | 0.8 (default) | 2,667 | 30.7% | 0.933 | 6.7% |
| phi4-mini-reasoning | 0.8 (default) | — | no clean run | — | run broke |
| phi4-mini-reasoning | 0.3 | 240 (gas turbine only) | 29.6% | 0.600 | 40.0% |

Two of the four models are reasoning models, and they landed at opposite ends. nemotron-3-nano:4b is
the top result — 51.8%, perfectly clean across all 2,667 calls. phi4-mini-reasoning never produced a
clean full-set result: its default-temperature run broke, and the temperature-0.3 diagnostic on the
single hardest asset degraded badly (details below). So "reasoning model" is not itself a verdict —
the two diverge sharply, and the difference is the story.

## What I learned

**Deterministic tasks want low temperature.** Fault diagnosis is a one-right-answer task. Lower
temperature (0–0.3) is the correct regime — more accurate, more reproducible, more auditable. The
vendor's recommended sampling temperature is tuned for open-ended generation, not for this. phi4-mini
proved it directly: 30.7% at its default 0.8, 36.6% at 0.3 — six points purely from the setting.

**Gemma 3 4B is temperature-insensitive, which is its own kind of robustness.** It scored 41.9% at
the default and 42.1% at 0.3 — essentially flat — and returned clean structured output on every
single one of 2,667 calls at both settings. A model that does not wobble when you change the knob is
easier to commission and trust on a shop floor.

**A reasoning model can be the best tool here — or the worst — and they do not behave alike.** The
two reasoning models split to opposite ends. nemotron-3-nano:4b topped the panel at 51.8%, clean.
phi4-mini-reasoning was the worst: at temperature 0 it loops and never finishes, at high temperature
it comes apart, and at the task-ideal 0.3 it ran clean for ~120 sequential calls then collapsed into
garbage for the rest of the run. The lesson is not "avoid reasoning models" — it is that a reasoning
model has to be tested for *endurance under a long run*, not just scored on a short sample.

**The collapse was a serving-runtime failure, not a model-knowledge failure.** I isolated it: the
input was identical across the cliff, question difficulty did not predict failure, and six questions
that produced garbage late in the run all answered cleanly when re-sent to a freshly loaded model. The
cause is cumulative serving-state degradation in the runtime — the leading hypothesis is the KV cache,
the runtime's reusable working memory, but the exact mechanism has not been confirmed by controlled
tests. What is settled is the location: it is the runtime's (Ollama's) state, not the model's weights
and not the model maker's — the same questions ran clean on a fresh load. nemotron, whose Mamba-hybrid
architecture carries far less of that growing cache, stayed clean across all 2,667 calls; whether the
architecture is the *reason* is a plausible hypothesis the two-model comparison cannot prove on its
own. A vendor benchmark will never warn you about any of this, because it is a property of how you
serve the model.

**Clean output and a correct answer are two different axes.** Returning well-formed structured output
means the model is *wired* right; getting the diagnosis right is a separate question. Early in this
work a large share of "wrong" answers were actually my parser failing to read a correct answer the
model had given in an unexpected format. The glue code between the model and the system is often the
real weak link — on a small model it can cost as many points as the model's actual knowledge.

**Even the top result is real capability but not a trustworthy decision.** nemotron's 51.8% is the
strongest score on the panel and well above guessing, but it still sits ~8 points below mean expert
performance (~60%) and ~14 below the best expert (~66%) — nowhere near reliable enough to make an
unsupervised maintenance call. The model is a reasoning *layer*, not the decision-maker, no matter
which one wins.

**One average hides large per-asset variation.** The gas turbine was the hard asset where everything
struggled; motors, pumps and transformers were clean. Capability has to be validated per asset and per
task, not generalised from a single headline number.

**Endurance is something you monitor continuously, not certify once.** The degradation lesson
generalises: a model can pass every check on day one and fail later because the *serving* ages, not
the model. The deployment rule is to watch reliability continuously and reload on a schedule.

## Model verdict

For an edge-deployed fault-diagnosis layer, **nemotron-3-nano:4b (reasoning on, provider settings) is
the pick**: top accuracy at 51.8%, perfectly clean output across all 2,667 calls, no degradation over
the full run, 2.8 GB on an 8 GB box, ~5.3 s/call, with a full chain of thought saved per question for
audit. **gemma3:4b at low temperature is the strong non-reasoning fallback** — clean,
temperature-insensitive, and simpler to run where a reasoning trace is not wanted. phi4-mini is a
weaker non-reasoning option. phi4-mini-reasoning is out — no good temperature and it degraded over the
run.

## What this means for the use case I build next

These learnings are the design inputs, not the deliverable:

1. **Model and setting are decided:** nemotron-3-nano:4b (reasoning on, temp 0.6), with gemma3:4b at
   temp 0.3 as the non-reasoning fallback. Settled by this baseline.
2. **Do not ship the bare model as the decision-maker.** A 51.8% top raw score means the use case
   still needs a scaffolding layer above the model — reference data, retrieval, or tools to ground it
   — or a human-in-the-loop sign-off on the decision. The next question to test is how much that
   scaffolding lifts the ceiling.
3. **Budget engineering for the integration, not just the model.** The parser and structured-output
   handling earned real points here; the use case should treat the glue layer as a first-class part,
   with the integration-hygiene checks built in.
4. **Commission per asset, and narrow the task.** Rather than one general diagnosis prompt across all
   ten assets, the use case should commission and validate per asset, and consider narrowing to the
   assets where the model is already strong.
5. **Bake in continuous reliability monitoring and a periodic model reload** as a standing runtime
   policy, so serving-state degradation can never quietly take the box down.
6. **Check the task is even LLM-shaped first.** Where a plant decision is a fixed threshold or a
   lookup, that belongs in plain code, not a 4B model. Reserve the model for the genuinely
   judgement-shaped parts of the workflow.

The baseline did its job: it told me which model, which temperature, where the failure modes are, and
what the integration has to carry. The use case is built from there.
