# V4 Intent Classifier — Findings

This is the plain-language summary of what I tested and what I found. It is written for an
industrial-engineering reader, so I define the few technical terms as I go.

## What I was testing, in one paragraph

A three-tier supply chain (an OEM, its ancillary supplier, and that supplier's component
maker) places monthly replenishment orders for an Indian automotive parts line. Each month the
demand goes up and down with the Indian calendar: a peak at financial-year end in March, the big
Diwali peak in November, and a dip during the monsoon. I wanted to know whether a language model
(I used gpt-4.1-mini on Azure) could help set the right safety-stock buffer each month without
making the ordering swing wildly. The trick I tested is this: instead of asking the model to
output a number, I only let it pick one of five plain labels for the month ahead --
STRONG_INCREASE, MODERATE_INCREASE, NEUTRAL, MODERATE_DECREASE, STRONG_DECREASE. A fixed lookup
table then turns that label into a buffer multiplier (for example, STRONG_INCREASE means hold 2.5
times the base buffer), and a plain arithmetic formula computes the actual order. The model never
produces a number; it only classifies the situation.

The metric I care about most is **OVAR**, the Order Variance Amplification Ratio. In everyday
words: how wildly the orders swing compared with how wildly customer demand actually swings. An
OVAR of 1 means orders are as steady as demand. An OVAR above 1 means the ordering is
*amplifying* the swing -- this is the classic "bullwhip effect," where a small wobble at the
customer end turns into a big wobble upstream. Lower is better.

## The three conditions

I ran the model under three levels of information, 20 runs each:

- **IC-Blind** -- the model sees only the current inventory numbers, no calendar.
- **IC-Context** -- it also sees the current month and a note about Indian automotive seasonality.
- **IC-Stateful** -- it sees all of the above plus the last three months of its own history.

I also ran two non-AI baselines for comparison: **exponential smoothing** (a standard demand-
forecasting heuristic that gently averages recent demand) and a **hybrid control** (the same
order formula with the buffer fixed at its base level).

## What I found

**1. The label interface is rock-solid.** Intent compliance was perfect -- 1.000 across every
condition and every one of the runs, with zero fallbacks. "Compliance" here means the model
returned one of the five valid labels in clean form every single time, so the system never had to
fall back to a default. This is the good news: confining the model to a small fixed set of labels
gave a completely reliable output format. That was the main design bet, and it held.

**2. But the AI amplified the bullwhip far more than the plain formula.** Here are the headline
chain-OVAR numbers (lower is better):

| Approach | Chain OVAR | Stockouts |
|---|---|---|
| Exponential smoothing (baseline) | 0.545 | 5 |
| Hybrid control (baseline) | 1.710 | 14 |
| IC-Blind (gpt-4.1-mini) | 3.843 | 12.05 |
| IC-Context (gpt-4.1-mini) | 3.268 | 15.70 |
| IC-Stateful (gpt-4.1-mini) | 3.762 | 12.05 |

Read that against the exponential-smoothing baseline of 0.545. Every AI condition landed between
about 3.3 and 3.8 -- roughly six to seven times more order-swing than the plain smoothing formula
(IC-Blind is about 7x worse; IC-Context, the steadiest AI condition, is about 6x worse). The
exponential-smoothing heuristic also held fewer stockouts. So on the operational metric that
matters, the simple deterministic formula clearly beat the language model here.

**3. The three information conditions barely moved -- the "Equaliser Effect."** Giving the model
the calendar (IC-Context) or its own history (IC-Stateful) changed the OVAR only a little, and not
in a way that rescued it. This is the same pattern the later V4 WorldEvents experiment named the
**Equaliser Effect**: once you force the decision into a small fixed set of labels mapped to fixed
multipliers, you put a ceiling and a floor on how far the outcome can move. The label set, not the
model's cleverness or the information it sees, dominates the result. More context could not push
the outcome past that structural wall.

**4. The result is robust, not a small-sample fluke.** I first ran 10 repetitions per condition,
then doubled it to 20. Across every headline metric -- chain OVAR, the per-tier OVAR for the OEM,
ancillary, and component tiers, stockouts, and compliance -- every average moved by less than one
standard deviation when I doubled the sample. In plain terms: the extra runs did not change the
story, so I am confident the numbers above are stable rather than noise. The n=20 set is the
result of record here; the earlier n=10 set is kept only so this stability check can be reproduced.

## What this does and does not show

This experiment shows, for this setup, that the discrete-label interface is a dependable way to
get structured output from a language model, but that it did not beat a standard forecasting
heuristic at keeping orders steady -- the AI amplified the bullwhip about six to seven times more
than exponential smoothing, and adding context or memory did not close that gap. These are useful,
checkable facts about one model and one simulated chain.

The limits are worth stating plainly. I tested a single model (gpt-4.1-mini), a single 25-month
synthetic demand series calibrated to Indian automotive seasonality, and a single simplified
three-tier chain with a one-month lead time and no demand shocks or supply disruptions. The
intent-to-multiplier lookup values come from domain logic and are not guaranteed to be optimal.
So I would not generalise these numbers to other models, other markets, or more complex chains
without testing them there. The hypotheses here were not pre-registered.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my
employer, any model or service provider, or any third party. This work is self-funded -- run on
personally procured hardware and subscriptions, using publicly available data or synthetic data
derived from publicly available sources and my own professional experience.*
