# V4 WorldEvents — Findings: Intent Classification in a Disrupted Supply Chain

## Executive Summary

This report documents Version 4 of my ongoing research into whether Large Language Models (LLMs) can meaningfully improve supply chain inventory management. V4 was directly motivated by a specific failure uncovered in V3b: the previous architecture asked the AI to invent a precise mathematical number (a multiplier like `1.34`), and it consistently over-estimated, causing dangerous inventory swings. **V4 tests the proposed fix: replace that free-form math with a multiple-choice question.**

Instead of calculating a number, the AI is now asked to classify the situation into one of five text labels — `STRONG_INCREASE`, `MODERATE_INCREASE`, `NEUTRAL`, `MODERATE_DECREASE`, or `STRONG_DECREASE`. A fixed, hard-coded lookup table then translates that label into a pre-approved multiplier. This is a fundamental architectural change: the AI reads the situation, and software does the math.

**The fix worked as a guardrail — but not as an improvement.** Compared to V3b, order variance was successfully contained (OVAR dropped from 2.3–3.1 down to 1.73–1.78). The AI no longer caused catastrophic amplification. However, all four AI models tested — from a lightweight fast model to a 120-billion-parameter reasoning behemoth — produced identical supply chain outcomes. No model, no prompt design, and no amount of additional information could push performance below the deterministic mathematical baseline.

I then ran a specific sub-experiment (E4) to test whether explicitly telling the AI to "do nothing unless the signal is clear" would reduce order variance. It did not. Not by a single meaningful unit.

**The core discovery of V4 is the Equaliser Effect**: the discrete-label architecture creates a structural ceiling and floor on OVAR. Once you commit to translating five text labels into five fixed numbers, you have removed the AI's ability to make fine-grained adjustments. All models, regardless of how intelligently they classify, are forced through the same narrow funnel.

### Key Takeaways

1. **The V3b fix worked as a guardrail, not an improvement.** Discrete labels prevented catastrophic over-ordering. But they did not enable AI to outperform a 1950s formula.
2. **The Equaliser Effect is the fundamental barrier.** Five labels → five fixed multipliers creates a ceiling that no prompt or model can escape. The AI's intelligence is discarded at the lookup table.
3. **Context makes the AI smarter, but not more effective.** Giving the AI calendar context and seasonal knowledge improved classification accuracy by 70–90% relative — yet OVAR did not move.
4. **Model size and reasoning capability are irrelevant to supply chain outcomes.** A 120B-parameter model and a lightweight fast model produced statistically identical OVAR values.
5. **You cannot prompt your way out of the bullwhip effect.** Explicitly biasing the AI toward inaction (E4) had zero measurable effect on any metric.
6. **World events accidentally dampen the bullwhip.** Removing world events from the simulation *worsened* OVAR from ~1.75 to ~2.10. The disruption shocks create demand variation that partially cancels the AI's over-ordering in opposite phases.

---

## 1. Background and Lineage

To understand V4, it helps to understand what came before.

| Version | Architecture | What the AI Did | Key Finding |
|---|---|---|---|
| V2 | AI orders directly | Computed exact unit quantities | LLM order variance far exceeded any baseline |
| V3b | AI sets a float multiplier × math formula | Invented a number like `1.34` | Float output unreliable; context made things worse; best OVAR 2.33 |
| **V4 WorldEvents** | AI picks a 5-label class → lookup → math formula | Chose one of 5 text labels | Guardrail success; Equaliser Effect discovered; best OVAR 1.73 |

**The Bullwhip Effect** is the central phenomenon under study. In a supply chain, small fluctuations in customer demand get amplified as they travel upstream — a 5% demand blip at the shop floor becomes a 20% order swing at the factory. This research measures amplification using **OVAR** (Order Variance Amplification Ratio):
- OVAR = 1.0 → perfect, orders match demand exactly
- OVAR > 1.0 → bullwhip effect; orders are more volatile than demand
- OVAR < 1.0 → system is actively smoothing demand (excellent)

