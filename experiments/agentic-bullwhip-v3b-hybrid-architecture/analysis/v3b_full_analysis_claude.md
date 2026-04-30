
# V3b Hybrid Architecture — Full Three-Model Analysis
## nemotron-super-3:120b (local) · gpt-4.1-mini (Azure) · o4-mini (Azure)

---

## 1. Complete Results Table

### 1.1 Deterministic References (shared across all arms)

| Condition | Chain OVAR | Chain Stockouts | Mean On-Hand |
|---|---:|---:|---:|
| `exp_smoothing` | 0.5446 | 5.0 | 4,769 |
| `hybrid_control` | 1.7097 | 14.0 | 5,142 |

### 1.2 Hybrid Conditions — All Models

| Model | Condition | Chain OVAR | ±std | Stockouts | On-Hand | Mult Mean | MPS | PS |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| nemotron | H1 Blind | 2.4178 | 0.2814 | 12.2 | 6,511 | 1.2249 | 0.1591 | 0.1992 |
| nemotron | H2 Context | 2.7629 | 0.2319 | 12.3 | 6,852 | 1.3489 | **0.3977** | **0.3371** |
| nemotron | H3 Stateful | 2.6846 | 0.2413 | **9.6** | 6,943 | 1.3671 | 0.3273 | 0.2803 |
| gpt-4.1-mini | H1 Blind | **2.3325** | 0.1108 | 10.6 | 6,030 | 1.1298 | 0.1875 | 0.2011 |
| gpt-4.1-mini | H2 Context | 2.9763 | 0.0958 | 11.0 | 6,781 | 1.3103 | 0.2667 | 0.3125 |
| gpt-4.1-mini | H3 Stateful | 2.7226 | 0.1512 | 11.6 | 7,248 | 1.4291 | 0.3193 | 0.2826 |
| o4-mini | H1 Blind | 2.5232 | 0.2791 | **8.9** | 7,609 | 1.4808 | 0.3189 | 0.1958 |
| o4-mini | H2 Context | 2.4395 | 0.1616 | 11.7 | 6,487 | 1.2447 | 0.3250 | 0.3390 |
| o4-mini | H3 Stateful | 3.1211 | 0.1320 | 10.7 | 7,218 | 1.3488 | 0.3038 | 0.3106 |

### 1.3 Tier-Level OVAR Breakdown

| Model | Condition | OEM | Ancillary | Component |
|---|---|---:|---:|---:|
| nemotron | Blind | 2.6502 | 2.3858 | 2.2174 |
| nemotron | Context | 2.8050 | 2.8159 | 2.6678 |
| nemotron | Stateful | 2.5046 | 2.7763 | 2.7730 |
| gpt-4.1-mini | Blind | 2.3474 | 2.3125 | 2.3376 |
| gpt-4.1-mini | Context | 2.9930 | 3.0459 | 2.8899 |
| gpt-4.1-mini | Stateful | 2.7145 | 2.8206 | 2.6325 |
| o4-mini | Blind | 2.7265 | 2.4325 | 2.4107 |
| o4-mini | Context | 2.5640 | 2.4596 | 2.2950 |
| o4-mini | Stateful | 3.2188 | 3.2647 | 2.8797 |

---

## 2. Hypothesis Verdicts — All Models

| Hypothesis | nemotron | gpt-4.1-mini | o4-mini |
|---|---|---|---|
| H1: any hybrid ≤ exp_smoothing (OVAR + SO) | **Failed** | **Failed** | **Failed** |
| H2: context improves blind by ≥ 0.5 OVAR | **Failed** (−0.3451, worsened) | **Failed** (−0.6438, worsened) | **Failed** (+0.0837, too small) |
| H3: stateful improves context by ≥ 0.5 OVAR | **Failed** (+0.0783, too small) | **Failed** (+0.2537, too small) | **Failed** (−0.6816, worsened) |
| H4: context MPS ≥ 0.5 | **Failed** (0.3977, closest) | **Failed** (0.2667) | **Failed** (0.3250) |

All four hypotheses failed across all three models. This is the primary finding: a joint negative result replicated across a local reasoning model and two Azure models, under identical experimental protocol.

---

## 3. Cross-Model Findings

### 3.1 The Context Penalty

Two of three models — nemotron and gpt-4.1-mini — produced **worse** OVAR when given seasonal context compared to the blind condition:

| Model | Blind OVAR | Context OVAR | Delta |
|---|---:|---:|---:|
| nemotron | 2.4178 | 2.7629 | +0.3451 (worse) |
| gpt-4.1-mini | 2.3325 | 2.9763 | +0.6438 (worse) |
| o4-mini | 2.5232 | 2.4395 | −0.0837 (marginally better) |

Context information caused these models to increase their multipliers (nemotron: 1.22→1.35, gpt-4.1-mini: 1.13→1.31) without producing tighter variance. The multiplier increase inflated inventory but did not stabilize orders. o4-mini is the exception: context reduced its multiplier from 1.48 to 1.24 and produced a small OVAR improvement — suggesting it interpreted seasonal context as a reason to moderate its default over-buffering rather than amplify it.

