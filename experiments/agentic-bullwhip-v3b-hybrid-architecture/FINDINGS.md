# V3b Hybrid Architecture — Findings

## What I Tested

I asked a simple question: can a large language model (LLM) help run a supply chain better than a traditional ordering formula if I keep the model out of the arithmetic? Instead of letting the model decide order quantities directly, I gave it one small job — pick a safety-stock multiplier between 0.5 and 3.0 — and let a deterministic Order-Up-To formula place the actual orders. The idea was that the model would handle the qualitative part (is a busy season coming, should I hold more or less buffer?) while the formula handled the numbers.

I ran this over a 25-month synthetic Indian automotive demand series through a three-tier serial supply chain (OEM, then ancillary supplier, then component supplier). I tested three models — gpt-4.1-mini and o4-mini on Azure OpenAI, and nemotron-super-3:120b running locally on Ollama — across three information conditions: Blind (state only), Context (adds the calendar month and Indian seasonal event flags), and Stateful (adds the last three periods of demand, order, multiplier, backlog and stockout history).

## How I Measured It

The primary metric is chain OVAR (Order Variance Amplification Ratio = variance of orders divided by variance of demand, averaged across the three tiers). An OVAR below 1.0 means the system is smoothing variance; above 1.0 means it is amplifying the bullwhip effect. I always reported OVAR jointly with the stockout count and mean on-hand inventory, because a low OVAR achieved by chronically starving or hoarding inventory is a different failure, not a win.

I used two deterministic reference points. The within-experiment benchmark is exponential smoothing (exp_smoothing), the 1950s-era forecasting formula. The architectural control is hybrid_control: the same Order-Up-To execution path with the multiplier permanently fixed at 1.0 and no model involved at all. Any model condition scoring worse than hybrid_control proves the model's active adjustments degraded the base formula rather than improving it.

Each LLM condition ran 20 replications. The deterministic baselines ran once because they are fully deterministic. The hybrid formula per period per tier was:

```
F_t             = 0.30 * D_t + 0.70 * F_{t-1}   (exponential smoothing forecast)
SS_t            = base_SS * multiplier_t          (base_SS ~ 5,061 units)
target_position = round(F_t) + SS_t
order_t         = max(0, target_position - inventory_position_t)
```

The multiplier was clamped to [0.5, 3.0] in code, and any parse failure fell back to 1.0 (neutral).

## Key Results

All four hypotheses were rejected. The deterministic exponential smoothing baseline outperformed every model in every condition.

**Deterministic references:**

| Condition | Chain OVAR | Chain Stockouts | Mean On-Hand |
|---|---:|---:|---:|
| exp_smoothing | 0.5446 | 5.0 | 4,769 |
| hybrid_control (fixed 1.0x, no AI) | 1.7097 | 14.0 | 5,142 |

**Model hybrid conditions (20 runs per condition; mean ± std):**

| Model | Condition | Chain OVAR | OVAR std | Stockouts | On-Hand | Mult Mean | MPS |
|---|---|---:|---:|---:|---:|---:|---:|
| nemotron-super-3:120b | H1 Blind | 2.4178 | 0.2814 | 12.2 | 6,511 | 1.2249 | 0.1591 |
| nemotron-super-3:120b | H2 Context | 2.7629 | 0.2319 | 12.3 | 6,852 | 1.3489 | 0.3977 |
| nemotron-super-3:120b | H3 Stateful | 2.6846 | 0.2413 | 9.6 | 6,943 | 1.3671 | 0.3273 |
| gpt-4.1-mini | H1 Blind | 2.3325 | 0.1108 | 10.6 | 6,030 | 1.1298 | 0.1875 |
| gpt-4.1-mini | H2 Context | 2.9763 | 0.0958 | 11.0 | 6,781 | 1.3103 | 0.2667 |
| gpt-4.1-mini | H3 Stateful | 2.7226 | 0.1512 | 11.6 | 7,248 | 1.4291 | 0.3193 |
| o4-mini | H1 Blind | 2.5232 | 0.2791 | 8.9 | 7,609 | 1.4808 | 0.3189 |
| o4-mini | H2 Context | 2.4395 | 0.1616 | 11.7 | 6,487 | 1.2447 | 0.3250 |
| o4-mini | H3 Stateful | 3.1211 | 0.1320 | 10.7 | 7,218 | 1.3488 | 0.3038 |