**What V3b proposed at its close:** Restrict the AI to multiple-choice text outputs. Let hard-coded software handle the math. This is what V4 tests.

---

## 2. Methodology

### 2.1 The Architecture

Each month, for each of three supply chain tiers (OEM → Ancillary Supplier → Component Supplier), the AI receives the current inventory situation and answers one question: *"How should safety stock be adjusted this period?"*

```
LAYER 1 — AI Classification
  Input:  inventory state + optional context
  Output: one text label (e.g., "STRONG_INCREASE")
        ↓
LAYER 2 — Hard-coded Lookup (no AI)
  STRONG_INCREASE  → multiplier 1.30
  MODERATE_INCREASE→ multiplier 1.15
  NEUTRAL          → multiplier 1.00
  MODERATE_DECREASE→ multiplier 0.90
  STRONG_DECREASE  → multiplier 0.80
        ↓
LAYER 3 — Deterministic Math Formula (no AI)
  order = max(0, forecast + safety_stock × multiplier − inventory_position)
```

The AI's only contribution is the label. Everything downstream is traditional software.

### 2.2 Simulation Environment

- **Horizon:** 36 months (January 2025 – December 2027)
- **Demand:** Indian automotive industry seasonal pattern for Tatva Motors (OEM), averaging ~37,000–42,000 units/month
- **Lead times:** Stochastic (LogNormal distribution), further modified by world events
- **Fill rates:** Stochastic (Beta distribution), further capped during world events
- **World events injected:**
  - **Pandemic** (months 7–12): demand collapses −45%, then surges +35%, then recovers
  - **Geopolitical conflict** (months 19–21): moderate demand suppression, severe supply restriction
  - **Port strike** (months 28–30): supply-side disruption only; customer demand unaffected

### 2.3 Models Tested

| Model | Type | Deployed via |
|---|---|---|
| gpt-4.1-mini | Lightweight fast model | Microsoft Azure |
| o4-mini | Reasoning model | Microsoft Azure |
| phi4:14b | Open-source 14B | Local Ollama |
| nemotron-super 120B | Open-source 120B | Local Ollama |

### 2.4 Information Conditions

Each model was tested under three levels of information given to the AI:

1. **Blind:** AI sees only current inventory numbers. No calendar, no world event information.
2. **Context:** AI is told the calendar month and given a role-specific persona with knowledge of Indian automotive seasonal patterns. Does *not* receive world event signals.
3. **Unstructured:** Context plus live news-style event headlines during disruption periods (e.g., *"Global pandemic declared. Consumer demand has collapsed."*).

### 2.5 Sub-Experiments

| Experiment | Purpose | Runs |
|---|---|---|
| **Baselines** | Non-AI reference policies | 100 runs each |
| **E1_IC** (gpt-4.1-mini + phi4) | Core intent classification, all 3 conditions | 20 runs (gpt), 10 runs (phi4) |
| **E2_IC** (o4-mini + nemotron) | Reasoning-tier models, all 3 conditions | 20 runs (o4-mini), 10 runs (nemotron) |
| **E3_IC** | Ablation: world events OFF, phi4, blind + context | 10 runs each |
| **E4_IC** | Neutral-prior prompt: AI biased toward inaction | 20 runs (gpt, o4-mini), 10 runs (phi4) |

---

## 3. Results

### 3.1 Baseline Reference (No AI)

These three non-AI policies anchor the comparison. Every AI result must be judged against them.

| Policy | Chain OVAR | Stockouts/run | What it does |
|---|---|---|---|
| **naive_passthrough** | **0.996** | 96.0 | Orders exactly last month's demand. Zero amplification — but 96 stockouts per 36-month run means near-constant shortages. Not viable operationally. |
| **exp_smoothing** | **1.185** | 89.6 | Exponential smoothing formula. Dampens demand spikes. Best OVAR of any tested policy, including all AI conditions. |
| **order_up_to (OUT)** | **1.767** | 87.0 | The Order-Up-To formula — the same math every AI agent uses internally. This is the structural ceiling: any agent built on OUT will naturally land near this value. |

