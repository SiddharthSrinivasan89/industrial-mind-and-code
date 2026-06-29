# FailureSensorIQ V1 — Full Experiment: An Edge LLM as the Diagnosis Layer Above Deterministic Fault Monitoring

**Author:** Siddharth Srinivasan · **Date:** 2026-06-23 · **Status:** full-experiment design — cold rung complete, loose and tool rungs to run.

> This document elevates the earlier "validator" framing into the full experiment. The cold rung (graded test of unaided knowledge) is now the first of three rungs, and the experiment's real question is architectural: where does a deployable small model add value that a deterministic system cannot, and how much scaffolding does it need to get there.

## 1. Why this experiment — the deployment picture

Picture a small industrial computer next to a line of machines, wired into their sensor feeds. Most plants already have a **deterministic fault-monitoring system** on that data: threshold alarms, condition-monitoring rules, FMEA-derived logic, learned anomaly envelopes. These are excellent at **detection** — they fire, instantly and auditably, when a signal crosses a known limit. Where a rule exists, it is right by construction, free to run, and explainable.

So the LLM is **not** competing with that layer at its own job, and it should not be sold as a replacement. The cold result already proves it would lose: a small model knows the verified sensor-to-fault mapping only about 42% of the time, below the ~60% expert mark, and it sometimes invents answers. A rule base that encodes that mapping is right every time.

The LLM's proposed role is the **reasoning and interface layer above** the deterministic one. The value it can add, that a rule system structurally cannot:

1. **Breadth without authoring.** A rule system only knows the faults, sensors, and thresholds someone hand-built into it — a large per-machine SME effort. A model carries much of that mapping from training, for equipment that never got a rule base.
2. **The ambiguous diagnosis step.** Detection is easy; diagnosis is the hard direction — one symptom, many faults (vibration → bearing wear, misalignment, imbalance, looseness, or a blade problem). A threshold raises the alarm; it does not reason through which candidate it is.
3. **Explanation and interface.** A rule outputs a flag or a code. A model turns the alarm plus asset context into plain-language probable cause, a recommended action, and a draft work order — and answers the follow-up "why the bearing?"
4. **Graceful behaviour on the unanticipated.** When a pattern was never programmed, the rule system is silent; the model attempts a reasoned guess (with the real risk of being confidently wrong — which is exactly why it must be measured).

This experiment measures whether a model small enough to deploy on that box can be trusted in that role, and **how much scaffolding it takes** to get there.

## 2. What the model is asked to do

The task is the FailureSensorIQ benchmark (IBM Research, NeurIPS 2025): multiple-choice questions tying sensors to faults on 10 industrial assets, in two directions — given a fault, which sensor reveals it; or given a sensor reading, which fault it points to. The model picks the single best option. The answer is the option marked correct in the benchmark's fixed key, so grading is clean. No live plant data — this is purely whether the model knows and can reason about the sensor-to-fault relationships the way an experienced maintenance engineer would.

## 3. The three rungs — a scaffolding ladder mapped to the architecture

Each model is run three ways. Only the first is the bare model; the other two add scaffolding, and **each rung is scored separately — never folded into the cold number.** The lift between rungs is the central measurement: it tells us how much of the gap to expert is closed by giving the model a knowledge source to reason over.

1. **Cold — the model alone (memory).** Question and options only, no help. Measures unaided knowledge. *This is the LLM-with-no-deterministic-support condition.* **(Complete — see §8.)**
2. **Loose — the model + a plain reference.** We also hand the model a human-readable description of what each monitoring signal on that machine measures, with the faults left out so it cannot read the answer off the page. Measures whether it can **reason from a manual.** *This is the LLM-reasoning-over-provided-documents condition — the value it uniquely brings.*
3. **Tool — the model + a lookup it must call.** Instead of answering from memory, the model calls a retrieval tool, gets back knowledge, and then chooses. Measures whether it can **orchestrate over an external knowledge source** — the role it would play on top of a deterministic system.

**Design constraint on the tool rung (critical).** The tool must return *knowledge the model still has to reason over* — failure-mechanism descriptions, manual passages, what each signal physically measures — **not** the benchmark's relevancy labels. If the tool returned "the relevant sensors for fault F are [...]", the model would copy the answer and the rung would score ~100% while measuring nothing. The tool encodes domain knowledge, not the answer key. This keeps the tool rung a test of reasoning-with-retrieval, not of reading the key.

## 4. Research questions

