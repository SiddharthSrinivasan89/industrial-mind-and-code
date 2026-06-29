# IHF Preflight — phi4-mini-reasoning

**Gate:** ✅ PASS — cleared for full run

- Model version (pinned): `3ca8c2865ce91b6be85`
- Settings: temp `0.8` · top_p `0.95` · top_k `50` · seed `42` · num_ctx `8192` · num_predict `16384`
- Card: `frameworks/models/phi4-mini-reasoning.md` · calls: `20` · 20260623T180713

| Dimension | Result | Value | Threshold |
|---|---|---|---|
| Structured Output Reliability | PASS | 1.0 (20/20 first-pass) | >= 0.95 |
| API Flag Compliance | PASS | temp=0.8 top_p=0.95 top_k=50 empty=0 | flags behaved, no empties |
| Temperature Compliance | PASS | operating=0.8 vs card=0.8 | == provider default |
| Token Budget Compliance | PASS | budget=16384 rec=8192 max=32768 trunc=0 | rec <= budget <= max, no truncation |
| Failure Predictability | PASS | fallback=0.0 (0/20) | <= 0.05 |
