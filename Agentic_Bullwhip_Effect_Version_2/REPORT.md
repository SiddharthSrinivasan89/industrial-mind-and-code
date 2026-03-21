

# Agentic Bullwhip: Evaluating LLMs as Supply Chain Planners Against Deterministic Heuristics

**Date:** March 2026
**Author:** Siddharth Srinivasan - Blog: industrial mind and code 
**Subject:** Technical Report

---

## Executive Summary

This report presents the results of a controlled simulation experiment investigating the efficacy of Large Language Models (LLMs) as autonomous supply chain planners. The study tests whether LLM agents can outperform traditional statistical heuristics in a multi-echelon (OEM → Ancillary → Component) environment characterised by 25 periods of synthetic demand, deterministic lead times, and significant seasonal volatility reflecting Indian automotive market patterns (FY-end peaks, monsoon dips, Diwali surges).

We compared four LLM configurations across two model families and two context conditions, running 20 independent trials per condition. All results were measured against three heuristic baselines run under identical conditions.

**Key Findings:**

- **Heuristics dampen bullwhip; LLMs do not.** The best heuristic — exponential smoothing — achieved a chain-average Order Variance Ratio (OVAR) of **0.54**, meaning it actively smooths demand volatility. All LLM configurations produced chain-average OVAR between **4.33 and 6.35** — 8–12× higher than the best heuristic, and 4–6× higher than the naive passthrough baseline.

- **Stockouts are catastrophically worse under LLMs.** Exponential smoothing generated 5 stockout periods. Every LLM condition generated between 37 and 43 — a 700–800% increase. No LLM configuration came close to matching heuristic service levels.

- **Context is unreliable.** For the frontier lightweight model (gpt-4.1-mini), adding supply chain tier persona and the current calendar month reduced OVAR marginally (4.70 → 4.47). For the local lightweight model (phi4:14b), the same context made performance dramatically worse (4.33 → 6.35, +47%), with Ancillary tier OVAR reaching 10.8 and a standard deviation of 8.1 between runs — indicating erratic, unpredictable ordering.

- **Reasoning models showed no observed ordering advantage over lightweight models in this task.** Chain-average OVAR ranges overlapped substantially (o4-mini: 4.52–4.72; gpt-4.1-mini: 4.47–4.70). No formal significance test was run; the comparison also conflates model family, quantisation level, and temperature — so the result is directional, not causal.

- **Local and frontier outcomes varied by condition.** For blind conditions, local and frontier OVAR means were within 0.37. For the lightweight context condition, local diverged sharply (Δ=1.87). The local/frontier comparison simultaneously changes the model (phi4:14b vs gpt-4.1-mini; gpt-oss:120b vs o4-mini), quantisation, serving stack (Ollama vs Azure OpenAI), and hardware. Any observed difference could be due to any combination of these factors — this should not be read as a local-vs-cloud infrastructure test.

- **Event recognition was weak and inconsistent.** Aggregate pattern scores across all conditions were low (0.20–0.23), indicating limited alignment between seasonal language cues and correctly directed order adjustments.

**Conclusion:** In this single-product replenishment task with fixed lead times and no unstructured context, LLM agents did not outperform deterministic heuristics. The exponential smoothing heuristic outperformed every LLM configuration by a wide margin on both OVAR and service level(Stockouts) simultaneously. These results should be interpreted within this narrow scope — the experiment was not designed to, and does not, address broader supply chain settings involving exceptions, multi-supplier negotiation, or unstructured information nor does it emulate a real world supplychain with disruptions and stochastic lead times. 
---

## 1. Introduction

The Bullwhip Effect — the amplification of order variance as signals propagate upstream through a supply chain — is a primary driver of inventory costs and service failures. Traditional statistical heuristics (exponential smoothing, order-up-to policies) are calibrated to dampen this amplification. They achieve this by constraining order quantities to a formula, eliminating the discretionary variability that generates bullwhip.

As LLMs become capable of acting as autonomous agents, a critical question arises: **can LLMs interpret complex, event-driven demand patterns to smooth orders better than deterministic algorithms?**

