# Post-Study: Small Language Models on an Industrial Fault-Diagnosis Dataset

**Author:** Siddharth Srinivasan
**Date:** 2026-06-24
**Target use case:** an edge-deployed model on a shop-floor box (no cloud) that reads the sensor
feed and acts as the fault-reasoning layer over an existing monitoring system.

This is a baseline capability study. The goal was not to ship a product but to characterise what a
small, edge-deployable model can do on industrial fault diagnosis — and to run every model under an
integration-hygiene discipline, so the result reports both task quality and deployment reliability.
The actual use case is designed on top of what this study establishes.

---

## 1. The data

**Dataset:** IBM FailureSensorIQ (NeurIPS 2025, arXiv:2506.03278). A benchmark that tests whether a
model understands the relationship between sensor readings and failure modes across industrial
equipment.

- **2,667 single-answer multiple-choice questions** (the single-answer rung used throughout this study).
- **10 industrial assets:** industrial gas turbine, aero gas turbine, steam turbine, power
  transformer, electric generator, electric motor, pump, compressor, fan, reciprocating internal
  combustion engine.
- Each question gives a sensor or failure-mode situation and asks for the single best option from a
  labelled set (A, B, C, …).
- **Question types** include positive framing ("which sensor is most pertinent") and negative
  framing ("which is *not* pertinent") — the negative-polarity items are harder.

**Reference points (from the benchmark):**

| Baseline | Score | Meaning |
|---|---|---|
| Blind guessing | ~27.5% | random choice across options |
| Always answer "A" | ~28.2% | degenerate constant-answer baseline |
| Human expert (mean) | ~60.2% | reported expert mean accuracy |
| Human expert (best) | ~66.2% | reported best single expert |

These anchor every result below: above ~28% means the model has learned real sensor-to-fault
structure; mean expert performance is ~60%, and the best expert reached ~66% — that band, not a
single number, is the practical target.

---

## 2. Methodology

### 2.1 Models

Edge-deployable small language models that fit an 8 GB box (the target hardware), all served locally
through Ollama:

| Model | Type | Params | Disk | Architecture |
|---|---|---|---|---|
| gemma3:4b | non-reasoning instruct | 4.3B dense | 3.3 GB | Transformer |
| phi4-mini | non-reasoning instruct | 3.8B dense | 2.5 GB | Transformer |
| phi4-mini-reasoning | reasoning | 3.8B dense | 3.2 GB | Transformer |
| nemotron-3-nano:4b | reasoning (unified) | 4.0B | 2.8 GB | Nemotron-H (Mamba-2 + Transformer hybrid) |

### 2.2 Integration Hygiene Framework (IHF)

Every run was treated as a deployment, not just a benchmark. Each call recorded telemetry —
structured-output reliability, parse status, finish reason, token counts, sampling settings, and the
pinned model version — and each model was gated before its full run. The five frozen IHF dimensions:

- **SOR — Structured Output Reliability:** fraction of calls returning a parseable answer (target ≥ 0.95).
- **AFC — API Flag Compliance:** the flags sent (e.g. native `think`) match the model's contract.
- **TCA — Temperature Compliance:** the temperature run matches the task-mandated setting.
- **TBC — Token Budget Compliance:** output budget large enough to avoid truncating the answer.
- **FP — Failure Predictability:** fallback rate stays low and bounded (target ≤ 0.05).

Plus **Step 0 — version pinning:** the exact model digest is recorded so a run reproduces.

A two-stage gate is available: a short smoke (~12–20 calls) to confirm wiring, then a **rolling gate**
evaluated over the first 10% of the run (clamped 50–250 calls, seeded shuffle so the sample is
representative across assets). If structured-output reliability or fallback rate breaches threshold,
the run aborts rather than burning hours on off-spec wiring.

The gate was not applied uniformly across this study's runs, and the manifests record which mode each
used:

- **Rolling-gated final runs** (`rolling_gate` present in the manifest): the task-mandated
  temperature-0.3 comparison runs for gemma3:4b and phi4-mini, and the nemotron-3-nano:4b run. These
  are the canonical comparison runs.
