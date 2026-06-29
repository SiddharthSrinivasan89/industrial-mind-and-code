# FailureSensorIQ — Small Language Models for Industrial Fault Diagnosis (baseline)

A baseline characterisation of four small (4B-class) language models on **IBM's FailureSensorIQ**
benchmark — 2,667 single-answer fault-diagnosis questions across ten industrial asset classes — run
locally via Ollama under an integration-hygiene discipline (accuracy and output reliability scored as
separate axes).

**Headline:** Nemotron-3 Nano 4B reached **51.8%** with clean, machine-readable output on all 2,667
calls — above the ~27.5% blind-guessing floor, below the ~60.2% human-expert mean. A capable local
assistant, not an autonomous decision-maker. The two most practical lessons sit outside the ranking:
sampling **temperature** and **serving reliability** often decide whether a small model's output is
usable at all. The full writeup is on the site: [industrialmindandcode.ai](https://www.industrialmindandcode.ai/blog/small-language-models-fault-diagnosis.html).

## What's here

- **Findings:** [WHAT-WE-LEARNED.md](WHAT-WE-LEARNED.md) (the lessons), [POST-STUDY-SLM-INDUSTRIAL-FAULT.md](POST-STUDY-SLM-INDUSTRIAL-FAULT.md) (methodology + report), [RUN1-DEGRADATION-REPORT.md](RUN1-DEGRADATION-REPORT.md) (the serving-runtime failure case), and [DESIGN.md](DESIGN.md) (experiment design).
- **Reproducible assets (code):** the IHF harness and scoring — `ihf.py`, `ihf_preflight.py`, `run_ihf.py`, `run_cold.py`, `rescore.py` — and the data fetcher `fetch_data.py`.
- **Results:** per-model metric manifests (`results_ihf_*.manifest.json`) carry the accuracy and reliability numbers for each run.
- **Data provenance:** [data/DATA.md](data/DATA.md), [data/PROVENANCE.json](data/PROVENANCE.json), and placeholder pointers under `data/raw/` to the IBM source.

## Data

This work uses IBM Research's **FailureSensorIQ** benchmark (Apache-2.0). The raw dataset is **not**
republished here — get it from the source: [Hugging Face](https://huggingface.co/datasets/ibm-research/FailureSensorIQ) ·
[IBM GitHub](https://github.com/IBM/FailureSensorIQ) · [arXiv:2506.03278](https://arxiv.org/abs/2506.03278).
The large raw per-call model outputs are also omitted to keep the repository light; the metric manifests
hold the scored results.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
