# Findings — V3 World Events Injection

## What I set out to test

V3 is the third version of my Agentic Bullwhip Effect study. The earlier version (V2) ran LLM ordering agents against deterministic ordering rules in a clean, well-behaved supply chain, and the deterministic rules won by a wide margin. V3 was built to ask a harder question: do LLM agents do any better when the supply chain stops behaving nicely — when lead times become uncertain, deliveries fall short, and the world throws disruptions at the chain?

The reasoning behind the question is that the deterministic rules — exponential smoothing and an Order-Up-To policy — are tuned for steady conditions. When a pandemic, a geopolitical conflict, or a port crisis hits, their fixed settings can become a liability. An LLM carries broad world knowledge and can, in principle, reason about a novel event. So a disrupted environment is exactly where an LLM might show a structural advantage it never had in calm conditions.

## How the experiment is set up

The simulation is a three-tier serial supply chain (OEM, then Ancillary supplier, then Component supplier) over 36 months, January 2025 through December 2027, built on SimPy discrete-event simulation. Demand follows a synthetic Indian automotive seasonal pattern (March financial-year-end peak, June-to-August monsoon trough, November Diwali peak), grown 5% year on year, with multiplicative Gaussian noise at a coefficient of variation of 8% drawn fresh on every run so that each replication is a genuinely different demand realisation rather than a repeat.

On top of that baseline I layer three disruption events modelled on real history: a pandemic over periods 7 to 12, a geopolitical conflict over periods 19 to 21, and a port/logistics disruption over periods 28 to 30. Each event period applies a demand multiplier, a fill-rate cap, and a lead-time multiplier. The most severe phase is the pandemic demand collapse (periods 7 to 9), which caps the fill rate at 0.40, multiplies lead time by 2.5, and cuts demand to 0.55 of baseline. Lead time in normal operations is drawn from a LogNormal distribution (mu = 0, sigma = 0.25, mean roughly 1 period); fill rate in normal operations is drawn from a Beta(9, 1) distribution (mean about 90%). Each tier has a per-period production capacity (60,000 OEM, 65,000 Ancillary, 70,000 Component) that is non-binding in calm periods but binds during surges.

The design is a two-by-three factorial: model tier (lightweight versus reasoning) crossed with prompt condition (blind, context, and a new "unstructured" condition that adds a one-line news headline during active events). An ablation group (E3) runs the lightweight model with world events switched off, to separate the effect of the disruptions from the effect of prompt context alone.

The deterministic baselines are naive passthrough, exponential smoothing (alpha = 0.30), and an Order-Up-To policy (alpha = 0.30). Because demand noise makes every run different, the baselines run 100 Monte Carlo replications each, while each LLM condition is set to run 20.

## What I am measuring

The primary metric is OVAR, the order-variance ratio: the variance of orders a tier places divided by the variance of demand it receives. An OVAR of 1.0 passes demand through unchanged, above 1.0 amplifies variance (the bullwhip), and below 1.0 dampens it. Alongside OVAR I count stockouts per run and compute a pattern score that checks whether an agent both mentions a seasonal or disruption signal and orders in the right direction.

## Results

I did not run V3 to completion. The experiment is code-complete and passed smoke-test validation — the experiment registry, the SimPy simulation engine, the world-events module, and the agent interface are all functional — but it was superseded before the full 20-run production conditions were executed. Because of that, I have no production numbers to evaluate the V3 hypotheses against, and I am not reporting any. The smoke-test summaries retained under `results/` were exploratory checks (a handful of runs, and in some cases a different local model than the designed configuration); they are provenance artefacts, not findings.

The only firm numbers carried into this writeup are the V2 baseline that V3 was designed to improve on, recorded here as the performance floor the experiment aimed to overcome:

| Condition | Model | Chain OVAR | Stockouts |
|---|---|---|---|
| exp_smoothing (best deterministic baseline) | — | 0.54 | 5 |
| naive_passthrough | — | 1.00 | 3 |
| order_up_to | — | 1.71 | 14 |
| Best LLM (blind) | phi4:14b | 4.33 | 41 |
| Best frontier LLM (context) | gpt-4.1-mini | 4.47 | 39 |

In V2 the best LLM condition (OVAR 4.33, 41 stockouts) was about 8 times worse than exponential smoothing (OVAR 0.54, 5 stockouts) on both metrics at once — not a trade-off between variance and service level, but a shortfall on both. V2 also showed that adding calendar-and-persona context helped frontier models only marginally (gpt-4.1-mini 4.70 to 4.47 OVAR) while hurting the smaller local model substantially, and that a reasoning model bought no OVAR advantage over a lightweight one despite generating far more tokens. Those V2 observations are the motivation for V3's design; they are not V3 results.

## Why it was superseded

Before testing whether agents can exploit a disruption signal, it is more useful to first establish whether they can calibrate the magnitude of any response at all. The follow-on (V3b, a hybrid architecture) isolated that by restricting the LLM to a single scalar safety-stock multiplier inside a deterministic planning layer, so directional reasoning and numerical calibration could be tested separately. V3b produced complete production results; the quantitative outcomes for this lineage live there.

## Limitations

Production runs were not executed, so the V3 hypotheses cannot be evaluated quantitatively. The chain is a single product on a single three-tier topology and should not be generalised to multi-product or multi-echelon networks. The agents are stateless — each period is a fresh decision with no memory of prior orders or outcomes — which isolates single-period reasoning quality but prevents any within-run learning. The demand series is synthetic, calibrated to published Indian automotive seasonal patterns rather than proprietary data. The smoothing parameter alpha = 0.30 was inherited from V2's sweep on the deterministic series; under stochastic demand its sensitivity becomes a secondary question rather than a validated setting. Finally, V3 swapped V2's local lightweight model for a different one, which breaks direct continuity with the V2 local-model results.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