This study answers this question through a rigorous, multi-run simulation of a 3-tier supply chain over 25 periods. We evaluate not just whether LLMs "understand" the demand environment, but whether that understanding translates into better ordering behaviour. The joint reporting of OVAR and stockout count is mandatory: a smoother order pattern achieved by chronic under-ordering is not a success — it is a different failure mode.

### 1.1 Scope and Boundaries

- **Environment:** 3-tier chain (OEM → Ancillary → Component).
- **Lead Time:** 1 month, deterministic. Replenishment ordered in period *t* arrives at the start of period *t+1*.
- **Demand:** Synthetic series calibrated on Indian automotive seasonal patterns (Tatva Motors Vecta). Two full annual cycles (2025–2026), 24 active ordering periods (period 25 is close-out only).
- **Agent Constraints:** Stateless (no memory between periods), JSON-enforced output, zero order floor.
- **Success Criterion:** An LLM configuration must achieve a chain-average OVAR at least 0.5 lower than the best heuristic baseline *without* increasing total stockouts above heuristic levels.

### 1.2 Scope and Generalisability

This experiment is intentionally narrow. Any finding should be read within its scope:

> *"LLM agents do [or do not] outperform simple blind heuristics in a stylised single-product replenishment task with fixed lead times and no unstructured context."*

This result does not generalise — in either direction — to supply chain management more broadly. Settings that may produce different results include: exception-driven replenishment, multi-supplier negotiation, regime shifts and demand shocks, decisions requiring unstructured context (regulatory text, supplier communications, logistics alerts), and multi-objective tradeoffs. Whether LLMs add value in those settings is an open empirical question not addressed here.

---

## 2. Experimental Design

### 2.1 The Simulation Environment

The simulation executes in discrete monthly periods (*t* = 1 to 25). Each period follows a strict sequence:

1. **Demand Arrival:** Retail demand hits the OEM tier.
2. **Fulfilment:** Each tier serves demand + accumulated backlog from on-hand stock. Unmet demand becomes backlog.
3. **Ordering:** Agents observe their post-fulfilment state (on_hand, backlog) and place an upstream order.
4. **Replenishment:** Orders placed in period *t* arrive as stock at the start of *t+1*.

Period 25 is a close-out period: all tiers fulfil remaining demand but no new orders are placed. This ensures order variance statistics are computed over a clean 24-period ordering window.

### 2.2 Agent Configurations

Four LLM conditions were tested across two experiments (E1: lightweight; E2: reasoning). Three deterministic heuristics served as baselines.

**LLM Conditions:**

| Config | Experiment | Model | Backend | Temperature | Context Provided |
| :--- | :--- | :--- | :--- | :--- | :--- |
| L-Blind (Azure) | E1 | gpt-4.1-mini | Azure OpenAI | 0.4 | No history or events |
| L-Context (Azure) | E1 | gpt-4.1-mini | Azure OpenAI | 0.4 | Tier persona (company, product, role) + current calendar month |
| L-Blind (Local) | E1 | phi4:14b (14.7B, Q4_K_M) | Ollama | 0.4 | No history or events |
| L-Context (Local) | E1 | phi4:14b (14.7B, Q4_K_M) | Ollama | 0.4 | Tier persona (company, product, role) + current calendar month |
| R-Blind (Azure) | E2 | o4-mini | Azure OpenAI | API-constrained (=1.0) | No history or events |
| R-Context (Azure) | E2 | o4-mini | Azure OpenAI | API-constrained (=1.0) | Tier persona (company, product, role) + current calendar month |
| R-Blind (Local) | E2 | gpt-oss:120b (116.8B, MXFP4) | Ollama | 0.0 | No history or events |
| R-Context (Local) | E2 | gpt-oss:120b (116.8B, MXFP4) | Ollama | 0.3 | Tier persona (company, product, role) + current calendar month |

**Note on temperature:** The o4-mini API ignores caller-supplied temperature; the model runs at its internal default (~1.0). This is reflected in the high run-to-run variance observed for R-Blind (Azure) results (§4.6).

**Heuristic Baselines (1 deterministic run each):**

