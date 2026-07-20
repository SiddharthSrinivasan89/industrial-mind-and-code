# Finding out which part broke: LLMs vs. a one-line rule on simulated sensor data

*By Siddharth Srinivasan, industrialmindandcode.ai.*

*Disclaimer: This is self-funded, independent research. The dataset used is the Microsoft Azure Predictive Maintenance sample dataset, obtained under the MIT license. I am not affiliated with Microsoft.*

## TL;DR

- **The task:** Attribute a known machine breakdown to one of four components using pre-failure sensor and error logs.
- **The dataset:** 677 single-component breakdowns from a Microsoft-simulated dataset, with 213 events held out for evaluation.
- **The results:** A classical logistic regression baseline achieved 0.995 on macro-F1. A deterministic rule selecting the most recent error scored 0.923. Zero-shot LLMs trailed significantly at 0.355–0.440. Providing LLMs with training-period statistics improved performance (0.855–0.908), but they still fell short of the simple recent-error rule.
- **Contamination probe:** I evaluated a 51-event subset with disguised component names. gpt-5.4 and nemotron-3-super showed no contamination signal, while gpt-oss:120b exhibited a slight performance drop, consistent with a minor reliance on the original labeling conventions.
- **Conclusion:** On this specific, simulated dataset, a trained classical model outperformed LLMs, and even a simple heuristic exceeded LLM reasoning capabilities.

## Evaluation design

I investigated whether large language models could accurately attribute machine failures by analyzing raw sensor data and error logs, and whether they would outperform standard deterministic baselines. 

I utilized the Microsoft Azure Predictive Maintenance dataset, which simulates a fleet of 100 machines over the year 2015. It records hourly telemetry, including voltage, rotation, pressure, and vibration, alongside error events and maintenance logs. I identified 677 single-component failure events across 98 machines. I split this data chronologically: 464 early events were used to construct baselines and training statistics, while a frozen set of 213 events across 91 machines was reserved for evaluation.

The task required the models to identify which of four components failed, conditional on a known breakdown, given a text window of telemetry, error counts, and maintenance records immediately preceding the failure. I evaluated three models: gpt-5.4, gpt-oss:120b, and nemotron-3-super:120b. Note that nemotron-3-super was added to the evaluation post-hoc.

I evaluated the LLMs across three conditions. In the zero-shot condition, the model received only the raw pre-failure evidence window. In the with-history condition, the model was also provided a summary of training-period statistics, including failure base rates and component-specific error frequencies. Finally, in the disguised-names condition, I tested a 51-event subset where component and error labels were systematically renamed. This probe was designed to check if models were relying on memorized naming conventions rather than reasoning over the provided data.

I compared the LLM performance against four baselines derived from the training data. The simplest baseline was a no-evidence majority guess. The next baseline used a heuristic that selected the oldest component. A third baseline applied a deterministic rule that selected the component corresponding to the most recent error. Finally, I trained a classical logistic regression model as the champion baseline. All outputs were scored via exact-match parsing, without reliance on LLM judges. I established my hypotheses before running the analysis, although they were not formally pre-registered.

## Results and analysis

I measured performance primarily using macro-F1. Because this metric averages performance equally across all four components, it heavily penalizes models that safely default to the most common failure type. I also recorded standard accuracy. All reported confidence intervals are 95%, computed using a machine-cluster bootstrap (B=10,000).

| Method | Macro-F1 [95% CI] | Accuracy | n |
|---|---|---|---|
| B2 no-evidence (majority) | 0.140 [0.125, 0.155] | 0.390 | 213 |
| B3 oldest component | 0.467 [0.395, 0.534] | 0.474 | 213 |
| B4 recent-error rule | 0.923 [0.881, 0.959] | 0.930 | 213 |
| B5 classical champion (logreg) | 0.995 [0.983, 1.000] | 0.995 | 213 |
| gpt-5.4 · zero-shot | 0.440 [0.369, 0.508] | 0.498 | 213 |
| gpt-5.4 · with-history | 0.908 [0.863, 0.947] | 0.920 | 213 |
| gpt-5.4 · disguised-names | 0.858 [0.682, 0.981] | 0.882 | 51 |
| gpt-oss:120b · zero-shot | 0.366 [0.300, 0.427] | 0.408 | 213 |
| gpt-oss:120b · with-history | 0.883 [0.827, 0.929] | 0.897 | 213 |
| gpt-oss:120b · disguised-names | 0.829 [0.691, 0.931] | 0.843 | 51 |
| nemotron-3-super:120b · zero-shot | 0.355 [0.297, 0.414] | 0.380 | 213 |
| nemotron-3-super:120b · with-history | 0.855 [0.800, 0.902] | 0.859 | 213 |
| nemotron-3-super:120b · disguised-names | 0.832 [0.670, 0.948] | 0.843 | 51 |

My initial hypothesis was that a zero-shot LLM would outperform the basic deterministic baselines. The data did not support this. While all three zero-shot LLMs outperformed the majority-guessing baseline (0.140), they did not reliably exceed the oldest-component heuristic (0.467), and they trailed the recent-error rule (0.923) by a wide margin.

I also hypothesized that the classical champion would outperform the LLMs even when they were provided with historical context, which the results confirmed. The logistic regression model achieved a near-perfect macro-F1 of 0.995. Even when the LLMs were supplied with the exact training-period statistics utilized by the logistic regression model, their performance peaked between 0.855 and 0.908. The confidence intervals between the classical champion and the LLM models do not overlap.

Providing the LLMs with historical context yielded a substantial improvement, adding between 0.47 and 0.52 macro-F1 points across all tested models. However, it is notable that even with this statistical context, no LLM configuration managed to exceed the 0.923 macro-F1 of the deterministic recent-error rule. Because I did not run a formal equivalence test, the precise observation is simply that they failed to exceed it.

The disguised-names probe yielded mixed results. I observed no contamination signal for gpt-5.4 (an accuracy gap of 0.000) or nemotron-3-super (a gap of -0.039). For gpt-oss:120b, I measured a gap of +0.059, which is consistent with a minor effect where the model relied on original labeling conventions. As this probe was restricted to 51 events, the sample size is too small to prove the models are entirely clean. The numbers simply rule out gross memorization effects.

## Conclusion

On this near-deterministic simulator data, the performance hierarchy is unambiguous. The trained classical model performed best (0.995), followed by the recent-error rule (0.923), the with-history LLMs (0.855–0.908), the oldest-component heuristic (0.467), the zero-shot LLMs (0.355–0.440), and the no-evidence majority guess (0.140).

The observation that an LLM analyzing raw sensor evidence could not consistently outperform a basic heuristic is a key finding. It indicates that on this specific simulated tabular dataset, strong performance requires access to the prior training distribution rather than relying on zero-shot reasoning capabilities.

Several scope constraints bound these findings. The dataset consists of simulated data; the "ground truth" reflects the simulator's internal logic. The task focuses narrowly on attribution conditional on a known failure, rather than predictive anomaly detection or complex root-cause analysis. Furthermore, because the evaluation chronologically splits a single fleet of simulated machines, the results estimate performance on that exact fleet over time. These findings do not guarantee comparable performance on unseen machines or different real-world data distributions. Finally, the contamination probe was too small to completely rule out the possibility that the models memorized the specific structural dynamics of this simulator. Within these stated limits, the results support a clear conclusion: for this specific task, a trained classical model or a deterministic rule outperforms LLM-based approaches.
