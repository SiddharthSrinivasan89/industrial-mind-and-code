# IMC-EXP-004 — MaintIE operational reliability

This is the public evidence package for the Industrial Mind & Code article
“Can consistent AI classifications be trusted?” It is a curated release from
the completed and independently reviewed IMC-EXP-004 experiment.

## Question

Does the association between independently elicited cross-level consistency
and exact detailed-label correctness remain stable across repeated model
realizations on the MaintIE maintenance-text benchmark?

## Result

Yes, within this frozen evaluation. Qwen 3.5 122B and Gemma 4 31B each met the
predeclared replication rule in five of five new runs. Astra was a separate
stability comparison and also showed a positive mean effect. Mean accuracy
separation between consistent and inconsistent predictions was 0.303 for
Qwen, 0.209 for Gemma, and 0.152 for Astra.

Consistency did not guarantee correctness. Consistent-set mean accuracy was
64.0% for Qwen, 65.0% for Gemma, and 74.7% for Astra. The expert operational
analysis used only 15 exactly joinable records and remains exploratory.

## Package contents

- `DESIGN.md` — frozen prospective method.
- `FINDINGS.md` — public findings and limitations.
- `run-config.json` — privacy-redacted copy of the frozen prospective run
  configuration. Its pre-production state fields are historical, not the
  experiment's current completed status.
- `results/analysis/` — exact aggregate, detailed, and operational analysis
  files from the reviewed result package.
- `src/` and `tests/` — scoring/analysis implementation and offline tests.
- `data/PROVENANCE.json` — hashes and source bindings for this public release.

The raw provider responses, encrypted reasoning payloads, request headers,
human transcript, and raw expert rationale are not republished. This package
therefore supports inspection of the reported analysis and implementation but
does not independently reproduce inference or rescore from raw responses.

## Inspection and limited reproduction

Python 3.11 or newer is sufficient for the public-package integrity tests:

```bash
python3 -m unittest discover -s tests -v
```

The analysis JSON files can be inspected without additional dependencies. A
full inference rerun or raw-response rescore requires the non-public execution
evidence, exact model access, and upstream MaintIE data at the commit and hashes
recorded in `data/PROVENANCE.json`; those materials are not bundled here.

The source experiment's final result lock has SHA-256
`7219db6ad9d37ef2f8e6ad8f8d11467b1e2ad79deb100934935b5f8a17a28e20`.
Its independent result review returned Grade B / `CHECK_GO`. Publication of
this curated package does not expand the findings beyond the tested MaintIE
records or establish operational safety.