| Heuristic | Description |
| :--- | :--- |
| `exp_smoothing` | Exponential smoothing with α=0.30, safety stock derived from demand series |
| `naive_passthrough` | Each tier orders exactly what was demanded in the prior period |
| `order_up_to` | Order up to a target stock level; target derived from demand statistics |

### 2.3 Metrics

Two primary metrics are reported jointly for every result. Reporting only one is insufficient:

1. **OVAR (Order Variance Ratio):** Var(Orders) / Var(Demand), computed per tier and averaged across the chain.
   - < 1.0: Order variance is dampened — the agent is smoothing.
   - = 1.0: No amplification.
   - \> 1.0: Bullwhip amplification.
   - **MPRD (Minimum Practically Relevant Difference):** |ΔOVAR| ≥ 0.5 required for a result to be considered practically meaningful.

2. **Stockout Count:** Total number of (period, tier) pairs where on-hand stock could not fully cover demand + backlog. Reported as chain total (maximum possible: 75 = 25 periods × 3 tiers).

Secondary metric:

3. **Pattern Score:** Average of (a) keyword score — fraction of event months where the agent's rationale text mentioned relevant seasonal keywords, and (b) elevation score — fraction of event months where order quantity moved in the correct direction (up for elevation events, down for monsoon dip months). A perfect score of 1.0 requires both correct language *and* correct quantities at every event month.

---

## 3. Methodology

### 3.1 Execution Protocol

- **Runs per LLM condition:** 20 independent runs per condition per backend.
- **Heuristic runs:** 1 (fully deterministic).
- **Error handling:** Exponential backoff with 10 retries per API call, cap 60 seconds. Failed runs are replaced to maintain 20 valid runs per condition. Observed retry rate: **0.0%** across all conditions — zero retries were needed.
- **Checkpointing:** Per-condition checkpoint written after each of the 20 runs, enabling recovery from interruption without data loss.

### 3.2 Data and Events

The demand series covers two full annual cycles (Jan 2025 – Jan 2027, 25 periods) with named seasonal event windows:

- **Elevation events:** Makar Sankranti (Jan), Union Budget (Feb), FY-end (Mar), Wedding season (Apr–May), Navratri/Dasara (Oct), Diwali (Nov), Year-end (Dec).
- **Dip events:** Monsoon months (Jun–Aug).

The series is synthetic, generated from real Indian automotive seasonal structure and calibrated to Tatva Motors Vecta dispatch data. The same series and initial stock positions were used across all runs: initial inventory S ≈ 43,609 units (derived as mean + 1.65 × std of the demand series), from which a safety stock of ≈ 5,061 units is derived for use by forecast-based heuristics. A SHA-256 checksum in each provenance file guarantees data integrity across experiments.

### 3.3 Infrastructure

All experiments ran under nohup in a tmux session on an Asus Ascent GX10 (NVIDIA GB10 Blackwell SoC) for local inference, with Azure OpenAI (GlobalStandard tier) for frontier conditions. Experiments ran concurrently: local and cloud runs were executed in parallel sessions.

---

## 4. Results

### 4.1 Heuristic Baselines

Before examining LLM performance, it is essential to understand what the heuristics actually achieve — the original report mischaracterised this, which distorted every subsequent comparison.

| Heuristic | Chain OVAR | Stockouts (of 75 possible) |
| :--- | :---: | :---: |
| `exp_smoothing` | **0.54** | **5** |
| `naive_passthrough` | 1.00 | 3 |
| `order_up_to` | 1.71 | 14 |

The best heuristic, exponential smoothing, does not merely hold OVAR at 1.0 — it actively dampens order variance to 0.54, below the demand variance. This is the correct comparison point for LLM evaluation. No LLM configuration approached this. Naive passthrough, which simply echoes last period's demand, achieves OVAR=1.00 by definition. Order-up-to, the most common textbook policy, generates materially more amplification than the other heuristics (1.71), but still far less than any tested LLM condition.

### 4.2 Primary Finding: Bullwhip Persistence

**No LLM configuration reduced the Bullwhip effect below 4.3 chain-average OVAR.** The gap between LLMs and the best heuristic is not marginal — it is an order of magnitude.