- **Default-temperature contrast runs** (gemma 1.0, phi4-mini 0.8): preflight/telemetry-only, run
  without the rolling gate, used to measure the temperature effect against the gated 0.3 runs.
- **No-gate diagnostic** (phi4-mini-reasoning gas-turbine set): run deliberately with `--no-gate` so
  the degradation could be observed to completion rather than aborted at the gate.

All runs, gated or not, carry the full per-call IHF telemetry.

### 2.3 Sampling settings — provider defaults, never temperature 0

`top_p`, `top_k`, and the reasoning-model temperatures are **provider-recommended defaults** read
from each model card. The temperature for the non-reasoning models is the one deliberate **override**:
the task is deterministic (one right answer), so the ICAF temperature regime mandates a low
temperature (0.3) for them. Each non-reasoning model was therefore run twice — once at the
task-mandated 0.3 (the canonical comparison run) and once at its provider-default temperature (gemma
1.0, phi4-mini 0.8) as a contrast. Reasoning models keep their provider-default temperature, since
they cannot use a very low value without looping. Settings actually used (verified from the run
manifests):

| Model | Temperature | top_p | Reasoning | Output budget (num_predict / num_ctx) |
|---|---|---|---|---|
| gemma3:4b | **0.3** (task-mandated); 1.0 contrast | 0.95 | — | 2048 / 8192 |
| phi4-mini | **0.3** (task-mandated); 0.8 contrast | 0.95 | — | 2048 / 8192 |
| phi4-mini-reasoning | 0.3 / 0.8 (provider) | 0.95 | on (emits `<think>`) | 16384 / 8192 |
| nemotron-3-nano:4b | 0.6 (provider) | 0.95 | on (native `think` flag) | 16384 / 32768 |

### 2.4 Serving and parsing

- Calls went through Ollama's native `/api/chat`. `num_ctx` was set explicitly (8K–32K) — leaving
  the default 128K–256K window loads tens of GB and runs ~5× slower for no benefit.
- For native-thinking models (nemotron), `think: true` is set at the top level of the payload;
  Ollama then returns the reasoning trace in a separate `message.thinking` field and a clean final
  answer in `message.content`, so the answer parser never has to strip a reasoning block.
- The answer parser handles four output styles: a leading option letter (plain instruct), a
  `\boxed{X}` form (math-reasoning models), a committed "X)" after an answer word, and an
  "answer is X" fallback — stripping any `<think>` block first. This matters: on small models, a
  parser that only reads the leading letter loses real points to formatting, not knowledge.

---

## 3. Per-model report

### 3.1 Gemma 3 4B — the robust non-reasoning baseline

| Setting | Accuracy | SOR | Fallback | Truncated |
|---|---|---|---|---|
| temp 0.3 | **42.1%** (1,124/2,667) | 1.000 | 0.0% | 0 |
| temp 1.0 (default) | 41.9% | 1.000 | 0.0% | 0 |

Gemma returned clean, parseable output on every one of 2,667 calls at both temperatures, and its
accuracy barely moved between them (42.1% vs 41.9%). That temperature-insensitivity is its own form
of robustness — a model that does not wobble when the knob changes is easy to commission and trust.
It set the bar to beat: well above guessing, clean, stable, fits an 8 GB box. Its limitation is the
ceiling — 42% is roughly 18 points short of an expert.

### 3.2 Phi-4-mini — temperature sensitivity, demonstrated

| Setting | Accuracy | SOR | Fallback | Truncated |
|---|---|---|---|---|
| temp 0.3 | 36.6% (977/2,667) | 0.951 | 4.9% | 3 |
| temp 0.8 (default) | 30.7% | 0.933 | 6.7% | 4 |

Phi-4-mini is the clearest demonstration of the temperature rule. At its vendor default of 0.8 it
scored 30.7% and breached the reliability bar (6.7% fallback). Moved to the task-correct 0.3, it
recovered six points to 36.6% and cleared the fallback threshold — same model, same weights, only the
temperature changed. Note the token-budget dimension: even at 0.3 it produced 3 truncated calls
(finish reason = length) out of 2,667 — a small but non-zero TBC signal, where gemma and nemotron had
none. It trails gemma throughout, but it proved the principle: for a one-right-answer task, match
the temperature to the task, not the vendor's generation default.

