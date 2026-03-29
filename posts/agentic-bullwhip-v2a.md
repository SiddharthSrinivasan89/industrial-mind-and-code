---
title: "Agentic Bullwhip Effect: sarvam-30b"
date: March 2026
domain: SUPPLY CHAIN · SOVEREIGN MODEL · EXPERIMENT WRITEUP
summary: India's sovereign model performed as well as GPT OSS on a synthetic Indian automotive dataset. I expected it would have more India-specific capabilities. OVAR 4.50 vs 4.52, identical pattern scores, identical stockout counts.
experiment: Agentic Bullwhip Effect Version 2a — sarvam-30b
slug: agentic-bullwhip-v2a
---

## Abstract

Version 2 showed that no LLM configuration could beat a 1970s smoothing formula on supply chain order variance or stockouts. This experiment asked a follow-up question: would a model trained on Indian data show stronger seasonal awareness on an Indian automotive demand series?

I tested sarvam-30b (India's sovereign model, 30B total parameters, 2.4B active) against GPT OSS 120B as a reference. The supply chain task was identical to Version 2. The demand series was calibrated to real Indian PV market seasonality — festive peaks, monsoon troughs, fiscal year-end patterns.

The answer: no meaningful difference in task performance. sarvam-30b OVAR 4.504 vs GPT OSS 120B OVAR 4.52 — statistically identical on every metric. Neither model detected Indian seasonal demand patterns. The exponential smoothing baseline (OVAR 0.54) won by roughly 8x.

One finding did emerge from the integration work: enabling sarvam-30b's native reasoning flag (think=True) eliminated all run-level failures and had no effect on supply chain outcomes.

Full experiment: [github.com/SiddharthSrinivasan89/industrial-mind-and-code/tree/main/Agentic_Bullwhip_Effect_Version_2a](https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/tree/main/Agentic_Bullwhip_Effect_Version_2a)

---

## Experiment Setup

| Field | Value | Notes |
|---|---|---|
| Model | sarvam-30b Q4_K_M (Sarvam AI · MoE · 2.4B active of 30B) | Indian sovereign model |
| Reference | gpt-oss:120B | V2 results for comparison |
| Conditions | E1: context, think=False · E2: context, think=True | Blind condition not run — see below |
| Replications | 10 runs per condition (V2d canonical) | V2d = top_p=1.0 per GGUF card |
| Primary metrics | Chain OVAR · Stockout count · Pattern score | |
| Supply chain | 3-tier serial: OEM → Ancillary → Component | Tatva Motors Vecta (fictional) |
| Demand series | 25 months (Jan 2025–Jan 2027) · single SKU · two Indian festive cycles | Calibrated to real PV market data |
| Lead time | 1 month deterministic at all tiers | |
| Initial inventory | ~43,600 units (mean + 1.65σ) | |
| Agent design | Stateless, no memory between periods | |
| Temperature | 1.0 all conditions | Mandated by GGUF model card |
| Inference | llama-server (llama.cpp), local, NVIDIA GB10 Blackwell | |

**Blind condition:** Not run in main experiment. Pre-experiment calibration showed ~20% per-call error rates with minimal prompts, making 10-run completion infeasible. Individual smoke runs did complete (1/3 E1 blind, 1/1 E2 blind). A subsequent calibration pass produced 0/3 before being stopped. Context conditions only were used for main runs.

OVAR interpretation: below 1.0 = dampening · 1.0 = pass-through · above 1.0 = bullwhip amplification.

---

## Key Findings

**01. Task performance was identical across models.**
sarvam-30b chain OVAR 4.504 ± 0.044 (E1) and 4.501 ± 0.093 (E2). GPT OSS 120B achieved 4.52 ± 0.05. Difference is well within noise. Neither model approached the exponential smoothing baseline (OVAR 0.54). India's sovereign model did not produce measurably different ordering behaviour on this task, despite being trained on Indian data and the demand series being calibrated to Indian market patterns.

**02. Neither model detected Indian seasonal demand patterns.**
Pattern scores: sarvam-30b 0.219–0.232, GPT OSS 120B 0.21. All identical within noise. Both models received only calendar month names in the user message — no event labels, no seasonal background. Any seasonal reasoning would have to come from the model's world knowledge. Neither model showed it. The festive peaks (Navratri, Diwali) and monsoon troughs in the demand series went unrecognised by both models.

**03. Enabling think=True eliminated run-level failures without changing outcomes.**
E1 (think=False): 15 of 25 run attempts needed replacement. E2 (think=True): 0 of 10 attempts needed replacement. Chain OVAR difference between conditions: 0.003. The reasoning flag changed integration reliability substantially; it had no effect on what the model ordered. This is a reproducible, model-specific finding — not a general property of reasoning models.

**04. The structural constraint holds.**
LLMs are stateless — they cannot self-correct drift across periods. No amount of cultural training, prompt enrichment, or model size changes this on a period-by-period ordering task. The bullwhip failure is architectural.

---

## Results

### Heuristic Baselines

| Heuristic | Chain OVAR | Stockouts (of 75) |
|---|:---:|:---:|
| **Exponential smoothing** | **0.54** | **5** |
| Naive passthrough | 1.00 | 3 |
| Order-up-to | 1.71 | 14 |

### V2 Reference — phi4:14b and gpt-oss:120b

| Condition | Model | Chain OVAR | Stockouts | Pattern |
|---|---|:---:|:---:|:---:|
| E1 Blind | phi4:14b | 4.33 ± 0.00 | 41.0 | 0.22 |
| E1 Context | phi4:14b | 6.35 ± 2.53 | 37.2 | 0.23 |
| E2 Blind | gpt-oss:120b | 4.52 ± 0.00 | 40.0 | 0.20 |
| E2 Context | gpt-oss:120b | 4.52 ± 0.05 | 39.6 | 0.21 |

### sarvam-30b — V2d Canonical (top_p=1.0, context conditions only)

| Condition | Chain OVAR | Stockouts | Pattern | Run replacements |
|---|:---:|:---:|:---:|:---:|
| E1 Context (think=False) | 4.504 ± 0.044 | 39.9 | 0.219 | 15/25 attempts |
| E2 Context (think=True) | 4.501 ± 0.093 | 40.5 | 0.232 | 0/10 attempts |

V2d note: correcting top_p from the llama.cpp default (0.95) to the documented value (1.0) produced no meaningful change — OVAR difference within noise. The documented settings reproduce results faithfully.

---

## Integration Issues — sarvam-30b

Two model-specific issues required resolution before stable runs were possible. Both are reproducible and specific to the local GGUF deployment of sarvam-30b via llama-server.

| Issue | What happened | Fix |
|---|---|---|
| API flag + prompt conflict | think=False API flag conflicts with "Think silently" instruction in system prompt. Model receives contradictory instructions about whether to use internal reasoning. | Remove "Think silently" from system prompt when using think=False flag. |
| Blind condition structural failure | Minimal prompts (no context, no persona) produced ~20% per-call error rates. 10-run completion was infeasible. Individual smoke runs did complete but a subsequent calibration pass produced 0/3 successes. | Not resolved — context conditions used for all main runs. |

GPT OSS 120B triggered neither issue across 20 runs.

The broader finding from integration work: sarvam-30b is available as a cloud API and as a local GGUF. The two documentation sources give different temperature recommendations. Cloud docs: 0.2 (non-thinking). GGUF model card: 1.0 (reasoning). Running the experiment confirmed the GGUF card is correct for local inference — cloud recommendations cause 40-60% call failures on local GGUF deployment. This is documented in the pre-experiment calibration notes.

---

## Relation to Integration Hygiene Framework

This experiment contributes the first sarvam-30b data point to the Integration Hygiene Framework (IHF) — a research framework for measuring how reliably a model can be integrated, independently of benchmark scores. The think=True vs think=False reliability finding (Finding 03) and the blind condition structural failure are IHF findings, not supply chain findings. The IHF research lives at [research/model-integration-hygiene/](https://github.com/SiddharthSrinivasan89/industrial-mind-and-code-dev/tree/main/research/model-integration-hygiene).

---

## Scope and Limitations

- Context conditions only. Blind results not available for sarvam-30b.
- 10 runs per condition. V2 used 20 runs; the confidence intervals are wider here.
- Single product, single supply chain structure, fixed lead times.
- Stateless agents only — no memory, no coordination between tiers.
- Integration findings (think=True reliability, blind failure) are specific to local GGUF deployment via llama-server. Cloud API deployment is a different integration surface.
- Results should not be generalised to supply chain management broadly.

All companies, products, and supply chain structures are fictional. The demand series is calibrated to real Indian PV market data (autopunditz.com, CY2023–CY2025) but is synthetic.

---

## Experiment Source

Full technical report, code, and data (public repo):
[github.com/SiddharthSrinivasan89/industrial-mind-and-code/tree/main/Agentic_Bullwhip_Effect_Version_2a](https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/tree/main/Agentic_Bullwhip_Effect_Version_2a)

- [ANALYSIS.md](https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/blob/main/Agentic_Bullwhip_Effect_Version_2a/ANALYSIS.md) — full findings and metric definitions
- [DESIGN.md](https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/blob/main/Agentic_Bullwhip_Effect_Version_2a/DESIGN.md) — experiment design
- [COMPARISON.md](https://github.com/SiddharthSrinivasan89/industrial-mind-and-code/blob/main/Agentic_Bullwhip_Effect_Version_2a/COMPARISON.md) — V2 vs V2a cross-version comparison