| Condition | Backend | Chain OVAR (mean ± std) | Chain Stockouts (mean ± std) |
| :--- | :--- | :---: | :---: |
| **Heuristic: exp_smoothing** | — | **0.54** | **5** |
| **Heuristic: naive_passthrough** | — | 1.00 | 3 |
| **Heuristic: order_up_to** | — | 1.71 | 14 |
| L-Blind | Azure | 4.70 ± 0.14 | 40.5 ± 0.83 |
| L-Context | Azure | 4.47 ± 0.07 | 39.0 ± 0.83 |
| L-Blind | Local | 4.33 ± 0.00 | 41.0 ± 0.00 |
| L-Context | Local | **6.35 ± 2.53** | 37.2 ± 3.11 |
| R-Blind | Azure | 4.72 ± 1.12 | 42.9 ± 3.85 |
| R-Context | Azure | 4.52 ± 0.08 | 40.1 ± 0.85 |
| R-Blind | Local | 4.52 ± 0.00 | 40.0 ± 0.00 |
| R-Context | Local | 4.52 ± 0.05 | 39.6 ± 0.76 |

No LLM condition satisfies the success criterion. The minimum OVAR achieved by any LLM (4.33, local L-Blind) is still 8× above the best heuristic (0.54) and simultaneously generates 8× the stockouts (41 vs 5). The OVAR/stockout trade-off that might exist between heuristics does not apply here: the LLMs are strictly worse on both dimensions simultaneously.

**Tier-level OVAR** reveals that Ancillary is consistently the most amplified tier — consistent with classic bullwhip dynamics where middle tiers accumulate the most distortion:

| Condition | Backend | OEM | Ancillary | Component |
| :--- | :--- | :---: | :---: | :---: |
| exp_smoothing | — | 0.41 | 0.65 | 0.58 |
| L-Blind | Azure | 4.21 | **6.64** | 3.25 |
| L-Context | Azure | 4.12 | 6.01 | 3.30 |
| L-Blind | Local | 3.71 | 5.89 | 3.40 |
| L-Context | Local | 4.62 | **10.82** | 3.61 |
| R-Blind | Azure | 5.94 | 5.18 | 3.05 |
| R-Context | Azure | 4.13 | 5.99 | 3.45 |
| R-Blind | Local | 4.13 | 5.99 | 3.45 |
| R-Context | Local | 4.13 | 6.01 | 3.43 |

### 4.3 The Context Effect

**For cloud lightweight (gpt-4.1-mini):** context marginally reduced chain OVAR (4.70 → 4.47, Δ=−0.23) and stockouts (40.5 → 39.0, Δ=−1.5). The Δ is below the MPRD threshold of 0.5; the improvement is not practically meaningful.

**For local lightweight (phi4:14b):** context made performance dramatically and unpredictably worse. Chain OVAR increased from 4.33 to 6.35 (+47%), with a standard deviation of 2.53 — indicating some runs were near the cloud average while others were catastrophically high. The Ancillary tier was the failure point: OVAR 10.82 ± 8.14. In the worst observed runs, Ancillary OVAR exceeded 20. Stockouts improved slightly (41.0 → 37.2) only because some runs under-ordered severely — reducing stockout count by accepting chronic inventory starvation rather than service.

**For reasoning models (both backends):** context provided no practically meaningful OVAR improvement. R-Blind Azure (4.72) vs R-Context Azure (4.52): Δ=−0.20, below MPRD. R-Blind local (4.52) vs R-Context local (4.52): Δ≈0.

The pattern is consistent: context does not help and can hurt. It adds signal that agents cannot reliably translate into correctly-sized quantity adjustments.

### 4.4 Lightweight vs Reasoning: No Material Difference

| | Azure | Local |
| :--- | :---: | :---: |
| Best lightweight OVAR | 4.47 (L-Context) | 4.33 (L-Blind) |
| Best reasoning OVAR | 4.52 (R-Context) | 4.52 (R-Blind) |

Reasoning models (o4-mini, gpt-oss:120b) showed no observed ordering advantage over lightweight models (gpt-4.1-mini, phi4:14b) in this task. On the cloud, lightweight OVAR means were marginally lower. On local, the two families were nearly identical in the blind condition. The additional compute cost of reasoning models — o4-mini generated 1,083,968 reasoning tokens vs 101,879 completion tokens for gpt-4.1-mini — did not correspond to any measurable ordering improvement.

