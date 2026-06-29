# FailureSensorIQ — Data Inventory & Schema (acquired metadata)

Source: HuggingFace `ibm-research/FailureSensorIQ`, revision
`5f9a736201916597345285bb6e712e3b8f4f0cfe`, downloaded 2026-06-20 (UTC).
Per-file SHA-256 + byte sizes in [PROVENANCE.json](PROVENANCE.json). Raw files in
`raw/`. Dataset card preserved at `raw/README.md`. Pulled via
[../fetch_data.py](../fetch_data.py); schema confirmed via [../inspect_data.py](../inspect_data.py).

**License is unresolved.** HF card metadata says `apache-2.0`; the GitHub README says
`CC-BY-4.0`. Both require attribution; resolve which governs before any redistribution
or publication. Cite: FailureSensorIQ, IBM Research, NeurIPS 2025, arXiv:2506.03278.

## File inventory

| File | Rows | Role |
|---|---|---|
| `failuresensoriq_standard/all.jsonl` | 2,667 | single-answer base (4-opt nominal, see below) |
| `failuresensoriq_standard/all_multi_answers.jsonl` | 5,629 | multi-answer base |
| `failuresensoriq_standard/all_10_options.jsonl` | 2,667 | OptionsPert base (10 options) |
| `failuresensoriq_perturbed/perturbed_simple.jsonl` | 2,667 | SimplePert (format perturbation) |
| `failuresensoriq_perturbed/perturbed_complex.jsonl` | 2,667 | ComplexPert (LLM-reworded) |
| `failuresensoriq_perturbed/all_10_options_all_perturbed_simple.jsonl` | 2,667 | 10-opt × SimplePert |
| `failuresensoriq_perturbed/all_10_options_perturbed_complex.jsonl` | 2,667 | 10-opt × ComplexPert |
| `raw/README.md` | — | dataset card |

## Answer encoding (canonical across all files)

`correct` is a **boolean mask aligned position-by-position to `options`**, not an index
or a letter. `option_ids` are the display labels (`["A","B",...]`; SimplePert uses
`["P)","Q)",...]`). A prediction is scored by mapping the chosen label → option index →
compare to the mask. Single-answer files have exactly one `true`; multi-answer has
several.

Example (single): `options:["partial discharge","resistance","oil debris","current","voltage"]`,
`correct:[false,false,false,true,false]` → answer = "current".

## Single-answer set (`all.jsonl`, 2,667) — the V1 workhorse

- **Exactly one correct** per question (verified all 2,667).
- **Option count varies: 2 (487), 3 (266), 4 (389), 5 (1,525).** So the random-guess
  floor is **0.2754** (mean of 1/n_options), *not* a flat 0.25. This replaces the "25%"
  rung in the design's baseline ladder.
- **Direction** (from `relevancy`): FM2Sensor (sensors-for-failure-mode) 1,342 vs
  Sensor2FM (failure-modes-for-sensor) 1,325 — balanced.
- **Polarity** (from `question_type`): `mcp1_positive` ("most relevant") 923 vs
  `mcp1_negative` ("least likely relevant") 1,744 — negative-heavy. Negative questions
  ask for the *odd one out*, a distinct reasoning mode worth a sub-analysis.
- **Assets (10):** power transformer (544), aero gas turbine (336), reciprocating
  internal combustion engine (336), industrial gas turbine (240), electric motor (234),
  electric generator (234), compressor (220), fan (200), steam turbine (171), pump (152).
- **Stratification feasibility:** the 10×2 asset×direction grid has min cell 72, so an
  asset-balanced FSIQ-core subset (≤~70/cell, or 50/asset) is comfortably supported.

## Multi-answer set (`all_multi_answers.jsonl`, 5,629)

- **Every question is exactly 2-correct-of-5-options** (uniform; not variable).
- **No `asset_name` field** — this set is a separate id-space and cannot be
  asset-stratified the way the single-answer set can. Scoring uses set F1 / exact-set
  over the boolean mask.

## OptionsPert (`all_10_options.jsonl`, 2,667)

- Exactly 10 options, one correct → random floor **0.10**. Distractors drawn from other
  assets' sensors (e.g. "compressor efficiency", "pressure ratio" injected into an
  electric-motor question).

## Perturbation alignment (matched-item analysis is clean)

`perturbed_simple`, `perturbed_complex`, and `all_10_options` each carry the **same
2,667 base ids**, 1:1 with `all.jsonl` (verified). Δaccuracy (base → variant) is
therefore a clean per-item paired comparison. The 10-option perturbed files add
`context` and `trigger_statement` fields.

## Design implications (flagged, not yet folded into DESIGN.md)

1. Baseline-ladder random floor: single-answer **0.275** (computed), OptionsPert **0.10**
   — replace the "25%" placeholder.
2. Add **polarity** (positive/negative) as a reported stratum alongside direction; the
   negative "odd-one-out" questions are a distinct reasoning mode.
3. Multi-answer cannot be asset-stratified (no `asset_name`); keep it secondary and
   score by set-F1 over the boolean mask. Note every item is 2-of-5.
4. FSIQ-core should stratify the single-answer set by asset × direction × polarity
   using the boolean-mask answers; min-cell 72 makes 50/asset feasible.
