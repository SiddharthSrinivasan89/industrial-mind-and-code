"""
base_agent.py
Shared OpenAI API call logic used by both blind and context agents.

Model-specific handling:
  - o1 / o3 reasoning models: temperature is API-fixed (not sent), and the
    API expects max_completion_tokens rather than max_tokens.
  - All other models: temperature sent as-is; max_tokens used.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from openai import AzureOpenAI, OpenAI

logger = logging.getLogger(__name__)

# Singleton client — created lazily so the import itself never fails if
# OPENAI_API_KEY is not yet set (e.g. during unit tests).
_client: OpenAI | None = None

# Models whose temperature is API-fixed and that use max_completion_tokens.
_REASONING_MODEL_PREFIXES = ("o1", "o3")


def _is_reasoning_model(model: str) -> bool:
    return any(model.startswith(p) for p in _REASONING_MODEL_PREFIXES)


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ["OPENAI_API_KEY"]
        base_url = os.environ.get("OPENAI_BASE_URL")
        azure_version = os.environ.get("AZURE_API_VERSION")
        if base_url and azure_version:
            _client = AzureOpenAI(
                api_key=api_key,
                azure_endpoint=base_url,
                api_version=azure_version,
            )
        elif base_url:
            _client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            _client = OpenAI(api_key=api_key)
    return _client


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float | None,
    max_tokens: int,
) -> dict[str, Any]:
    """
    Make a single chat-completion call and return a structured result dict.

    Returns a dict with keys:
        order_quantity   int   — parsed from JSON; 0 on parse failure
        reasoning        str   — parsed from JSON; "" on parse failure
        latency_seconds  float
        prompt_tokens    int
        completion_tokens int
        total_tokens     int
        raw_content      str   — verbatim model output
        parse_error      str | None
    """
    client = get_client()
    reasoning = _is_reasoning_model(model)

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    # Token limit parameter differs by model family
    if reasoning:
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens

    # Temperature: skip for reasoning models (API-fixed at 1.0)
    if temperature is not None and not reasoning:
        kwargs["temperature"] = temperature

    t0 = time.perf_counter()
    response = client.chat.completions.create(**kwargs)
    latency = round(time.perf_counter() - t0, 3)

    raw_content: str = response.choices[0].message.content or ""
    usage = response.usage

    result: dict[str, Any] = {
        "latency_seconds": latency,
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
        "raw_content": raw_content,
        "parse_error": None,
        "order_quantity": 0,
        "reasoning": "",
    }

    # Parse JSON from model output
    try:
        content_stripped = raw_content.strip()
        # Some models wrap JSON in markdown code fences — strip them
        if content_stripped.startswith("```"):
            lines = content_stripped.splitlines()
            # Remove first and last fence lines
            inner = [l for l in lines if not l.startswith("```")]
            content_stripped = "\n".join(inner).strip()
        # Strip thousand-separator commas from numbers (e.g. "27,959" → "27959")
        content_stripped = re.sub(r'(?<=\d),(?=\d)', '', content_stripped)
        # Strip Python-style underscore separators from numbers (e.g. "50_806" → "50806")
        content_stripped = re.sub(r'(?<=\d)_(?=\d)', '', content_stripped)
        parsed = json.loads(content_stripped)
        result["order_quantity"] = int(parsed["order_quantity"])
        result["reasoning"] = str(parsed.get("reasoning", ""))
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        result["parse_error"] = str(exc)
        logger.error(
            "LLM parse error [model=%s]: %s | raw: %.200s", model, exc, raw_content
        )

    return result
