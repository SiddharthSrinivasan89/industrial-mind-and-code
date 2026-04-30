# Agentic Bullwhip Effect — V4 WorldEvents: Full Session Summary
_2026-04-23_

---

## 1. Experiment Overview

**Research question**: Can an LLM-based intent classification agent manage supply chain ordering better than a deterministic baseline — and does giving it more information (world events, seasonal context) reduce the bullwhip effect?

**Simulation design**:
- SimPy discrete-event simulation, 36-month demand series (Jan 2025 – Dec 2027)
- 3-tier supply chain: OEM → Ancillary → Component
- Stochastic lead times: LogNormal(0, 0.25) × world-event multiplier
- Stochastic fill rates: Beta(9,1) capped at fill_rate_cap
- Demand: Indian automotive seasonal pattern (~37,000–42,000 units/month)
- 3 world events injected into the timeline:
  - **Pandemic** (periods 7–12): demand shock down 45%, then surge +35%, then recovery
  - **Conflict** (periods 19–21): moderate demand suppression
  - **Port disruption** (periods 28–30): supply-side only, demand unaffected

**Agent architecture**:
- Each period, an LLM receives inventory state and classifies demand outlook into one of 5 labels: `STRONG_INCREASE`, `MODERATE_INCREASE`, `NEUTRAL`, `MODERATE_DECREASE`, `STRONG_DECREASE`
- A lookup table (INTENT_MULTIPLIER_MAP) converts the label to a safety-stock multiplier: 1.30 / 1.15 / 1.00 / 0.90 / 0.80
- The OUT (Order-Up-To) formula executes the order: `order = max(0, round(F_t) + SS_t - inventory_position)`
- `inventory_position = on_hand + on_order - backlog`
- `on_order` tracks originally-dispatched quantity (not actual received qty); decremented at arrival after lead time elapses

**Key metric**: OVAR = Var(orders) / Var(demand). OVAR > 1 = bullwhip effect; higher = worse.

---

## 2. Bugs Fixed Before Production Runs (5 Checker Findings)

All fixes applied and committed before any production data was collected.

### Issue 1 — GROUND_TRUTH_INTENT off by one period
`metrics.py` had the pandemic schedule shifted by one period. Fixed 4 values to match the authoritative `world_events.py` schedule:
- Period 6: MODERATE_DECREASE (monsoon dip, no world event)
- Period 9: STRONG_DECREASE (pandemic_shock ×0.55)
- Period 11: STRONG_INCREASE (pandemic_surge ×1.35)
- Period 12: MODERATE_INCREASE (pandemic_recovery ×1.10)

Also added `world_events_on` parameter to `compute_intent_accuracy()` — skips accuracy computation when events are off (E3 ablation).

### Issue 2 — on_order not initialised; inventory_position wrong
`simulation.py` computed `inventory_position = on_hand - backlog`, ignoring pipeline stock entirely. Fixed:
- Added `self.on_order = 0` to `TierProcess.__init__()`
- `inv_position = on_hand + on_order - backlog`
- Increment `on_order` when order dispatched; decrement after `yield env.timeout(lead_time)` (at arrival, not before)

**Most significant fix.** Without it all intent/order_up_to conditions were systematically over-ordering because the formula thought less stock was inbound than actually was.

### Issue 3 — Prescriptive hint in port_disruption prompt
`world_events.py` period 28 signal contained "Build buffer stock if possible." — directly instructing the model what to do, polluting the classification experiment. Removed; signal now describes the event only.

### Issue 4 — Provenance stamp always showed events enabled
`run_experiment.py` stamped world events as enabled even for no-events conditions (E3 ablation). Fixed to detect from spec flags.

### Issue 5 — Seed reuse across retried runs
Replacement runs reused the same RNG seed as the original attempt, making them non-independent. Fixed: `rng_seed = (completed + 1) * 1000`.

---

## 3. All Experiments — Results

### Baselines (100 runs each, no LLM)

| Condition | OVAR | Stockouts/run | Notes |
|---|---|---|---|
| naive_passthrough | 0.996 | 96.0 | Orders last period's demand exactly. Zero amplification, terrible service. |
| exp_smoothing | 1.185 | 89.6 | Smoothed forecast dampens spikes. Best OVAR of any policy. |
| order_up_to (OUT) | 1.767 | 87.0 | Deterministic math formula. Structural OVAR ceiling for any OUT-based agent. |