**Implication for all AI results below:** If an AI condition scores OVAR near 1.77, it has achieved no improvement over doing the math directly with no AI. If it scores above 1.77, the AI classification is actively making things worse than formula-only. The target to beat is exp_smoothing at 1.185.

---

### 3.2 E1_IC — Core Results (Lightweight Models)

#### gpt-4.1-mini (20 runs per condition)

| Condition | Chain OVAR | ±std | Stockouts | Dir Accuracy | Entropy | Dominant Label |
|---|---|---|---|---|---|---|
| Blind | 1.747 | 0.092 | 86.3 | 0.41 | 0.81 | STRONG_INCREASE 75% |
| Context | 1.737 | 0.088 | 87.0 | 0.72 | 2.14 | NEUTRAL 40%, all 5 used |
| Unstructured | 1.771 | 0.108 | 86.8 | 0.76 | 2.16 | NEUTRAL 37%, all 5 used |

#### phi4:14b (10 runs per condition)

| Condition | Chain OVAR | ±std | Stockouts | Dir Accuracy | Entropy | Dominant Label |
|---|---|---|---|---|---|---|
| Blind | 1.748 | 0.130 | 84.9 | 0.48 | 0.60 | STRONG_INCREASE 89% |
| Context | 1.726 | 0.093 | 86.7 | 0.80 | 2.20 | STRONG_INCREASE 34%, all 5 used |
| Unstructured | 1.780 | 0.130 | 86.2 | 0.84 | 2.17 | STRONG_INCREASE 32%, all 5 used |

**What to notice:** phi4 achieves the highest direction accuracy in the dataset (0.84 on unstructured) yet produces OVAR indistinguishable from gpt-4.1-mini. A model being twice as accurate at classification produces zero benefit in supply chain outcomes.

---

### 3.3 E2_IC — Reasoning Models

#### o4-mini (20 runs per condition)

| Condition | Chain OVAR | ±std | Stockouts | Dir Accuracy | Entropy | Dominant Label |
|---|---|---|---|---|---|---|
| Blind | 1.763 | 0.113 | 85.3 | 0.44 | 0.41 | STRONG_INCREASE 92% |
| Context | 1.748 | 0.105 | 87.0 | 0.72 | 2.17 | NEUTRAL 38%, all 5 used |
| Unstructured | 1.774 | 0.106 | 86.7 | 0.79 | 2.21 | NEUTRAL 33%, all 5 used |

#### nemotron-super 120B (10 runs per condition)

| Condition | Chain OVAR | ±std | Stockouts | Dir Accuracy | Entropy | Dominant Label |
|---|---|---|---|---|---|---|
| Blind | 1.734 | 0.133 | 84.7 | 0.47 | 0.30 | STRONG_INCREASE 95% |
| Context | 1.745 | 0.128 | 86.7 | 0.74 | 2.21 | MOD_DECREASE 29%, MOD_INCREASE 26% |
| Unstructured | 1.775 | 0.130 | 86.7 | 0.83 | 2.21 | All 5 labels, well-spread |

**What to notice:** o4-mini's blind condition is the worst in the dataset — 92% STRONG_INCREASE and H=0.41 (near-zero diversity). A reasoning model with nothing to reason about becomes aggressively overconfident. Nemotron at 120B parameters matches o4-mini and gpt-4.1-mini on OVAR despite being 10× larger.

---

### 3.4 Cross-Model OVAR Summary

The full range of all AI conditions across all models and information levels:

| Model | OVAR range (all conditions) |
|---|---|
| gpt-4.1-mini | 1.737 – 1.771 |
| o4-mini | 1.748 – 1.774 |
| phi4:14b | 1.726 – 1.780 |
| nemotron 120B | 1.734 – 1.775 |
| **exp_smoothing (target)** | **1.185** |
| **order_up_to (structural ceiling)** | **1.767** |

