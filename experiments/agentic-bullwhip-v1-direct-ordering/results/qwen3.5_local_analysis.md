# Qwen3.5 Local (Ollama) — Agentic Bullwhip Experiment
**Date:** 2026-03-06
**Model:** `qwen3.5:latest` (9.7B Q4_K_M, via Ollama native API, `think: false`)
**Hardware:** MacBook Pro M1
**Runs:** 1 run per config (blind_lightweight + context_lightweight)
**Context window:** 4096 tokens | `max_tokens`: 2000 | `temperature`: 0.4

---

## Results Summary

| Config | OEM OVAR | Ancillary OVAR | Component OVAR | Stockouts (OEM) | Pattern Score |
|---|---|---|---|---|---|
| blind_lightweight | **4.09** | 2.25 | 1.26 | 13/13 | 0.50 |
| context_lightweight | **2.21** | 3.49 | 4.45 | 7/13 | 0.33 |

---

## Blind Treatment (no calendar/product context)

- **OEM OVAR: 4.09** — strong bullwhip at the first tier
- Order amplification decreases downstream (ancillary 2.25 → component 1.26) — inverse of classic bullwhip pattern
- **13/13 stockout periods** — model severely under-ordered in period 1 (812 units vs 44,624 demand) due to high starting inventory masking true demand
- **Pattern score 0.50**: elevation_score=1.0 (model boosted orders at festival periods Sep-Nov), keyword_score=0.0 (no festival language used — expected, no calendar context given)
- Parse errors: 1 (component tier, period 2 — truncated reasoning string in JSON; recovered via retry)
- Total cost: $0.37 (estimated, local pricing inapplicable — token counts reflect Ollama eval counts)

### OEM Order Sequence (blind)
| Period | Month | OEM Order |
|---|---|---|
| 1 | Dec 2024 | 812 ← severe under-order |
| 2 | Jan 2025 | 46,318 |
| 3 | Feb 2025 | 47,095 |
| 4 | Mar 2025 | 49,287 |
| 5 | Apr 2025 | 44,653 |
| 6 | May 2025 | 39,841 |
| 7 | Jun 2025 | 36,478 |
| 8 | Jul 2025 | 38,193 |
| 9 | Aug 2025 | 40,756 |
| 10 | Sep 2025 | 56,892 ← festive spike |
| 11 | Oct 2025 | 59,608 ← festive spike |
| 12 | Nov 2025 | 55,347 ← festive spike |
| 13 | Dec 2025 | — (no order) |

---

## Context Treatment (with calendar, product, tier context)

- **OEM OVAR: 2.21** — lower than blind at OEM tier (context helps dampen)
- **Bullwhip amplifies downstream**: ancillary 3.49 → component 4.45 — classic bullwhip propagation pattern
- **7/13 stockout periods** — significant improvement over blind (13/13)
- **Pattern score 0.33**: elevation_score=0.67, keyword_score=0.0 — model partially anticipates seasonal peaks when given calendar context but still no explicit festival vocabulary
- Parse errors: 1 (component tier, period 9 — truncated string; recovered)
- Total cost: $0.59 (slightly higher due to longer context prompts)

### OEM Order Sequence (context)
| Period | Month | OEM Order |
|---|---|---|
| 1 | Dec 2024 | 44,624 ← immediate correct fulfillment |
| 2 | Jan 2025 | 48,824 |
| 3 | Feb 2025 | 48,872 |
| 4 | Mar 2025 | 50,479 |
| 5 | Apr 2025 | 40,019 |
| 6 | May 2025 | 35,029 |
| 7 | Jun 2025 | 36,478 |
| 8 | Jul 2025 | 36,545 |
| 9 | Aug 2025 | 43,319 |
| 10 | Sep 2025 | 73,028 ← festive spike |
| 11 | Oct 2025 | 62,324 ← festive spike |
| 12 | Nov 2025 | 51,086 |
| 13 | Dec 2025 | — (no order) |

---

## Key Observations vs Azure GPT-4.1-mini Results

1. **Context treatment helps at OEM** (2.21 vs 4.09 blind) — consistent with Azure results direction
2. **Inverse bullwhip in blind condition**: OVAR decreases downstream (OEM 4.09 → component 1.26), unlike Azure where OVAR typically increases downstream — possibly due to Qwen3.5's more conservative downstream ordering
3. **No keyword pattern recognition**: keyword_score=0.0 in both treatments — Qwen3.5 doesn't use Indian festival terminology even with calendar context, unlike GPT-4.1-mini
4. **Better stockout recovery in context**: 7 vs 13 stockout periods — context significantly helps in first period ordering
5. **Parse reliability**: 1 error per 36 calls (~2.8%) — the long reasoning strings occasionally truncate at 2000 tokens. Acceptable for a local test run
6. **Speed**: ~15 sec/call on M1, total ~17 min for both runs

## Infrastructure Notes
- Used native Ollama `/api/chat` API with `think: false` (OpenAI compat `/v1` endpoint does not reliably disable Qwen3.5 thinking mode)
- `max_tokens: 2000` via Ollama `num_predict` — occasionally truncates long reasoning strings, causing JSON parse errors recovered by retry logic
- `temperature: 0.4` passed via Ollama `options`
- No inter-call delay needed (local, no rate limits)
- Raw results saved to `results/raw/blind_lightweight_run01.json` and `results/raw/context_lightweight_run01.json`

