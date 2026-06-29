# Findings — Agentic Bullwhip Effect Version 2a: sarvam-30b on an Indian Automotive Supply Chain

## What I tested

I tested whether sarvam-30b — India's sovereign large language model — produces materially different supply chain ordering behaviour from GPT OSS 120B when both are given a demand series calibrated to Indian automotive market seasonality. The motivating idea was simple: if a model is trained on a lot of Indian data, perhaps it would recognise Indian seasonal patterns (festive peaks around Dasara and Diwali, the monsoon trough, the fiscal year-end peak) and order more sensibly on a demand series built from those patterns. I ran sarvam-30b as the ordering agent at every tier of a three-tier serial supply chain and compared it against the deterministic heuristic baselines and against the GPT OSS 120B reference results from Version 2.

This is an extension of Version 2, not a strict controlled swap. The supply chain structure, demand series, metric definitions, and the practically-meaningful-difference threshold are held identical to Version 2. What changed is the model (sarvam-30b instead of the four Version 2 models), the inference stack (llama-server / llama.cpp instead of Ollama), the conditions (context only — the blind condition was not viable, see below), and the replication count (10 runs per condition instead of 20). Because several operational parameters moved together, the cross-version comparison is informative but not a ceteris paribus comparison.

## Methodology

The supply chain is a three-tier serial cascade: Tatva Motors (OEM) orders from a lighting manufacturer (Ancillary), which orders from an LED component manufacturer (Component). All companies and scenarios are fictional. Each tier is an independent agent that sees only the order placed by its immediate downstream customer — no tier has visibility into any other tier's inventory or orders. Lead time is one month, deterministic, at every tier.

The demand series is 25 months (January 2025 to January 2027, period 25 is fulfilment-only so there are 24 active ordering periods). It is synthetic but calibrated to real Indian passenger-vehicle market data from public sources (autopunditz.com, CY2023–2025): festive peaks in October–November confirmed at +17–19% year on year in 2025, a monsoon trough in June–August at −6% to −8%, a March fiscal-year-end peak, and a roughly 5% year-on-year growth baseline. Mean monthly demand is 38,548 units with a standard deviation of about 3,067 units. Initial inventory is set to S ≈ 43,600 units at all three tiers (mean + 1.65 × std). The data provenance is recorded in `data/sources.md` and `data/calibration_notes.md`.

Agents are stateless: each period is a single-turn call with no memory. Every agent (and every heuristic) receives the same four numeric state variables each period — demand received, on-hand inventory after fulfilment, backlog, and inventory position. In the context condition the agent also receives a tier-specific persona (company, product, role) and the current calendar month name. It is never told the year, never given a forecast, and never given any seasonal background or event label. Any seasonal reasoning therefore has to come from the model's own world knowledge — that is the capability I was probing.

I ran two conditions: E1 (context, lightweight, `think=False`) and E2 (context, reasoning, `think=True`), 10 runs each. Each run is 24 ordering periods × 3 tiers = 72 agent calls, so 720 calls per condition (confirmed by the provenance `n_calls: 720`). The canonical dataset is V2d, which uses the GGUF-documented settings (temperature 1.0, top_p 1.0, ctx-size 65536, 4096 max tokens lightweight / 8192 reasoning, JSON object response format). An earlier V2a run used the llama.cpp default top_p of 0.95 and produced numerically identical results; V2d supersedes it.

The deterministic baseline I held everything up against is exponential smoothing (α = 0.3: F_t = 0.30 × D_t + 0.70 × F_{t-1}, order the smoothed forecast plus backlog coverage, floored at zero). I also report naive passthrough and an Order-Up-To base-stock policy as additional comparators.