All four models, across all conditions, fall within the same 0.05-unit band — and that band sits right on top of the order_up_to baseline. No model or condition has come close to exp_smoothing.

---

### 3.5 E3_IC — World Events Ablation (What Happens Without Disruptions?)

phi4:14b, blind and context conditions, world events disabled. 10 runs each.

| Condition | Chain OVAR | ±std | Stockouts | Notes |
|---|---|---|---|---|
| Blind, no events | 2.082 | 0.199 | 50.0 | OVAR significantly worse than events-on |
| Context, no events | 2.117 | 0.205 | 53.5 | Highest OVAR of any AI condition in the experiment |

**Comparison to events-on equivalents:**
- phi4 blind with events: OVAR 1.748 → without events: OVAR 2.082 (+19%)
- phi4 context with events: OVAR 1.726 → without events: OVAR 2.117 (+23%)

This is a counterintuitive and important finding, discussed in detail in Section 5.

---

### 3.6 E4_IC — Neutral-Prior Sub-Experiment (Rewarding Inaction)

This sub-experiment was designed to test whether explicitly instructing the AI to "do nothing unless the signal is strong" would reduce order amplification. The prompt instruction added was: *"Default to NEUTRAL unless the signal is strong and unambiguous. When in doubt, classify NEUTRAL."*

#### gpt-4.1-mini (20 runs per condition)

| Condition | OVAR | Dir Acc | Entropy | Label Distribution |
|---|---|---|---|---|
| Blind (E1 baseline) | 1.747 | 0.41 | 0.81 | STRONG_INC 75%, NEUTRAL 25% |
| Blind + neutral prior (E4) | 1.748 | 0.41 | 0.81 | STRONG_INC 75%, NEUTRAL 25% |
| Context (E1 baseline) | 1.737 | 0.72 | 2.14 | NEUTRAL 40%, all 5 |
| Context + neutral prior (E4) | 1.741 | 0.72 | 2.15 | NEUTRAL 40%, all 5 |

#### phi4:14b (10 runs per condition)

| Condition | OVAR | Dir Acc | Entropy | Label Distribution |
|---|---|---|---|---|
| Blind (E1 baseline) | 1.748 | 0.48 | 0.60 | STRONG_INC 89%, NEUTRAL 6% |
| Blind + neutral prior (E4) | 1.742 | 0.45 | 1.00 | STRONG_INC 77%, NEUTRAL 15% |
| Context (E1 baseline) | 1.726 | 0.80 | 2.20 | STRONG_INC 34%, NEUTRAL 23% |
| Context + neutral prior (E4) | 1.725 | 0.80 | 2.13 | STRONG_INC 41%, NEUTRAL 13% |

#### o4-mini (20 runs per condition)

| Condition | OVAR | Dir Acc | Entropy | Label Distribution |
|---|---|---|---|---|
| Blind (E2 baseline) | 1.763 | 0.44 | 0.41 | STRONG_INC 92%, NEUTRAL 8% |
| Blind + neutral prior (E4) | 1.748 | 0.42 | 0.81 | STRONG_INC 77%, NEUTRAL 22% |
| Context (E2 baseline) | 1.748 | 0.72 | 2.17 | NEUTRAL 38%, all 5 used |
| Context + neutral prior (E4) | 1.740 | 0.73 | 2.20 | NEUTRAL 33%, all 5 used |

Note: o4-mini's blind condition showed more visible behavioural change than the other models — STRONG_INCREASE dropped from 92% to 77%, and entropy nearly doubled from 0.41 to 0.81. This is because o4-mini was the most collapsed of all blind conditions (near-zero label diversity), so the neutral instruction had the most room to move the distribution. Yet OVAR moved by only 0.015 — confirming that label distribution shifts do not translate to OVAR changes in this architecture.

**Result across all three models:** Complete null on OVAR. The neutral-prior instruction is a prompt-layer intervention and cannot reach the architectural source of amplification.

---

## 4. Hypothesis Outcomes

The experiment pre-defined five hypotheses.