- **RQ1 — Unaided knowledge (cold).** How much sensor-to-fault knowledge does a deployable edge model hold on its own? *(Answered — §8.)*
- **RQ2 — Reference lift (loose).** How much does a plain machine reference recover, toward the expert mark? This is the clearest proxy for "the model reasoning over documents it was handed."
- **RQ3 — Tool lift / ceiling (tool).** With a retrieval tool over domain knowledge, how close to expert does it get? This is the architecture's core condition: the model as an orchestrator over an external source of truth.
- **RQ4 — Where it fails (all rungs).** Do errors concentrate on the genuinely ambiguous questions — one overloaded symptom pointing to many faults (vibration above all), the same place a deterministic system and a human technician also struggle — or are they spread everywhere? If the model fails mainly on the confusing slice, its knowledge tracks real difficulty; if it fails everywhere, a good headline score is hiding guesswork. **This requires a per-question difficulty label that does not yet exist.** `build_relevance_matrix.py` only summarises strong sensor↔fault links from the positive questions; it is not a saved per-item clear/confusing split, and the SME relevance audit (`relevance_audit_verdicts.jsonl`) shows some keys are themselves ambiguous. So RQ4 is **not answerable until a frozen per-question difficulty label is built** (see §12 gate). It is a planned analysis, not a present result.
- **RQ5 — Reasoning effect at the edge tier.** At the same 8 GB budget, does the reasoning variant beat the plain model, and does the gain land on the confusing questions? (Reported as a side finding.)

## 5. The panel — the edge tier

The models are the ones a plant could realistically run on the box, not a server model:

| Model | Size on disk | Fits | Reasoning |
|---|---|---|---|
| `gemma3:4b` | 3.3 GB | 8 GB box | no |
| `phi4-mini` (3.8B) | 2.5 GB | 8 GB box | no |
| `phi4-mini-reasoning` (3.8B) | 3.2 GB | 8 GB box | yes |

All run on local Ollama (Kratos), `num_ctx=8192` (the questions need a fraction of the 128K window; the full window loaded 28 GB and crawled — capping it dropped that to ~5 GB and sped calls ~5×). Larger server models are a separate, out-of-scope comparison; the whole point here is what fits on the floor.

## 6. Metrics and yardsticks

