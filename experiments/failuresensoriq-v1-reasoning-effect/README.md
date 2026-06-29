# FailureSensorIQ — Small Language Models for Industrial Fault Diagnosis

A baseline characterisation of four small (4B-class) language models on IBM's **FailureSensorIQ**
benchmark — 2,667 single-answer fault-diagnosis questions across ten industrial asset classes — run
locally via Ollama under an integration-hygiene discipline (accuracy and output reliability scored
separately).

**Headline:** Nemotron-3 Nano 4B reached **51.8%** with clean output on all 2,667 calls — above the
~27.5% guessing floor, below the ~60.2% human-expert mean. A capable local assistant, not an autonomous
decision-maker. Two practical lessons sit outside the ranking: sampling **temperature** and **serving
reliability** decide whether a small model's output is usable at all.

→ **Findings:** [FINDINGS.md](FINDINGS.md) (methodology, results, limitations — all in one place).
→ **Experiment design:** [DESIGN.md](DESIGN.md) (the full design and hypotheses).
→ **Plain-language writeup:** [on the site](https://www.industrialmindandcode.ai/blog/small-language-models-fault-diagnosis.html).

## Repository layout

```
FINDINGS.md      consolidated findings (read this first)
README.md        this file
ihf.py           integration-hygiene scoring (the two-axis scorer + telemetry)
ihf_preflight.py ~20-call wiring check before a full run
run_ihf.py       run the full IHF baseline for one model
run_cold.py      cold (pretraining-only) baseline runner
rescore.py       re-score an existing results JSONL
fetch_data.py    fetch the benchmark into data/raw/
data/            data provenance + placeholder pointers to the IBM source
results/         per-model metric manifests (the scored numbers)
```

## Run it yourself

**Prerequisites**
- [Ollama](https://ollama.com) running locally, and Python 3.12.
- Pull the models you want to test:
  ```bash
  ollama pull nemotron-3-nano:4b
  ollama pull gemma3:4b
  ollama pull phi4-mini
  ollama pull phi4-mini-reasoning
  ```

**1. Get the data.** FailureSensorIQ is IBM's benchmark (Apache-2.0) and is not bundled here. Fetch it
into `data/raw/`:
```bash
python fetch_data.py
```
…or download it manually from [Hugging Face](https://huggingface.co/datasets/ibm-research/FailureSensorIQ)
and place the JSONL files under `data/raw/failuresensoriq_standard/` (see the READMEs there).

**2. Preflight the wiring** (cheap ~20-call check; aborts if structured output or reliability is broken):
```bash
python ihf_preflight.py --model gemma3:4b --num-predict 8192 --temperature 0.3
```

**3. Run the full baseline** for a model (writes a JSONL of per-call records plus a `*.manifest.json`):
```bash
# non-reasoning, deterministic temperature
python run_ihf.py --model gemma3:4b   --num-predict 8192  --temperature 0.3

# reasoning model: enable native thinking, give it a larger output budget
python run_ihf.py --model nemotron-3-nano:4b --num-predict 16384 --think
```
Useful flags: `--asset "industrial gas turbine"` (one asset only), `--n 200` (cap to first N), `--seed`,
`--num-ctx`, `--no-gate` (diagnostic: don't abort on the rolling reliability gate).

**4. Score / re-score** an existing results file:
```bash
python rescore.py results/<your-results>.jsonl
```

The metric manifests under [`results/`](results/) are the scored outputs of these runs. Raw per-call
JSONL outputs are not committed here (they are large); re-running the steps above regenerates them.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
