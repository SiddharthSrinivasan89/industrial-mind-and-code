"""
Resilience utilities shared by all backends.

Provides call_with_backoff() — a single place for exponential backoff with
jitter across transient API errors (500, 429, 503, connection, timeout).

Separation of concerns
----------------------
This module handles *server-side* failures only:
  - HTTP 5xx (Azure service errors)
  - HTTP 429 (rate limit — back off and retry)
  - Network failures (connection reset, DNS, timeout)

JSON parse failures are *model-side* and are handled separately in each
backend's get_order_decision() attempt loop. The two layers are independent:
a successful API call that returns unparseable JSON triggers the parse-retry
loop; a failed API call (network/server error) triggers this backoff layer.

Backoff schedule (base=1s, factor=2, jitter=uniform[0,1], cap=60s):
  Attempt 1 → wait ~1s
  Attempt 2 → wait ~2s
  Attempt 3 → wait ~4s
  Attempt 4 → wait ~8s
  Attempt 5 → wait ~16s
  Attempt 6 → wait ~32s
  Attempts 7–10 → wait ~60s (capped)

With 10 retries the total worst-case wait before giving up is ~8 minutes.
This is intentional: a transient Azure 500 burst typically clears within
60–120s. The retry policy should survive it without hammering the endpoint.
"""

import logging
import random
import time

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

# Errors that are transient and safe to retry.
_RETRYABLE = (InternalServerError, RateLimitError, APIConnectionError, APITimeoutError)

_BASE_WAIT  = 1.0   # seconds
_FACTOR     = 2.0
_MAX_WAIT   = 60.0  # seconds — cap so the code does not wait >1 min between retries


def call_with_backoff(fn, *args, max_retries: int = 10, context: str = "", **kwargs):
    """
    Call fn(*args, **kwargs) with exponential backoff on transient errors.

    Parameters
    ----------
    fn          : Callable that makes the API call. Must be idempotent.
    *args       : Positional arguments forwarded to fn.
    max_retries : Maximum number of retry attempts after the first failure.
                  Total attempts = max_retries + 1.
    context     : Optional string logged on each retry for traceability
                  (e.g. "run=abc period=3 tier=OEM").
    **kwargs    : Keyword arguments forwarded to fn.

    Returns
    -------
    Whatever fn returns on success.

    Raises
    ------
    The last exception if all attempts are exhausted.
    Non-retryable errors (AuthenticationError, BadRequestError, etc.)
    are re-raised immediately without retrying.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error(
                    "%s — transient error on attempt %d/%d, giving up: %s",
                    context, attempt + 1, max_retries + 1, exc,
                )
                raise

            wait = min(_BASE_WAIT * (_FACTOR ** attempt) + random.uniform(0, 1), _MAX_WAIT)
            logger.warning(
                "%s — transient error on attempt %d/%d (%s: %s), retrying in %.1fs",
                context, attempt + 1, max_retries + 1, type(exc).__name__, exc, wait,
            )
            time.sleep(wait)

    raise last_exc  # unreachable but satisfies type checkers
