# pdm-component-attribution-v1-azure

Can a large language model name which machine component failed, from the evidence available just
before the breakdown — and does it beat the classical tools used for this today? I tested three
LLMs against deterministic baselines and a trained classifier on Microsoft's **simulated** Azure
Predictive Maintenance sample dataset.

**Result.** A trained logistic-regression classifier scored 0.995 macro-F1 and a one-line
recent-error rule scored 0.923. Zero-shot LLMs trailed at 0.355–0.440; giving them the training
period's statistics lifted them to 0.855–0.908, but none exceeded the one-line rule. A
label-disguising probe found no contamination signal for two of three models. For this tabular
sensor task, classical ML is the stronger approach. Full writeup: **[FINDINGS.md](FINDINGS.md)**.

The dataset is simulated, so these results describe method behaviour on this simulator, not
real-plant capability.

## Repo layout
- `FINDINGS.md` — consolidated writeup (method, results, limitations).
- `DESIGN.md` — experiment design and hypotheses.
- `specs/FROZEN-SPEC.md` — the frozen protocol: task, arms, baselines, decision rules, seeds.
- `data/` — provenance and license pointer (raw data is not republished; fetch from source).
- `results/` — `ANALYSIS.json` (metrics, CIs, hypothesis verdicts) and the classical baseline
  outputs.
- `code/` — feature rendering, baselines, subject runner, classical arm, and analysis.

## Reproduce
1. **Data.** Fetch the five `PdM_*.csv` files from `github.com/microsoft/sqlworkshops`
   (`SQLServerAndAzureMachineLearning/ML Services for SQL Server/data/`, MIT license) into
   `data/raw/`. Checksums are in `data/PROVENANCE.json`.
2. **Gate evidence + features.** `python3 code/build_gate_evidence.py` (renders windows, runs
   the leakage audits).
3. **Classical arm.** `python3 code/run_classical.py` (champion selection, gates, baselines).
4. **LLM arms.** `python3 code/run_subjects.py --subject <model> --arm <A|B|C>` — local models
   via Ollama, `gpt-5.4` via Azure (supply your own endpoint/key via an env file). Serial on a
   single GPU.
5. **Analysis.** `python3 code/analyze.py` → `results/ANALYSIS.json`.

Prereqs: Python 3.12, pandas, numpy, scikit-learn; Ollama for local models; an Azure OpenAI
deployment for the frontier arm.

## Attribution
Microsoft Azure Predictive Maintenance sample dataset (Predictive Maintenance Modelling Guide),
© Microsoft Corporation, MIT License, obtained from github.com/microsoft/sqlworkshops.

*Independent, self-funded research by Siddharth Srinivasan (industrialmindandcode.ai). Not
affiliated with or endorsed by Microsoft.*
