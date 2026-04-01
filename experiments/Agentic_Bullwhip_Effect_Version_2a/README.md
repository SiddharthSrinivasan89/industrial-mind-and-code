# Agentic Bullwhip Effect — Version 2a

Version 2a extends V2 by testing **sarvam-30b** on the same supply chain task and demand series. It is **not** a strict ceteris paribus swap: V2a uses local `llama-server`, temperature `1.0`, 10 runs per condition, and context-only main runs because blind conditions were not stable enough to complete a 10-run experiment.

**The question:** Does a model trained on Indian data produce different results on an Indian supply chain task?

**The answer:** Not in the tested context conditions. In the canonical `sarvam_v2d` runs, sarvam-30b reached OVAR `4.504 ± 0.044` (`think=False`) and `4.501 ± 0.093` (`think=True`). The V2 GPT-OSS-120B context reference is `4.52 ± 0.05`. Exponential smoothing still wins by about 8×.

---

## V2 Core Findings (recap)

- No LLM configuration beat exponential smoothing on OVAR or stockouts. Best LLM: OVAR 4.33. Heuristic: OVAR 0.54. Gap is 8×.
- Stockouts were catastrophic under every LLM (50–57% of possible periods). Heuristic: 7%.
- Context helped one model slightly, badly destabilised another. More inference compute (120B vs 14B) bought nothing.
- The failure is structural: stateless agents cannot self-correct drift. This is not a prompting problem.

Full V2 reference results: [../Agentic_Bullwhip_Effect_Version_2/REPORT.md](../Agentic_Bullwhip_Effect_Version_2/REPORT.md)

---

## V2a Setup

| Parameter | Value |
|---|---|
| Model | sarvam-30b Q4_K_M — Sarvam AI, MoE, 2.4B active of 30B total |
| Supply chain | 3-tier: Tatva Motors (OEM) → Ancillary → LED Component |
| Demand series | 25 months, Indian automotive, two festive cycles |
| Conditions | Context only in the main experiment (blind abandoned after repeated instability in smoke/calibration runs) |
| Replications | 10 runs per condition |
| Inference | llama-server (llama.cpp), local, NVIDIA GB10 |
| Temperature | 1.0 (per GGUF model card) |
| Prompt inputs | Tier persona + current month name + demand, on-hand inventory, backlog, inventory position |

---

## V2a Results (sarvam-30b, canonical `sarvam_v2d`)

| Condition | OVAR | Stockouts | Pattern score |
|---|:---:|:---:|:---:|
| E1 context (think=False) | 4.504 ± 0.044 | 39.9 | 0.219 |
| E2 context (think=True) | 4.501 ± 0.093 | 40.5 | 0.232 |
| GPT OSS 120B context (V2 ref) | 4.52 ± 0.05 | 39.6 | 0.21 |
| Exponential smoothing (baseline) | **0.54** | **5** | — |

sarvam-30b shows no practically meaningful difference from the GPT-OSS-120B context reference on this task. Pattern scores remain low in both cases — no seasonal awareness was detected.

Full comparison with V2: [COMPARISON.md](COMPARISON.md)

---

## Run It Yourself

```bash
cd code
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt

# Start from the canonical local config used for V2d
cp .env.sarvam_v2d .env.local
# Edit .env.local if your endpoint, model name, or token limits differ

# Verify (no API calls)
python run_experiment.py --experiments baselines

# Smoke test
python run_experiment.py --experiments E1 --runs 1 --env .env.local

# Full canonical context-only experiment
python run_experiment.py --experiments baselines E1 E2 --conditions context --runs 10 --env .env.local --results-dir ../results/sarvam_v2d
```

Canonical results: `../results/sarvam_v2d/<experiment>/<timestamp>/` — `records.parquet`, `summary.json`, `provenance.json` per run.

> **Note on legacy result folders:** The top-level `results/E1/` and `results/E2/` directories are copied V2-style bundles and are not V2a canonical results. The `results/sarvam/E1/` and `results/sarvam/E2/` directories are earlier V2a runs using the llama.cpp default `top_p=0.95` (superseded by V2d). The canonical V2a dataset is in `results/sarvam_v2d/` only.

---

## Files

| File | What it is |
|---|---|
| [ANALYSIS.md](ANALYSIS.md) | Full V2a analysis — methodology deltas, results, interpretation |
| [DESIGN.md](DESIGN.md) | Experiment design — conditions, metrics, parameter choices |
| [COMPARISON.md](COMPARISON.md) | V2 vs V2a side-by-side results |
| [data/](data/) | 25-month demand series + calibration notes |

---

**Disclaimer:** Personal experiment. Data is synthetic. No employer or vendor data used. Local compute on Asus Ascent GX10 (NVIDIA GB10), personally owned.
