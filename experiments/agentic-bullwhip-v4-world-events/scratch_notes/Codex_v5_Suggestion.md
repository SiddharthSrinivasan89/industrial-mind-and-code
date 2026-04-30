# Codex V5 Suggestion
_2026-04-23_

## Recommendation

The next iteration should stop comparing additional models or prompt variants inside the current V4 architecture. The current evidence already points to a clear bottleneck: context improves intent classification accuracy, but the downstream `intent label -> fixed safety-stock multiplier -> OUT formula` execution layer collapses those differences back toward the deterministic `order_up_to` baseline.

In other words, the agent is getting smarter at classification, but the control surface it has been given is too weak to materially change supply-chain behavior.

## Current Interpretation

The V4 WorldEvents result is a useful negative result rather than a failed experiment.

Key interpretation:

- Context and unstructured event signals improve direction accuracy substantially.
- Model scale and reasoning budget do not materially change OVAR.
- Neutral-prior prompting does not help when `NEUTRAL` still triggers a full OUT recalculation.
- All valid LLM conditions cluster near the deterministic OUT baseline, suggesting the formula is the equalizer.
- The architecture gives the LLM control over safety stock only, while most order variance appears to come from the OUT mechanics, stochastic lead times, fill rates, backlog, and inventory-position correction.

The strongest research claim is therefore:

> Better LLM classification does not necessarily translate into better operational control when the agent's actuator is narrow or mis-specified.

## Hygiene Before V5

Before launching V5, freeze and clean the V4 evidence.

Recommended cleanup:

- Mark canonical runs separately from smoke tests, invalid runs, dry runs, or suspicious artifacts.
- Quarantine the E4 o4-mini result directories that show all `NEUTRAL`, zero latency, zero prompt tokens, zero completion tokens, and empty rationales. These look dry-run-like despite Azure provenance and should not be used as live-LLM evidence until explained.
- Fix the stockout interpretation in the summary: if `stockouts/run` is a count of stockout periods, then lower is better. The `naive_passthrough` value of `96` is not best service relative to `84-89`; it is worse service.
- Add a short canonical-results index listing which result directories support each table in the narrative.
- Preserve the negative-result framing rather than rewriting the experiment as a success case.

## V5 Core Question

Suggested V5 research question:

> Can an LLM-based supply-chain agent reduce bullwhip amplification when the control architecture gives it leverage over the actual source of order variance, rather than only over safety-stock multipliers?

This keeps continuity with V4 but moves the experiment from "Can the model classify better?" to "Can the model control better?"

## Phase 1: Deterministic Ablations First

Run cheap deterministic ablations before spending more LLM calls. These should isolate whether the architecture has enough leverage at all.

### A1: Oracle Intent Labels

Feed the ground-truth intent labels directly into the existing V4 policy.

Purpose:

- Tests the best possible classifier under the current execution formula.
- If OVAR remains near `1.77`, classification accuracy is proven not to be the limiting factor.
- This is the cleanest evidence for the equalizer-effect claim.

Expected outcome:

- OVAR likely remains close to the OUT baseline unless the multiplier map has more leverage than current results suggest.

### A2: Safety-Stock Multiplier Sweep

Run the existing intent architecture with deterministic labels and wider multiplier maps.

Candidate maps:

- Conservative: `0.80 / 0.90 / 1.00 / 1.15 / 1.30` current V4 map.
- Moderate: `0.60 / 0.80 / 1.00 / 1.25 / 1.50`.
- Aggressive: `0.40 / 0.70 / 1.00 / 1.40 / 1.80`.
- Asymmetric: stronger decreases than increases, e.g. `0.40 / 0.75 / 1.00 / 1.15 / 1.30`.

Purpose:

- Tests whether safety-stock control can ever move OVAR meaningfully.
- Identifies whether the V4 multiplier band was simply too narrow.

Decision rule:

- If even aggressive maps do not beat OUT meaningfully, do not continue with safety-stock-only architectures.
- If aggressive maps reduce OVAR but damage service level badly, V5 should become a trade-off/control optimization experiment.

### A3: Mechanical NEUTRAL Redefinition

Change `NEUTRAL` from "OUT formula with multiplier 1.0" to a true inaction or dampened action.

Candidate definitions:

- `NEUTRAL = repeat last order`.
- `NEUTRAL = order smoothed forecast only`.
- `NEUTRAL = no order unless inventory position is below a hard floor`.
- `NEUTRAL = dampened OUT`, e.g. 25-50% movement toward the OUT target.

Purpose:

- Tests the observation that the prompt's "default to NEUTRAL" instruction did not map to mechanical inaction.
- Separates language-level caution from policy-level caution.

### A4: Order Dampening Layer

Add an order-smoothing actuator after the OUT calculation.

Candidate formula:

```text
raw_order_t = OUT(...)
order_t = round(last_order + beta * (raw_order_t - last_order))
```

Sweep:

- `beta = 1.00` current behavior.
- `beta = 0.75`.
- `beta = 0.50`.
- `beta = 0.25`.

Purpose:

- Directly targets the bullwhip metric by penalizing large period-to-period order swings.
- Provides a strong deterministic baseline for any future LLM controller.

Expected outcome:

- This is the most likely ablation to reduce OVAR.
- The main question will be service-level trade-off, not just OVAR.

### A5: Forecast-Control Oracle

Allow an oracle or deterministic rule to adjust `F_t`, not just `SS_t`.

