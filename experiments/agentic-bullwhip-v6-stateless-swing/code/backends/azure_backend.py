"""
Azure OpenAI backend for V6 StatelessSwing.

Public interface:
  get_alpha_decision() — called by agent_interface.get_alpha_value(); validates `alpha` field

Retry architecture:
  Layer 1 (server): call_with_backoff(), 10 retries, exponential backoff capped at 60s.
  Layer 2 (parse):  3-attempt loop; attempt 3 applies json_repair on raw string.
"""

import json
import logging
import os
import time

from openai import AzureOpenAI, BadRequestError
from json_repair import repair_json
from backends.resilience import call_with_backoff

logger = logging.getLogger(__name__)

_VALID_ALPHAS = frozenset({0.1, 0.3, 0.5, 0.7})


# ---------------------------------------------------------------------------
# Client and per-call configuration
# ---------------------------------------------------------------------------

def _build_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_ENDPOINT"],
        api_key=os.environ["AZURE_API_KEY"],
        api_version=os.environ.get("AZURE_API_VERSION", "2025-01-01-preview"),
        max_retries=0,
    )


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
    """Streaming API call. Returns (raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens)."""
    t0 = time.perf_counter()
    ttft_ms = 0.0
    ttft_captured = False
    prompt_tokens = 0
    completion_tokens = 0
    reasoning_tokens = 0
    cached_tokens = 0
    chunks = []

    kwargs = dict(
        model=model,
        messages=messages,
        max_completion_tokens=max_tokens,
        response_format={"type": "json_object"},
        stream=True,
        stream_options={"include_usage": True},
    )
    if temperature is not None:
        kwargs["temperature"] = temperature

    stream = client.chat.completions.create(**kwargs)

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
            details = getattr(chunk.usage, "completion_tokens_details", None)
            if details:
                reasoning_tokens = getattr(details, "reasoning_tokens", 0) or 0
            cache = getattr(chunk.usage, "prompt_tokens_details", None)
            if cache:
                cached_tokens = getattr(cache, "cached_tokens", 0) or 0

    latency_ms = (time.perf_counter() - t0) * 1000
    raw = "".join(chunks)
    return raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens, reasoning_tokens, cached_tokens


# ---------------------------------------------------------------------------
# Shared retry core
# ---------------------------------------------------------------------------

def _call_and_parse(
    client,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float | None,
    ctx: str,
) -> tuple[dict, int, float, float, int, int, int, int]:
    """
    Run the 3-attempt retry loop and return (parsed_dict, attempt, latency_ms,
    ttft_ms, prompt_tokens, completion_tokens, reasoning_tokens, cached_tokens).

    Raises RuntimeError if all 3 parse attempts fail.
    """
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
                raw, latency_ms, ttft_ms, prompt_tokens, completion_tokens, reasoning_tokens, cached_tokens = (
                    call_with_backoff(
                        _stream_call,
                        client, model, messages, max_tokens, temperature,
                        max_retries=10,
                        context=ctx,
                    )
                )
            else:
                logger.warning("%s attempt=3 applying json_repair", ctx)
                raw = repair_json(raw)

            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise TypeError(f"Expected JSON object, got {type(parsed).__name__}")

            if attempt > 1:
                logger.warning("%s resolved on attempt=%d", ctx, attempt)

            return parsed, attempt, latency_ms, ttft_ms, prompt_tokens, completion_tokens, reasoning_tokens, cached_tokens

        except BadRequestError as exc:
            raise RuntimeError(f"API 400 BadRequest — {ctx}: {exc}") from exc
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("%s attempt=%d parse error: %s", ctx, attempt, exc)
            if attempt == 3:
                raise RuntimeError(f"All 3 parse attempts failed — {ctx}") from exc

    raise RuntimeError(f"Unreachable — {ctx}")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_alpha_decision(
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
    Call Azure and return alpha selection + telemetry.

    The `alpha` field must be one of {0.1, 0.3, 0.5, 0.7}.
    If the parsed alpha is missing or invalid, RuntimeError is raised so
    agent_interface.get_alpha_value() can apply the 0.3 fallback.
    """
    client  = _build_client()
    model   = _model_name(model_tier, model_name)
    max_tok = _max_tokens(model_tier)
    # o4-mini (reasoning tier) does not accept temperature — Azure enforces 1.0
    if model_tier == "reasoning":
        temperature = None
    elif temperature is None:
        temperature = _temperature(model_tier)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]
    ctx = f"run={run_id} period={period} tier={tier} [alpha]"

    parsed, attempt, latency_ms, ttft_ms, prompt_tokens, completion_tokens, reasoning_tokens, cached_tokens = (
        _call_and_parse(client, model, messages, max_tok, temperature, ctx)
    )

    try:
        alpha = round(float(parsed["alpha"]), 1)
        rationale = str(parsed.get("rationale", ""))
    except (KeyError, ValueError, TypeError) as exc:
        raise RuntimeError(f"Missing or invalid alpha field in response — {ctx}") from exc

    if alpha not in _VALID_ALPHAS:
        raise RuntimeError(
            f"Invalid alpha {alpha} — expected one of {sorted(_VALID_ALPHAS)} — {ctx}"
        )

    generation_tps = (
        round(completion_tokens / (latency_ms / 1000), 1)
        if latency_ms > 0 and completion_tokens > 0 else 0.0
    )

    return {
        "alpha":             alpha,
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