### H1: Can intent classification match or beat exp_smoothing?
**Threshold:** Best IC OVAR ≤ 1.185 (exp_smoothing)
**Result: FAILED.**
Best AI OVAR achieved: 1.726 (phi4 context). This is 46% higher than exp_smoothing. No model, in any condition, came close.

### H2: Does world event signal (unstructured) reduce OVAR vs calendar-only (context)?
**Threshold:** Unstructured OVAR ≤ Context OVAR
**Result: FAILED.**
In every model tested, the unstructured condition produced *higher* OVAR than context — not lower. gpt-4.1-mini: 1.771 vs 1.737. phi4: 1.780 vs 1.726. o4-mini: 1.774 vs 1.748. nemotron: 1.775 vs 1.745.

When shown explicit disruption headlines, models over-committed to extreme labels (`STRONG_INCREASE`, `STRONG_DECREASE`), adding noise to the order formula rather than precision. More information, in this format, made outcomes slightly worse.

### H3: Does world event signal improve direction accuracy by ≥ 10 percentage points?
**Threshold:** Unstructured direction accuracy − Context direction accuracy ≥ 0.10
**Result: FAILED.**
Observed deltas: gpt-4.1-mini +0.04, phi4 +0.04, o4-mini +0.07, nemotron +0.09. None reached the 0.10 threshold. The largest gain (nemotron, 0.74→0.83) came close but fell short.

### H4: Does intent compliance remain ≥ 0.99 under disruption conditions?
**Threshold:** Compliance rate ≥ 0.99 across all conditions
**Result: PASSED.**
Intent compliance was 1.00 (perfect) across every condition and every model. Even emotionally charged pandemic and conflict headlines did not cause JSON parse failures. The structured output interface proved robust.

### H5: Does adding world events materially change OVAR?
**Threshold:** E1_IC OVAR ≠ E3_IC OVAR (either direction)
**Result: PASSED — but in a surprising direction.**
E1_IC (events on) OVAR: 1.73–1.78. E3_IC (events off) OVAR: 2.08–2.12. World events are present → lower OVAR. World events removed → higher OVAR. See Section 5.3 for the explanation.

---

## 5. Key Observations

### 5.1 The Equaliser Effect — Why No Model or Prompt Can Move OVAR

This is the central finding of V4. Regardless of which model was used, how much context was provided, or how the prompt was framed, every AI condition produced OVAR in a tight band of 1.73–1.78. The reason is architectural.

The AI controls only one variable: the safety stock multiplier (range: 0.80 to 1.30). Order amplification in this simulation is primarily driven by stochastic lead times and fill rates — randomness in when stock arrives and how much of an order gets fulfilled. These are features of the physical supply chain, not of the AI's decision. Even if the AI classified every single period perfectly, the OUT formula's response to arrival randomness would still produce OVAR near 1.77.

**An analogy:** A pilot can move the rudder, but if the aircraft is in turbulence, the rudder affects heading — not altitude loss. The AI is adjusting a control surface that governs the wrong dimension of the problem.

### 5.2 Context Unlocks Accuracy, Not Efficiency

One of the clearest patterns in the data is the gap between what context does to classification accuracy versus what it does to supply chain outcomes.

| Information level | Direction accuracy (avg across models) | OVAR change vs blind |
|---|---|---|
| Blind | 0.41 – 0.48 | — |
| Context | 0.72 – 0.80 | −0.01 to −0.02 |
| Unstructured | 0.76 – 0.84 | +0.01 to +0.03 |

Adding a calendar and a persona roughly doubles the model's ability to correctly identify which direction demand is moving. Direction accuracy goes from ~44% to ~75%. This is a genuine and substantial improvement in the AI's situational awareness.

Yet OVAR improves by roughly one percent. The accuracy improvement is real — it simply doesn't flow through to the outcome that matters, because the lookup table bottlenecks it.

### 5.3 The Counter-Intuitive World Events Finding

The ablation (E3_IC) produced the most surprising number in the entire dataset: removing world events *increased* OVAR from ~1.75 to ~2.10.