### 3.3 Phi-4-mini-reasoning — the wrong tool, two ways over

Phi-4-mini-reasoning never produced a clean full-set result.

- At its default temperature 0.8 the full run **broke** — no usable score.
- At the task-ideal 0.3, a focused 240-question diagnostic on the industrial gas turbine asset scored
  **29.6%** with a **40% fallback rate** (SOR 0.600) — barely above guessing, because two of every
  five answers came back unusable.

The failure had two distinct causes. First, there is no good temperature: at 0 it loops and never
finishes; at high temperature it is unstable. Second, and more important, it **degraded over the
run** — clean for the first ~120 sequential calls, then collapsing into degenerate token salad and
wrong-task hallucination for the remainder. That collapse was isolated to the serving runtime, not
the model: input was identical across the cliff, difficulty did not predict failure, and six
questions that produced garbage late in the run all answered cleanly when re-sent to a freshly loaded
model. The cause is cumulative serving-state degradation — most plausibly the KV cache, the
runtime's reusable attention memory, which a long-reasoning Transformer churns hard. (Full analysis:
`RUN1-DEGRADATION-REPORT.md`.)

### 3.4 Nemotron-3 Nano 4B — the top result

| Metric | Value |
|---|---|
| Accuracy | **51.8%** (1,382/2,667) |
| SOR | 1.000 |
| Fallback / Truncated / Empty | 0 / 0 / 0 |
| Latency | 5.3 s/call |
| Reasoning | on (native `think`), avg ~1,700-char chain of thought per question |

Nemotron-3 Nano is a unified reasoning model on the Nemotron-H hybrid backbone (mostly Mamba-2
state-space layers with a few Transformer attention layers). Run with reasoning on at NVIDIA's
recommended settings (temperature 0.6), it scored **51.8%** — about 10 points above gemma and roughly
halfway between gemma and the ~60% expert ceiling. It returned a clean, parseable answer on every one
of 2,667 calls.

Two properties stand out. First, **endurance** (observed): fallbacks by run-position decile were
**0 in all ten deciles** — perfectly clean from question 1 to 2,667, where the pure-Transformer
reasoning model collapsed after ~120. That endurance *difference* is a measured fact. The *reason* is
a hypothesis, not yet confirmed: the hybrid carries a fixed-size recurrent state in most layers rather
than a growing KV cache, so there is plausibly far less of the fragile, growing serving state that
corrupted on the Transformer model — but the two runs differ in model *and* architecture at once, so
this study cannot isolate the architecture as the cause. The controlled tests that would (re-order
run, periodic reload) are noted in `RUN1-DEGRADATION-REPORT.md` and have not been run. Second, **it
wins on the hard asset**: the industrial gas turbine — which produced
80% garbage on phi4-mini-reasoning and which the other models found hardest — was its *best* asset at
71%.

Per-asset accuracy (nemotron-3-nano:4b, all assets clean, zero fallback):

| Asset | Accuracy | | Asset | Accuracy |
|---|---|---|---|---|
| Industrial gas turbine | 71% (171/240) | | Electric generator | 51% (119/234) |
| Fan | 60% (119/200) | | Aero gas turbine | 48% (162/336) |
| Recip. internal combustion engine | 57% (193/336) | | Compressor | 45% (100/220) |
| Pump | 55% (84/152) | | Power transformer | 43% (236/544) |
| Electric motor | 55% (128/234) | | Steam turbine | 41% (70/171) |

---

## 4. Cross-model comparison

Full 2,667-question single-answer set, each model at its task-appropriate setting:

| Model | Type | Accuracy | SOR | Clean full run? |
|---|---|---|---|---|
| **nemotron-3-nano:4b** | reasoning (Mamba-hybrid) | **51.8%** | 1.000 | yes |
| gemma3:4b | non-reasoning | 42.1% | 1.000 | yes |
| phi4-mini | non-reasoning | 36.6% | 0.951 | yes |
| phi4-mini-reasoning | reasoning (Transformer) | — | 0.600* | no — degraded |

