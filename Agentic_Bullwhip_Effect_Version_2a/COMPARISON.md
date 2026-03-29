# V2 vs V2a: Comparison — GPT OSS 120B vs sarvam-30b

**Last updated:** March 2026
**Status:** V2 complete · V2a complete · V2d complete (canonical sarvam-30b dataset)

---

## What Changed

V2a replaces the V2 model stack (phi4:14b + gpt-oss:120b) with sarvam-30b. The model is not the only change — temperature, inference stack, replication count, and blind condition availability all differ. The cross-version comparison is informative but not a strict controlled swap. The question: does India's sovereign model produce different results on an Indian demand series?

| Parameter | V2 | V2a |
|---|---|---|
| Lightweight model | phi4:14b (Microsoft, general) | sarvam-30b (Indian MoE) |
| Reasoning model | gpt-oss:120b (general, 120B) | sarvam-30b (same model, both tiers) |
| Temperature | 0.0 blind / 0.3 context | 1.0 all conditions |
| Inference | Ollama, local | llama-server (llama.cpp), local |
| Replications | 20 per condition | 10 per condition (context only) |
| Blind condition | Run | Not run in main experiment — high per-call error rate made 10-run completion infeasible; individual smoke runs did complete |

---

## Heuristic Baselines (shared)

| Heuristic | Chain OVAR | Stockouts |
|---|:---:|:---:|
| **Exponential smoothing** | **0.54** | **5** |
| Naive passthrough | 1.00 | 3 |
| Order-up-to | 1.71 | 14 |

---

## V2 Results — phi4:14b and gpt-oss:120b (20 runs each)

| Condition | Model | OVAR (mean ± std) | Stockouts | Pattern |
|---|---|:---:|:---:|:---:|
| E1 Blind | phi4:14b | 4.33 ± 0.00 | 41.0 | 0.22 |
| E1 Context | phi4:14b | 6.35 ± 2.53 | 37.2 | 0.23 |
| E2 Blind | gpt-oss:120b | 4.52 ± 0.00 | 40.0 | 0.20 |
| E2 Context | gpt-oss:120b | 4.52 ± 0.05 | 39.6 | 0.21 |

**Tier breakdown (OVAR):**

| Condition | OEM | Ancillary | Component |
|---|:---:|:---:|:---:|
| Exp smoothing | 0.41 | 0.65 | 0.58 |
| E1 Blind (phi4:14b) | 3.71 | 5.89 | 3.40 |
| E1 Context (phi4:14b) | 4.62 | **10.82** | 3.61 |
| E2 Blind (gpt-oss:120b) | 4.13 | 5.98 | 3.45 |
| E2 Context (gpt-oss:120b) | 4.13 | 6.01 | 3.43 |

---

## V2a Results — sarvam-30b (10 runs, context only)

*Note: blind condition not run in main experiment. Pre-experiment smoke tests showed ~20% per-call error rates with minimal prompts, making 10-run blind completion infeasible. Individual smoke runs did complete (1/3 E1 blind; 1/1 E2 blind at temp=1.0), but a subsequent calibration pass produced 0/3 before being stopped. Context conditions were used for all main runs.*

| Condition | Model | OVAR (mean ± std) | Stockouts | Pattern |
|---|---|:---:|:---:|:---:|
| E1 Context (think=False) | sarvam-30b | 4.514 ± 0.003 | 40.0 | 0.224 |
| E2 Context (think=True) | sarvam-30b | 4.516 ± 0.004 | 40.0 | 0.222 |

**V2d — sarvam-30b, top_p=1.0 (complete):**

| Condition | OVAR (mean ± std) | Stockouts | Pattern | Replacements |
|---|:---:|:---:|:---:|:---:|
| E1 Context (think=False) | 4.504 ± 0.044 | 39.9 | 0.219 | 15/25 attempts |
| E2 Context (think=True) | 4.501 ± 0.093 | 40.5 | 0.232 | 0/10 attempts |

---

## Direct Comparison — Best V2 vs V2d (context_reasoning, canonical)

*sarvam-30b figures from V2d (top_p=1.0, documented GGUF settings). V2d supersedes the earlier V2a baseline (top_p=0.95 implicit); results are numerically identical within noise.*

| Model | OVAR | Stockouts | Pattern | Notes |
|---|:---:|:---:|:---:|---|
| gpt-oss:120b (V2) | 4.52 ± 0.05 | 39.6 | 0.21 | General purpose, 120B |
| sarvam-30b (V2d) | 4.501 ± 0.093 | 40.5 | 0.232 | India's sovereign MoE, 30B total / 2.4B active |
| Exp smoothing | **0.54** | **5** | — | Wins by 8× |

**Finding:** sarvam-30b and gpt-oss:120b produce statistically identical results (OVAR difference = 0.019, well within noise). India's sovereign model does not produce meaningfully different ordering behaviour on this task. Neither model approaches the heuristic baseline.

**V2d note:** Correcting top_p from the llama.cpp default (0.95) to the documented value (1.0) produced no meaningful change — OVAR 4.504 vs 4.514 in E1, 4.501 vs 4.516 in E2. The documented settings reproduce results faithfully.
