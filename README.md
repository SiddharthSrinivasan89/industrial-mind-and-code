# 🏭 Industrial Mind & Code

> **Exploring LLM agents at the intersection of industrial operations and decision-making**

---

## Overview

**Industrial Mind & Code** is a personal research project investigating the behavior, capabilities, and limitations of large language model (LLM) agents when applied to industrial and operational decision-making problems.

This work sits at the boundary of AI systems research and industrial engineering, asking a core question: *Can LLM agents make operationally sound decisions in complex, noisy, real-world industrial contexts — and if so, under what conditions?*

Experiments will be posted here as they are completed.

---

## Experiments Index 🗂️

| Experiment | Status | Key Signal | Path |
|---|---|---|---|
| Agentic Bullwhip Effect (Version 1) | ✅ Published | Bullwhip appears across all configs; best chain-average OVAR from `context_lightweight` | `agentic_bullwhip_effect_version_1/` |

---

## Latest Experiment: Agentic Bullwhip Effect (Version 1) 📦📈

Path: `agentic_bullwhip_effect_version_1/`

### Snapshot 🧪
- 2×2 design: `Blind vs Context` × `gpt-4.1-mini vs o1`
- 20 runs total (5 per configuration)
- 720 LLM ordering decisions
- Primary metric: **OVAR** (Order Variance Amplification Ratio)

### Key Findings ✅
- Bullwhip effect appears in all tested setups (`OVAR > 1` across all tiers/configs).
- Best chain-average OVAR: **context_lightweight = 2.9289** 🥇
- Worst chain-average OVAR: **context_reasoning = 4.4124** ⚠️
- Context improved the **component tier** for both models:
  - `gpt-4.1-mini`: `4.2664 → 3.4119`
  - `o1`: `3.6493 → 2.6976`
- `o1` showed higher run-to-run variability in this run set (e.g., blind OEM CV `57.15%`).

### Public Artifacts 📂
- Experiment package: `agentic_bullwhip_effect_version_1/`
- Aggregated findings: `agentic_bullwhip_effect_version_1/results/aggregated/`
- Analysis summary: `agentic_bullwhip_effect_version_1/results/analysis_2026-02-27_08-05.md`

---

## Disclosure

> ⚠️ **This is a personal research project.**

- All scenarios, supply chain structures, company names, and operational parameters used in this research are **entirely fictional and constructed for experimental purposes**.
- **No proprietary, confidential, internal, or employer-owned data** of any kind has been used or referenced in this project.
- This research does not represent the views, products, strategies, or endorsements of any employer, client, or affiliated organization.
- Any resemblance to real companies, products, or operational systems is coincidental and unintentional.
- Data used to calibrate baselines and demand scenarios is either synthetically generated or derived from publicly available academic literature and sources.
- This project is conducted independently, in personal time, using personal compute resources and publicly available model APIs.

---


## License

This project is shared for transparency and academic interest.

---

## Contact

For research discussion, methodology questions, or collaboration inquiries, feel free to open an issue or reach out via GitHub.

---

*Industrial Mind & Code — Personal Research | Not affiliated with or endorsed by any employer or organization.*
