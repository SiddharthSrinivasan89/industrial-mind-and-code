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

status: In Progress
domain: SUPPLY CHAIN · 4 EXPERIMENTS · GPT-4.1-MINI · O4-MINI · PHI-4-REASONING-PLUS

V1 compared AI configurations against each other. V2 asks a harder question: do AI agents beat simple heuristics at all — and if so, which configuration gets closest and why?

- Ordering fully unconstrained — V1 guardrails removed to observe natural agent behaviour
- Three heuristic baselines set the bar: exponential smoothing (OVAR 0.54), Order-Up-To (OVAR 1.71), naive passthrough (OVAR 1.0)
- Four sub-experiments: lightweight, reasoning, synthesis, and open-source vs proprietary reasoning (Phi-4-reasoning-plus vs o4-mini)
- 25-month demand series spanning two festive cycles · 20 runs per condition

#### What Changed from V1

|Parameter        |V1                                    |V2                                                                                      |
|-----------------|--------------------------------------|----------------------------------------------------------------------------------------|
|Models           |gpt-4.1-mini vs o1                    |gpt-4.1-mini (lightweight) · o4-mini (reasoning) · Phi-4-reasoning-plus (E4 — OSS vs proprietary)|
|Structure        |Single 2×2 run                        |4 sub-experiments: E1 (lightweight), E2 (reasoning), E3 (synthesis), E4 (OSS vs proprietary)|
|Initial inventory|180,000 units                         |43,600 units — derived at runtime from demand series at ~95% service level               |
|Order constraints|Floor 0.2× and ceiling 5× demand      |None — fully unconstrained                                                              |
|Product          |Headlamps, tail lamps, DRLs (multiple)|LED headlight assembly for the Vecta (single)                                           |
|Demand series    |13 months                             |25 months (Jan 2025 – Jan 2027) · two full festive cycles                               |

#### Research Question — Two Layers

**Layer 1 (primary):** Do LLM agents beat simple heuristics on the OVAR–stockout tradeoff? If no, the case for deployment is weak regardless of configuration.

**Layer 2 (conditional on Layer 1):** Among LLM configurations, which gets closest to the optimal balance — and is it driven by context, reasoning capability, or the combination?

|Factor |Levels                                                               |
|-------|---------------------------------------------------------------------|
|Context|Blind (numbers only) vs Context (company, product, supply chain role)|
|Model  |Lightweight (gpt-4.1-mini) vs Reasoning (o4-mini)                    |

#### Scope — Read Before Interpreting Results

Intentionally narrow: single product, fixed 1-month lead times, no supplier disruptions, no unstructured context, no multi-objective tradeoffs. In this class of stable, repetitive replenishment decision, blind heuristics may be strong competitors — that is itself a question this experiment answers. Any finding should be read within this scope and not generalised to supply chain management broadly.

#### Supply Chain & Benchmarks

- Tatva Motors (OEM) → Lighting Manufacturer (Ancillary) → LED Component Manufacturer (Supplier)
- 25-month demand series calibrated to Indian PV market data · 20 runs per LLM condition · 8,640 total LLM calls
- Primary benchmark: exponential smoothing — OVAR 0.54, stockouts 5 (LLMs must beat this on both metrics)
- Secondary diagnostic: Order-Up-To with fixed safety stock — OVAR 1.71, stockouts 14
- Floor reference: naive passthrough — OVAR 1.0, stockouts 3

#### Files

```
Agentic_Bullwhip_Effect_Version_2/
├── Experiment_Parameters/
│   └── experiment_design_v3.md
└── statutory_docs/
```

links:

- Request early access: https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/issues

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