### 3.2 The Stateful Divergence

Adding short-term history produced opposite effects across models:

- **nemotron and gpt-4.1-mini**: stateful partially recovered from the context-induced regression (OVAR improved vs context, though not vs blind)
- **o4-mini**: stateful condition was catastrophic — OVAR jumped from 2.44 to 3.12, the worst single condition in the entire experiment

The o4-mini stateful collapse is concentrated at the OEM and Ancillary tiers (3.22 and 3.26), suggesting reactive over-ordering at the upstream tiers when recent history is available. The reasoning model appears to anchor on recent negative signals (backlog, stockout events) and over-amplifies its response. This is precisely the behaviour that produces the bullwhip effect.

For nemotron, the stateful condition produced the lowest stockout count of any hybrid condition across all three models (9.6), despite not improving OVAR to competitive levels. The history may have helped it recognise and avoid under-ordering situations even if it did not suppress variance.

### 3.3 Multiplier Behaviour Patterns

Three distinct patterns emerged:

**gpt-4.1-mini — monotonic escalation:**
Blind (1.13) → Context (1.31) → Stateful (1.43). Every additional input layer increases buffering. Context causes a step-change; history amplifies further. The model treats more information as more reason to hold more stock.

**nemotron — moderate escalation:**
Blind (1.22) → Context (1.35) → Stateful (1.37). Similar direction to gpt-4.1-mini but less aggressive. The stateful increment is small (1.35→1.37), suggesting nemotron's history processing does not dramatically change its position.

**o4-mini — non-monotonic, context-sensitive:**
Blind (1.48) → Context (1.24) → Stateful (1.35). Starts most aggressive of all models without context, pulls back strongly when context is added, then increases again with history. The default state without any context is high caution; context provides a moderating signal; history then partially undoes that moderation.

All nine hybrid conditions showed mean multiplier above 1.0. No model in any condition learned to systematically reduce safety stock below the base level, even in low-demand months.

### 3.4 Semantic Alignment vs Operational Control

Pattern scores and multiplier pattern scores measure directional reasoning quality, independent of control performance. Key observations:

| Model | Context MPS | Context PS | OVAR (context) |
|---|---:|---:|---:|
| nemotron | **0.3977** | **0.3371** | 2.7629 (worst) |
| o4-mini | 0.3250 | 0.3390 | 2.4395 (best) |
| gpt-4.1-mini | 0.2667 | 0.3125 | 2.9763 (worst) |

nemotron achieves the highest semantic alignment scores across the entire experiment (MPS 0.40, PS 0.34) — yet produces the worst OVAR in the context condition among the three models. This is the clearest demonstration that semantic alignment and operational control are dissociated in this architecture. A model can correctly identify that December calls for higher safety stock while simultaneously producing multiplier values that destabilise the chain.

o4-mini achieves the second-best MPS with the best OVAR in the context condition — not because its alignment is perfect, but because its multiplier moderation happens to reduce over-buffering in a way that improves variance. The relationship is coincidental rather than causal.

### 3.5 Run-to-Run Variance

OVAR standard deviation across runs reflects how consistent each model's behaviour is:

| Model | Blind std | Context std | Stateful std |
|---|---:|---:|---:|
| nemotron | 0.2814 | 0.2319 | 0.2413 |
| gpt-4.1-mini | 0.1108 | 0.0958 | 0.1512 |
| o4-mini | 0.2791 | 0.1616 | 0.1320 |

gpt-4.1-mini shows consistently low run-to-run variance, especially in the context condition (std=0.096). This suggests more deterministic behaviour — the model's multiplier strategy is stable across runs but wrong. nemotron shows the highest variance, indicating more stochastic exploration. The practical implication: gpt-4.1-mini's failure is systematic (consistently bad), whereas nemotron's failure contains more run-level variation — some runs may perform better than average.

### 3.6 Best Condition by Metric

| Metric | Best value | Model + Condition |
|---|---:|---|
| Lowest OVAR | 2.3325 | gpt-4.1-mini H1 Blind |
| Lowest Stockouts | 8.9 | o4-mini H1 Blind |
| Best MPS | 0.3977 | nemotron H2 Context |
| Best PS | 0.3390 | o4-mini H2 Context |
| Lowest On-Hand | 6,030 | gpt-4.1-mini H1 Blind |

No single model dominates across all metrics. The blind condition produces the best OVAR for two models but the worst MPS. The context condition produces the best semantic scores but often the worst OVAR. The stateful condition produces the best stockouts for nemotron (9.6) but the worst OVAR for o4-mini (3.12).

---

## 4. Structural Interpretation

### 4.1 Why the Hybrid Formula is the Primary Constraint

Even before introducing the LLM, `hybrid_control` (multiplier=1.0) produces OVAR=1.7097 versus `exp_smoothing` OVAR=0.5446. This 3× gap means the LLM must choose multipliers that actively counteract the formula's inherent instability — not simply maintain a neutral buffer. None of the nine hybrid conditions achieved this. All exceeded `hybrid_control` OVAR, meaning the LLM's decisions uniformly made the formula worse, not better.

