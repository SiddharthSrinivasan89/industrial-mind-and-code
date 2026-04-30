"""
Local inference backend for V4 WorldEvents.

Targets any OpenAI-compatible endpoint (Ollama, vLLM, LM Studio).

Public interface:
  get_intent_decision() — called by agent_interface.get_intent_class()

Key difference from azure_backend: temperature IS always passed because local
servers don't enforce fixed temperature the way Azure does for o4-mini.
"""

import json
import logging
import os
import time

from openai import OpenAI
from json_repair import repair_json
from backends.resilience import call_with_backoff

logger = logging.getLogger(__name__)

_VALID_INTENTS = frozenset({
    "STRONG_INCREASE", "MODERATE_INCREASE", "NEUTRAL",
    "MODERATE_DECREASE", "STRONG_DECREASE",
})


# ---------------------------------------------------------------------------
# Client and per-call configuration
# ---------------------------------------------------------------------------

_DEFAULT_MAX_TOKENS = {"lightweight": 512, "reasoning": 32768}
_DEFAULT_TEMPS      = {"lightweight": 0.4, "reasoning": 0.3}


def _build_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ.get("LOCAL_ENDPOINT", "http://localhost:11434/v1"),
        api_key=os.environ.get("LOCAL_API_KEY", "ollama"),
        max_retries=0,
    )


def _model_name(model_tier: str, model_name: str | None = None) -> str:
    if model_name:
        return model_name
    key = "MODEL_LIGHTWEIGHT" if model_tier == "lightweight" else "MODEL_REASONING"
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Env var {key} must be set — e.g. MODEL_LIGHTWEIGHT=phi4:14b")
    return val


def _max_tokens(model_tier: str) -> int:
    key     = "MAX_TOKENS_LIGHTWEIGHT" if model_tier == "lightweight" else "MAX_TOKENS_REASONING"
    default = _DEFAULT_MAX_TOKENS[model_tier]
    return int(os.environ.get(key, default))


def _temperature(model_tier: str) -> float:
    key     = "TEMP_LIGHTWEIGHT" if model_tier == "lightweight" else "TEMP_REASONING"
    default = _DEFAULT_TEMPS[model_tier]
    return float(os.environ.get(key, default))


def _stream_call(client, model, messages, max_tokens, temperature):
    """Streaming call. Returns (raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens)."""
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
            if not ttft_captured and content:
                ttft_ms = (time.perf_counter() - t0) * 1000
                ttft_captured = True
            chunks.append(content)
        if chunk.usage:
            prompt_tokens     = chunk.usage.prompt_tokens or 0
            completion_tokens = chunk.usage.completion_tokens or 0

    latency_ms = (time.perf_counter() - t0) * 1000
    raw = "".join(chunks)
    return raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens


# ---------------------------------------------------------------------------
# Shared retry core
# ---------------------------------------------------------------------------

def _call_and_parse(client, model, messages, max_tokens, temperature, ctx):
    """3-attempt parse loop. Returns (parsed_dict, attempt, latency, ttft, p_tok, c_tok)."""
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
                logger.warning("%s attempt=3 applying json_repair", ctx)
                raw = repair_json(raw)

            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise TypeError(f"Expected JSON object, got {type(parsed).__name__}")

            if attempt > 1:
                logger.warning("%s resolved on attempt=%d", ctx, attempt)

            return parsed, attempt, latency_ms, ttft_ms, prompt_tokens, completion_tokens

        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("%s attempt=%d parse error: %s", ctx, attempt, exc)
            if attempt == 3:
                raise RuntimeError(f"All 3 parse attempts failed — {ctx}") from exc

    raise RuntimeError(f"Unreachable — {ctx}")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_intent_decision(
    system_prompt: str,
    user_prompt: str,
    model_tier: str,
    run_id: str,
    period: int,
    tier: str,
    model_name: str | None = None,
    temperature: float | None = None,
) -> dict:
    """Call local endpoint and return intent classification + telemetry."""
    client  = _build_client()
    model   = _model_name(model_tier, model_name)
    max_tok = _max_tokens(model_tier)
    if temperature is None:
        temperature = _temperature(model_tier)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]
    ctx = f"run={run_id} period={period} tier={tier} [intent]"

    parsed, attempt, latency_ms, ttft_ms, prompt_tokens, completion_tokens = (
        _call_and_parse(client, model, messages, max_tok, temperature, ctx)
    )

    try:
        intent = str(parsed["intent"]).strip().upper()
        rationale = str(parsed.get("rationale", ""))
    except (KeyError, ValueError, TypeError) as exc:
        raise RuntimeError(f"Missing or invalid intent field — {ctx}") from exc

    if intent not in _VALID_INTENTS:
        raise RuntimeError(
            f"Unrecognised intent '{intent}' — expected one of {sorted(_VALID_INTENTS)} — {ctx}"
        )

    generation_tps = (
        round(completion_tokens / (latency_ms / 1000), 1)
        if latency_ms > 0 and completion_tokens > 0 else 0.0
    )

    return {
        "intent":            intent,
        "rationale":         rationale,
        "attempt_number":    attempt,
        "latency_ms":        round(latency_ms, 1),
        "ttft_ms":           round(ttft_ms, 1),
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": completion_tokens,
        "generation_tps":    generation_tps,
    }
