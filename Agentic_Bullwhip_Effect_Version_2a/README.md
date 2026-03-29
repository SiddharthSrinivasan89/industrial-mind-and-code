# Agentic Bullwhip Effect — Version 2a

Version 2a is a direct extension of V2. Everything is identical — same supply chain, same demand series, same conditions, same metrics. The only change is the model: sarvam-30b (Sarvam AI) replaces the V2 model stack.

**The question:** Does a model trained on Indian data produce different results on an Indian supply chain task?

**The answer:** No. sarvam-30b OVAR (4.516) matches GPT OSS 120B OVAR (4.523) within noise. The heuristic still wins by 8×.

---

## V2 Core Findings (recap)

- No LLM configuration beat exponential smoothing on OVAR or stockouts. Best LLM: OVAR 4.33. Heuristic: OVAR 0.54. Gap is 8×.
- Stockouts were catastrophic under every LLM (50–57% of possible periods). Heuristic: 7%.
- Context helped one model slightly, badly destabilised another. More inference compute (120B vs 14B) bought nothing.
- The failure is structural: stateless agents cannot self-correct drift. This is not a prompting problem.

Full V2 results: [REPORT.md](REPORT.md)

---

## V2a Setup

| Parameter | Value |
|---|---|
| Model | sarvam-30b Q4_K_M — Sarvam AI, MoE, 2.4B active of 30B total |
| Supply chain | 3-tier: Tatva Motors (OEM) → Ancillary → LED Component |
| Demand series | 25 months, Indian automotive, two festive cycles |
| Conditions | Context only (blind abandoned — 0% run success with minimal prompt) |
| Replications | 10 runs per condition |
| Inference | llama-server (llama.cpp), local, NVIDIA GB10 |
| Temperature | 1.0 (per GGUF model card) |

---

## V2a Results (sarvam-30b)

| Condition | OVAR | Stockouts | Pattern score |
|---|:---:|:---:|:---:|
| E1 context (think=False) | 4.514 ± 0.003 | 40.0 | 0.224 |
| E2 context (think=True) | 4.516 ± 0.004 | 40.0 | 0.222 |
| GPT OSS 120B context (V2 ref) | 4.523 ± 0.078 | 40.1 | 0.216 |
| Exponential smoothing (baseline) | **0.54** | **5** | — |

sarvam-30b matches GPT OSS 120B on OVAR (difference = 0.007, within noise). Pattern scores are identical — no seasonal awareness detected in either model.

Full comparison with V2: [COMPARISON.md](COMPARISON.md)

---

## Run It Yourself

```bash
cd code
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt

# Local backend (llama-server, Ollama, vLLM, LM Studio)
cp env.local.template .env.local
# Edit .env.local — point LOCAL_ENDPOINT at your server

# Verify (no API calls)
python run_experiment.py --experiments baselines

# Smoke test
python run_experiment.py --experiments E1 --runs 1 --env .env.local

# Full experiment
python run_experiment.py --experiments E1 E2 --runs 10 --env .env.local
```

Results: `../results/<experiment>/<timestamp>/` — `records.parquet`, `summary.json`, `provenance.json` per run.

---

## Files

| File | What it is |
|---|---|
| [REPORT.md](REPORT.md) | Full research paper — V2 methodology, results, discussion |
| [DESIGN.md](DESIGN.md) | Experiment design — conditions, metrics, parameter choices |
| [COMPARISON.md](COMPARISON.md) | V2 vs V2a side-by-side results |
| [data/](data/) | 25-month demand series + calibration notes |

---

**Disclaimer:** Personal experiment. Data is synthetic. No employer or vendor data used. Local compute on Asus Ascent GX10 (NVIDIA GB10), personally owned.
