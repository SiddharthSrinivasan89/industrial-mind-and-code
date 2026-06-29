# A 4-Billion-Parameter Model on the Shop Floor? An Indicative, Footprint-Based Comparison of Small Language Models for Industrial Fault Diagnosis

**Author:** Siddharth Srinivasan
**Date:** 2026-06-25
**Status:** Findings writeup (public). This is an **indicative analysis**. Diagnostic *capability* is
measured directly — full runs on the 2,667-question set, verified against the saved run manifests.
*Edge-deployability* is assessed **by model footprint only**: the runs were on a 128 GB development
machine, not constrained edge hardware, so "edge" here means the model is small enough to fit, not that
it has been validated running on a real edge box.

---

## The question

Can a language model small enough to run on a box next to the machines — no cloud, no data leaving
the plant — act as the fault-diagnosis reasoning layer on top of an existing monitoring system? Not
"AI replaces your control system," but: given a sensor reading, can a small local model name the
likely failure mode well enough to be useful?

I tested four small models — all in the size class that *fits* an 8 GB edge box — against IBM's
FailureSensorIQ benchmark: 2,667 single-answer questions that ask a model to connect a sensor
situation to the right failure mode across ten classes of industrial equipment, from gas turbines to
pumps to power transformers. The whole study was run under an integration-hygiene discipline, so every
model was scored on two separate things: did it answer *reliably* (clean, parseable output every
time), and did it answer *correctly*.

**A word on scope, because it matters for how to read everything below.** This is an *indicative*
analysis on two fronts. The capability numbers are real and measured. But the edge-deployment angle is
indicative only: I am using **model footprint** — does it fit in 8 GB — as a proxy for "deployable on
the edge," and the runs themselves were on a 128 GB development machine, not a constrained shop-floor
unit. So this study answers "are these models *small enough and good enough* to be worth deploying on
the edge?" It does not yet answer "do they actually run well on real edge hardware?" — that is a
separate, later test. Read the result as a green light to pursue edge deployment, not as proof of it.

This was a baseline. The goal was to find out what these models can and cannot do, so the real use
case can be built on evidence rather than a demo.

## The benchmark, in plain terms

Each question gives a sensor or failure situation and a short list of options (A, B, C…), and asks for
the single best one. Some are positively framed ("which sensor is most relevant"), some negatively
("which is *not* relevant") — the negative ones are harder.

Three reference points anchor every score:

- **Blind guessing: ~27.5%.** Random choice.
- **Human expert: ~60.2% on average, ~66.2% for the best expert.** This is a genuinely hard task —
  even domain experts are far from perfect.

So the band that matters is roughly 28% (knows nothing) to 60% (matches a typical expert).

## The models

All four are small enough by memory footprint to fit an 8 GB edge box, and were served locally
through Ollama:

| Model | Type | Size on disk |
|---|---|---|
| Gemma 3 4B | non-reasoning | 3.3 GB |
| Phi-4-mini | non-reasoning | 2.5 GB |
| Phi-4-mini-reasoning | reasoning (Transformer) | 3.2 GB |
| Nemotron-3 Nano 4B | reasoning (Mamba-hybrid) | 2.8 GB |

Two are plain instruct models; two are reasoning models that think step by step before answering.
Each ran at its provider-recommended sampling settings — never at temperature 0, which makes
reasoning models loop and never finish.

## The result

| Model | Accuracy | Clean-output reliability |
|---|---|---|
| **Nemotron-3 Nano 4B** (reasoning) | **51.8%** | 1.000 |
| Gemma 3 4B | 42.1% | 1.000 |
| Phi-4-mini | 36.6% | 0.951 |
| Phi-4-mini-reasoning | no clean run — degraded | 0.600 |

**Nemotron-3 Nano 4B is the clear winner at 51.8%** — about 10 points above the next model and
roughly halfway between blind guessing and a typical human expert. It returned a clean, readable
answer on every one of 2,667 calls, and it did best on the single hardest asset (the industrial gas
turbine, 71%). That is a strong result for a 2.8 GB model — small enough to sit on a
shop-floor box — at about five seconds per question on the development hardware, with its full
reasoning saved for every answer so a person can audit *why* it decided what it did.

Three things from the study are worth more than the leaderboard.

### 1. The temperature setting is not a detail

"Temperature" controls how much randomness a model uses when it writes. Vendors recommend a fairly
high default tuned for open-ended, creative writing. But fault diagnosis is a one-right-answer task,
and there a low temperature is correct. Phi-4-mini showed it directly: it scored **30.7% at its
vendor default and 36.6% at the lower task-correct setting** — six points, same model, same weights,
just the right setting. The lesson that kept holding: match the temperature to the task, not to the
vendor's default.