**Important caveat:** This comparison conflates model family, quantisation level, serving stack, and temperature (gpt-4.1-mini at T=0.4 vs o4-mini API-constrained at ~1.0; phi4:14b at T=0.4 vs gpt-oss:120b at T=0.0). The experiment was not designed to isolate the effect of reasoning capability alone from these confounding factors. The directional finding is that spending more on inference did not help; the causal attribution to "reasoning" specifically is not cleanly supported.

The high variance of R-Blind Azure (chain OVAR std=1.12, OEM std=3.91) reflects o4-mini's API-constrained temperature (~1.0). The model occasionally generated very high-confidence large orders that propagated as a shock upstream, producing outlier OVAR values. Context reduced this variance substantially (std: 1.12 → 0.08), suggesting context partially constrains the model's ordering range — though not toward the correct level.

### 4.5 Local vs Frontier Inference: Conditional Equivalence

The local/frontier comparison must be split by condition — the aggregate "equivalent" claim obscures a critical divergence:

| Condition | Azure OVAR | Local OVAR | |Δ| | Equivalent? |
| :--- | :---: | :---: | :---: | :---: |
| L-Blind | 4.70 | 4.33 | 0.37 | Borderline (within ±0.5) |
| L-Context | 4.47 | 6.35 | **1.87** | No — diverges significantly |
| R-Blind | 4.72 | 4.52 | 0.20 | Yes |
| R-Context | 4.52 | 4.52 | 0.00 | Yes |

**The lightweight context condition is where local and frontier diverge.** phi4:14b (local) became highly unstable under the longer context prompt, while gpt-4.1-mini (frontier) remained tightly distributed. This suggests phi4:14b's ordering behaviour is sensitive to prompt length or structure in a way that gpt-4.1-mini is not.

**For reasoning model conditions, observed OVAR means were nearly identical** (R-Context Δ=0.00, R-Blind Δ=0.20). However, this comparison reflects the combined effect of model (gpt-oss:120b vs o4-mini), quantisation (MXFP4 vs frontier float), serving stack, and hardware. The experiment does not isolate infrastructure from model differences. The result shows that local and frontier produced similar observed outcomes in this task; it does not establish that the two stacks are equivalent in general.

### 4.6 Determinism and Variance

A notable empirical observation: two local model configurations produced perfectly deterministic output across all 20 runs.

| Config | Temperature | Chain OVAR std |
| :--- | :---: | :---: |
| L-Blind (Local, phi4:14b) | 0.4 | ~0 |
| R-Blind (Local, gpt-oss:120b) | 0.0 | ~0 |

For phi4:14b at T=0.4, 20 identical blind prompts produced 20 identical responses. This implies the model's token distribution, given this prompt, is sharply peaked — temperature had no effective impact on output diversity. The model settled into a fixed ordering pattern and never deviated.

This is not stability — it is rigidity. A stateless agent repeating the same order quantity regardless of the evolving supply chain state is generating bullwhip by construction.

By contrast, o4-mini at its API-constrained temperature produced chain OVAR standard deviation of 1.12 across 20 runs (blind condition) — the most variable configuration in the experiment. High stochasticity in reasoning did not improve outcomes; it just made them unpredictable.

### 4.7 Event Recognition (Pattern Score)

| Condition | Backend | Pattern Score (mean ± std) |
| :--- | :--- | :---: |
| L-Blind | Azure | 0.21 ± 0.00 |
| L-Context | Azure | 0.22 ± 0.01 |
| L-Blind | Local | 0.20 ± 0.00 |
| L-Context | Local | 0.22 ± 0.02 |
| R-Blind | Azure | 0.22 ± 0.02 |
| R-Context | Azure | 0.22 ± 0.01 |
| R-Blind | Local | 0.23 ± 0.00 |
| R-Context | Local | 0.22 ± 0.01 |

