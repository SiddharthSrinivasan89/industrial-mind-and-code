# Industrial Mind & Code — Development

Private research repository for AI experiments in industrial supply chains.

## Experiments

| Experiment | Description | Status |
|---|---|---|
| [Agentic_Bullwhip_Effect](Agentic_Bullwhip_Effect/) | Can LLM agents with domain context reduce the Bullwhip Effect in a 3-tier Indian automotive supply chain? 2×2 factorial: blind vs context × lightweight (gpt-4.1-mini) vs reasoning (o1). | Ready to run — 5 runs/config |

## Environment

- Azure OpenAI (gpt-4.1-mini, o1)
- Python 3.12
- See each experiment's `requirements.txt` for dependencies

## Security

`.env` and `*.log` are gitignored. Never commit secrets. Configure API credentials in the experiment's `.env` before running.
