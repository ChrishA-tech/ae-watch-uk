"""API Resilience and Retry Strategies for AE-Watch UK.

Enforces tenacity bounded retries, exponential backoff with random jitter,
explicit timeouts, and HTTP 429 Retry-After header adherence.
Author: CHRISH PEP FELIX A
"""

import random
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)
from tenacity.wait import wait_base

from ae_watch.utils.logger import logger


def parse_retry_after(response: httpx.Response) -> float | None:
    """Parse HTTP 429 Retry-After header as delay seconds."""
    header = response.headers.get("Retry-After")
    if not header:
        return None

    header = header.strip()
    try:
        # Check if integer seconds
        return max(0.0, float(header))
    except ValueError:
        pass

    try:
        # Parse RFC 2822 / RFC 7231 date
        target_date = parsedate_to_datetime(header)
        now = datetime.now(UTC)
        delay = (target_date - now).total_seconds()
        return max(0.0, delay)
    except (ValueError, TypeError, OverflowError):
        return None


def is_transient_http_error(exc: BaseException) -> bool:
    """Determine if an exception represents a recoverable transient failure."""
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        # 429 Too Many Requests, or 502/503/504 Bad Gateway / Unavailable
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


class WaitRetryAfterOrExponential(wait_base):
    """Wait strategy adhering to HTTP 429 Retry-After headers, falling back to exponential jitter."""

    def __init__(self, multiplier: float = 1.5, max_seconds: float = 60.0):
        self.exponential = wait_random_exponential(multiplier=multiplier, max=max_seconds)

    def __call__(self, retry_state: RetryCallState) -> float:
        if retry_state.outcome and retry_state.outcome.failed:
            exc = retry_state.outcome.exception()
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
                retry_after = parse_retry_after(exc.response)
                if retry_after is not None:
                    # Add small random jitter (0.1 to 1.0s)
                    jitter = random.uniform(0.1, 1.0)
                    total_wait = retry_after + jitter
                    logger.warning(
                        "http_429_retry_after_detected",
                        retry_after=retry_after,
                        jitter=jitter,
                        total_wait=total_wait,
                        url=str(exc.request.url),
                        attempt=retry_state.attempt_number,
                    )
                    return total_wait

        return self.exponential(retry_state)


def log_retry_attempt(retry_state: RetryCallState) -> None:
    """Callback to log retry attempts with structured context."""
    attempt = retry_state.attempt_number
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "transient_error_retrying",
        attempt=attempt,
        exception_type=type(exc).__name__ if exc else None,
        exception_message=str(exc) if exc else None,
    )


def create_resilient_retryer(max_attempts: int = 5) -> AsyncRetrying:
    """Instantiate a configured AsyncRetrying runner."""
    return AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=WaitRetryAfterOrExponential(multiplier=1.5, max_seconds=30.0),
        retry=retry_if_exception(is_transient_http_error),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


async def execute_with_resilience(
    func: Callable[..., httpx.Response],
    *args,
    max_attempts: int = 5,
    **kwargs,
) -> httpx.Response:
    """Execute an async HTTP callable with strict tenacity resilience."""
    retryer = create_resilient_retryer(max_attempts=max_attempts)
    async for attempt in retryer:
        with attempt:
            resp = await func(*args, **kwargs)
            resp.raise_for_status()
            return resp
    raise RuntimeError("Unreachable: retry loop terminated without return or raise")
