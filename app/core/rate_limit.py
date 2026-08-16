"""Dependency-based rate limiting.

Implemented as FastAPI dependencies (not decorators) so it never interferes with
endpoint signature/dependency injection. Uses an in-memory sliding window keyed
by client IP + limiter name — adequate for a single instance / first version.

For multiple instances behind a load balancer, swap the in-memory ``_HITS``
store for a shared Redis backend; the ``RateLimiter`` dependency interface stays
the same, so no endpoint code changes are required.

NOTE: this module intentionally does NOT use ``from __future__ import
annotations``. ``RateLimiter`` is used as a callable-instance FastAPI dependency,
and instances have no ``__globals__`` for FastAPI to resolve string annotations
against — so ``Request`` must be a real object in ``__call__``'s annotations.
"""

import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import AppError

# name+ip -> timestamps (monotonic seconds) of recent hits.
_HITS: dict[str, deque[float]] = defaultdict(deque)


class TooManyRequestsError(AppError):
    status_code = 429
    code = "TOO_MANY_REQUESTS"
    message = "Demasiadas solicitudes. Intenta de nuevo más tarde."


class RateLimiter:
    """A configurable per-IP sliding-window limiter usable as a dependency."""

    def __init__(self, *, limit: int, window_seconds: int, name: str) -> None:
        self.limit = limit
        self.window = window_seconds
        self.name = name

    async def __call__(self, request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        client_ip = request.client.host if request.client else "anonymous"
        key = f"{self.name}:{client_ip}"
        now = time.monotonic()

        hits = _HITS[key]
        cutoff = now - self.window
        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= self.limit:
            raise TooManyRequestsError()
        hits.append(now)


def reset_rate_limits() -> None:
    """Clear all counters (used by tests)."""
    _HITS.clear()


# Named limiters for sensitive endpoints.
login_rate_limit = RateLimiter(limit=10, window_seconds=60, name="login")
register_rate_limit = RateLimiter(limit=5, window_seconds=60, name="register")
forgot_password_rate_limit = RateLimiter(limit=5, window_seconds=60, name="forgot_password")
payment_rate_limit = RateLimiter(limit=20, window_seconds=60, name="payment")
webhook_rate_limit = RateLimiter(limit=120, window_seconds=60, name="webhook")
