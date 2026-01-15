from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Callable

from fastapi import Depends, HTTPException, Request, Security

from app.core.security import OrgContext, get_org_context


@dataclass
class _BucketState:
    tokens: float
    last_refill_ts: float


class TokenBucketRateLimiter:
    """In-memory token bucket limiter.

    Notes:
    - Thread-safe within a single process.
    - For multi-process deployments, use an external shared store (e.g. Redis).
    """

    def __init__(
        self,
        capacity: int,
        refill_rate_per_sec: float,
        *,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_rate_per_sec <= 0:
            raise ValueError("refill_rate_per_sec must be > 0")

        self._capacity = float(capacity)
        self._refill_rate = float(refill_rate_per_sec)
        self._time_fn = time_fn
        self._lock = Lock()
        self._buckets: dict[str, _BucketState] = {}

    def allow(self, key: str, cost: float = 1.0) -> tuple[bool, float | None]:
        now = self._time_fn()
        with self._lock:
            state = self._buckets.get(key)
            if state is None:
                state = _BucketState(tokens=self._capacity, last_refill_ts=now)
                self._buckets[key] = state

            elapsed = max(0.0, now - state.last_refill_ts)
            if elapsed:
                state.tokens = min(self._capacity, state.tokens + elapsed * self._refill_rate)
                state.last_refill_ts = now

            if state.tokens >= cost:
                state.tokens -= cost
                return True, None

            needed = cost - state.tokens
            retry_after = needed / self._refill_rate
            return False, retry_after


def enforce_rate_limit(
    request: Request,
    org: OrgContext = Security(get_org_context),
) -> OrgContext:
    limiter: TokenBucketRateLimiter = request.app.state.limiter

    client_host = request.client.host if request.client else "unknown"
    key = f"org:{org.org_id}:ip:{client_host}"

    allowed, retry_after = limiter.allow(key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"message": "Rate limit exceeded", "retry_after_seconds": retry_after},
        )

    return org
