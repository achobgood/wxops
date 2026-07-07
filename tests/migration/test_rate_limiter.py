"""Tests for per-endpoint rate limiter.

Acceptance criteria:
- Concurrent request limit enforced
- 429 triggers backoff
- Backoff increases exponentially
"""

import asyncio
import time

import pytest

from wxcli.migration.rate_limiter import RateLimiter, RateLimitConfig


@pytest.fixture
def limiter():
    return RateLimiter(RateLimitConfig(
        max_concurrent=5,
        base_delay=0.1,  # fast for tests
        max_delay=10.0,
        backoff_factor=2.0,
        max_retries=5,
    ))


class TestBackoff:
    def test_exponential_increase(self, limiter):
        d1 = limiter.record_429("/v1/people")
        d2 = limiter.record_429("/v1/people")
        d3 = limiter.record_429("/v1/people")
        # base_delay * factor^n: 0.1*2^1=0.2, 0.1*2^2=0.4, 0.1*2^3=0.8
        assert abs(d1 - 0.2) < 0.01
        assert abs(d2 - 0.4) < 0.01
        assert abs(d3 - 0.8) < 0.01

    def test_max_delay_cap(self):
        limiter = RateLimiter(RateLimitConfig(
            base_delay=1.0, max_delay=5.0, backoff_factor=10.0, max_retries=10,
        ))
        for _ in range(8):
            delay = limiter.record_429("/v1/people")
        assert delay <= 5.0

    def test_success_resets_backoff(self, limiter):
        limiter.record_429("/v1/people")
        limiter.record_429("/v1/people")
        limiter.record_success("/v1/people")
        assert limiter.wait_time("/v1/people") == 0.0

    def test_should_retry_under_limit(self, limiter):
        for _ in range(4):
            limiter.record_429("/v1/people")
        assert limiter.should_retry("/v1/people") is True

    def test_should_retry_at_limit(self, limiter):
        for _ in range(5):
            limiter.record_429("/v1/people")
        assert limiter.should_retry("/v1/people") is False


class TestPerEndpoint:
    def test_independent_endpoints(self, limiter):
        limiter.record_429("/v1/people")
        limiter.record_429("/v1/people")
        # Different endpoint should have zero backoff
        assert limiter.wait_time("/v1/locations") == 0.0


class TestSyncAcquire:
    def test_basic_acquire(self, limiter):
        with limiter.acquire("/v1/people"):
            pass  # Should not raise

    def test_concurrent_limit(self, limiter):
        """Verify _sync_count tracks active slots."""
        with limiter.acquire("/v1/people"):
            assert limiter._sync_count == 1
            with limiter.acquire("/v1/locations"):
                assert limiter._sync_count == 2
        assert limiter._sync_count == 0


class TestAsyncAcquire:
    def test_basic_async_acquire(self, limiter):
        """Verify async acquire runs without error."""
        async def _run():
            async with limiter.acquire_async("/v1/people"):
                pass
        asyncio.run(_run())

    def test_concurrent_limit_enforced(self):
        """Max 3 concurrent requests."""
        limiter = RateLimiter(RateLimitConfig(max_concurrent=3, base_delay=0.01))
        max_active = 0

        async def _run():
            nonlocal max_active
            active = 0

            async def worker(endpoint: str):
                nonlocal active, max_active
                async with limiter.acquire_async(endpoint):
                    active += 1
                    if active > max_active:
                        max_active = active
                    await asyncio.sleep(0.05)
                    active -= 1

            tasks = [worker(f"/v1/endpoint{i}") for i in range(10)]
            await asyncio.gather(*tasks)

        asyncio.run(_run())
        assert max_active <= 3


class TestWaitTime:
    def test_wait_time_positive_after_429(self, limiter):
        limiter.record_429("/v1/people")
        assert limiter.wait_time("/v1/people") > 0

    def test_wait_time_zero_for_new_endpoint(self, limiter):
        assert limiter.wait_time("/v1/new") == 0.0
