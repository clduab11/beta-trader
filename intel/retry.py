"""Retry utility with exponential backoff.

Implements the retry patterns from docs/interfaces/errors.md:
- APIError: 3 attempts, 1s/2s/4s base delays
- RateLimitError: 5 attempts, 2s/4s/8s/16s/32s base delays, 32s cap
- Jitter: ±50% randomization to prevent thundering herd
"""

from __future__ import annotations

import asyncio
from random import uniform
from typing import TYPE_CHECKING, TypeVar

import structlog

from intel.errors import APIError, RateLimitError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

log = structlog.get_logger(__name__)
T = TypeVar("T")

# Default retry parameters per exception type
API_ERROR_MAX_ATTEMPTS = 3
API_ERROR_BASE_DELAY = 1.0
API_ERROR_MAX_DELAY = 30.0

RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_BASE_DELAY = 2.0
RATE_LIMIT_MAX_DELAY = 32.0


async def retry_with_backoff[T](
    fn: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (APIError, RateLimitError),
    on_retry: Callable[[int, float, Exception], Awaitable[None]] | None = None,
    *,
    rate_limit_max_attempts: int = RATE_LIMIT_MAX_ATTEMPTS,
    rate_limit_base_delay: float = RATE_LIMIT_BASE_DELAY,
    rate_limit_max_delay: float = RATE_LIMIT_MAX_DELAY,
) -> T:
    """Execute fn with exponential backoff on failure.

    Differentiates retry behaviour by exception type:
    - ``RateLimitError``: *rate_limit_max_attempts* attempts with
      *rate_limit_base_delay* (doubling, capped at *rate_limit_max_delay*).
      Respects ``retry_after_seconds`` when present.
    - Other retryable errors (e.g. ``APIError``): *max_attempts* attempts
      with *base_delay* (doubling, capped at *max_delay*).

    Args:
        fn: Async callable to execute.
        max_attempts: Maximum attempts for non-rate-limit errors.
        base_delay: Initial delay for non-rate-limit errors.
        max_delay: Maximum delay cap for non-rate-limit errors.
        jitter: Add ±50% randomization to delay.
        retryable_exceptions: Exception types that trigger retries.
        on_retry: Optional callback after each failed attempt (attempt, delay, exc).
        rate_limit_max_attempts: Maximum attempts for RateLimitError (default 5).
        rate_limit_base_delay: Initial delay for RateLimitError (default 2s).
        rate_limit_max_delay: Cap for RateLimitError delays (default 32s).

    Returns:
        Result from fn.

    Raises:
        The last exception if all attempts exhausted.
    """
    last_exception: Exception | None = None
    # Track attempts separately for rate-limit vs other errors so we
    # can apply the right budget to each class of error.
    rl_attempt = 0  # attempts consumed by RateLimitError
    other_attempt = 0  # attempts consumed by other retryable errors
    total_attempt = 0  # overall attempt counter (for logging / callbacks)

    while True:
        total_attempt += 1
        try:
            return await fn()
        except retryable_exceptions as exc:
            last_exception = exc

            is_rate_limit = isinstance(exc, RateLimitError)

            if is_rate_limit:
                rl_attempt += 1
                effective_max = rate_limit_max_attempts
                attempt_idx = rl_attempt  # 1-based
            else:
                other_attempt += 1
                effective_max = max_attempts
                attempt_idx = other_attempt

            if attempt_idx >= effective_max:
                log.error(
                    "All retry attempts exhausted",
                    attempt=total_attempt,
                    max_attempts=effective_max,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                raise

            # Calculate delay
            if is_rate_limit:
                delay = min(
                    rate_limit_base_delay * (2 ** (rl_attempt - 1)),
                    rate_limit_max_delay,
                )
                # Respect Retry-After header for rate limits
                if exc.retry_after_seconds:
                    delay = max(delay, exc.retry_after_seconds)
            else:
                delay = min(base_delay * (2 ** (other_attempt - 1)), max_delay)

            if jitter:
                delay = uniform(delay * 0.5, delay * 1.5)

            log.warning(
                "Retrying after failure",
                attempt=total_attempt,
                max_attempts=effective_max,
                delay_seconds=round(delay, 2),
                error_type=type(exc).__name__,
                error=str(exc),
            )

            if on_retry:
                await on_retry(total_attempt, delay, exc)

            await asyncio.sleep(delay)

    # Should never reach here, but satisfy type checker
    assert last_exception is not None
    raise last_exception