The pattern score (0.0–1.0) is the simple average of two independent sub-scores: keyword score (fraction of event months where the rationale mentioned seasonally relevant terms) and elevation score (fraction of event months where order quantity moved in the correct direction). A composite score of 0.22 does not mean agents succeeded on both components simultaneously 22% of the time — an agent scoring 0.44 on keywords and 0.00 on elevation would also produce 0.22. The two sub-scores are not available separately in the aggregated summary output.

Three observations:

1. **Pattern scores are indistinguishable across all conditions.** Blind and context models score identically. Lightweight and reasoning score identically. Cloud and local score identically. The calendar month signal makes no measurable difference to whether agents act correctly at event months.

2. **The score reflects two separate failures.** An agent can mention "Diwali approaching" in its rationale and still place a low order (keyword credit, no elevation credit) — or place a high order while citing unrelated logic (elevation credit, no keyword credit). The aggregated score of 0.22 does not distinguish these failure modes, but both indicate a gap between articulation and execution.

3. **The context treatment was designed to help here most.** Agents in L-Context and R-Context were given tier identity (company name, product, role) and the current calendar month — enough for a model with world knowledge to infer "November = Diwali." Despite this signal, pattern scores were unchanged from blind conditions. The calendar month was available; the translation into correctly-sized quantities was not.

### 4.8 Hypothesis Verdicts

All hypotheses required |ΔOVAR| ≥ 0.5 (MPRD) at chain level. OVAR and stockout count are reported jointly for each verdict.

| Hypothesis | Prediction | Result | Verdict |
| :--- | :--- | :--- | :---: |
| **H1** (Layer 1 — Primary) | At least one LLM achieves lower chain-average OVAR than exp smoothing (0.54) with ≤5 stockouts | Best LLM: OVAR 4.33, stockouts 41. Heuristic: OVAR 0.54, stockouts 5. | REJECTED |
| **H2** (C1 — Context, lightweight) | context_lightweight OVAR < blind_lightweight by ≥0.5, no increase in stockouts | Δ = 4.70 − 4.47 = 0.23 — below MPRD | REJECTED |
| **H3** (C2 — Context, reasoning) | context_reasoning OVAR < blind_reasoning by ≥0.5, no increase in stockouts | Δ = 4.72 − 4.52 = 0.20 — below MPRD | REJECTED |
| **H4** (C3 — Reasoning, no context) | blind_reasoning OVAR < blind_lightweight by ≥0.5 | Δ = 4.70 − 4.72 = −0.02 — opposite direction | REJECTED |
| **H5** (C4 — Reasoning, with context) | context_reasoning OVAR < context_lightweight by ≥0.5 | Δ = 4.47 − 4.52 = −0.05 — opposite direction | REJECTED |
| **H6** (C5 — Interaction) | Context benefit larger for reasoning than lightweight (C5 = C2 − C1 > 0) | C5 = 0.20 − 0.23 = −0.03 — opposite direction | REJECTED |
| **H7** (E4 — Local/frontier replication) | Local context_lightweight within ±0.5 OVAR of frontier context_lightweight | Δ = 6.35 − 4.47 = 1.88 — well outside ±0.5 equivalence bounds | REJECTED |

All seven hypotheses were rejected. H1 — the primary layer one question — was rejected by the widest margin: the best LLM configuration produced OVAR 8× above the best heuristic while simultaneously generating 8× more stockouts. H2 and H3 were rejected on the MPRD threshold: context produced directional improvements for frontier models, but neither reached the 0.5 OVAR unit threshold required for a practically meaningful claim. H4 and H5 show reasoning models performed no better than lightweight — the contrast was negative in both conditions. H7 confirms that the local/frontier divergence under the context condition was substantial and practically significant, not noise.

---

## 5. Discussion

### 5.1 Why LLMs Fail to Smooth

The results indicate that the bullwhip failure is structural, not a matter of model capability or prompt quality.

**Statelesness compounds over time.** Each period, the agent sees only the current prompt — it has no memory of the order it placed in *t*−1 or the stockout it caused in *t*−2. The supply chain state it inherits (high backlog, low on-hand) was partly its own creation, but it has no causal chain connecting that state to its past decisions. Without this, there is no mechanism for the agent to self-correct a drift toward over- or under-ordering.