Every score is placed against four marks: **blind guessing 27.5%** (options vary 2–5, so the floor is above a flat 25%), **always-pick-A 28.2%** (the cheap shortcut), **IBM's published model scores** as an outside check, and the **~60% expert ceiling** from the benchmark's expert study (IBM's figure, not measured here). Beyond accuracy, because this is an edge-deployment question, each run also reports the metrics that decide deployability:

- **Per-rung lift** — cold → loose → tool, the central number.
- **Polarity split** — positive "most relevant" vs negative "least relevant / odd-one-out". The set is negative-heavy (1,744 vs 923), so both must be reported separately; a single blended number is dominated by the negative form.
- **Clear-vs-confusing split** — RQ4, once the frozen difficulty label exists.
- **Unreadable / fallback rate** — must stay under 5%; the parser must read the model's committed answer, not a letter that happens to appear in its explanation (see §8).
- **Latency per call and memory footprint** — an edge box has a time and memory budget; a model that is accurate but takes 60s/call or needs 28 GB is not deployable.

## 7. Reading the result against deterministic monitoring (the analysis spine)

The rung ladder is built to answer the architectural question directly:

- **If cold → tool closes most of the gap to expert**, the finding is that the model's value is **reasoning and interface over a knowledge source, not the knowledge itself.** That validates the architecture: keep the verified mapping deterministic (a rule base or the FMEA), and let the model reason, explain, and orchestrate over it. The model earns its place on breadth, the ambiguous diagnosis step, and explanation — not by memorising the mapping.
- **If even the tool rung underperforms**, the small model is not ready as the reasoning layer: it cannot reliably use a source it is handed, and the job needs a larger model or heavier scaffolding.
- **The clear-vs-confusing split (RQ4)** decides whether the model fails where everyone fails (defensible — it struggles exactly where diagnosis is genuinely ambiguous) or fails everywhere (it is guessing, and the headline flatters it).

This is what makes the experiment more than a leaderboard: it tells you *which layer should own the knowledge* and *what the model is actually for* in a shop-floor stack.

## 8. Cold rung — completed results

Cold is done on the full single-answer set (2,667 questions) for the edge panel. Full writeup in `FINDINGS.md`; the short version:

| Model | Cold accuracy |
|---|---|
| `gemma3:4b` | **42.0%** (1,121/2,667) |
| `phi4-mini` | **37.8%** (1,009/2,667) |
| `phi4-mini-reasoning` | in progress (~41% interim) |

All clear the 27.5% floor by a wide margin but fall well short of expert; both completed models are weakest on the power transformer (electrically complex, specialist signals) and strongest on simple rotating machines. A parser lesson surfaced here and is now baked into the method: a model that commits its answer mid-sentence ("the answer would be D) Current") rather than leading with a letter will be mis-scored unless the parser reads the committed answer — it cost phi4-mini 4.5 points before the fix. Answers are scored from saved raw replies, so scoring can be re-derived without re-running the model.

## 9. Loose rung — design

- **Scaffold:** `sensor_reference.md` — one plain-language line per monitoring signal describing **only what it measures**, faults omitted so no answer leaks. For a question about a given machine, the model sees only that machine's signals.
- **Run:** same frozen question set, same scoring, same edge panel, `num_ctx` sized to fit the reference. A new runner (`run_loose.py`) injects the reference ahead of the question.
- **Prompt gate (required):** print the exact prompt — reference block, then question, then the letter-only instruction — and confirm it adds *measurement descriptions only*, no nudge toward an option, before any run.

## 10. Tool rung — design

- **Tool:** a lookup the model calls with the asset and the fault (or sensor), returning **domain knowledge** — the failure mechanism and what it physically affects, or what each candidate signal measures — drawn from reference/FMEA text, **not** the benchmark's relevancy labels (see §3 constraint). The model reads the returned knowledge and then commits to an option.
- **Run:** same frozen set, same scoring, same panel. Scored separately from cold and loose. Report tool-call success rate (did the model call the tool and use it) alongside accuracy.
- **Honest caveat to record:** the tool rung measures whether the model can *use* a knowledge source, not whether it *knows* the material. That is the intended measurement — it is the orchestration condition — and it must be stated plainly so the tool score is not read as standalone knowledge.

## 11. What "done" looks like

1. The question sample is frozen (done); each rung's prompt is gated and signed off; a frozen per-question difficulty + polarity label set exists (§12); and each run writes a metadata manifest (§12).
2. All three rungs scored for the edge panel, each against the four yardsticks, with fallback under 5%.
3. Per-rung lift reported (cold → loose → tool) — the central result.
4. Polarity split reported for every rung; clear-vs-confusing split reported for at least cold and tool (RQ4), against the frozen difficulty label.
5. Reasoning-vs-plain reported at the 8 GB tier (RQ5).
6. Latency and memory footprint reported per model — the deployability check.
7. The architecture read-out written: which layer should own the knowledge, and what the model adds on top.
8. Every number scoped to the run actually done; no claim beyond it.

## 12. Gates and operating rules

- **Data gate.** Data pulled, checksummed, inspected (`data/PROVENANCE.json`, `data/DATA.md`); frozen sample fixed so every model and rung sees the same questions.
- **Prompt gate.** For every rung, print the exact wording and confirm it states the task and answer format only — no hints, no nudges — before running.
- **Smoke gate.** A handful of questions first per new rung, confirming real, varied answers and sensible timing.
- **Run-metadata gate (required; not yet implemented).** `run_cold.py` currently records only per-question fields (`id/asset/qtype/key/parsed/correct/ms/raw`) — no run-level provenance, and resume skips existing ids without checking compatibility. Before the loose and tool runs, each run must write a metadata manifest beside its results: git commit, the exact prompt text and its hash, the model and its settings (temperature, `num_ctx`, `num_predict`), the frozen sample id, and a UTC timestamp. Resume must verify the manifest matches (same prompt hash, model, settings) before appending, and refuse on mismatch rather than silently blend incompatible records. This will be retrofitted to `run_cold.py` and shared by `run_loose.py`.
- **Difficulty & polarity label gate (required).** Build and freeze a per-question label file — clear/confusing by a stated, signed-off rule, plus positive/negative polarity read from the data — before any RQ4/RQ5 difficulty analysis. The rule is fixed in advance, not improvised at analysis time.
- **Leakage-audit gate (required for loose and tool).** Before scoring an aided rung, audit its injected text — the reference for loose, the retrieved knowledge for tool — and confirm no entry names or implies a fault. The entries already flagged in `sensor_reference.md` (dissolved gas analysis, partial discharge, ultrasound, RF emissions) get explicit sign-off, with the documented caveat that some signal *names* are inherently diagnostic — a property of the benchmark's option labels, not something the reference adds. Record the audited reference / tool transcript with the run so the leak-control claim is checkable.
- **Operating rules.** Retry-with-backoff and per-item checkpointing (resume on crash); everything in `tmux` with `nohup`; a monitor armed for crashes and completion; local models capped at `num_ctx=8192` for speed.

## 13. What this is not

Not a re-run of IBM's full leaderboard, and not a server-model study — the panel is deliberately edge-only. Not a claim that the model replaces deterministic monitoring; the experiment's own framing is that it sits above it. Not a verdict on real-world maintenance performance — the benchmark is a knowledge-and-reasoning test, and the link from scoring well here to doing the real job is the one check this design cannot close on its own (it would need a held-out real task), noted as the known limit.
