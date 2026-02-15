"""
Azure AI Foundry Client
========================
Wraps Azure AI Foundry endpoints.
Handles auth, retries, JSON parsing, call logging.
"""

import json
import hashlib
import time
import re
import os
import logging
from dataclasses import dataclass
from typing import Optional

from openai import AzureOpenAI

logger = logging.getLogger(__name__)


@dataclass
class APICallLog:
    timestamp: str
    model: str
    prompt_hash: str
    temperature: float
    response_raw: str
    response_parsed: Optional[dict]
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    success: bool
    error: Optional[str] = None


class FoundryClient:
    """Azure AI Foundry API wrapper with retry and JSON parsing."""

    def __init__(self, config: dict):
        self.endpoint = config["azure"]["endpoint"]
        self.api_version = config["azure"].get("api_version", "2024-12-01-preview")
        self.api_key = (
            config["azure"].get("api_key")
            or os.environ.get("AZURE_AI_API_KEY", "")
        )
        self.models = config["models"]
        self.call_log: list = []

        # Track last call time per model tier for rate limiting
        self._last_call_time = {}

        # Default client
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )

        # Per-model clients for models with different endpoints
        self._model_clients = {}
        for tier, mcfg in self.models.items():
            if "endpoint" in mcfg and mcfg["endpoint"] != self.endpoint:
                self._model_clients[tier] = AzureOpenAI(
                    azure_endpoint=mcfg["endpoint"],
                    api_key=self.api_key,
                    api_version=self.api_version,
                )

    def call(self, model_tier: str, prompt: str,
             system_prompt: Optional[str] = None,
             max_retries: int = 3, retry_delay: float = 2.0) -> dict:
        """
        Call LLM and return parsed JSON.

        Args:
            model_tier: 'lightweight', 'reasoning', or 'open_source'
            prompt: User prompt
            system_prompt: Optional system message
            max_retries: Retry count
            retry_delay: Base delay (exponential backoff)

        Returns:
            Parsed JSON dict from LLM

        Raises:
            RuntimeError: If all retries fail
        """
        model_config = self.models[model_tier]
        deployment = model_config["deployment"]
        temperature = model_config["temperature"]
        max_tokens = model_config["max_tokens"]
        inter_call_delay = model_config.get("inter_call_delay", 0.0)

        # Rate limiting: Wait before making call if needed
        if inter_call_delay > 0 and model_tier in self._last_call_time:
            elapsed = time.time() - self._last_call_time[model_tier]
            if elapsed < inter_call_delay:
                wait_time = inter_call_delay - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.1f}s before next call")
                time.sleep(wait_time)

        # Use per-model client if configured, otherwise default
        client = self._model_clients.get(model_tier, self.client)

        messages = []
        is_o1 = "o1" in deployment.lower()

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        last_error = None

        for attempt in range(max_retries):
            start = time.time()
            try:
                # o1 doesn't support temperature; uses max_completion_tokens
                # o1 needs more tokens as it uses them for internal reasoning
                call_params = {
                    "model": deployment,
                    "messages": messages,
                }
                if is_o1:
                    call_params["max_completion_tokens"] = max(max_tokens, 4000)
                else:
                    call_params["max_tokens"] = max_tokens
                    call_params["temperature"] = temperature

                response = client.chat.completions.create(**call_params)
                latency = (time.time() - start) * 1000
                raw = response.choices[0].message.content or ""
                
                # Log raw response for debugging
                if not raw.strip():
                    # o1 may use refusal or different content structure
                    choice = response.choices[0]
                    logger.warning(
                        f"Empty content from {deployment}. "
                        f"finish_reason={choice.finish_reason}, "
                        f"refusal={getattr(choice.message, 'refusal', None)}"
                    )
                    raise ValueError(f"Empty response from {deployment}")
                
                usage = response.usage
                parsed = self._parse_json(raw)

                # Record successful call time for rate limiting
                self._last_call_time[model_tier] = time.time()

                self.call_log.append(APICallLog(
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                    model=deployment, prompt_hash=prompt_hash,
                    temperature=temperature, response_raw=raw,
                    response_parsed=parsed, latency_ms=round(latency, 1),
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    success=True,
                ))
                logger.debug(
                    f"OK: {deployment} {latency:.0f}ms {usage.total_tokens}tok"
                )
                return parsed

            except Exception as e:
                latency = (time.time() - start) * 1000
                last_error = str(e)
                self.call_log.append(APICallLog(
                    timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                    model=deployment, prompt_hash=prompt_hash,
                    temperature=temperature, response_raw="",
                    response_parsed=None, latency_ms=round(latency, 1),
                    prompt_tokens=0, completion_tokens=0, total_tokens=0,
                    success=False, error=last_error,
                ))
                logger.warning(
                    f"FAIL ({attempt+1}/{max_retries}): {last_error}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))

        raise RuntimeError(
            f"All {max_retries} retries failed for {deployment}: {last_error}"
        )

    def _parse_json(self, raw: str) -> dict:
        """Parse JSON from LLM response, handling fences, preamble, and comma numbers."""
        text = raw.strip()

        # Strip commas from numbers in JSON (e.g. 28,155 -> 28155)
        # Matches digits,digits patterns that aren't inside quotes
        def strip_number_commas(s):
            # Remove commas between digits: 28,155 -> 28155
            return re.sub(r'(?<=\d),(?=\d)', '', s)

        # Direct parse
        try:
            return json.loads(strip_number_commas(text))
        except json.JSONDecodeError:
            pass

        # Strip markdown fences
        for pat in [r"```json\s*\n?(.*?)\n?\s*```", r"```\s*\n?(.*?)\n?\s*```"]:
            m = re.search(pat, text, re.DOTALL)
            if m:
                try:
                    return json.loads(strip_number_commas(m.group(1).strip()))
                except json.JSONDecodeError:
                    continue

        # Find JSON object in text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(strip_number_commas(text[start:end + 1]))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Cannot parse JSON from {len(raw)} chars:\n{raw[:300]}")

    def get_usage_summary(self) -> dict:
        ok = [l for l in self.call_log if l.success]
        fail = [l for l in self.call_log if not l.success]
        tokens = sum(l.total_tokens for l in ok)
        latency = sum(l.latency_ms for l in ok)

        by_model = {}
        for l in ok:
            if l.model not in by_model:
                by_model[l.model] = {"calls": 0, "tokens": 0, "latency_ms": 0}
            by_model[l.model]["calls"] += 1
            by_model[l.model]["tokens"] += l.total_tokens
            by_model[l.model]["latency_ms"] += l.latency_ms
        for m in by_model:
            by_model[m]["avg_latency_ms"] = round(
                by_model[m]["latency_ms"] / max(by_model[m]["calls"], 1), 1
            )

        return {
            "total_calls": len(self.call_log),
            "successful": len(ok),
            "failed": len(fail),
            "total_tokens": tokens,
            "avg_latency_ms": round(latency / max(len(ok), 1), 1),
            "by_model": by_model,
        }

    def export_logs(self, filepath: str):
        logs = [{
            "timestamp": l.timestamp, "model": l.model,
            "prompt_hash": l.prompt_hash, "temperature": l.temperature,
            "response_raw": l.response_raw,
            "response_parsed": l.response_parsed,
            "latency_ms": l.latency_ms,
            "prompt_tokens": l.prompt_tokens,
            "completion_tokens": l.completion_tokens,
            "total_tokens": l.total_tokens,
            "success": l.success, "error": l.error,
        } for l in self.call_log]

        with open(filepath, "w") as f:
            json.dump(logs, f, indent=2)
        logger.info(f"Exported {len(logs)} logs to {filepath}")




















# """
# Azure AI Foundry Client
# ========================
# Wraps Azure AI Foundry endpoints.
# Handles auth, retries, JSON parsing, call logging.
# """

# import json
# import hashlib
# import time
# import re
# import os
# import logging
# from dataclasses import dataclass
# from typing import Optional

# from openai import AzureOpenAI

# logger = logging.getLogger(__name__)


# @dataclass
# class APICallLog:
#     timestamp: str
#     model: str
#     prompt_hash: str
#     temperature: float
#     response_raw: str
#     response_parsed: Optional[dict]
#     latency_ms: float
#     prompt_tokens: int
#     completion_tokens: int
#     total_tokens: int
#     success: bool
#     error: Optional[str] = None


# class FoundryClient:
#     """Azure AI Foundry API wrapper with retry and JSON parsing."""

#     def __init__(self, config: dict):
#         self.endpoint = config["azure"]["endpoint"]
#         self.api_version = config["azure"].get("api_version", "2024-12-01-preview")
#         self.api_key = (
#             config["azure"].get("api_key")
#             or os.environ.get("AZURE_AI_API_KEY", "")
#         )
#         self.models = config["models"]
#         self.call_log: list = []

#         self.client = AzureOpenAI(
#             azure_endpoint=self.endpoint,
#             api_key=self.api_key,
#             api_version=self.api_version,
#         )

#     def call(self, model_tier: str, prompt: str,
#              system_prompt: Optional[str] = None,
#              max_retries: int = 3, retry_delay: float = 2.0) -> dict:
#         """
#         Call LLM and return parsed JSON.

#         Args:
#             model_tier: 'lightweight', 'reasoning', or 'open_source'
#             prompt: User prompt
#             system_prompt: Optional system message
#             max_retries: Retry count
#             retry_delay: Base delay (exponential backoff)

#         Returns:
#             Parsed JSON dict from LLM

#         Raises:
#             RuntimeError: If all retries fail
#         """
#         model_config = self.models[model_tier]
#         deployment = model_config["deployment"]
#         temperature = model_config["temperature"]
#         max_tokens = model_config["max_tokens"]

#         messages = []
#         is_o1 = "o1" in deployment.lower()

#         if system_prompt:
#             if is_o1:
#                 # o1 doesn't support system role; prepend as developer message
#                 messages.append({"role": "developer", "content": system_prompt})
#             else:
#                 messages.append({"role": "system", "content": system_prompt})
#         messages.append({"role": "user", "content": prompt})

#         prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
#         last_error = None

#         for attempt in range(max_retries):
#             start = time.time()
#             try:
#                 # o1 doesn't support temperature or max_tokens params
#                 call_params = {
#                     "model": deployment,
#                     "messages": messages,
#                 }
#                 if is_o1:
#                     call_params["max_completion_tokens"] = max_tokens
#                 else:
#                     call_params["max_tokens"] = max_tokens
#                     call_params["temperature"] = temperature

#                 response = self.client.chat.completions.create(**call_params)
#                 latency = (time.time() - start) * 1000
#                 raw = response.choices[0].message.content
#                 usage = response.usage
#                 parsed = self._parse_json(raw)

#                 self.call_log.append(APICallLog(
#                     timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
#                     model=deployment, prompt_hash=prompt_hash,
#                     temperature=temperature, response_raw=raw,
#                     response_parsed=parsed, latency_ms=round(latency, 1),
#                     prompt_tokens=usage.prompt_tokens,
#                     completion_tokens=usage.completion_tokens,
#                     total_tokens=usage.total_tokens,
#                     success=True,
#                 ))
#                 logger.debug(
#                     f"OK: {deployment} {latency:.0f}ms {usage.total_tokens}tok"
#                 )
#                 return parsed

#             except Exception as e:
#                 latency = (time.time() - start) * 1000
#                 last_error = str(e)
#                 self.call_log.append(APICallLog(
#                     timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
#                     model=deployment, prompt_hash=prompt_hash,
#                     temperature=temperature, response_raw="",
#                     response_parsed=None, latency_ms=round(latency, 1),
#                     prompt_tokens=0, completion_tokens=0, total_tokens=0,
#                     success=False, error=last_error,
#                 ))
#                 logger.warning(
#                     f"FAIL ({attempt+1}/{max_retries}): {last_error}"
#                 )
#                 if attempt < max_retries - 1:
#                     time.sleep(retry_delay * (2 ** attempt))

#         raise RuntimeError(
#             f"All {max_retries} retries failed for {deployment}: {last_error}"
#         )

#     def _parse_json(self, raw: str) -> dict:
#         """Parse JSON from LLM response, handling fences, preamble, and comma numbers."""
#         text = raw.strip()

#         # Strip commas from numbers in JSON (e.g. 28,155 -> 28155)
#         # Matches digits,digits patterns that aren't inside quotes
#         def strip_number_commas(s):
#             # Remove commas between digits: 28,155 -> 28155
#             return re.sub(r'(?<=\d),(?=\d)', '', s)

#         # Direct parse
#         try:
#             return json.loads(strip_number_commas(text))
#         except json.JSONDecodeError:
#             pass

#         # Strip markdown fences
#         for pat in [r"```json\s*\n?(.*?)\n?\s*```", r"```\s*\n?(.*?)\n?\s*```"]:
#             m = re.search(pat, text, re.DOTALL)
#             if m:
#                 try:
#                     return json.loads(strip_number_commas(m.group(1).strip()))
#                 except json.JSONDecodeError:
#                     continue

#         # Find JSON object in text
#         start = text.find("{")
#         end = text.rfind("}")
#         if start != -1 and end != -1:
#             try:
#                 return json.loads(strip_number_commas(text[start:end + 1]))
#             except json.JSONDecodeError:
#                 pass

#         raise ValueError(f"Cannot parse JSON:\n{raw[:500]}")

#     def get_usage_summary(self) -> dict:
#         ok = [l for l in self.call_log if l.success]
#         fail = [l for l in self.call_log if not l.success]
#         tokens = sum(l.total_tokens for l in ok)
#         latency = sum(l.latency_ms for l in ok)

#         by_model = {}
#         for l in ok:
#             if l.model not in by_model:
#                 by_model[l.model] = {"calls": 0, "tokens": 0, "latency_ms": 0}
#             by_model[l.model]["calls"] += 1
#             by_model[l.model]["tokens"] += l.total_tokens
#             by_model[l.model]["latency_ms"] += l.latency_ms
#         for m in by_model:
#             by_model[m]["avg_latency_ms"] = round(
#                 by_model[m]["latency_ms"] / max(by_model[m]["calls"], 1), 1
#             )

#         return {
#             "total_calls": len(self.call_log),
#             "successful": len(ok),
#             "failed": len(fail),
#             "total_tokens": tokens,
#             "avg_latency_ms": round(latency / max(len(ok), 1), 1),
#             "by_model": by_model,
#         }

#     def export_logs(self, filepath: str):
#         logs = [{
#             "timestamp": l.timestamp, "model": l.model,
#             "prompt_hash": l.prompt_hash, "temperature": l.temperature,
#             "response_raw": l.response_raw,
#             "response_parsed": l.response_parsed,
#             "latency_ms": l.latency_ms,
#             "prompt_tokens": l.prompt_tokens,
#             "completion_tokens": l.completion_tokens,
#             "total_tokens": l.total_tokens,
#             "success": l.success, "error": l.error,
#         } for l in self.call_log]

#         with open(filepath, "w") as f:
#             json.dump(logs, f, indent=2)
#         logger.info(f"Exported {len(logs)} logs to {filepath}")