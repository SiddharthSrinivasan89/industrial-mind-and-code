"""
TPM Cross-Pillar Reasoning Agent
Machine: PB-07 Press Brake

The agent reads all issues across the 8 TPM pillars and reasons
across them to surface connections that no single-pillar team would see.

Uses: Qwen3.5 (local Ollama) with thinking enabled
"""

import json
import urllib.request
import urllib.error
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3.5"

EXPERIMENTS_PATH = Path(__file__).parent / "experiments_v2.md"


# ── Prompts ────────────────────────────────────────────────────────────────

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


# ── Ollama client ──────────────────────────────────────────────────────────

def chat_stream(system: str, user: str, think: bool = True) -> tuple[str, str]:
    """Stream from Ollama. Returns (thinking, content)."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "think": think,
        "options": {
            "temperature": 0.6,
            "top_p": 0.95,
            "num_ctx": 8192,
        },
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    thinking_buf = []
    content_buf = []
    printed_thinking_header = False

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode().strip()
                if not line:
                    continue

                chunk = json.loads(line)
                msg = chunk.get("message", {})
                thinking_delta = msg.get("thinking", "")
                content_delta = msg.get("content", "")

                if thinking_delta:
                    if not printed_thinking_header:
                        print("[THINKING]\n", flush=True)
                        printed_thinking_header = True
                    print(thinking_delta, end="", flush=True)
                    thinking_buf.append(thinking_delta)

                if content_delta:
                    if thinking_buf and not content_buf:
                        print("\n\n[RESPONSE]\n", flush=True)
                    print(content_delta, end="", flush=True)
                    content_buf.append(content_delta)

                if chunk.get("done"):
                    print("\n", flush=True)
                    break

    except urllib.error.URLError as e:
        raise RuntimeError(f"Ollama unreachable: {e}") from e

    return "".join(thinking_buf), "".join(content_buf)


# ── Agent ──────────────────────────────────────────────────────────────────

def run_agent():
    print("=" * 60)
    print("TPM Cross-Pillar Reasoning Agent")
    print("Machine: PB-07 | Model: qwen3.5 (thinking)")
    print("=" * 60)

    # Load dataset
    if not EXPERIMENTS_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {EXPERIMENTS_PATH}")

    dataset = EXPERIMENTS_PATH.read_text()
    print(f"\n[+] Loaded dataset ({len(dataset)} chars)")
    print("[+] Sending to Qwen3.5 for cross-pillar reasoning...\n")

    # Run investigation
    user_prompt = INVESTIGATION_PROMPT.format(dataset=dataset)
    thinking, content = chat_stream(SYSTEM_PROMPT, user_prompt, think=True)

    # Print full report header (content already streamed live above)
    print("=" * 60)
    print("INVESTIGATION COMPLETE")
    print("=" * 60)

    # Save report
    report_path = Path(__file__).parent / "report_v2.md"
    report_path.write_text(f"# TPM Cross-Pillar Investigation Report\n\n{content}\n")
    print(f"\n[+] Report saved to: {report_path}")

    print(f"[+] Thinking length: {len(thinking)} chars | Report length: {len(content)} chars")


if __name__ == "__main__":
    run_agent()
