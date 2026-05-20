"""
Rate limiter Redis (mode décorateur) — Flashback Restore.

Remplace le stub no-op par un vrai rate limiter Redis.
Utilisé par auth.py avec @limiter.limit("5/minute").
"""
import asyncio
import logging
from functools import wraps

import redis.asyncio as redis

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


async def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_keepalive=True,
            health_check_interval=30,
        )
    return _redis


def _parse_limit(value: str) -> tuple[int, int]:
    """Parse '5/minute' → (5, 60)."""
    parts = value.split("/")
    count = int(parts[0])
    unit = parts[1].lower()
    multipliers = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    window = multipliers.get(unit, 60)
    return count, window


class Limiter:
    """Rate limiter Redis avec interface décorateur."""

    def limit(self, value: str):
        """Décorateur de rate limiting Redis."""
        max_req, window = _parse_limit(value)

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extraire l'IP de la requête (request est toujours le 1er arg)
                request = None
                for arg in args:
                    if hasattr(arg, "client") and hasattr(arg, "url"):
                        request = arg
                        break
                if request is None:
                    return await func(*args, **kwargs)

                ip = request.client.host if request.client else "unknown"
                forwarded = request.headers.get("X-Forwarded-For", "")
                if forwarded:
                    ip = forwarded.split(",")[0].strip()

                key = f"rate:{ip}:{request.url.path}"
                try:
                    r = await _get_redis()
                    current = await r.incr(key)
                    if current == 1:
                        await r.expire(key, window)
                    if current > max_req:
                        from fastapi import HTTPException
                        raise HTTPException(
                            status_code=429,
                            detail="Trop de requêtes. Veuillez réessayer plus tard.",
                        )
                except Exception as e:
                    if "429" in str(e) or "HTTPException" in str(type(e).__name__):
                        raise
                    logger.warning("Limiter Redis down — requête autorisée: %s", e)

                return await func(*args, **kwargs)

            return wrapper

        return decorator


limiter = Limiter()