Candidate variants:

- Event-adjusted forecast using known world-event demand multipliers.
- Seasonal forecast using month-level expected demand.
- Forecast dampening during supply-side disruptions.

Purpose:

- Tests whether forecast control has more leverage than safety-stock control.
- This is likely closer to where an LLM could add value: interpreting context and shaping expected demand.

## Phase 2: V5 Architecture Candidates

After deterministic ablations identify where leverage exists, run one or two LLM-backed architectures.

### Candidate 1: Continuous Scalar Controller

Replace the five intent labels with a continuous scalar output.

Example output:

```json
{
  "demand_multiplier": 0.92,
  "confidence": 0.68,
  "rationale": "Monsoon softness and no strong event signal imply mild demand reduction."
}
```

Recommended control:

- Use the scalar to adjust forecast `F_t`, not only safety stock.
- Clamp outputs to a safe range, e.g. `0.70-1.30` or `0.50-1.50`.
- Log raw scalar, clamped scalar, confidence, and final order.

Why this is better than V4:

- Preserves gradient information instead of compressing the model into five labels.
- Allows small changes for ambiguous periods.
- Can encode intensity without forcing extreme class jumps.

### Candidate 2: Intent Plus Dampening

Keep the five-label classifier but add a mechanical order dampening layer.

Architecture:

```text
intent -> multiplier -> raw OUT order -> dampened final order
```

Why this is useful:

- Minimally changes V4.
- Preserves the classification-compliance benefit.
- Tests whether the missing ingredient was not better classification, but safer actuation.

### Candidate 3: Intent-Gated Policy Selection

Let the intent class choose among policy modes rather than only a multiplier.

Example:

- `STRONG_INCREASE`: OUT with moderate upward adjustment.
- `MODERATE_INCREASE`: smoothed OUT.
- `NEUTRAL`: repeat last order or dampened OUT.
- `MODERATE_DECREASE`: reduced forecast plus dampening.
- `STRONG_DECREASE`: aggressive forecast reduction plus cap on new orders.

Why this is promising:

- Makes each intent class operationally distinct.
- Gives `NEUTRAL` a real behavioral meaning.
- Still keeps the LLM output constrained and auditable.

## Phase 3: LLM Runs Only After Architecture Passes

Only run live LLM experiments after deterministic ablations show that a candidate policy can reduce OVAR without unacceptable stockout penalties.

Recommended minimal LLM matrix:

| Experiment | Model | Conditions | Runs |
|---|---|---|---|
| V5_A | gpt-4.1-mini or phi4 | context, unstructured | 20 |
| V5_B | same model | context_no_events | 10 |

Avoid a broad model bake-off initially. V4 already shows that model family is not the primary bottleneck.

Run additional models only if:

- The V5 architecture beats OUT or exp_smoothing.
- The result depends strongly on classification nuance.
- There is a specific claim about model scale, reasoning, or local-vs-cloud deployment.

## Metrics to Add in V5

OVAR alone is not enough. Add metrics that reveal the control trade-off.

Recommended additions:

- Fill rate or service level, not just stockout count.
- Average backlog magnitude.
- Maximum backlog.
- Average on-hand inventory.
- Excess inventory holding proxy.
- Order adjustment variance: `Var(order_t - order_{t-1})`.
- Forecast error if the agent controls `F_t`.
- Policy intervention magnitude: how far final order deviates from raw OUT.

The key V5 result should be a Pareto comparison:

```text
OVAR reduction vs service-level degradation
```

## Suggested V5 Hypotheses

### H1: Oracle Labels Under Current V4 Will Not Beat OUT

If true, this confirms that classification accuracy is not the bottleneck.

### H2: Order Dampening Reduces OVAR More Than Intent Accuracy Improvements

If true, this supports the claim that control mechanics dominate model intelligence for bullwhip mitigation.

### H3: Forecast-Control Agents Outperform Safety-Stock-Only Agents

If true, V5 identifies the better actuator for LLM supply-chain agents.

### H4: Unstructured Event Context Improves Forecast Direction But Can Harm Stability Without Dampening

This preserves the V4 insight that world-event text improves awareness but can also encourage overreaction.

### H5: V5 Policy Must Be Judged by OVAR-Service Pareto Position, Not OVAR Alone

This prevents a policy from "winning" by suppressing orders while creating unacceptable backlogs.

## Recommended Implementation Order

1. Add canonical-result indexing and quarantine suspicious E4 artifacts.
2. Implement deterministic oracle-intent mode.
3. Implement multiplier-map sweep.
4. Implement `NEUTRAL` mechanical variants.
5. Implement order dampening.
6. Run deterministic ablations with 100 Monte Carlo runs each.
7. Select the best 1-2 architectures based on OVAR-service Pareto behavior.
8. Only then run live LLM V5 conditions.
9. Write V5 as an architecture-control experiment, not a model-comparison experiment.

## Likely V5 Story

The likely next paper-quality story is:

> V4 showed that LLMs can classify supply-chain context more accurately when given calendar and world-event information, but that improved semantic accuracy did not reduce bullwhip amplification because the policy actuator was too narrow. V5 tests whether giving the agent a stronger and safer control surface, especially forecast control and order dampening, converts contextual intelligence into operational improvement.

This is stronger than simply saying "LLMs did not help." The more precise claim is:

> LLM intelligence must be paired with the right control architecture; otherwise, better reasoning is absorbed by deterministic execution mechanics.

