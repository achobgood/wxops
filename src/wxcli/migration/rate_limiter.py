"""Per-endpoint rate limiter with exponential backoff.

Enforces max concurrent requests and handles 429 (Too Many Requests) responses
with exponential backoff. Configurable via migration settings.

(from cucm-wxc-migration.md lines 443-444,
 05-dependency-graph.md rate limit budget section)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    """Configuration for the rate limiter."""
    max_concurrent: int = 5
    base_delay: float = 1.0         # seconds
    max_delay: float = 60.0         # seconds
    backoff_factor: float = 2.0
    max_retries: int = 5


@dataclass
class _EndpointState:
    """Tracks backoff state for a single endpoint."""
    consecutive_429s: int = 0
    next_allowed_at: float = 0.0


class RateLimiter:
    """Per-endpoint rate limiter with exponential backoff on 429 responses.

    Usage (sync):
        limiter = RateLimiter()
        with limiter.acquire("/v1/people"):
            response = make_api_call()
        if response.status_code == 429:
            limiter.record_429("/v1/people")

    Usage (async):
        limiter = RateLimiter()
        async with limiter.acquire_async("/v1/people"):
            response = await make_api_call()
        if response.status_code == 429:
            limiter.record_429("/v1/people")
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._sync_count: int = 0
        self._sync_count_lock = None  # lazy init for threading
        self._endpoints: dict[str, _EndpointState] = {}

    def _get_endpoint(self, endpoint: str) -> _EndpointState:
        if endpoint not in self._endpoints:
            self._endpoints[endpoint] = _EndpointState()
        return self._endpoints[endpoint]

    def record_429(self, endpoint: str) -> float:
        """Record a 429 response. Returns the delay (seconds) before next retry."""
        state = self._get_endpoint(endpoint)
        state.consecutive_429s += 1
        delay = min(
            self.config.base_delay * (self.config.backoff_factor ** state.consecutive_429s),
            self.config.max_delay,
        )
        state.next_allowed_at = time.monotonic() + delay
        return delay

    def record_success(self, endpoint: str) -> None:
        """Record a successful response, resetting backoff."""
        state = self._get_endpoint(endpoint)
        state.consecutive_429s = 0
        state.next_allowed_at = 0.0

    def should_retry(self, endpoint: str) -> bool:
        """Check if retries are still allowed for this endpoint."""
        state = self._get_endpoint(endpoint)
        return state.consecutive_429s < self.config.max_retries

    def wait_time(self, endpoint: str) -> float:
        """Seconds to wait before the next request to this endpoint."""
        state = self._get_endpoint(endpoint)
        remaining = state.next_allowed_at - time.monotonic()
        return max(0.0, remaining)

    # -- Sync context manager --

    class _SyncSlot:
        """Sync concurrency slot.

        Note: The sync acquire path uses a simple counter and is NOT
        thread-safe.  For threaded usage, use ``acquire_async`` with an
        asyncio event loop.  The executor uses the async path for
        concurrent API requests.
        """

        def __init__(self, limiter: RateLimiter, endpoint: str) -> None:
            self._limiter = limiter
            self._endpoint = endpoint

        def __enter__(self) -> _SyncSlot:
            # Wait for per-endpoint backoff
            wait = self._limiter.wait_time(self._endpoint)
            if wait > 0:
                time.sleep(wait)
            # Enforce concurrency (simple counter — not thread-safe)
            while self._limiter._sync_count >= self._limiter.config.max_concurrent:
                time.sleep(0.05)
            self._limiter._sync_count += 1
            return self

        def __exit__(self, *args: object) -> None:
            self._limiter._sync_count -= 1

    def acquire(self, endpoint: str) -> _SyncSlot:
        """Sync context manager that enforces rate limits."""
        return self._SyncSlot(self, endpoint)

    # -- Async context manager --

    class _AsyncSlot:
        def __init__(self, limiter: RateLimiter, endpoint: str) -> None:
            self._limiter = limiter
            self._endpoint = endpoint

        async def __aenter__(self) -> _AsyncSlot:
            wait = self._limiter.wait_time(self._endpoint)
            if wait > 0:
                await asyncio.sleep(wait)
            await self._limiter._semaphore.acquire()
            return self

        async def __aexit__(self, *args: object) -> None:
            self._limiter._semaphore.release()

    def acquire_async(self, endpoint: str) -> _AsyncSlot:
        """Async context manager that enforces rate limits."""
        return self._AsyncSlot(self, endpoint)
