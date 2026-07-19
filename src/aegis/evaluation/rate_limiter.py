"""
RateLimiter

Reusable request-rate throttling for LLM providers with per-minute,
per-hour, and per-day request budgets (e.g. Groq's free-tier limits).

Token-based limiting (``tokens_per_minute``, ``tokens_per_day``) is
deliberately interface-only for v1: the config fields and the
``token_usage``/``record_request(estimated_tokens=...)`` shape exist so a
future revision can wire in real token-budget enforcement without
changing callers, but no sliding-window token budget is enforced yet --
only request counts are.

Only used inside ``aegis.evaluation`` (via ``RateLimitedReasoningProvider``)
to protect evaluation runs that issue many real Groq calls back-to-back.
Never wired into the production request path
(``aegis.infrastructure.crewai.reasoning_provider``, ``aegis.api.bootstrap``)
-- a single interactive clinical submission does not need the throttling a
batch evaluation run does.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import TYPE_CHECKING, Any, Callable

from pydantic import Field

from aegis.models.base import DomainModel
from aegis.services.clinical_reasoning_service import ReasoningProvider

if TYPE_CHECKING:
    from aegis.models.reasoning_context import ReasoningContext

logger = logging.getLogger("aegis.evaluation.rate_limiter")

_SECONDS_PER_MINUTE = 60.0
_SECONDS_PER_HOUR = 60.0 * 60.0
_SECONDS_PER_DAY = 24.0 * 60.0 * 60.0


class RateLimitConfig(DomainModel):
    """
    Declarative request/token budgets for one reasoning provider.

    ``requests_per_minute``/``_hour``/``_day`` are enforced by
    ``RateLimiter``. ``tokens_per_minute``/``_day`` are accepted and
    validated here so evaluation configs can declare them today, but are
    not yet enforced -- see this module's docstring.
    """

    requests_per_minute: int | None = Field(default=None, gt=0)
    requests_per_hour: int | None = Field(default=None, gt=0)
    requests_per_day: int | None = Field(default=None, gt=0)
    tokens_per_minute: int | None = Field(default=None, gt=0)
    tokens_per_day: int | None = Field(default=None, gt=0)
    max_retries: int = Field(default=5, ge=0)
    initial_backoff_seconds: float = Field(default=1.0, gt=0.0)
    backoff_multiplier: float = Field(default=2.0, gt=1.0)


class RateLimiter:
    """
    Sliding-window request-rate limiter.

    ``clock`` is injectable so tests can advance time deterministically
    instead of sleeping in real time.
    """

    def __init__(
        self,
        config: RateLimitConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._clock = clock
        self._minute_requests: deque[float] = deque()
        self._hour_requests: deque[float] = deque()
        self._day_requests: deque[float] = deque()
        self._total_tokens_seen = 0

    @property
    def config(self) -> RateLimitConfig:
        return self._config

    @property
    def token_usage(self) -> int:
        """
        Cumulative estimated tokens observed via ``record_request``.

        Observability only today -- see module docstring; not used to
        throttle requests.
        """
        return self._total_tokens_seen

    def seconds_until_available(self) -> float:
        """
        How long the caller must wait before the next request is allowed
        under the configured per-minute/hour/day request budgets.

        Returns 0.0 if a request may proceed immediately. Does not mutate
        state -- callers must call ``record_request`` once the request
        actually proceeds.
        """
        now = self._clock()
        self._evict_expired(now)

        return max(
            self._wait_for_window(
                self._minute_requests, self._config.requests_per_minute, _SECONDS_PER_MINUTE, now
            ),
            self._wait_for_window(
                self._hour_requests, self._config.requests_per_hour, _SECONDS_PER_HOUR, now
            ),
            self._wait_for_window(
                self._day_requests, self._config.requests_per_day, _SECONDS_PER_DAY, now
            ),
        )

    def record_request(self, estimated_tokens: int = 0) -> None:
        """Record that one request just proceeded, for future budget checks."""
        now = self._clock()
        self._minute_requests.append(now)
        self._hour_requests.append(now)
        self._day_requests.append(now)
        self._total_tokens_seen += estimated_tokens

    def _evict_expired(self, now: float) -> None:
        self._evict_window(self._minute_requests, _SECONDS_PER_MINUTE, now)
        self._evict_window(self._hour_requests, _SECONDS_PER_HOUR, now)
        self._evict_window(self._day_requests, _SECONDS_PER_DAY, now)

    @staticmethod
    def _evict_window(window: deque[float], window_seconds: float, now: float) -> None:
        while window and now - window[0] >= window_seconds:
            window.popleft()

    @staticmethod
    def _wait_for_window(
        window: deque[float], limit: int | None, window_seconds: float, now: float
    ) -> float:
        if limit is None or len(window) < limit:
            return 0.0
        oldest = window[0]
        return max(0.0, window_seconds - (now - oldest))


class RateLimitedReasoningProvider(ReasoningProvider):
    """
    ``ReasoningProvider`` decorator that throttles calls to a delegate
    provider under a ``RateLimiter``'s request budgets, with exponential
    backoff and retry on transient failures.

    Wraps any concrete ``ReasoningProvider`` -- in practice
    ``CrewAIReasoningProvider`` -- without modifying it. Applied only by
    ``aegis.evaluation.runner``, never by the production composition root
    (``aegis.api.bootstrap``).
    """

    def __init__(self, delegate: ReasoningProvider, rate_limiter: RateLimiter) -> None:
        self._delegate = delegate
        self._rate_limiter = rate_limiter

    async def reason(self, context: ReasoningContext, prompt: str) -> dict[str, Any]:
        config = self._rate_limiter.config
        backoff = config.initial_backoff_seconds
        # Rough token estimate (chars/4) for observability only -- see
        # this module's docstring on token-budget enforcement scope.
        estimated_tokens = len(prompt) // 4
        last_error: Exception | None = None

        for attempt in range(config.max_retries + 1):
            wait_seconds = self._rate_limiter.seconds_until_available()
            if wait_seconds > 0:
                logger.info("Rate limit reached; waiting %.1fs before next request.", wait_seconds)
                await asyncio.sleep(wait_seconds)

            try:
                result = await self._delegate.reason(context, prompt)
                self._rate_limiter.record_request(estimated_tokens=estimated_tokens)
                return result
            except Exception as error:
                last_error = error
                self._rate_limiter.record_request(estimated_tokens=estimated_tokens)
                if attempt >= config.max_retries:
                    break
                logger.warning(
                    "Reasoning provider call failed (attempt %d/%d): %s. Retrying in %.1fs.",
                    attempt + 1,
                    config.max_retries + 1,
                    error,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff *= config.backoff_multiplier

        assert last_error is not None
        raise last_error
