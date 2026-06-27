"""
Lightweight in-memory rate limiter (sliding window, per client IP + path).

Used as a FastAPI dependency to throttle abuse-prone endpoints such as login
and registration. State is per-process; for multi-instance deployments back it
with Redis (the REDIS_URL is already configured) — noted in PRODUCTION_READINESS.
"""
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

# key -> timestamps (monotonic seconds) of recent hits
_hits: Dict[str, Deque[float]] = defaultdict(deque)


def reset_rate_limits() -> None:
    """Clear all rate-limit state (used between tests)."""
    _hits.clear()


class RateLimiter:
    """A dependency that allows `max_requests` per `window_seconds` per client IP."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        now = time.monotonic()

        hits = _hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - hits[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)


# Endpoint limiters. Conservative defaults to blunt brute-force / credential
# stuffing without hindering legitimate use.
login_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
register_rate_limiter = RateLimiter(max_requests=5, window_seconds=300)