Lower OVAR, lower stockouts, and lower on-hand are better. MPS is the Multiplier Pattern Score, which measures how often the model moved the multiplier in the correct seasonal direction.

The best model result was gpt-4.1-mini Blind at OVAR 2.3325 with 10.6 stockouts. That is 4.3x worse on OVAR than exponential smoothing (0.5446, 5.0 stockouts) and roughly twice the stockouts. Every single model condition also exceeded hybrid_control's OVAR of 1.7097, which means the models' active multiplier choices made the formula worse than leaving the multiplier fixed at 1.0.

**Hypothesis verdicts:**

| Hypothesis | Prediction | Verdict |
|---|---|---|
| H1 | At least one model condition beats exp_smoothing on OVAR and stockouts together | Rejected — best model OVAR 2.3325 vs. baseline 0.5446 |
| H2 | Context improves OVAR over Blind by >= 0.5 for at least two models | Rejected — context worsened OVAR for nemotron (+0.3451) and gpt-4.1-mini (+0.6438); o4-mini improved only -0.0837 |
| H3 | Stateful improves OVAR over Context by >= 0.5 for at least two models | Rejected — gains were too small (nemotron +0.0783, gpt-4.1-mini +0.2537) and o4-mini worsened by +0.6816 |
| H4 | Multiplier pattern score >= 0.50 | Rejected — best observed MPS 0.3977 (nemotron, Context) |

## What Explains the Failure

The clearest finding is a split between two capabilities that sound related but are not. Reading the models' written rationales, all three correctly recognised when a high-demand season was approaching and reasoned that more buffer was warranted. That is semantic alignment — the model understands the concept. What the models could not do was choose the exact multiplier value needed to stabilise the system. A model that correctly says "December needs more buffer" but outputs 1.45x when 1.05x would have sufficed is reasoning correctly and controlling badly.

The failure was a consistent over-buffering bias. Mean chosen multipliers ranged from 1.13 to 1.48 across all nine conditions; no model in any condition learned to systematically reduce the buffer below the base level even in low-demand months. Because higher buffers inflate the target position and then force large catch-up orders when inventory depletes, that caution amplified variance rather than damping it. When in doubt, every model added buffer, and adding buffer was worse than doing nothing.

Two condition-level patterns stand out. First, context hurt: giving nemotron and gpt-4.1-mini the calendar and seasonal flags made their ordering more erratic, not more precise — they treated more information as a reason to hold more stock. Second, memory backfired most for the strongest model: o4-mini's Stateful condition reached OVAR 3.1211, the worst single result in the experiment, concentrated at the upstream OEM (3.22) and ancillary (3.26) tiers. Its reasoning logs showed it anchoring on recent backlogs and stockouts and over-correcting — the bullwhip effect operating inside the model's own reasoning rather than across the supply chain.

The structural constraint sits underneath all of this. Even hybrid_control at multiplier 1.0 produces OVAR 1.7097 against exponential smoothing's 0.5446 — a roughly 3x gap. The model would have had to choose multipliers that actively counteract the formula's own instability, and buffer adjustment alone cannot close that gap.

## Limitations

This is a single-product, fixed-topology supply chain — a stylised three-tier serial chain with deterministic one-month lead times and one Indian automotive product. It does not generalise to multi-product, multi-echelon, or internationally distributed networks. The demand series is synthetic; it is calibrated to published Indian automotive seasonal patterns and so captures structural seasonality but not firm-level idiosyncrasy. The model's task was still a numerical precision task (a real-valued multiplier), so whether a discrete classification output resolves the calibration problem is untested here. The heuristic baselines ran once and the model conditions ran 20 times, which is internally valid but does not probe heuristic parameter sensitivity. The smoothing alpha was fixed at 0.30, selected empirically on this same series in the prior experiment, and its sensitivity is not evaluated. There were no disruption conditions — no supply shocks, stochastic lead times, or demand spikes.

These hypotheses were not pre-registered. The next architectural step the results point to is to replace the free-form continuous multiplier with a small set of discrete intent labels (for example STRONG_INCREASE through STRONG_DECREASE) mapped to fixed multipliers by a hard-coded lookup, converting the task from numerical calibration to classification and targeting the directional capability that does appear to exist. The observed multiplier range (means 1.13-1.48) gives a concrete basis for those guardrails.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