**Quantity estimation is not what LLMs optimise for.** LLMs are trained on text prediction tasks where precise numerical outputs rarely carry direct consequence. "Order 6,800 units" vs "order 7,200 units" generates similar training signal if both are plausible responses to the context. The model has no intrinsic motivation to hit a specific quantity range, whereas the heuristic's formula guarantees it.

**Discretion generates variance.** Every period, an LLM makes a fresh judgement call. Even a well-calibrated model will exhibit run-to-run variance in this call, which manifests directly as order variance. A deterministic formula has zero within-run variance by construction. The OVAR comparison is, in a sense, a comparison between the variance introduced by formula (≈0) versus the variance introduced by LLM discretion (substantial).

**Reasoning does not narrow the gap.** o4-mini generated over 1 million reasoning tokens during E2 — long internal chains of thought on each ordering decision. These reasoned orders were not closer to the optimal quantity than gpt-4.1-mini's simpler outputs. The reasoning capacity was applied to contextual interpretation, not to numerical convergence.

### 5.2 Context as Noise Amplifier

The L-Context (local) result deserves specific attention. Adding the tier persona and current calendar month to phi4:14b's prompt did not help it order better — it destabilised an otherwise rigid model. The Ancillary tier's standard deviation of 8.14 OVAR across 20 runs indicates some runs had near-normal Ancillary variance while others were extreme outliers.

This likely reflects a threshold effect in the model's attention over longer prompts: when the context triggered a particular interpretation of the demand pattern, the model committed to an aggressive order stance that then propagated as an amplified shock upstream. The rigid blind model, repeating the same order every run, at least produced *predictable* underperformance.

### 5.3 The Order-Up-To Comparison

A secondary finding worth noting: `order_up_to` — one of the most widely deployed inventory policies — produced OVAR of 1.71, well below the LLM range of 4.33–6.35 but 3× above the best heuristic (exp_smoothing at 0.54). This suggests that the bullwhip problem is not unique to AI agents; naive policy design can generate significant amplification. The differentiator is `exp_smoothing` with α=0.30, calibrated against this demand series. The conclusion is not that LLMs are uniquely bad relative to all heuristics, but that well-calibrated statistical heuristics set a high bar that no tested LLM configuration approached.

### 5.4 Implications for Industry

- **In repetitive, low-information replenishment tasks of this type, do not use LLM agents as autonomous order-placement agents.** The observed gap to a simple statistical heuristic is large and was not closed by any combination of model size, context, or backend. Whether this finding extends to more complex supply chain settings — exceptions, disruptions, multi-objective tradeoffs — is outside the scope of this experiment.

- **Higher inference spend did not improve ordering outcomes in this task.** Upgrading from a lightweight to a reasoning model cost 3.4× more in mean call latency and substantially more in tokens, with no observed OVAR or stockout improvement. The reasoning/lightweight comparison is confounded by model family and temperature, so this should be treated as a directional finding rather than a causal one.

- **Local and frontier deployments produced similar outcomes in the reasoning model conditions.** The comparison conflates model, quantisation, stack, and hardware, so it should not be read as an infrastructure equivalence test. The practical takeaway is narrow: in this task, local gpt-oss:120b and frontier o4-mini produced similar OVAR means with zero failures on both sides.

- **LLMs have a role in the planning loop, not the execution loop.** Pattern scores, while low in absolute terms, show that agents consistently produce articulate rationales naming seasonal dynamics. This capability — generating explanations for demand movements — is where LLMs create value. Hybrid systems that use LLM analysis to adjust the *parameters* of a deterministic model (e.g., modifying safety stock for a Diwali window) represent a more promising architecture than fully autonomous LLM ordering.

---

## 6. Conclusion

This experiment tested the hypothesis that LLM agents — including state-of-the-art reasoning models — can outperform traditional statistical heuristics in supply chain order management. **The hypothesis was rejected across all configurations and both model families.**

In this task — single product, fixed lead times, three tiers, 24 ordering periods, stateless agents — the exponential smoothing heuristic achieved OVAR=0.54 and 5 stockouts. Every LLM configuration produced chain-average OVAR between 4.33 and 6.35 and between 37 and 43 stockouts. The gap is large. Within the bounds of this experiment, no combination of model size, context treatment, or backend closed it.

