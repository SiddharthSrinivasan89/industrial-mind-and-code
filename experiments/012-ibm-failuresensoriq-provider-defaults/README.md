# IMC-EXP-012 — IBM FailureSensorIQ at provider defaults

Exploratory collection closed at 702 model evaluations;170 same questions/model form
the primary comparison,22 additional responses retained. Pro 93/170, Flash 92/170,
Sol 83/170, Argon 73/170. One-question Pro–Flash separation is not a clear general
winner. Strict released-mask agreement scores multiple selections zero; IBM native
prompt permits option(s), so response behavior materially affects the ranking.
Four asset classes, sensor-selection convenience prefix, no confirmatory/general
industrial knowledge, human superiority, hallucination or repeatability claim.
Provider controls omitted, unlike IBM reference temperature 0.0.512/full 2,667 targets
incomplete; no inference remains active. Direct Claude Code Opus 5/high scientific
result review returned B/CHECK_GO; this is not academic peer review.

Public files are deliberate projections of unchanged frozen evidence:
- `item-scores.json`: all 702 mask scores, including 22 unshared observations.
- `responses.jsonl`: original generated answer texts, usage and successful latency,
  with account endpoints/response IDs/private paths/review transcripts omitted.
- `analysis.json`: primary/secondary statistics and descriptive four-asset ranges.
- `provenance.json`: exact dataset/source revisions, original hashes and review binding.
- `reproduce.py`: offline native-parser replay and statistics/cost verification.

Obtain the upstream dataset and IBM parser from the pinned URLs in provenance.json
and save them as `all.jsonl` and `KPPerturbation.py`, respectively. Then run:

```sh
python3 reproduce.py --dataset all.jsonl --ibm-source KPPerturbation.py
```

No provider key or paid API request is needed. Replaying saved outputs is supported;
a new provider-default inference run is not guaranteed to produce identical outputs.
Full IBM data/source are not republished here. Upstream declarations differ
(Apache-2.0 dataset card; CC-BY-4.0 repository); retain the two declarations and
source attribution. Sources: https://huggingface.co/datasets/ibm-research/FailureSensorIQ
and https://github.com/IBM/FailureSensorIQ .

Successful list-price API usage: approximately $4.16; uncertain failed-request charges
and reviewer usage excluded. This is not an invoice.719 attempts: 702 success,
8 recovered 408 timeouts,8 unscored 429 quota responses,one old truncated Pro147. Its unavailable
partial body and unknown possible billing remain preserved in the original records.

The private authoritative result lock is identified in provenance.json. Public
manifest hashes bind this exported package, not the complete original private
snapshot. No credentials, billing account records or unrelated experiments exported.
