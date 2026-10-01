# Findings

## Primary result

The predeclared panel replication criterion was satisfied. Qwen 3.5 122B and
Gemma 4 31B each had five of five estimable runs, five positive cross-level
accuracy separations, and a crossed run/record-group bootstrap 95% interval
wholly above zero. Astra was not part of the panel decision; its five
prespecified comparison runs also produced a positive mean effect.

| Model | Overall accuracy | Valid-A coverage | Accuracy if consistent | Accuracy if inconsistent | Mean separation | Crossed 95% CI |
|---|---:|---:|---:|---:|---:|---:|
| Astra | 71.4% | 100.0% | 74.7% | 59.5% | 0.152 | [0.038, 0.263] |
| Qwen 3.5 122B | 43.4% | 91.2% | 64.0% | 33.7% | 0.303 | [0.185, 0.416] |
| Gemma 4 31B | 54.1% | 97.3% | 65.0% | 44.1% | 0.209 | [0.100, 0.320] |

These between-model differences are descriptive point estimates; no
between-model inferential comparison was performed.

## Repeated-question comparison

Repeated-question agreement produced a larger point-estimate accuracy
separation than cross-level agreement in all five Qwen and all five Gemma runs.
Those ten comparisons met the frozen evidence rule. Astra's repeated-disagree
strata contained only 18–26 items and were below that rule in every run, so its
repeated-question comparison is descriptive only. A larger separation does not
establish a better or safer decision policy.

## Expert operational layer

Only 15 expert-reviewed records were exact outcome-joinable matches. The
annotator was also the study author; there was no second rater or inter-rater
reliability estimate. An AI assistant derived context sufficiency for four of
the 15 records, operational consequence for one, and specificity for three
from preserved expert rationale under explicit authorization. The first seven
records also underwent a documented conversion from an earlier
operational-ambiguity schema. The annotator had prior aggregate-result exposure
while remaining blind to record-level outcomes.

Across all three models, mean accuracy was lower for the high-consequence,
high-specificity, and missing-machine-identity groups than for their respective
comparison groups. These are exploratory patterns from 15 records, not stable
subgroup effects. All 18 predeclared subgroup rows and every sparse theme are
reported in `results/analysis/detailed-analysis.json`.

Among six expert-rated high-consequence records, cross-level-consistent but
wrong rates ranged from 23.1–28.6% for Astra and 40.0–45.5% for Qwen; Gemma was
54.5% in every run. These are conditional benchmark-performance measurements,
not plant-risk or safety estimates.

## Operations

All 15 runs and 4,860 logical calls completed. The ledger contains 4,905
attempts, including 45 transient Astra failures that recovered under the same
logical observations, and zero terminal failures. Astra had no invalid calls;
Gemma had five invalid-label calls per run; Qwen had 11–23 invalid or truncated
calls per run.

## Conclusion

Cross-level consistency was a repeatable accuracy-enrichment signal on this
MaintIE evaluation. It was not a correctness guarantee, calibrated confidence,
deployment validation, or safety measure. General claims require another
industrial dataset, a larger prospectively annotated expert sample, and a
predeclared decision-policy comparison.