\* phi4-mini-reasoning figure is the gas-turbine diagnostic (n=240); it never produced a clean
full-set run.

---

## 5. Findings

**1. A small reasoning model can beat the non-reasoning baseline — but reasoning models differ sharply
in whether they survive a long run.** Nemotron-3 Nano (51.8%) beat gemma (42.1%) by ~10 points and ran
perfectly clean across 2,667 sequential calls. Phi-4-mini-reasoning, also a 4B reasoning model,
*degraded into garbage* after ~120 calls. That endurance gap is the observed fact. The likely
explanation is architectural — the Mamba-hybrid carries a fixed-size state in most layers rather than
the growing KV cache that aged and corrupted on the pure-Transformer model — but the two models differ
in more than architecture, and the controlled endurance tests to confirm the mechanism have not been
run, so this is a hypothesis. Either way the practical lesson holds: choosing a reasoning model is not
enough; its endurance under a long edge duty cycle must be tested, not assumed.

**2. For a deterministic task, match the temperature to the task, not the vendor default.**
Phi-4-mini gained six points (30.7% → 36.6%) purely by moving from its 0.8 default to the
task-correct 0.3. Low temperature (0–0.3) is the right home for one-right-answer industrial work.
Reasoning models are the exception — they cannot use temperature 0 — which is itself an argument for
preferring a non-reasoning model where strict determinism is required.

**3. Degradation under load is a serving (runtime) problem, not a model-knowledge problem.** The
phi4-mini-reasoning collapse was confirmed by a fresh-load test: the same questions that produced
garbage late in a run answered cleanly on a freshly loaded model. The fix is operational — monitor
output reliability continuously and reload the model periodically — and it is the runtime's
responsibility, not the model maker's. Commissioning must certify a model over a duty cycle, not just
at a point in time.

**4. Clean output and a correct answer are two different axes.** Every model here was scored on both
structured-output reliability (is it wired right?) and accuracy (is it right?). A large share of early
"wrong" answers were actually a parser failing to read a correctly given answer in an unexpected
format. On small models the integration layer — the glue that parses output — can cost as many points
as the model's knowledge, and must be engineered as a first-class part of the system.

**5. Even the best small model is a reasoning *layer*, not an unsupervised decision-maker.** 51.8% is
a real lift and the strongest result on this panel, but it is still roughly 8 points below an expert
and far from reliable enough to make a high-stakes maintenance call alone — it sits ~8 points below
mean expert performance (~60%) and ~14 below the best expert (~66%). The deployed use case needs a
scaffolding layer above the model — reference data, retrieval, or tools — or a human sign-off on the
decision.

**6. Capability varies sharply by asset; commission per asset.** Within one model, accuracy ranged
from 41% (steam turbine) to 71% (industrial gas turbine). A single headline number hides this. The
deployed system should validate and commission per asset, and consider narrowing to the assets where
the model is already strong.

**7. The deployable pick from this study:** `nemotron-3-nano:4b`, reasoning on, at provider settings —
top accuracy, perfectly clean output, endurance-safe over a long run, 2.8 GB on an 8 GB edge box,
5.3 s/call, with a full chain of thought saved per question for audit. Gemma3:4b remains a strong,
stable non-reasoning fallback. Phi-4-mini-reasoning is excluded for this task on both temperature and
endurance grounds.

---

## 6. Reproducibility

- Dataset: IBM FailureSensorIQ single-answer set, 2,667 questions.
- Each run carries a manifest: pinned model digest, exact sampling settings, prompt fingerprint, git
  commit, per-call IHF telemetry, and the rolling-gate result.
- Result files: `results_ihf_<model>*.jsonl` with per-question record (answer, correctness, parse
  status, finish reason, token counts; chain of thought for nemotron).
- Settings are read from machine-readable provider-default blocks in `frameworks/models/<model>.md`.
- Runner: `run_ihf.py`; plumbing and parser: `ihf.py`; preflight gate: `ihf_preflight.py`.
