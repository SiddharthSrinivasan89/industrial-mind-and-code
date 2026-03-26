# Industrial Mind & Code
*Placing a probabilistic system inside a deterministic environment*

Personal research by [Siddharth Srinivasan](https://www.linkedin.com/in/siddharthsrinivasan89). Site: [industrialmindandcode.ai](https://industrialmindandcode.ai)

---

## What this is

What happens when you place a probabilistic system inside a deterministic environment? Industrial Mind & Code runs controlled experiments that put LLM agents into industrial engineering problems — supply chains, maintenance systems, production planning — and measures their performance against analytical baselines.

Each experiment takes a foundational IE problem, builds a simulation, places LLM agents in the decision-making role, and compares the result against what a formula or a heuristic would have done.

Two experiments are published. A third is in progress. All experiments are personal, use personal compute locally or in the cloud, and involve entirely fictional scenarios.

---

## Experiment Index

### Agentic Bullwhip Effect — Version 2
**Status:** Published
**Domain:** Supply Chain · Heuristics vs LLMs · 11,520 LLM calls

Every heuristic outperformed every LLM on both order variance and stockout count simultaneously. Exponential smoothing achieved OVAR 0.54. The best LLM achieved 4.33. Four models tested against three deterministic baselines across 20 runs per condition. All seven pre-registered hypotheses rejected.

- [Experiment folder](./Agentic_Bullwhip_Effect_Version_2/)
- [Read post](https://industrialmindandcode.ai/blog/agentic-bullwhip-v2.html)

---

### Agentic Bullwhip Effect — Version 1
**Status:** Published
**Domain:** Supply Chain · 2×2 Factorial · GPT-4.1-mini vs O1

All four configurations amplified demand variability. Context had opposite effects depending on the model. The context × reasoning condition produced an inverted tier pattern not predicted by classical bullwhip theory.

- [Experiment folder](./agentic_bullwhip_effect_version_1/)
- [Read post](https://industrialmindandcode.ai/blog/agentic-bullwhip-v1.html)

---

### Total Productive Maintenance (TPM) Agent — Press Brake Maintenance Records
**Status:** In Progress
**Domain:** TPM / Predictive Maintenance · Fragmented Records · Vernacular Normalisation

Tests whether LLM agents can reason over maintenance records that reflect how data actually exists in many Indian manufacturing environments — fragmented entries, mixed languages, inconsistent terminology. One experimental condition introduces a vernacular normalisation layer upstream.

---

## Stack

| Layer | Tools |
|---|---|
| Cloud | Azure AI Foundry · Azure OpenAI Service |
| Local | ASUS Ascent GX10 · Ollama |
| Code | Claude Code · Codex |

---

## Methodology

**Analytical baselines, not model comparisons** — Each experiment measures LLM performance against a deterministic analytical method that already exists for the problem — exponential smoothing, order-up-to policies, SPC rules. The question is not which model is better than which. It is whether any model outperforms the established approach.

**Controlled simulation environments** — Parameters are synthetic but grounded in published literature. All scenarios are fictional. No proprietary data is used.

**Statistical design** — Factorial designs with 20–100 replications per cell. Hypotheses are pre-registered. Effect size thresholds are set before the experiment runs.

---

## Disclosure

This is a personal research project.

- All scenarios, supply chain structures, company names, and operational parameters are entirely fictional and constructed for experimental purposes.
- No proprietary, confidential, internal, or employer-owned data of any kind has been used or referenced.
- This research does not represent the views, products, strategies, or endorsements of any employer, client, or affiliated organisation.
- Any resemblance to real companies, products, or operational systems is coincidental and unintentional.
- Data used to calibrate baselines and demand scenarios is either synthetically generated or derived from publicly available sources.
- This project is conducted independently, in personal time, using personal compute resources and publicly available model APIs.

---

## License

Shared for transparency and academic interest.

---

*Industrial Mind & Code — Placing a probabilistic system inside a deterministic environment*

*Personal research. Not affiliated with or endorsed by any employer or organisation.*
