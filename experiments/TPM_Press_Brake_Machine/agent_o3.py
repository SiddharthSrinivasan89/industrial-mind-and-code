"""
TPM Cross-Pillar Reasoning Agent — o3-mini (Azure OpenAI)
Same task as agent.py / Qwen3.5. Identical prompts for fair comparison.
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

# ── Azure OpenAI config ────────────────────────────────────────────────────
# Reads from the shared .env in Agentic_Bullwhip_Effect or from environment variables.
import os

def _load_env() -> dict:
    env_path = Path(__file__).parent.parent / "Agentic_Bullwhip_Effect" / ".env"
    vals = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
    return vals

_env = _load_env()

API_KEY      = os.environ.get("OPENAI_API_KEY") or _env.get("OPENAI_API_KEY", "")
BASE_URL     = os.environ.get("OPENAI_BASE_URL") or _env.get("OPENAI_BASE_URL", "https://industrial-mind-and-cod-resource.openai.azure.com")
DEPLOYMENT   = "o3-mini"
API_VERSION  = os.environ.get("AZURE_API_VERSION") or _env.get("AZURE_API_VERSION", "2025-01-01-preview")

OLLAMA_URL   = f"{BASE_URL}/openai/deployments/{DEPLOYMENT}/chat/completions?api-version={API_VERSION}"

EXPERIMENTS_PATH = Path(__file__).parent / "experiments_v2.md"

# ── Prompts (identical to agent.py) ───────────────────────────────────────

SYSTEM_PROMPT = """You are a senior TPM investigator specializing in cross-functional root cause analysis on industrial machinery.

You have access to issue logs from all 8 pillars of TPM for a press brake machine (PB-07):
1. Autonomous Maintenance
2. Focused Improvement
3. Planned Maintenance
4. Quality Maintenance
5. Early Equipment Management
6. Training and Education
7. Safety, Health and Environment
8. Administration and Office TPM

Your job is NOT to analyze each pillar in isolation.
Your job is to find CONNECTIONS between issues that span multiple pillars —
connections that no single-pillar team would ever see because they only see their own data.

A connection is only worth surfacing if:
- It spans at least 2 different pillars
- There is a plausible causal or contributing relationship between the issues
- The connection explains something that looks unexplained within any single pillar

For each connection you find:
- State the pillars involved
- Trace the exact chain of events (with issue IDs)
- Explain why this connection matters (consequence or latent risk)
- Rate your confidence: HIGH / MEDIUM / LOW

Also explicitly flag any apparent connections that you investigated but concluded are NOT causally linked (red herrings). Explain why they look connected but aren't.

Think carefully. The most important connections are the ones no rule would catch."""


INVESTIGATION_PROMPT = """Here is the full issue dataset for PB-07 press brake over the period Jan 1 – Mar 7, 2024:

{dataset}

---

Investigate this dataset for cross-pillar connections.

Work through the data systematically. Start with quality defects and safety events (they are the visible symptoms), then trace backwards through maintenance, training, procurement, and equipment history to find the root causes that cross pillar boundaries.

After your investigation, produce a report with the following structure:

## Cross-Pillar Connection Report — PB-07

For each connection found:

### Connection [N]: [Short title]
**Pillars:** [list pillars]
**Chain:** [Issue ID] → [Issue ID] → ... → [outcome]
**Mechanism:** [explain the causal link]
**Consequence / Risk:** [what this means operationally]
**Confidence:** HIGH / MEDIUM / LOW

---

## Red Herrings Investigated
List any patterns that looked like cross-pillar connections but are NOT supported by the evidence. Explain why.

---

At the end, add:

## Priority Actions
Ranked list of the top 3 interventions that would break the most connection chains simultaneously."""


# ── Azure OpenAI client (streaming) ───────────────────────────────────────

def chat_stream(system: str, user: str) -> tuple[str, str]:
    """Stream from Azure OpenAI o3-mini. Returns (reasoning, content)."""
    payload = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "stream": True,
        "reasoning_effort": "high",
        "max_completion_tokens": 32000,
    }

    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "api-key":      API_KEY,
        },
        method="POST",
    )

    content_buf     = []
    reasoning_buf   = []
    printed_header  = False

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode().strip()
                if not line or line == "data: [DONE]":
                    if line == "data: [DONE]":
                        print("\n", flush=True)
                    continue

                if line.startswith("data: "):
                    line = line[6:]

                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})

                # o3-mini reasoning tokens (if surfaced)
                reasoning_delta = delta.get("reasoning_content") or ""
                content_delta   = delta.get("content") or ""

                if reasoning_delta:
                    if not printed_header:
                        print("[REASONING TOKENS]\n", flush=True)
                        printed_header = True
                    print(reasoning_delta, end="", flush=True)
                    reasoning_buf.append(reasoning_delta)

                if content_delta:
                    if not content_buf:
                        print("\n\n[RESPONSE]\n", flush=True)
                    print(content_delta, end="", flush=True)
                    content_buf.append(content_delta)

    except urllib.error.URLError as e:
        raise RuntimeError(f"Azure OpenAI unreachable: {e}") from e

    return "".join(reasoning_buf), "".join(content_buf)


# ── Agent ──────────────────────────────────────────────────────────────────

def run_agent():
    print("=" * 60)
    print("TPM Cross-Pillar Reasoning Agent")
    print("Machine: PB-07 | Model: o3-mini (Azure OpenAI)")
    print("=" * 60)

    if not EXPERIMENTS_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {EXPERIMENTS_PATH}")

    dataset = EXPERIMENTS_PATH.read_text()
    print(f"\n[+] Loaded dataset ({len(dataset)} chars)")
    print("[+] Sending to o3-mini for cross-pillar reasoning...\n")

    user_prompt = INVESTIGATION_PROMPT.format(dataset=dataset)
    reasoning, content = chat_stream(SYSTEM_PROMPT, user_prompt)

    print("=" * 60)
    print("INVESTIGATION COMPLETE")
    print("=" * 60)

    report_path = Path(__file__).parent / "report_o3.md"
    report_path.write_text(f"# TPM Cross-Pillar Investigation Report — o3-mini\n\n{content}\n")
    print(f"\n[+] Report saved to: {report_path}")
    print(f"[+] Reasoning tokens: {len(reasoning)} chars | Report: {len(content)} chars")


if __name__ == "__main__":
    run_agent()