The primary metric is OVAR = Var(orders placed) / Var(demand received), computed per tier over the 24 ordering periods; chain OVAR is the arithmetic mean across the three tiers. OVAR below 1.0 is dampening, above 1.0 is bullwhip amplification. Stockout count (tier-periods where shortfall > 0, out of 75 possible per run) is always reported alongside OVAR. Pattern score is the mean of a keyword score (seasonal terms in the agent's rationale at event months) and an elevation score (whether the order moved in the right direction at event months). The threshold for calling a difference practically meaningful (MPRD) is |ΔOVAR| ≥ 0.5 at chain level.

## Key results, with exact numbers

Heuristic baselines on this demand series (deterministic, one run each):

| Heuristic | Chain OVAR | OEM | Ancillary | Component | Stockouts (of 75) |
|---|---|---|---|---|---|
| Exponential smoothing | 0.545 | 0.408 | 0.647 | 0.578 | 5 |
| Naive passthrough | 1.000 | 1.000 | 1.000 | 1.000 | 3 |
| Order-Up-To | 1.710 | 1.689 | 1.712 | 1.728 | 14 |

sarvam-30b results (V2d canonical dataset, 10 runs each, context only):

| Condition | Chain OVAR (mean ± std) | OEM | Ancillary | Component | Stockouts | Pattern | Run replacements | Per-call retry rate |
|---|---|---|---|---|---|---|---|---|
| E1 context, `think=False` | 4.504 ± 0.044 | 4.126 | 5.883 | 3.503 | 39.9 ± 0.3 | 0.219 ± 0.010 | 15 / 25 attempts | 10.4% |
| E2 context, `think=True` | 4.501 ± 0.093 | 4.126 | 5.853 | 3.524 | 40.5 ± 0.8 | 0.232 ± 0.013 | 0 / 10 attempts | 4.2% |

GPT OSS 120B reference, taken directly from Version 2 (E2 context, 20 runs): chain OVAR 4.52 ± 0.05, stockouts 39.6, pattern score 0.21, tier OVAR OEM 4.13 / Ancillary 6.01 / Component 3.43.

From these numbers I draw the following findings.

**No India-specific ordering behaviour appeared.** sarvam-30b E2 context gave chain OVAR 4.501 ± 0.093 against GPT OSS 120B's 4.52 ± 0.05 — a delta of 0.019, far below the 0.5 MPRD threshold and well within noise. Stockouts were 40.5 versus 39.6, and pattern scores were 0.232 versus 0.21. Neither model showed festive-season awareness. A likely explanation is that the prompts and demand data were in English; whatever India-specific signal sarvam-30b's training carries did not surface in an English-language numerical ordering task. This does not rule out that such capabilities exist — it shows they did not activate here.

**No LLM beat exponential smoothing.** Every LLM I tested in this line — phi4:14b blind (OVAR 4.33), sarvam-30b context (4.50), GPT OSS 120B context (4.52) — amplifies demand variability by roughly 8× relative to exponential smoothing's 0.545. On stockouts, every LLM sat at 37–41 tier-periods out of 75 (roughly 49–55%) against exponential smoothing's 5 (about 7%). The gap is structural, not a prompting or model-capability problem: stateless agents with no persistent cross-period state cannot self-correct accumulated drift, even when they receive the current period's inventory state.

**The Ancillary tier is the main amplification source, and this is model-independent.** For sarvam-30b E2 the per-tier OVAR was OEM 4.126, Ancillary 5.853, Component 3.524 — the same Ancillary > OEM > Component hierarchy seen in GPT OSS 120B (4.13 / 6.01 / 3.43). The OEM sees the real consumer demand signal; the Ancillary sees the OEM's already-amplified orders and amplifies them further, which is the classic bullwhip mechanism at the second tier. This is a property of the chain structure and information asymmetry, not of the model.

**Enabling `think=True` removed run-level failures without changing the supply chain outcome.** E1 (`think=False`) required 25 attempts to produce 10 valid runs — 15 runs failed entirely and had to be rerun — at a 10.4% per-call retry rate. E2 (`think=True`) completed all 10 runs on the first attempt at a 4.2% per-call retry rate. The OVAR difference between the two was 0.003, negligible. So the reasoning flag here is about run-level stability, not answer quality. I cannot fully isolate this to the flag alone, because E1 also had a system-prompt / API-flag conflict (a "Think silently" instruction contradicting `think=False`); regardless of attribution, `think=True` is the configuration that completed reliably, and it is what I recommend for local GGUF deployment of sarvam-30b.

**Temperature and prompt anchoring are hard reliability requirements for sarvam-30b on local GGUF.** These are integration observations from pre-experiment calibration, not from the main V2d tables. On local GGUF, temperature 1.0 (the GGUF model card value) produced recoverable 5–10% per-call error rates; temperature 0.4 produced 40–60% error rates; and temperature 0.2 (the cloud API recommendation) produced about 100% failure (0 of 5 runs completed). Cloud documentation does not transfer to on-premises deployment. Separately, the minimal blind prompt produced about 20% per-call error rates, too high to sustain a reliable 10-run blind experiment, whereas the context prompt completed all runs at 4–10%. GPT OSS 120B and phi4:14b both ran blind conditions cleanly in Version 2, so this is a sarvam-30b-specific characteristic: it needs richer prompt scaffolding to produce stable structured output.

## Hypothesis verdicts

| Hypothesis | Prediction | Actual | Verdict |
|---|---|---|---|
| H1 | sarvam-30b chain OVAR differs from GPT OSS 120B by ≥ 0.5 | Δ = 0.019 | Rejected |
| H2 | sarvam-30b gives a higher seasonal pattern score | 0.232 vs 0.21 — equal within noise | Rejected |
| H3 | `think=True` produces meaningfully different chain OVAR | Δ = 0.003 | Rejected |

The broader Layer-1 question (does any LLM configuration beat exponential smoothing on both OVAR and stockouts at once) also failed: no configuration cleared the heuristic. Given the deliberately narrow task, that is an expected outcome rather than a generalised verdict against LLMs in supply chains.

## Limitations

This experiment is intentionally narrow. It tests stateless agents on a single product, a fixed three-tier topology, and a fixed one-month deterministic lead time, with no supplier disruptions, no negotiation, no exception handling, and no unstructured context in the loop. Results should not be generalised to supply chain management broadly.

Only context conditions were run for sarvam-30b; blind results are not available, so I cannot directly compare V2a to the Version 2 blind conditions. I used 10 runs per condition rather than the 20 used in Version 2, so the confidence intervals here are wider and the standard deviations should be read accordingly. The comparison to GPT OSS 120B is not ceteris paribus — different inference stack, temperature, and replication count all moved together. The integration findings (temperature, prompt sensitivity, think-flag behaviour) are specific to local GGUF deployment via llama-server with the Q4_K_M quantisation; a managed cloud API deployment of the same model may behave differently and was not tested in the main runs. All prompts were in English, so any India-specific language or reasoning capability of sarvam-30b was not exercised. The OVAR ceiling in this experiment is set by the task structure, not by model quality — all models cluster in a narrow 4.3–4.5 band — so these numbers should not be read as a general capability benchmark for any model.

---

*Independent personal research by Siddharth Srinivasan. Views are my own and do not represent my employer, any model or service provider, or any third party. This work is self-funded — run on personally procured hardware and subscriptions, using publicly available data or synthetic data derived from publicly available sources and my own professional experience.*
