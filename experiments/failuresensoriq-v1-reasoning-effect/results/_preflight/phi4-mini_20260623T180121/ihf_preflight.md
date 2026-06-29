# IHF Preflight — phi4-mini

**Gate:** ✅ PASS — cleared for full run

- Model version (pinned): `78fad5d182a7c33065e`
- Settings: temp `0.8` · top_p `0.95` · top_k `None` · seed `42` · num_ctx `8192` · num_predict `2048`
- Card: `frameworks/models/phi4-mini.md` · calls: `20` · 20260623T180121

| Dimension | Result | Value | Threshold |
|---|---|---|---|
| Structured Output Reliability | PASS | 1.0 (20/20 first-pass) | >= 0.95 |
| API Flag Compliance | PASS | temp=0.8 top_p=0.95 top_k=None empty=0 | flags behaved, no empties |
| Temperature Compliance | PASS | operating=0.8 vs card=0.8 | == provider default |
| Token Budget Compliance | PASS | budget=2048 rec=1024 max=8192 trunc=0 | rec <= budget <= max, no truncation |
| Failure Predictability | PASS | fallback=0.0 (0/20) | <= 0.05 |