This is the structural limit of the V3b architecture: the execution layer is not competitive with `exp_smoothing`, and the planning layer cannot compensate for that gap through buffer adjustment alone.

### 4.2 Why Multipliers Above 1.0 Do Not Help

Higher safety stock reduces stockouts but increases the inventory position, which reduces the urgency of placing large orders — yet in the hybrid formula, the smoothed forecast `F_t` drives the order independently of inventory. Raising the multiplier inflates the target position, which can transiently suppress orders when inventory is high, then requires large catch-up orders when inventory depletes. This creates variance rather than suppressing it. The models' systematic over-buffering tendency therefore works against the OVAR objective regardless of the directional accuracy of the reasoning.

### 4.3 The Calibration Gap

MPS values across all conditions range from 0.16 to 0.40. The 0.25 expected-by-chance baseline (for a ternary up/down/neutral classification) is relevant here: all models score above chance on directional alignment, particularly in context and stateful conditions. The models have genuine — if weak — seasonal signal recognition capability.

The failure is not directional; it is calibration. A model that correctly identifies "December needs more buffer" but sets the multiplier at 2.3 when 1.05 would suffice produces the same OVAR harm as a model that guesses randomly. The continuous multiplier output requires precision that none of these models demonstrated. This is the core motivation for the V4 intent classifier design.

---

## 5. Implications for V4 Intent Classifier

The V3b results provide direct empirical grounding for four V4 design decisions:

**1. Discrete labels replace continuous multipliers.**
MPS scores (0.16–0.40) confirm directional capability exists. The failure is in calibration, not direction. Mapping intent labels to fixed multipliers by a lookup table removes the calibration requirement while preserving the directional signal.

**2. Multiplier calibration bounds from empirical data.**
All three models' mean multipliers across all conditions fell in the range 1.13–1.48. The safest interpretation: no model ever produced a mean multiplier below 1.1 or above 1.5. V4's lookup table should map STRONG_INCREASE to ~1.5, MODERATE_INCREASE to ~1.2, NEUTRAL to 1.0, MODERATE_DECREASE to ~0.85, STRONG_DECREASE to ~0.7 — spans calibrated to the observed behavioral range.

**3. Stateful condition requires careful design for o4-mini.**
o4-mini's stateful OVAR of 3.12 is the worst single result in the experiment. If V4 includes a stateful or history-aware condition, the o4-mini arm should be monitored carefully for reactive amplification. The intent classifier's discrete labels may help constrain this — a model cannot output a multiplier of 2.5 when the maximum STRONG_INCREASE maps to 1.5.

**4. nemotron MPS of 0.40 is the benchmark.**
The highest MPS achieved in V3b was nemotron context at 0.3977. V4's H_IC1x hypothesis (intent classifier achieves MPS ≥ 0.5) is a meaningful improvement target relative to V3b's ceiling. Achieving ≥ 0.5 would represent a qualitative improvement in the architecture's semantic alignment, not just incremental progress.

---

## 6. Canonical Result Set

| Arm | Model | Conditions | Runs | Timestamp dirs |
|---|---|---|---|---|
| Azure | gpt-4.1-mini | baselines, H1, H2, H3 | 20 | 20260415T040840, 20260415T050149, 20260415T055625 |
| Azure | o4-mini | baselines, H1, H2, H3 | 20 | 20260415T133112, 20260415T160633, 20260415T182338 |
| Local | nemotron-super-3:120b | H1, H2, H3 | 10 | 20260415T132021, 20260416T072509, 20260416T145130 |

Baselines (`exp_smoothing`, `hybrid_control`) are deterministic and identical across arms. The local arm uses the Azure baselines as its reference. All production runs passed validation: zero fallback, zero clamp, all active periods showed live inference, all OVAR values finite.

---

## 7. Conclusion

All four hypotheses failed across all three models under identical experimental protocol. The joint negative finding is robust: neither a local 120B reasoning model nor two Azure models (a fast generation model and a reasoning model) could improve supply-chain control beyond the deterministic `exp_smoothing` benchmark on this demand series.

The failures share a common structure. Every model showed systematic over-buffering (all mean multipliers above 1.0). Every model demonstrated partial but insufficient seasonal alignment (MPS 0.16–0.40). No model produced multiplier choices calibrated precisely enough to compensate for the hybrid formula's structural disadvantage.

The most analytically useful contrast is between nemotron and o4-mini: nemotron achieves the best semantic alignment (MPS 0.40) and the best stockout performance in the stateful condition (9.6), but produces the worst OVAR under context. o4-mini achieves the best stockouts overall in the blind condition (8.9) and the best OVAR in the context condition, despite lower MPS scores. Neither model can be called better — they fail in complementary ways.

These results directly inform V4. The architecture's limitation is calibration, not direction. Replacing continuous multiplier output with discrete intent classification is the targeted structural response to what V3b found.