The explanation lies in the phase structure of disruptions. The pandemic sequence (months 7–12) creates a sharp demand drop followed by a sharp surge. The model, ordering aggressively during the surge, generates large positive order spikes. But because those spikes are anchored to a specific narrow window of elevated demand, the ratio of order variance to demand variance stays contained. The disruption generates both the signal *and* the noise in a correlated way.

Without world events, the simulation runs on pure Indian automotive seasonal variation — a smoother but relentlessly upward trend (monsoon dip → festival surge → year-end peak). The model's aggressive blind ordering creates order swings that are not correlated with any matching demand shock. The denominator (demand variance) shrinks; the numerator (order variance) grows. OVAR worsens.

**The practical warning:** Disruption events can create false impressions of AI effectiveness. If you evaluate this architecture only during disrupted periods, the AI appears to be managing variance well. The cleaner test — pure seasonal variation — reveals the underlying amplification.

### 5.4 Blind Models Are Systematically Wrong, and It Doesn't Matter

The ground truth intent distribution across the 36-month simulation:

| True intent | % of periods |
|---|---|
| NEUTRAL or DECREASE (combined) | **55.6%** |
| INCREASE (any) | **33.3%** |

What blind models actually classify:

| Model | STRONG_INCREASE | All other labels |
|---|---|---|
| gpt-4.1-mini (blind) | 75% | 25% |
| o4-mini (blind) | 92% | 8% |
| phi4:14b (blind) | 89% | 11% |
| nemotron 120B (blind) | 95% | 5% |

Without context, every model defaults to aggressive over-classification toward STRONG_INCREASE, despite the majority of periods requiring restraint or reduction. This systematic bias is empirically clear, consistent across four different model families, and perfectly intuitive: with only inventory numbers and no calendar or event context, the model sees stock being consumed and no reason not to order more.

**The critical insight:** This dramatic misclassification — 75–95% STRONG_INCREASE when only 25% of periods actually warrant it — produces an OVAR difference of less than 0.02 compared to the accurate context condition. The AI is catastrophically wrong in its blind state, but the discrete architecture is so rigid that even catastrophic misclassification barely affects the output.

### 5.5 The Neutral-Prior Null Result

The E4 sub-experiment tested the direct intervention: explicitly tell the model to default to inaction. The instruction was clear. The result was clearer.

**Why the blind condition didn't respond:** The model classifies STRONG_INCREASE because it genuinely believes demand is rising, based on the numbers it can see. An instruction to be sceptical of that conclusion has nothing to attach to — the model has no alternative signal to doubt itself with.

**Why the context condition didn't respond:** The context condition was already self-regulating. With a calendar and persona, the model naturally uses all five labels with NEUTRAL as the dominant choice (~40% of periods). There was no over-classification problem to correct.

**The deeper reason it can never work:** Even if the neutral instruction successfully pushed 100% of classifications to NEUTRAL, OVAR would not drop. The NEUTRAL label maps to multiplier 1.00, which still executes a full Order-Up-To calculation. "Do nothing" in the prompt is not "do nothing" in the formula.

---

## 6. Tier-Level OVAR — Where Amplification Lives

Across all AI conditions, amplification is concentrated at the OEM tier and diminishes upstream:

| Tier | Typical OVAR range |
|---|---|
| OEM (closest to customer) | 2.51 – 2.61 |
| Ancillary | 1.34 – 1.39 |
| Component | 1.31 – 1.36 |

The OEM tier, which directly receives customer demand noise plus stochastic fill rates from its supplier, carries the largest amplification load. The same pattern holds across all models and conditions — the bullwhip is not distributed; it is generated at the OEM interface and attenuates upstream.

---

## 7. Implications for V5

V4 proves the discrete-label architecture works as a safety guardrail but cannot be an improvement mechanism. To actually reduce OVAR, the architecture must change. Three candidates:

### Option A — Continuous Confidence Output
Instead of five discrete labels, the model outputs a confidence-weighted scalar between 0.5 and 1.5. A classification of "slight increase" produces a multiplier of 1.08 rather than the binary jump from 1.00 to 1.30. Small misclassifications have proportionally smaller consequences. This preserves the AI-in-the-loop architecture while removing the bottleneck.

### Option B — Dampening Term in the Formula
Add a term to the OUT formula that penalises large order swings period-to-period, regardless of intent label. This is a purely mechanical change — no AI involved — that structurally caps amplification. The AI continues classifying; the formula becomes self-dampening.

### Option C — Redefine NEUTRAL as True Inaction
Currently, NEUTRAL means "recalculate the full OUT order with multiplier 1.0." Change it to mean "repeat last period's order." A month where the AI picks NEUTRAL produces no new information — the supply chain carries forward its last decision. This directly tests whether true inaction reduces variance, and pairs naturally with a neutral-prior prompt design.

### Option D — Give the AI Forecast Control
The demand forecast F_t has much larger leverage on order quantity than the safety stock multiplier. Letting the AI propose a forecast adjustment (rather than a SS multiplier) would give it a lever that actually moves OVAR.

---

## 8. Summary Table — All Conditions

| Experiment | Condition | Model | n | OVAR | Dir Acc | Entropy |
|---|---|---|---|---|---|---|
| Baselines | naive_passthrough | — | 100 | 0.996 | — | — |
| Baselines | exp_smoothing | — | 100 | 1.185 | — | — |
| Baselines | order_up_to | — | 100 | 1.767 | — | — |
| E1_IC | blind | gpt-4.1-mini | 20 | 1.747 | 0.41 | 0.81 |
| E1_IC | context | gpt-4.1-mini | 20 | 1.737 | 0.72 | 2.14 |
| E1_IC | unstructured | gpt-4.1-mini | 20 | 1.771 | 0.76 | 2.16 |
| E1_IC | blind | phi4:14b | 10 | 1.748 | 0.48 | 0.60 |
| E1_IC | context | phi4:14b | 10 | 1.726 | 0.80 | 2.20 |
| E1_IC | unstructured | phi4:14b | 10 | 1.780 | 0.84 | 2.17 |
| E2_IC | blind | o4-mini | 20 | 1.763 | 0.44 | 0.41 |
| E2_IC | context | o4-mini | 20 | 1.748 | 0.72 | 2.17 |
| E2_IC | unstructured | o4-mini | 20 | 1.774 | 0.79 | 2.21 |
| E2_IC | blind | nemotron 120B | 10 | 1.734 | 0.47 | 0.30 |
| E2_IC | context | nemotron 120B | 10 | 1.745 | 0.74 | 2.21 |
| E2_IC | unstructured | nemotron 120B | 10 | 1.775 | 0.83 | 2.21 |
| E3_IC | blind, no events | phi4:14b | 10 | 2.082 | — | 0.79 |
| E3_IC | context, no events | phi4:14b | 10 | 2.117 | — | 2.22 |
| E4_IC | blind + neutral prior | gpt-4.1-mini | 20 | 1.748 | 0.41 | 0.81 |
| E4_IC | context + neutral prior | gpt-4.1-mini | 20 | 1.741 | 0.72 | 2.15 |
| E4_IC | blind + neutral prior | phi4:14b | 10 | 1.742 | 0.45 | 1.00 |
| E4_IC | context + neutral prior | phi4:14b | 10 | 1.725 | 0.80 | 2.13 |
| E4_IC | blind + neutral prior | o4-mini | 20 | 1.748 | 0.42 | 0.81 |
| E4_IC | context + neutral prior | o4-mini | 20 | 1.740 | 0.73 | 2.20 |

---

_All runs used fixed per-run RNG seeds for reproducibility. Each result directory contains a SHA-256 checksum of the demand dataset and a full provenance JSON. Production runs executed on Microsoft Azure (gpt-4.1-mini, o4-mini) and local Ollama (phi4:14b, nemotron 120B). All experiments complete as of 2026-04-23 16:29._

---

_Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience._
