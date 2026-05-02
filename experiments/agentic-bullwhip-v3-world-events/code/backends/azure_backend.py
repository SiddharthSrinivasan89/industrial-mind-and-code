"""
Azure OpenAI backend.

This module handles all communication with the Azure OpenAI API.
It implements get_order_decision() using the AzureOpenAI client from the openai SDK.

Both backends (azure and local) expose an identical function signature so
agent_interface.py can swap between them with zero code changes — just an
env var switch.

Why a separate module rather than an if/else in agent_interface?
  Keeping backends separate means the azure SDK never gets imported when you
  are running local experiments, and vice versa. It also keeps each backend
  file focused and easy to test in isolation.

Inference telemetry
-------------------
  All calls use stream=True so Time to First Token (TTFT) can be measured
  alongside total latency. The final streaming chunk carries usage stats including
  reasoning_tokens (o4-mini) and cached_tokens (Azure prompt caching).
"""

import json
import logging
import os
import time

from openai import AzureOpenAI
from json_repair import repair_json
from backends.resilience import call_with_backoff

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Client construction
# ---------------------------------------------------------------------------

def _build_client() -> AzureOpenAI:
    """
    Construct a fresh AzureOpenAI client using credentials from the environment.

    All three env vars are mandatory — Azure OpenAI requires an endpoint URL,
    an API key, and an API version string (e.g. "2025-01-01-preview").
    """
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_ENDPOINT"],
        api_key=os.environ["AZURE_API_KEY"],
        api_version=os.environ["AZURE_API_VERSION"],
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


def _stream_call(client, model, messages, max_tokens, temperature, model_tier):
    """
    Make a streaming Azure OpenAI call and return a telemetry tuple.

    Returns
    -------
    (raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens,
     reasoning_tokens, cached_tokens)

    reasoning_tokens — o4-mini internal chain-of-thought tokens
                       (from usage.completion_tokens_details.reasoning_tokens)
    cached_tokens    — prompt tokens served from Azure prompt cache
                       (from usage.prompt_tokens_details.cached_tokens)
    Both default to 0 if not present (non-reasoning models, cache miss).

    TTFT is wall-clock time from request dispatch to the first non-empty
    content chunk in the stream. For o4-mini this reflects both network
    round-trip and server-side reasoning time before first output token.
    """
    kwargs = dict(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        stream=True,
        stream_options={"include_usage": True},
    )
    if model_tier == "reasoning":
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = temperature

    t0 = time.perf_counter()
    ttft_ms = 0.0
    ttft_captured = False
    prompt_tokens = 0
    completion_tokens = 0
    reasoning_tokens = 0
    cached_tokens = 0
    chunks = []

    stream = client.chat.completions.create(**kwargs)

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            if not ttft_captured and content:   # first non-empty content chunk
                ttft_ms = (time.perf_counter() - t0) * 1000
                ttft_captured = True
            chunks.append(content)
        if chunk.usage:                         # arrives in the final usage chunk
            prompt_tokens     = chunk.usage.prompt_tokens or 0
            completion_tokens = chunk.usage.completion_tokens or 0
            ctd = getattr(chunk.usage, "completion_tokens_details", None)
            if ctd:
                reasoning_tokens = getattr(ctd, "reasoning_tokens", 0) or 0
            ptd = getattr(chunk.usage, "prompt_tokens_details", None)
            if ptd:
                cached_tokens = getattr(ptd, "cached_tokens", 0) or 0

    latency_ms = (time.perf_counter() - t0) * 1000
    raw = "".join(chunks)
    return raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens, reasoning_tokens, cached_tokens


# ---------------------------------------------------------------------------
# Public interface — matches local_backend.get_order_decision() exactly
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
    Call Azure OpenAI and return an inference result dict.

    Parameters
    ----------
    system_prompt  : The role/persona prompt from agent_interface.py
    user_prompt    : The per-period state variables from agent_interface.build_user_prompt()
    model_tier     : "lightweight" or "reasoning" — selects env var and temperature behaviour
    run_id         : Short identifier used in log messages only (no effect on the API call)
    period         : Current period number — used in log messages only
    tier           : "OEM", "Ancillary", or "Component" — used in log messages only
    model_name     : Optional override. If provided, the env var model is ignored.

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
      reasoning_tokens  (int)   — o4-mini chain-of-thought tokens; 0 for non-reasoning
      cached_tokens     (int)   — tokens served from Azure prompt cache; 0 on cache miss
      generation_tps    (float) — completion_tokens / (latency_ms / 1000)

    Retry hierarchy
    ---------------
    Two independent retry layers:

    Layer 1 — server/network errors (transient: 500, 429, 503, connection):
      call_with_backoff() retries the API call up to 10 times with exponential
      backoff (1s, 2s, 4s … capped at 60s). This layer never triggers on parse
      failures — it only catches openai exceptions raised before a response is received.

    Layer 2 — JSON parse failures (model-side):
      Attempt 1 — Streaming call, JSON mode enforced
      Attempt 2 — Identical repeat (handles stochastic token sampling failures)
      Attempt 3 — json_repair on raw string from attempt 2 (no new API call)

    Temperature note
    ----------------
    Temperature is NOT passed for reasoning model calls (o4-mini). Azure fixes
    reasoning model temperature at 1.0 and returns a 400 error if you send it.
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
    reasoning_tokens: int = 0
    cached_tokens: int = 0

    for attempt in range(1, 4):
        try:
            if attempt <= 2:
                raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens, \
                    reasoning_tokens, cached_tokens = call_with_backoff(
                        _stream_call,
                        client, model, messages, max_tokens, temperature, model_tier,
                        max_retries=10,
                        context=ctx,
                    )
            else:
                # Attempt 3: apply json_repair to the raw string from attempt 2.
                # No new API call — latency/ttft/tokens carry over from attempt 2.
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
                "reasoning_tokens":  reasoning_tokens,
                "cached_tokens":     cached_tokens,
                "generation_tps":    generation_tps,
            }

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            logger.warning("%s attempt=%d parse error: %s", ctx, attempt, exc)
            if attempt == 3:
                raise RuntimeError(
                    f"All 3 parse attempts failed — {ctx}"
                ) from exc
