# Industrial Mind & Code

Industrial Mind & Code is an independent research repository for testing LLM agents inside industrial engineering decision environments. The current published program focuses on the Agentic Bullwhip Effect: a controlled supply-chain simulation series that asks whether language-model agents can make replenishment decisions without amplifying demand variance.

The public site is hosted through GitHub Pages at `industrialmindandcode.ai`. GitHub Pages deploys from `docs/`: the homepage is `docs/index.html`, and experiment writeups live under `docs/blog/`.

## Research Frame

The core question is practical rather than benchmark-oriented:

Can probabilistic AI agents operate inside deterministic industrial control problems without degrading the system they are placed into?

Each experiment places one or more LLM agents in a controlled simulation, compares their behavior against deterministic analytical baselines, and reports operational metrics such as order variance ratio (OVAR), stockouts, and run reliability. The supply-chain studies use fictional companies and synthetic demand series calibrated to industrial patterns; no proprietary data is used.

## Experiment Lineage

The first five supply-chain experiments tested increasingly structured ways to put LLMs into replenishment decisions. V5 closed that intent-classification line: perfect oracle labels still could not overcome the structural variance introduced by the Order-Up-To formula plus safety-stock multiplier interface. That result did not end the research program. It changed the trajectory.

V6 starts the new line by moving the AI inside an exponential-smoothing control loop. Instead of choosing an intent label or a safety-stock multiplier, the agent selects the smoothing parameter `alpha`. This architecture produced the first positive result in the program: every AI condition dampened variance below OVAR 1.0, and the best gpt-oss 120B blind condition matched the fixed `alpha=0.3` baseline within uncertainty.

Published supply-chain sequence:

| Version | Focus | Main result |
|---|---|---|
| V1 | Direct ordering by LLM agents | All configurations amplified demand variance; context interacted with model capability in unexpected ways. |
| V2 | LLM agents versus heuristic baselines | Every heuristic beat every LLM condition on OVAR and stockouts. |
| V2a | sarvam-30b sovereign model evaluation | No meaningful difference from gpt-oss 120B in the tested context conditions. |
| V3b | Hybrid safety-stock multiplier control | Formula execution helped, but AI-controlled multipliers still amplified variance. |
| V4 | Discrete intent-classification interface | Better label accuracy did not translate into lower OVAR; the Equaliser Effect appeared. |
| V5 | Oracle labels and control-architecture ablations | Perfect labels failed; the V1-V5 intent-classification lineage closed. |
| V6 | Adaptive exponential-smoothing parameter control | New trajectory; all AI conditions dampened variance below OVAR 1.0. |

## Repository Layout

```text
.
├── docs/                      # GitHub Pages site source
├── experiments/               # Reproducible experiment source, data, reports, and results
└── README.md                  # Technical overview for repository readers
```

The `experiments/` directory is the source of research truth. Each experiment folder contains some combination of `README.md`, design notes, analysis reports, code, synthetic data, and result summaries. The `docs/blog/` HTML files are hand-authored public writeups derived from those experiment artifacts, not generated automatically by a build system.

## Publishing Model

The repository has a single published site source:

- GitHub Pages source: `docs/index.html`, `docs/blog/`, `docs/CNAME`, and `docs/.nojekyll`.

When a public writeup changes, update the `docs/` copy directly. The repository root is reserved for project documentation and experiment source, which avoids maintaining duplicate HTML trees.

## Reproduction Entry Points

Start with the experiment README for the version you want to inspect:

- `experiments/agentic-bullwhip-v1-direct-ordering/README.md`
- `experiments/agentic-bullwhip-v2-context-model-interactions/README.md`
- `experiments/agentic-bullwhip-v2a-sarvam-evaluation/README.md`
- `experiments/agentic-bullwhip-v3b-hybrid-architecture/README.md`
- `experiments/agentic-bullwhip-v4-world-events/README.md`
- `experiments/agentic-bullwhip-v5-control-architecture/README.md`
- `experiments/agentic-bullwhip-v6-stateless-swing/README.md`

Most experiment folders include a `code/` directory with a `run_experiment.py` entry point and a `requirements.txt`. Some earlier experiments use `src/` instead. Result summaries are stored as JSON under each experiment's `results/` tree.

## Current Technical Takeaway

The program's strongest finding so far is architectural. LLM quality, context quantity, and label accuracy did not fix variance amplification when the model controlled ordering through direct orders, safety-stock multipliers, or discrete intent labels. The first robust positive movement came from changing the interface: let the model choose a control parameter inside a variance-dampening formula, then let the formula execute the order.

That is the research trajectory after V5: less emphasis on making a classifier smarter, more emphasis on finding control surfaces where probabilistic reasoning can help without destabilizing the system.