### 2. Two reasoning models, opposite outcomes

This was the surprise. The two reasoning models landed at opposite ends — the best result *and* the
worst. Nemotron topped the panel and stayed perfectly clean. Phi-4-mini-reasoning never produced a
usable full run: at low temperature it loops forever, at high temperature it falls apart, and at the
in-between setting it ran clean for about 120 questions and then **collapsed into garbage** —
incoherent text and wrong-task answers — for the rest of the run.

So "use a reasoning model" is not, by itself, a decision. A reasoning model has to be tested for
endurance across a long, continuous run, not just scored on a short sample.

### 3. The collapse was the plumbing, not the model

I traced the phi-4-mini-reasoning failure. It was not the model getting confused by hard questions:
the inputs were identical on both sides of the collapse, difficulty did not predict failure, and the
clincher — six questions that produced garbage late in the run all answered cleanly when I reloaded
the model fresh and asked them again. The same questions, the same settings; only the serving state
was different.

That points to a build-up in the *runtime* that serves the model — the leading suspect is the
KV cache, the reusable working memory an inference engine keeps and churns hard when a reasoning model
writes long traces. I want to be precise about confidence here: the *location* of the fault is
settled (it is the runtime's state, not the model's weights, and not the benchmark) because a fresh
load fixes it; the exact *mechanism* is a strong hypothesis, not yet proven, because confirming it
needs a controlled test I have not run. Nemotron, whose hybrid architecture carries far less of that
growing cache, ran 2,667 questions without a single bad output — but it differs from phi-4-mini in
more than architecture, so I am calling the architecture a likely explanation, not a proven cause.

The practical takeaway is solid regardless: a model can pass every check on day one and fail later
because the *serving* ages, not the model. Reliability has to be monitored continuously and the model
reloaded on a schedule — and that is the runtime's responsibility, something a vendor benchmark will
never warn you about.

## The honest limit

51.8% is the strongest result here and well above guessing, but it still sits about 8 points below a
typical expert and 14 below the best one. The model is clearly learning real sensor-to-fault
relationships, but it is nowhere near reliable enough to make a high-stakes maintenance call on its
own. The right way to read this result is: a small model can be a capable *reasoning layer*, not the
decision-maker. To be trusted, it needs support around it — grounding data, retrieval, tools, or a
human sign-off — and lifting that ceiling is the next piece of work.

A second caveat worth stating plainly: clean output and correct answers are two different things.
Early in this study, a large share of "wrong" answers were really my own parsing code failing to read
a correct answer the model had given in an unexpected format. On small models the glue between the
model and the system can cost as many points as the model's knowledge. The integration is a
first-class part of the system, not an afterthought.

And — to restate the scope from the top, because it is the biggest limit — the edge-deployment claim
is indicative, by footprint. What this study has *not* done is run these models under the real
constraints of edge hardware: tight memory with no spare headroom, sustained thermal load, and the
latency a low-power board actually delivers. The five-seconds-per-question figure is from the 128 GB
development box and would change on a smaller one. So the honest reading is: these models are small
enough and capable enough that edge deployment is worth pursuing — and measuring that deployment on
real hardware is the test that turns "indicative" into "demonstrated."

## What this sets up

The baseline did its job. It settled which model (Nemotron-3 Nano 4B), which setting (low temperature,
reasoning on), where the failure modes are (serving-state endurance), and what the integration has to
carry. Two things build on top of it. First, a scaffolding layer — reference data and retrieval to
ground the model, with the reliability monitoring and periodic reload baked in — to find out how far
past 51.8% a small, on-prem model can be pushed toward something a plant could actually trust. Second,
moving off the development machine and onto genuinely constrained edge hardware, to confirm that
"runs on the edge" holds in latency, memory, and thermal terms and not just on paper.

---

### Methods note (for the technically inclined)

Benchmark: IBM FailureSensorIQ single-answer set, 2,667 questions, 10 assets. Hardware: all runs on a
single 128 GB development machine (NVIDIA DGX Spark, GB10) — edge-deployability in this paper is
inferred from model footprint (2.8–3.3 GB, within an 8 GB envelope), not measured on edge hardware.
Models served via Ollama's native chat API with the context window set explicitly. Every call recorded structured-output
reliability, parse status, finish reason, token counts, sampling settings, and the pinned model
version. Each full run was gated by a short wiring smoke plus a rolling reliability check over the
first 10% of the run. Reasoning models used native thinking (the reasoning trace is returned
separately from the answer). Non-reasoning models were run at a task-mandated low temperature (0.3)
with their vendor-default temperature run separately as a contrast; reasoning models used their
vendor-recommended temperature. Hypotheses here were not pre-registered. Full per-model results,
per-question records, and the degradation analysis are in the experiment folder.
