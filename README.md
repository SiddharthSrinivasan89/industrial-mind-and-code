# Industrial Mind & Code

Industrial Mind & Code is an independent research repository for testing AI — large language
models and small local models — inside industrial engineering decision environments. The core
question is practical rather than benchmark-oriented:

**Can probabilistic AI operate inside deterministic industrial systems without degrading the
system it is placed into — and where exactly does it belong?**

Each experiment places models in a controlled setting, compares them against deterministic and
classical baselines, and reports operational outcomes (variance ratios, stockouts, diagnostic
accuracy, output reliability) rather than text quality. The studies use public, synthetic, or
simulated data; no proprietary data is used. Findings are limited to the tested scope.

The public site is hosted through GitHub Pages at `industrialmindandcode.ai`. GitHub Pages
deploys from `docs/`: the homepage is `docs/index.html`, and experiment writeups live under
`docs/blog/`.

## Research tracks

**1. Supply-chain agents (Agentic Bullwhip series).** Can LLM agents make replenishment
decisions without amplifying demand variance? Eight published experiments traced a full arc:
direct ordering, safety-stock control, and intent classification all amplified variance
regardless of model quality; the first positive result came from changing the interface — the
model selects a bounded smoothing parameter inside an exponential-smoothing formula, and the
formula executes the order.

**2. Maintenance and fault diagnosis.** Can models read industrial evidence — sensor summaries,
error logs, replacement records, engineering questions — and support diagnosis? Two published
experiments so far: a four-model baseline of 4B-class local models on IBM's FailureSensorIQ
benchmark (assistance-level capability; integration settings decide usability), and a
component-attribution study on simulated maintenance telemetry where a trained classifier and a
one-line rule beat every LLM tested.

## Published experiments

| Experiment | Track | Main result |
|---|---|---|
| `agentic-bullwhip-v1-direct-ordering` | Supply chain | All LLM configurations amplified demand variance. |
| `agentic-bullwhip-v2-context-model-interactions` | Supply chain | Every heuristic beat every LLM condition on OVAR and stockouts. |
| `agentic-bullwhip-v2a-sarvam-evaluation` | Supply chain | sarvam-30b showed no meaningful difference from gpt-oss 120B in the tested conditions. |
| `agentic-bullwhip-v3-world-events` / `v3b-hybrid-architecture` | Supply chain | Formula execution helped, but AI-controlled multipliers still amplified variance. |
| `agentic-bullwhip-v4a-intent-classifier` / `v4b-world-events` | Supply chain | Better label accuracy did not lower OVAR; the Equaliser Effect appeared. |
| `agentic-bullwhip-v5-control-architecture` | Supply chain | Perfect oracle labels still failed; the intent-classification lineage closed. |
| `agentic-bullwhip-v6-stateless-swing` | Supply chain | First positive result: every AI condition dampened variance below OVAR 1.0; best condition matched the fixed α=0.3 baseline within uncertainty. |
| `failuresensoriq-v1-reasoning-effect` | Diagnosis | Best 4B local model reached 51.8% on 2,667 questions — assistance, not autonomy; sampling settings and serving health moved results as much as model choice. |
| `pdm-component-attribution-v1-azure` | Diagnosis | On simulated maintenance telemetry, a trained classifier (0.995 macro-F1) and a one-line recent-error rule (0.923) beat every LLM; models reached 0.86–0.91 only when given the training-period history, and never exceeded the rule. |

## Repository layout

```text
.
├── docs/          # GitHub Pages site source (homepage + blog writeups)
├── experiments/   # Reproducible experiment source, data pointers, reports, and results
└── README.md
```

The `experiments/` directory is the source of research truth. Each experiment folder contains
some combination of `README.md`, a design document, a consolidated `FINDINGS.md`, code, data
provenance (raw datasets are linked to their sources, not republished), and result summaries.
The `docs/blog/` HTML files are hand-authored public writeups derived from those artifacts.

## Reproduction entry points

Start with the experiment README for the study you want to inspect — each states
prerequisites, data fetch, run commands, and where results land. Most folders include a
`code/` directory with a runnable entry point; result summaries are stored as JSON under each
experiment's `results/` tree.

## Method, in brief

1. Compare against deterministic and classical baselines — a model result means little without
   the floor it must beat.
2. Measure operational outcomes, not textual quality.
3. Test model placement inside the architecture, separating model capability from control-loop
   or integration design.
4. Prefer repeatable setups, transparent assumptions, and preserved negative results.
5. Verify every claim against the underlying records before it is published.

## Current technical takeaway

The program's strongest finding is architectural. Across both tracks, model quality alone did
not decide outcomes: in replenishment, variance amplification persisted until the interface
changed; in diagnosis, a language model only became competitive once handed the site's
historical statistics — and still did not exceed a simple rule those statistics imply. The
productive question is not "which model is smartest" but "which control surfaces and evidence
inputs let probabilistic reasoning help without destabilizing — or underperforming — the
deterministic system around it."

---

*Independent, self-funded personal research by Siddharth Srinivasan. Views are my own and do
not represent my employer, any model or service provider, or any third party.*
