# IHF Preflight — gemma3:4b

**Gate:** ✅ PASS — cleared for full run

- Model version (pinned): `a2af6cc3eb7fa8be850`
- Settings: temp `1.0` · top_p `0.95` · top_k `64` · seed `42` · num_ctx `8192` · num_predict `2048`
- Card: `frameworks/models/gemma3-4b.md` · calls: `20` · 20260623T175957

| Dimension | Result | Value | Threshold |
|---|---|---|---|
| Structured Output Reliability | PASS | 1.0 (20/20 first-pass) | >= 0.95 |
| API Flag Compliance | PASS | temp=1.0 top_p=0.95 top_k=64 empty=0 | flags behaved, no empties |
| Temperature Compliance | PASS | operating=1.0 vs card=1.0 | == provider default |
| Token Budget Compliance | PASS | budget=2048 rec=1024 max=8192 trunc=0 | rec <= budget <= max, no truncation |
| Failure Predictability | PASS | fallback=0.0 (0/20) | <= 0.05 |