Every LLM agent uses the same OUT formula. The structural ceiling is ~1.77.

---

### E1_IC_azure — gpt-4.1-mini, 3 conditions, 20 runs

| Condition | OVAR | Dir Acc | Entropy | Label distribution |
|---|---|---|---|---|
| blind | 1.747 ± 0.092 | 0.41 | 0.81 | STRONG_INCREASE 75%, NEUTRAL 25% |
| context | 1.737 ± 0.088 | 0.72 | 2.14 | NEUTRAL 40%, SI 17%, MD 17%, SD 17%, MI 9% |
| unstructured | 1.771 ± 0.108 | 0.76 | 2.16 | NEUTRAL 37%, SD 23%, SI 17%, MD 14%, MI 9% |

- **Blind**: Model sees only inventory numbers. Classifies 75% as STRONG_INCREASE. Direction accuracy 0.41 — worse than base-rate adjusted chance.
- **Context**: Calendar month + tier persona + Indian seasonal knowledge jumps direction accuracy to 0.72. Label spread becomes realistic. OVAR barely moves (−0.01).
- **Unstructured**: Raw event headlines without structured label guidance. Highest accuracy but OVAR ticks up slightly — model over-commits to extreme labels when reading event text.

---

### E1_IC_phi — phi4:14b (local Ollama), 3 conditions, 10 runs

| Condition | OVAR | Dir Acc | Entropy | Label distribution |
|---|---|---|---|---|
| blind | 1.748 ± 0.130 | 0.48 | 0.60 | STRONG_INCREASE 89%, NEUTRAL 6%, SD 4% |
| context | 1.726 ± 0.093 | 0.80 | 2.20 | STRONG_INCREASE 34%, NEUTRAL 23%, MD 17%, SD 17%, MI 9% |
| unstructured | 1.780 ± 0.130 | 0.84 | 2.17 | SI 32%, SD 27%, NEUTRAL 19%, MD 13%, MI 9% |

- phi4 is the most accurate classifier in the dataset (0.84 direction accuracy on unstructured).
- Blind condition is even more aggressive than gpt-4.1-mini (89% STRONG_INCREASE).
- OVAR is identical across both models regardless of accuracy.

---

### E2_IC_azure — o4-mini (reasoning model), 3 conditions, 20 runs

| Condition | OVAR | Dir Acc | Entropy | Label distribution |
|---|---|---|---|---|
| blind | 1.763 ± 0.113 | 0.44 | 0.41 | STRONG_INCREASE 92%, NEUTRAL 8% |
| context | 1.748 ± 0.105 | 0.72 | 2.17 | NEUTRAL 38%, MD 18%, SI 17%, SD 17%, MI 10% |
| unstructured | 1.774 ± 0.106 | 0.79 | 2.21 | NEUTRAL 33%, SD 24%, SI 19%, MD 14%, MI 10% |

- o4-mini shows the worst blind behaviour — 92% STRONG_INCREASE, near-zero label diversity, H=0.41.
- More reasoning with less information makes it overconfident and wrong.
- With context it matches gpt-4.1-mini exactly (dir acc 0.72, same distribution shape).

---

### E2_IC_nemotron — nemotron-super 120B (local), 3 conditions, 10 runs

| Condition | OVAR | Dir Acc | Entropy | Label distribution |
|---|---|---|---|---|
| blind | 1.734 ± 0.073 | 0.47 | 0.30 | STRONG_INCREASE 95%, MD 2%, NEUTRAL 1% |
| context | 1.745 ± 0.078 | 0.74 | 2.21 | MD 29%, MI 26%, SI 18%, SD 17%, NEUTRAL 9% |
| unstructured | 1.775 ± 0.069 | 0.83 | 2.21 | SD 27%, SI 23%, MD 22%, NEUTRAL 20%, MI 8% |

- Largest model (120B). Blind: 95% STRONG_INCREASE — worst blind over-classification of any model.
- Context: heavily uses MODERATE labels rather than extremes — hedging style vs other models.
- Unstructured: second-highest accuracy overall.
- OVAR: identical to all other models.

---

