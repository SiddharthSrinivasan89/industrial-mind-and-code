# Agentic Fuel Transition Shock

**Series:** Industrial Mind & Code | Indian Automotive Supply Chain
**Status:** Design phase — not yet running

---

## Research Question

When LLM agents operating a diesel-dependent supply chain receive a credible signal that diesel passenger car demand will fall 30% over the next 3 years, do they propagate the shock rationally — or do they amplify it?

---

## Overview

A controlled simulation of a 3-tier diesel component supply chain (OEM → Ancillary → Component) facing a sustained, directional demand decline. Uses the same 2×2 blind vs context × lightweight vs reasoning design as the Agentic Bullwhip series, with one key addition: the context condition includes an explicit forward-looking market signal about the fuel transition.

**Primary question:** Do agents with market context act on the signal before the numbers confirm it?

**Industry grounding:** Calibrated to Mahindra's FY2025 diesel volume (4,25,329 units, 77.1% of its portfolio) — the highest diesel-concentrated OEM in India.

---

## Key Design Differences from Bullwhip Series

| | Bullwhip Series | This Experiment |
|---|---|---|
| Demand perturbation | Seasonal variance (mean-reverting) | Structural decline (directional, sustained) |
| Context signal | Company identity + calendar month | Company identity + explicit market warning |
| Simulation length | 13–25 months | 37 months (full shock trajectory) |
| New metric | Pattern score | Lead Indicator Score |
| Heuristic baselines | 3 | 3 (includes Adaptive Order-Up-To) |

---

## Project Structure

```
Agentic_Fuel_Transition_Shock/
├── README.md
├── docs/
│   ├── experiment_design_v1.md     # Full design specification
│   └── data_provenance.md          # Source data, derivations, demand file spec
├── data/
│   └── synthetic/
│       └── diesel_transition_37m.csv  # To be generated
├── src/                            # To be written
│   ├── generate_demand.py
│   ├── base_agent.py
│   ├── blind_agent.py
│   ├── context_agent.py
│   ├── supply_chain.py
│   └── run_experiment.py
└── results/
    ├── raw/                        # Per-run JSONs (4 conditions × 20 runs)
    └── aggregated/                 # Per-condition summary JSONs
```

---

## Current Status

- [x] Experiment design drafted (`docs/experiment_design_v1.md`)
- [x] Source data documented (`docs/data_provenance.md`)
- [ ] Open design questions resolved (see Section 12 of design doc)
- [ ] Demand series generated and checksummed
- [ ] Source code written
- [ ] Heuristic baselines tested
- [ ] LLM runs complete
