"""Fixed-window rate limiting with an in-memory or Redis backend.

* `RateLimitMiddleware` applies the global per-client limit (`RATE_LIMIT_DEFAULT`).
* `RateLimit` is a route dependency for stricter limits (login, registration, uploads...).
"""

import json
import re
import time
from dataclasses import dataclass
from typing import Protocol

from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import Settings
from app.core.exceptions import RateLimitedError
from app.core.logging import get_logger
from app.core.middleware import client_ip_from_scope

logger = get_logger(__name__)

_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
_RATE_PATTERN = re.compile(r"^\s*(\d+)\s*/\s*(second|minute|hour|day)s?\s*$")


@dataclass(frozen=True, slots=True)
class Rate:
    limit: int
    period_seconds: int


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int


def parse_rate(value: str) -> Rate:
    """Parse '10/minute', '300/minutes', '5/second', '1000/day'."""
    match = _RATE_PATTERN.match(value.lower())
    if not match or int(match.group(1)) < 1:
        raise ValueError(f"Invalid rate limit '{value}', expected e.g. '10/minute'")
    return Rate(limit=int(match.group(1)), period_seconds=_PERIODS[match.group(2)])


def _window(now: float, rate: Rate) -> tuple[int, int]:
    window = int(now // rate.period_seconds)
    retry_after = max(1, int((window + 1) * rate.period_seconds - now))
    return window, retry_after


class RateLimiter(Protocol):
    async def hit(self, key: str, rate: Rate) -> RateLimitResult: ...

    async def close(self) -> None: ...


class MemoryRateLimiter:
    """Per-process counters. Fine for development and single-instance deployments."""

    _MAX_KEYS = 50_000

    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, int]] = {}

    async def hit(self, key: str, rate: Rate) -> RateLimitResult:
        window, retry_after = _window(time.time(), rate)
        bucket = f"{key}:{rate.period_seconds}"
        current_window, count = self._counters.get(bucket, (window, 0))
        count = count + 1 if current_window == window else 1
        self._counters[bucket] = (window, count)
        if len(self._counters) > self._MAX_KEYS:
            self._prune(window)
        return RateLimitResult(count <= rate.limit, max(0, rate.limit - count), retry_after)

    def _prune(self, window: int) -> None:
        self._counters = {k: v for k, v in self._counters.items() if v[0] >= window}

    async def close(self) -> None:
        self._counters.clear()


class RedisRateLimiter:
    """Counters shared by every API replica. Fails open if Redis is unavailable."""

    def __init__(self, url: str) -> None:
        from redis.asyncio import Redis

        self._redis = Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)

    async def hit(self, key: str, rate: Rate) -> RateLimitResult:
        window, retry_after = _window(time.time(), rate)
        redis_key = f"ratelimit:{key}:{rate.period_seconds}:{window}"
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(redis_key)
                pipe.expire(redis_key, rate.period_seconds + 1)
                count, _ = await pipe.execute()
        except Exception as exc:  # noqa: BLE001 - availability over strictness
            logger.warning("rate_limiter_unavailable", error=type(exc).__name__)
            return RateLimitResult(True, rate.limit, 0)
        return RateLimitResult(count <= rate.limit, max(0, rate.limit - count), retry_after)

    async def close(self) -> None:
        await self._redis.aclose()


def build_rate_limiter(settings: Settings) -> RateLimiter:
    if settings.redis_url:
        return RedisRateLimiter(settings.redis_url)
    return MemoryRateLimiter()


class RateLimitMiddleware:
    """Global per-client limit, applied before routing."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limiter: RateLimiter,
        rate: Rate,
        exempt_paths: tuple[str, ...] = (),
    ) -> None:
        self.app = app
        self.limiter = limiter
        self.rate = rate
        self.exempt_paths = exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in self.exempt_paths:
            await self.app(scope, receive, send)
            return
        result = await self.limiter.hit(f"global:{client_ip_from_scope(scope)}", self.rate)
        if result.allowed:
            await self.app(scope, receive, send)
            return

        body = json.dumps(
            {
                "success": False,
                "error": {
                    "code": RateLimitedError.code,
                    "message": RateLimitedError.default_message,
                    "request_id": scope.get("state", {}).get("request_id"),
                },
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"retry-after", str(result.retry_after).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class RateLimit:
    """Route dependency enforcing a stricter limit, e.g. `Depends(RateLimit("login", "auth"))`.

    `setting` names the Settings attribute holding the rate: "auth" -> `rate_limit_auth`.
    """

    def __init__(self, scope_name: str, setting: str) -> None:
        self.scope_name = scope_name
        self.setting = f"rate_limit_{setting}"

    async def __call__(self, request: Request) -> None:
        settings: Settings = request.app.state.settings
        if not settings.rate_limit_enabled:
            return
        limiter: RateLimiter = request.app.state.rate_limiter
        rate = parse_rate(getattr(settings, self.setting))
        result = await limiter.hit(f"{self.scope_name}:{client_ip_from_scope(request.scope)}", rate)
        if not result.allowed:
            logger.warning("rate_limited", scope=self.scope_name)
            raise RateLimitedError(result.retry_after)
