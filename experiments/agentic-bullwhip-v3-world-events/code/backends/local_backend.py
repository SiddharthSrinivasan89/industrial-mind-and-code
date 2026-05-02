"""
Local inference backend.

Targets any OpenAI-compatible endpoint: Ollama, LM Studio, vLLM, llama.cpp server, etc.
Implements the same get_order_decision() signature as azure_backend so agent_interface.py
can swap backends with no code changes — just set BACKEND=local in the env file.

When to use this backend
------------------------
  - Running OSS models locally before committing to an Azure spend
  - E4 experiments with phi4:14b via Ollama or vLLM
  - Offline development and debugging — no API key or network required

Key difference from azure_backend
----------------------------------
  Temperature IS passed on every call (including reasoning-tier calls) because
  local servers don't enforce a fixed temperature the way Azure does for o4-mini.
  If you are running a reasoning model locally that rejects temperature, remove it
  from the kwargs dict in this backend or set TEMP_REASONING=1.0.

Inference telemetry
-------------------
  All calls use stream=True so Time to First Token (TTFT) can be measured alongside
  total latency. The final streaming chunk carries usage stats (prompt_tokens,
  completion_tokens) when stream_options={"include_usage": True} is set.
  Ollama ≥ 0.6 and vLLM ≥ 0.4 support this option.
"""

import json
import logging
import os
import time

from openai import OpenAI
from json_repair import repair_json
from backends.resilience import call_with_backoff

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Client construction
# ---------------------------------------------------------------------------

def _build_client() -> OpenAI:
    """
    Construct an OpenAI client pointed at the local inference server.

    LOCAL_ENDPOINT must be the base URL of the OpenAI-compatible API.
    Examples:
      Ollama:    http://localhost:11434/v1
      LM Studio: http://localhost:1234/v1
      vLLM:      http://localhost:8000/v1

    LOCAL_API_KEY defaults to "ollama" — Ollama requires a non-empty key string
    but ignores its value. For servers that enforce real keys, set this var.
    """
    return OpenAI(
        base_url=os.environ["LOCAL_ENDPOINT"],
        api_key=os.environ.get("LOCAL_API_KEY", "ollama"),
        max_retries=0,  # retries are handled here via call_with_backoff
    )


# ---------------------------------------------------------------------------
# Per-call configuration helpers
# ---------------------------------------------------------------------------

def _model_name(model_tier: str, model_name: str | None = None) -> str:
    if model_name:
        return model_name
    key = "MODEL_LIGHTWEIGHT" if model_tier == "lightweight" else "MODEL_REASONING"
    return os.environ[key]


def _max_tokens(model_tier: str) -> int:
    key = "MAX_TOKENS_LIGHTWEIGHT" if model_tier == "lightweight" else "MAX_TOKENS_REASONING"
    return int(os.environ[key])


def _temperature(model_tier: str) -> float:
    key = "TEMP_LIGHTWEIGHT" if model_tier == "lightweight" else "TEMP_REASONING"
    return float(os.environ[key])


def _stream_call(client, model, messages, max_tokens, temperature):
    """
    Make a streaming API call and return (raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens).

    Uses stream_options={"include_usage": True} so token counts arrive in the
    final chunk. If the server doesn't support this option, usage defaults to 0.

    TTFT is measured as the wall-clock time from request dispatch to the first
    non-empty content chunk. Total latency covers the full stream to the last chunk.
    """
    t0 = time.perf_counter()
    ttft_ms = 0.0
    ttft_captured = False
    prompt_tokens = 0
    completion_tokens = 0
    chunks = []

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={"type": "json_object"},
        stream=True,
        stream_options={"include_usage": True},
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            if not ttft_captured and content:   # first non-empty content chunk
                ttft_ms = (time.perf_counter() - t0) * 1000
                ttft_captured = True
            chunks.append(content)
        if chunk.usage:                         # arrives in the final chunk
            prompt_tokens     = chunk.usage.prompt_tokens or 0
            completion_tokens = chunk.usage.completion_tokens or 0

    latency_ms = (time.perf_counter() - t0) * 1000
    raw = "".join(chunks)
    return raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens


