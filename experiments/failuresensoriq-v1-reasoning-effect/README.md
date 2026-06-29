# FailureSensorIQ — Small Language Models for Industrial Fault Diagnosis (baseline)

A baseline characterisation of four small (4B-class) language models on **IBM's FailureSensorIQ**
benchmark — 2,667 single-answer fault-diagnosis questions across ten industrial asset classes — run
locally via Ollama under an integration-hygiene discipline (accuracy and output reliability scored as
separate axes).

**Headline:** Nemotron-3 Nano 4B reached **51.8%** with clean, machine-readable output on all 2,667
calls — above the ~27.5% blind-guessing floor, below the ~60.2% human-expert mean. A capable local
assistant, not an autonomous decision-maker. The two most practical lessons sit outside the ranking:
sampling **temperature** and **serving reliability** often decide whether a small model's output is
usable at all.

## What's here

- **Writeups:** [WHAT-WE-LEARNED.md](WHAT-WE-LEARNED.md) (the lessons), [POST-STUDY-SLM-INDUSTRIAL-FAULT.md](POST-STUDY-SLM-INDUSTRIAL-FAULT.md), [DESIGN.md](DESIGN.md), [PAPER.md](PAPER.md), [RUN1-DEGRADATION-REPORT.md](RUN1-DEGRADATION-REPORT.md) (the serving-runtime failure case), [relevance_audit.md](relevance_audit.md), [cold_review.md](cold_review.md), [sensor_reference.md](sensor_reference.md). A plain-language summary is in [aikosh-post.md](aikosh-post.md).
- **Code:** the IHF harness and scoring (`ihf.py`, `ihf_preflight.py`, `run_ihf.py`, `run_cold.py`, `rescore.py`), the task/commission scaffold (`icaf.py`, `icaf_catalog.py`), and the data/label helpers (`fetch_data.py`, `difficulty_labels.py`, `build_relevance_matrix.py`, `inspect_data.py`, `jsonl_to_md.py`) plus the run scripts.
- **Metrics:** per-model result manifests (`results_ihf_*.manifest.json`) carry the accuracy and reliability numbers; the IHF preflight reports and commission samples are under `results/`.
- **Data provenance:** [data/DATA.md](data/DATA.md) and [data/PROVENANCE.json](data/PROVENANCE.json).

## Data

This work uses IBM Research's **FailureSensorIQ** benchmark. The raw dataset is **not** republished here —
get it from the source: [Hugging Face](https://huggingface.co/datasets/ibm-research/FailureSensorIQ) ·
[IBM GitHub](https://github.com/IBM/FailureSensorIQ) · [arXiv:2506.03278](https://arxiv.org/abs/2506.03278).
The large raw per-call model outputs are also omitted to keep the repository light; the metric manifests
hold the scored results.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
