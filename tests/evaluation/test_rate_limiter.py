import pytest

from aegis.evaluation.rate_limiter import (
    RateLimitConfig,
    RateLimitedReasoningProvider,
    RateLimiter,
)


class FakeClock:
    """Injectable clock for deterministic sliding-window tests -- no real sleeping."""

    def __init__(self, start: float = 0.0) -> None:
        self.time = start

    def __call__(self) -> float:
        return self.time

    def advance(self, seconds: float) -> None:
        self.time += seconds


class TestRateLimiterRequestWindows:
    def test_allows_requests_up_to_the_configured_limit_without_waiting(self):
        clock = FakeClock()
        limiter = RateLimiter(RateLimitConfig(requests_per_minute=2), clock=clock)

        assert limiter.seconds_until_available() == 0.0
        limiter.record_request()
        assert limiter.seconds_until_available() == 0.0
        limiter.record_request()

        assert limiter.seconds_until_available() > 0.0

    def test_window_resets_once_the_oldest_request_expires(self):
        clock = FakeClock()
        limiter = RateLimiter(RateLimitConfig(requests_per_minute=1), clock=clock)

        limiter.record_request()
        assert limiter.seconds_until_available() > 0.0

        clock.advance(60.0)
        assert limiter.seconds_until_available() == 0.0

    def test_hour_and_day_bounds_are_independent_of_the_minute_bound(self):
        clock = FakeClock()
        limiter = RateLimiter(
            RateLimitConfig(requests_per_minute=100, requests_per_hour=1), clock=clock
        )

        limiter.record_request()

        # Minute bound has room, but the hour bound is now exhausted.
        assert limiter.seconds_until_available() > 0.0

    def test_unlimited_when_no_bound_configured(self):
        clock = FakeClock()
        limiter = RateLimiter(RateLimitConfig(), clock=clock)

        for _ in range(1000):
            limiter.record_request()

        assert limiter.seconds_until_available() == 0.0

    def test_token_usage_is_tracked_but_not_enforced(self):
        clock = FakeClock()
        limiter = RateLimiter(RateLimitConfig(tokens_per_minute=1), clock=clock)

        limiter.record_request(estimated_tokens=1_000_000)

        assert limiter.token_usage == 1_000_000
        # Interface only today -- see rate_limiter.py's module docstring.
        assert limiter.seconds_until_available() == 0.0


class _FailNTimesThenSucceed:
    def __init__(self, fail_count: int) -> None:
        self.fail_count = fail_count
        self.calls = 0

    async def reason(self, context, prompt):
        self.calls += 1
        if self.calls <= self.fail_count:
            raise RuntimeError("transient failure")
        return {"ok": True}


class _AlwaysFails:
    def __init__(self) -> None:
        self.calls = 0

    async def reason(self, context, prompt):
        self.calls += 1
        raise RuntimeError("permanent failure")


class TestRateLimitedReasoningProvider:
    async def test_retries_and_succeeds_after_transient_failures(self):
        config = RateLimitConfig(
            max_retries=3, initial_backoff_seconds=0.001, backoff_multiplier=1.01
        )
        delegate = _FailNTimesThenSucceed(fail_count=2)
        provider = RateLimitedReasoningProvider(delegate, RateLimiter(config))

        result = await provider.reason(context=None, prompt="hello")

        assert result == {"ok": True}
        assert delegate.calls == 3

    async def test_gives_up_after_max_retries_and_raises_the_last_error(self):
        config = RateLimitConfig(
            max_retries=2, initial_backoff_seconds=0.001, backoff_multiplier=1.01
        )
        delegate = _AlwaysFails()
        provider = RateLimitedReasoningProvider(delegate, RateLimiter(config))

        with pytest.raises(RuntimeError, match="permanent failure"):
            await provider.reason(context=None, prompt="hello")

        assert delegate.calls == config.max_retries + 1