These findings are specific to the task tested. The experiment was deliberately scoped to a stable, low-information, single-product setting — the class of problem where heuristics are known to be strong competitors. Results should not be extrapolated to supply chain settings that involve exceptions, disruptions, unstructured information, or multi-objective decisions.

**Final Recommendations:**

1. **In replenishment tasks with this profile** (single product, fixed lead times, low information state), do not use LLM agents as autonomous order-placement agents. Heuristics are faster, cheaper, more predictable, and performed far better on both metrics. Whether this conclusion holds in more complex settings — exceptions, disruptions, unstructured context — is an open question this experiment was not designed to answer.

2. **Higher inference spend showed no ordering benefit in this task.** The latency and cost increase of reasoning models (3.4× mean call time) produced no observed OVAR or stockout improvement. This is a directional observation, not a controlled comparison of reasoning capability alone.

3. **Use LLMs for demand interpretation and planning rationale.** The aggregated pattern score does not separately report keyword and elevation sub-scores, so the extent to which agents articulate seasonal dynamics correctly cannot be confirmed from the available summary data alone. Where qualitative rationale quality matters, inspect individual run records directly. If that analysis supports it, use agents to generate commentary or flag anomalies — then execute adjustments through a deterministic model.

4. **Local inference is worth evaluating** for simulation workloads. In this task, local gpt-oss:120b produced similar OVAR means to frontier o4-mini with zero failures and lower latency variance (p95: 6,844ms vs 11,128ms). The comparison is confounded by model and quantisation differences and should not be extrapolated to a general infrastructure equivalence claim.

The path to reliable agentic supply chains requires bridging the gap between semantic reasoning and numerical precision. Until that bridge is built, the heuristic remains the most reliable guardian against the Bullwhip.

---

## Appendix: Technical Notes

**Experiment structure:**

| Experiment | Conditions | Runs | Total API calls | Wall time |
| :--- | :--- | :---: | :---: | :--- |
| Baselines | 3 heuristics | 1 each | 0 | < 1 min |
| E1 (Azure) | blind_lw, context_lw | 20 each | 2,880 | ~82 min |
| E1 (Local) | blind_lw, context_lw | 20 each | 2,880 | ~111 min |
| E2 (Azure) | blind_rsn, context_rsn | 20 each | 2,880 | ~278 min |
| E2 (Local) | blind_rsn, context_rsn | 20 each | 2,880 | ~244 min |

API calls per condition = 20 runs × 3 tiers × 24 ordering periods = 1,440.

**Retry and parse errors:** Retry rate = 0.0% across all 11,520 LLM calls. No runs required replacement.

**Temperature notes:** gpt-4.1-mini and phi4:14b ran at T=0.4 in E1. o4-mini (Azure) is API-constrained to internal temperature ≈ 1.0 regardless of caller-supplied value. gpt-oss:120b ran at T=0.0 (blind) and T=0.3 (context) in E2.

**Determinism observation:** phi4:14b at T=0.4 (blind condition) and gpt-oss:120b at T=0.0 (blind condition) produced zero inter-run variance across 20 runs. Standard deviation was at machine epsilon (~9×10⁻¹⁶). This indicates both models' output distributions were sharply peaked for blind-condition prompts.

**Data integrity:** SHA-256 checksum `c9b26afdbfd551f4f88f72eb119292a3ed0e9c2619c787a26b29d63250539c4e` recorded in E1/E2 provenance files confirms identical demand series across all runs.

**Result artifacts:** Raw run outputs (`records.parquet`, `summary.json`, `provenance.json`) are written by the runner to `code/results/<experiment>/<timestamp>/` and are required for full auditability and reproducibility. Summary statistics and provenance details in this report are derived from those files. Anyone seeking to verify or reproduce individual run-level results should locate or regenerate those artifacts; the summary statistics reported here cannot substitute for them.

**Disclaimer:** Personal experiments. Data is synthetic. No employer, vendor, or technology partner data was used. Local compute runs on an Asus Ascent GX10 with NVIDIA GB10 Blackwell SoC — personally owned. Azure and other AI subscriptions are personal in nature. 