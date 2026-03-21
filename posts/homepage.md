-----

## page: homepage
title: Industrial Mind & Code

## Hero

eyebrow: Personal AI Research Initiative

# Industrial Mind & Code

Can AI agents operationalise the fundamentals of industrial engineering? I'm finding out — one micro-experiment at a time.

|Label     |Value                                 |
|----------|--------------------------------------|
|Researcher|Siddharth Srinivasan                  |
|Domain    |Industrial Engineering × AI and beyond|

-----

## Why this work exists

AI and LLMs have fundamentally transformed our approach to solving problems. With years of hands-on shop floor experience in Indian manufacturing, combined with a current focus on managing hyperscaler relationships from a techno-strategic point of view, I wanted to explore how these two worlds operate and how AI can add value to the core foundational aspects of Industrial Engineering. This program is how I explore that gap.

The core thesis: how can agentic AI operationalise IE theory? Explored through micro-experiments.

Each experiment takes a foundational IE concept, a supply chain dynamic, a maintenance framework, an inventory model, and turns it into a controlled simulation environment where LLM agents make decisions. This goes beyond model comparisons or benchmarks. It places LLMs into full-blown Industrial Engineering environments. Results are broken down, analysed, and shared with fellow AI researchers and domain peers.

All experiments are personal, use personal compute locally or in the cloud, and involve entirely fictional scenarios.

-----

## Experiments

### Agentic Bullwhip Effect — Version 1

status: Published
domain: SUPPLY CHAIN · 2×2 FACTORIAL · GPT-4.1-MINI vs O1

All four configurations amplified demand variability. Context reduced amplification for the lightweight model — and increased it for the reasoning model. The most capable configuration produced a pattern that classical bullwhip theory would not predict.

- OVAR exceeded 1.0 at every tier in every configuration — no configuration dampened variability
- The context effect reversed sign depending on the model — improvement for lightweight, degradation for reasoning
- context_reasoning produced a fully inverted cascade: OEM was the noisiest node, component the quietest — the opposite of what the classical model predicts

links:

- GitHub: https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/tree/main/agentic_bullwhip_effect_version_1
- Read Post: /blog/agentic-bullwhip-v1.html

-----

### Agentic Bullwhip Effect — Version 2

status: Published
domain: SUPPLY CHAIN · LIGHTWEIGHT · REASONING · FRONTIER · LOCAL

Every heuristic outperformed every LLM configuration. Exponential smoothing achieved OVAR 0.54; the best LLM reached 4.33 — 8× worse, with 8× the stockouts. All seven hypotheses rejected.

- Heuristics vs LLMs is not a tradeoff — LLMs were strictly dominated on both OVAR and stockouts simultaneously in every configuration tested
- Context had opposite effects: marginal improvement for frontier gpt-4.1-mini (Δ=0.23, below threshold), severe degradation for local phi4:14b (4.33 → 6.35, Ancillary tier hitting 10.82)
- Reasoning models showed no ordering advantage over lightweight — more inference spend produced no measurable OVAR improvement
- 11,520 LLM calls · 20 runs per condition · 25-month demand series · two full Indian festive cycles

links:

- GitHub: https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/tree/main/Agentic_Bullwhip_Effect_Version_2
- Read Post: /blog/agentic-bullwhip-v2.html

-----

### Total Productive Maintenance (TPM) Agent — Press Brake Maintenance Records

status: In Progress
domain: TPM / PREDICTIVE MAINTENANCE · FRAGMENTED RECORDS · VERNACULAR NORMALIZATION

Tests whether AI agents can support TPM workflows when reasoning over fragmented, realistic maintenance records, including a condition that simulates a vernacular input normalisation layer upstream.

links:

- Request early access: https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/issues

-----

## How experiments are designed

**01 — Analytical control baselines**
Every experiment pairs LLM agent performance against a non-LLM analytical benchmark, not just model-vs-model. Deviation from theory is the signal.

**02 — Controlled simulation environments**
Synthetic but calibrated parameters derived from public literature. All scenarios are entirely fictional with no proprietary data involved.

**03 — Multi-model comparison**
Experiments compare across model tiers and reasoning architectures, with 50-100 replications per cell to support statistical inference.

**Stack**
Cloud: Azure AI Foundry · Azure OpenAI Service
Local: ASUS Ascent GX10 · Ollama
Code: Claude Code · Codex

-----

## Where I write

Experiment writeups and methodology notes are published on the blog. The first post — Agentic Bullwhip Effect — Version 1 — is live. Code and data for each experiment are on GitHub.

links:
- Blog: /blog/
- First post: /blog/agentic-bullwhip-v1.html
- GitHub: https://github.com/SiddharthSrinivasan89/industrial-mind-and-code

-----

*industrial-mind-and-code · personal research · not affiliated with any employer*

- GitHub: https://github.com/SiddharthSrinivasan89/industrial-mind-and-code
- LinkedIn: https://www.linkedin.com/in/siddharthsrinivasan89