# ---------------------------------------------------------------------------
# Public interface — matches azure_backend.get_order_decision() exactly
# ---------------------------------------------------------------------------

def get_order_decision(
    system_prompt: str,
    user_prompt: str,
    model_tier: str,
    run_id: str,
    period: int,
    tier: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict:
    """
    Call a local OpenAI-compatible server and return an inference result dict.

    Parameters
    ----------
    system_prompt  : The role/persona prompt from agent_interface.py
    user_prompt    : The per-period state variables from agent_interface.build_user_prompt()
    model_tier     : "lightweight" or "reasoning" — selects env vars for model/tokens/temperature
    run_id         : Short identifier used in log messages only
    period         : Current period number — used in log messages only
    tier           : "OEM", "Ancillary", or "Component" — used in log messages only
    model_name     : Optional override. If provided, env var model is ignored.

    Returns
    -------
    dict with keys:
      order_quantity    (int)
      rationale         (str)
      attempt_number    (int)   — which attempt (1–3) succeeded
      latency_ms        (float) — total wall-clock time for the successful call
      ttft_ms           (float) — time to first token; 0.0 if json_repair path used
      prompt_tokens     (int)
      completion_tokens (int)
      generation_tps    (float) — completion_tokens / (latency_ms / 1000)

    Retry hierarchy
    ---------------
    Two independent retry layers:

    Layer 1 — server/network errors (transient: 500, 429, 503, connection):
      call_with_backoff() retries the API call up to 10 times with exponential
      backoff (1s, 2s, 4s … capped at 60s).

    Layer 2 — JSON parse failures (model-side):
      Attempt 1 — Streaming call, JSON mode enforced
      Attempt 2 — Identical repeat (handles stochastic token sampling failures)
      Attempt 3 — json_repair on raw string from attempt 2 (no new API call)

    RuntimeError is raised if all three parse attempts fail. Caller replaces the run.
    """
    client = _build_client()
    model = _model_name(model_tier, model_name)
    max_tokens = _max_tokens(model_tier)
    if temperature is None:
        temperature = _temperature(model_tier)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    ctx = f"run={run_id} period={period} tier={tier}"
    raw = ""
    latency_ms: float = 0.0
    ttft_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    for attempt in range(1, 4):
        try:
            if attempt <= 2:
                raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens = call_with_backoff(
                    _stream_call,
                    client, model, messages, max_tokens, temperature,
                    max_retries=10,
                    context=ctx,
                )
            else:
                # Attempt 3: apply json_repair to the raw string from attempt 2.
                # No new API call — latency/ttft carry over from attempt 2.
                logger.warning("%s attempt=3 applying json_repair", ctx)
                raw = repair_json(raw)

            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise TypeError(f"Expected JSON object, got {type(parsed).__name__}")
            order_qty = int(parsed["order_quantity"])
            rationale = str(parsed.get("rationale", ""))

            if attempt > 1:
                logger.warning("%s resolved on attempt=%d", ctx, attempt)

            generation_tps = (
                round(completion_tokens / (latency_ms / 1000), 1)
                if latency_ms > 0 and completion_tokens > 0 else 0.0
            )

            return {
                "order_quantity":    order_qty,
                "rationale":         rationale,
                "attempt_number":    attempt,
                "latency_ms":        round(latency_ms, 1),
                "ttft_ms":           round(ttft_ms, 1),
                "prompt_tokens":     prompt_tokens,
                "completion_tokens": completion_tokens,
                "generation_tps":    generation_tps,
            }

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            logger.warning("%s attempt=%d parse error: %s", ctx, attempt, exc)
            if attempt == 3:
                raise RuntimeError(
                    f"All 3 parse attempts failed — {ctx}"
                ) from exc
