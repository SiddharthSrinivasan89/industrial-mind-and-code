#!/usr/bin/env python3
"""IHF v1 plumbing for the FailureSensorIQ MCQ task.

Step-0 provider defaults from the model card, a telemetry-capturing Ollama call, and
answer parsing/classification. Frozen IHF v1 dimensions: SOR, AFC, TCA, TBC, FP.
Telemetry recorded per call so any run is IHF-scoreable after the fact.
"""
import json
import re
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CARDS = HERE.parent.parent / "frameworks" / "models"
OLLAMA = "http://localhost:11434/api/chat"
TAGS = "http://localhost:11434/api/tags"

CARD_FILE = {"gemma3:4b": "gemma3-4b.md",
             "phi4-mini": "phi4-mini.md",
             "phi4-mini-reasoning": "phi4-mini-reasoning.md",
             "nemotron-3-nano": "nemotron-3-nano.md"}


def resolve_defaults(model):
    """Step 0: read provider-recommended settings from frameworks/models/<model>.md.

    Returns dict with found, card, and the key:number pairs under the
    "## Provider defaults (IHF Step 0)" block (temperature, top_p, top_k,
    rec_output_tokens, max_output_tokens, context_window).
    """
    name = CARD_FILE.get(model) or CARD_FILE.get(model.split(":")[0])
    card = CARDS / name if name else None
    out = {"found": False, "card": str(card) if card else None}
    if not card or not card.exists():
        return out
    text = card.read_text()
    m = re.search(r"## Provider defaults \(IHF Step 0\)(.*?)(?:\n## |\Z)", text, re.S)
    if not m:
        return out
    out["found"] = True
    out["reasoning"] = bool(re.search(r"Thinking mode\*\*\s*\|\s*Yes", text, re.I))
    for line in m.group(1).splitlines():
        kv = re.match(r"\s*-\s*([a-z_]+):\s*([0-9.]+)\s*$", line)
        if kv:
            k, v = kv.group(1), kv.group(2)
            out[k] = float(v) if "." in v else int(v)
    return out


def model_version(model):
    """Version Pinning (Step 0): the exact model digest, so results reproduce."""
    base = model.split(":")[0]
    try:
        d = json.loads(urllib.request.urlopen(TAGS, timeout=5).read())
        for m in d.get("models", []):
            name = m.get("name", "")
            if name in (model, model + ":latest") or name.split(":")[0] == base:
                return (m.get("digest") or "")[:19] or "unknown"
    except Exception:
        return "unknown"
    return "unknown"


def call(model, prompt, settings, retries=5):
    """One call via native /api/chat. Returns (content, telemetry).

    Telemetry covers the IHF fields: attempts, finish_reason, prompt/completion tokens,
    empty, latency, and the sampling settings actually sent.
    """
    opts = {k: settings[k] for k in
            ("temperature", "top_p", "top_k", "seed", "num_ctx", "num_predict")
            if settings.get(k) is not None}
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "stream": False, "options": opts}
    if settings.get("think"):  # native thinking models: top-level flag, not in options
        payload["think"] = True
    delay = 2
    for attempt in range(1, retries + 1):
        try:
            t = time.time()
            req = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=600).read())
            msg = d.get("message", {})
            content = msg.get("content", "") or ""
            thinking = msg.get("thinking", "") or ""
            tele = {"attempts": attempt, "finish_reason": d.get("done_reason"),
                    "prompt_tokens": d.get("prompt_eval_count"),
                    "completion_tokens": d.get("eval_count"),
                    "empty": not content.strip(), "thinking_present": bool(thinking.strip()),
                    "thinking": thinking, "ms": round((time.time() - t) * 1000),
                    "temperature": opts.get("temperature"), "top_p": opts.get("top_p"),
                    "top_k": opts.get("top_k"), "num_ctx": opts.get("num_ctx"),
                    "num_predict": opts.get("num_predict")}
            return content, tele
        except Exception:
            if attempt == retries:
                raise
            time.sleep(min(delay, 60))
            delay *= 2


_LATEX = re.compile(r"\\boxed\{\s*([A-Z])\s*\}")


def parse_answer(reply, option_ids):
    """Pull the committed option label out of a reply. None if unreadable.

    Handles: \\boxed{X} (reasoning models), a leading letter (plain instruct), a
    committed "X)" after an answer word, and an "answer is X" fallback. Strips any
    <think> block first.
    """
    labels = [l.rstrip(")").upper() for l in option_ids]
    clean = re.sub(r"<think>.*?</think>", "", reply, flags=re.S | re.I)
    clean = re.sub(r"^.*?</think>", "", clean, flags=re.S | re.I)
    m = _LATEX.search(clean)
    if m and m.group(1) in labels:
        return option_ids[labels.index(m.group(1))]
    s = clean.strip().lstrip("*# ").strip()
    m = re.match(r"[*\s(]*([A-Z])(?![A-Za-z])", s)
    if m and m.group(1) in labels:
        return option_ids[labels.index(m.group(1))]
    mc = re.search(r"answer|correct|best|choose|select|pick|option", clean, re.I)
    if mc:
        pm = re.search(r"\b([A-Z])\)", clean[mc.start():])
        if pm and pm.group(1) in labels:
            return option_ids[labels.index(pm.group(1))]
    pm = re.search(r"\b([A-Z])\)", clean)
    if pm and pm.group(1) in labels:
        return option_ids[labels.index(pm.group(1))]
    for g in reversed(re.findall(r"(?:answer|option|correct)[^A-Za-z]{0,15}([A-Z])\b", clean, re.I)):
        if g.upper() in labels:
            return option_ids[labels.index(g.upper())]
    return None