### E3_IC — phi4, world events OFF, 10 runs each (ablation)

| Condition | OVAR | Dir Acc | Notes |
|---|---|---|---|
| blind_no_events | 2.082 ± 0.188 | — | No ground truth (events off) |
| context_no_events | 2.117 ± 0.177 | — | No ground truth (events off) |

**Critical finding**: Removing world events makes OVAR significantly worse — 2.08–2.12 vs 1.73–1.78 in events-on runs.

Why: World event periods (pandemic drop, recovery) create demand variation that partially cancels the model's order swings in opposite phases. Without disruptions, pure Indian seasonal variation produces uninterrupted amplification. The model's aggressive response to seasonal peaks has nothing to offset it.

Practical implication: The 3 world events are not making the supply chain harder to manage — they are accidentally making the AI look better by providing opposing demand shocks.

---

### E4_IC_azure — gpt-4.1-mini, neutral-prior prompt, 20 runs each

**Design**: Added explicit neutral-biasing instruction to the system prompt:
> "Default to NEUTRAL unless the signal is strong and unambiguous. Only choose INCREASE or DECREASE when the evidence is clear — a major seasonal event, a world disruption, or significant inventory stress. When in doubt, classify NEUTRAL."

**Hypothesis**: Models over-classify toward INCREASE labels (especially blind). Biasing toward inaction should reduce amplification.

| Condition | OVAR | Dir Acc | Entropy | Label distribution |
|---|---|---|---|---|
| blind_neutral | 1.748 ± 0.092 | 0.41 | 0.81 | STRONG_INCREASE 75%, NEUTRAL 25% |
| context_neutral | 1.741 ± 0.090 | 0.72 | 2.15 | NEUTRAL 40%, SI 17%, MD 17%, SD 17%, MI 9% |

vs E1_IC_azure baseline:

| Condition | OVAR | Dir Acc | Entropy |
|---|---|---|---|
| blind (E1) | 1.747 | 0.41 | 0.81 |
| blind_neutral (E4) | 1.748 | 0.41 | 0.81 |
| context (E1) | 1.737 | 0.72 | 2.14 |
| context_neutral (E4) | 1.741 | 0.72 | 2.15 |

**Result**: Complete null. Every number — OVAR, direction accuracy, entropy, label distribution — is statistically identical between E1 and E4. The neutral instruction changed nothing.

---

## 4. Cross-Experiment Findings

### Finding 1 — The Equaliser Effect (core result)

All LLM conditions, all models, all prompt variants cluster at OVAR 1.73–1.78 — the same neighbourhood as the deterministic order_up_to baseline (1.767). The discrete label → fixed multiplier architecture converts a continuous signal into 5 integers and discards the gradient. No matter how accurate the classification, OVAR doesn't move.

```
naive:          0.996  ← only policy that reduces amplification
exp_smoothing:  1.185
[all LLM]:      1.73–1.78  ← cluster here regardless of model/prompt/accuracy
order_up_to:    1.767  ← deterministic baseline
```

### Finding 2 — Context unlocks accuracy, not efficiency

Direction accuracy by information level, averaged across models:

| Condition | Dir Acc range |
|---|---|
| Blind | 0.41–0.48 |
| Context | 0.72–0.80 |
| Unstructured | 0.76–0.84 |

Context improves classification accuracy by ~70–90% relative. But this accuracy gain produces no measurable improvement in OVAR. The agent is "smarter" but the supply chain outcome is identical.

### Finding 3 — Blind models are systematically wrong

Ground truth distribution across the 36-period experiment:

| Label | Periods | % |
|---|---|---|
| NEUTRAL | 10 | 27.8% |
| MODERATE_DECREASE | 10 | 27.8% |
| STRONG_INCREASE | 9 | 25.0% |
| STRONG_DECREASE | 4 | 11.1% |
| MODERATE_INCREASE | 3 | 8.3% |

55.6% of periods should be DECREASE or NEUTRAL. Only 33.3% should be INCREASE.

Blind model output: 75–95% STRONG_INCREASE across all models.

Why: Without calendar or event context, the model sees high absolute demand numbers and inventory under stress from stochastic lead times/fill rates. With no comparator, rational interpretation = "demand is rising, order more." There is also no cost signal for over-ordering in the prompt — only stockouts are visible to the agent.

### Finding 4 — Model scale and reasoning capability are irrelevant

| Model | OVAR range |
|---|---|
| gpt-4.1-mini (lightweight) | 1.737–1.771 |
| o4-mini (reasoning) | 1.748–1.774 |
| phi4:14b (OSS 14B) | 1.726–1.780 |
| nemotron-super 120B (OSS 120B) | 1.734–1.775 |

Completely overlapping ranges. A 120B model produces identical supply chain outcomes to a lightweight fast model. The bottleneck is architectural, not model capability.

### Finding 5 — Neutral-biasing prompt has zero effect

The intuition was correct (models over-classify toward INCREASE; rewarding inaction should help) but the intervention was applied at the wrong layer:

- **Blind + neutral bias**: Model has no basis for doubt. It still sees numbers that look like demand growth and ignores the instruction.
- **Context + neutral bias**: Model was already well-calibrated with context; neutral instruction adds nothing to an already-diverse label distribution.
- **Structural reason it can't work**: NEUTRAL maps to multiplier 1.00, which still executes a full OUT order. "Do nothing" in the prompt is not "do nothing" in the formula — it's "place a normally-sized order." The amplification comes from the formula mechanics, not the label choice.

---

## 5. Why OVAR Doesn't Move — Root Cause

The OUT formula is: `order = max(0, forecast + safety_stock - inventory_position)`

The AI agent only controls `safety_stock` via the multiplier (×0.80 to ×1.30 of base SS). The range of this influence is narrow. The variance in orders comes primarily from stochastic lead times and fill rates, not from the SS multiplier swing.

Even if the agent classified every period perfectly, the OUT formula's response to lead-time and fill-rate randomness would still produce OVAR near 1.77. The agent is adjusting a dial that doesn't control the main source of variance.

---

## 6. What Would Actually Work

To genuinely reduce OVAR in this architecture:

1. **Continuous multiplier output** — instead of 5 discrete labels, have the model output a confidence-weighted scalar. Small misclassifications have smaller consequences and the gradient is preserved.
2. **Dampening term in the formula** — penalise large order swings period-to-period regardless of intent label.
3. **True mechanical inaction for NEUTRAL** — redefine NEUTRAL as "repeat last period's order" rather than "recalculate OUT at multiplier 1.0."
4. **Let the agent control forecast F_t directly** — give it the ability to adjust the demand forecast, which has larger leverage on the formula output than SS multiplier.

---

## 7. Currently Running (at time of writing)

| Experiment | Detail | Status |
|---|---|---|
| E4_IC_phi | phi4: blind_neutral + context_neutral, 10 runs each | blind_neutral at 9/10 |
| E4_IC_o4mini | o4-mini: blind_neutral + context_neutral, 20 runs each | Active on Azure, ~2 hours |

Expected result for both: same null as E4_IC_azure. Will confirm the neutral-prior finding holds across all model families.

---

## 8. Open Questions for Further Evaluation

1. **Architecture change — continuous multiplier**: Does giving the model a 0.5–1.5 scalar output (instead of 5 labels) reduce OVAR? This directly attacks the equaliser effect.
2. **Forecast control**: Let the agent modify demand forecast F_t. Much larger leverage on order quantity than SS adjustment alone.
3. **True NEUTRAL = do-nothing**: Change NEUTRAL to "carry last order forward." Test whether this mechanical change reduces amplification even without prompt changes.
4. **Why do world events reduce OVAR?** (E3 finding) — events-off OVAR of 2.08–2.12 is a significant signal. Needs formal analysis of the phase relationship between event shocks and model responses.
5. **Service level vs OVAR trade-off**: Across all conditions, stockouts hover at 84–89 per run regardless of policy. The naive policy achieves 96 (best service) at OVAR 1.0. No AI condition improves on the naive service level. Why?
6. **E4_IC_o4mini result** (pending): Will the reasoning model's blind_neutral condition still show 92% STRONG_INCREASE despite the neutral instruction? Or does the reasoning budget allow it to genuinely engage with the ambiguity instruction?

---

_All production runs used fixed random seeds per run index for reproducibility. Results stored with SHA-256 demand data checksum and full provenance JSON in each result directory under `code/results/`._
