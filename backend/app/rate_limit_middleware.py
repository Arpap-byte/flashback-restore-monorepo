"""
Rate limiter Redis — Flashback Restore.

Utilise Redis (INCR + EXPIRE) pour un rate limiting distribué
qui survit aux redémarrages et fonctionne avec plusieurs workers.

Remplace l'ancien rate limiter in-memory (threading.Lock + defaultdict).
"""
import logging
import redis.asyncio as redis
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

# Config: (route_path, max_requests, window_seconds)
LIMITS = {
    "/api/auth/register": (5, 60),
    "/api/auth/login": (5, 60),
    "/api/auth/forgot-password": (3, 60),
    "/api/health": (30, 60),       # plus permissif (monitoring)
    "/api/analyze": (10, 60),
    "/api/restore": (10, 60),
    "/api/animate": (10, 60),
    "/api/stripe/create-checkout": (5, 60),
    "/api/stripe/create-pack-checkout": (5, 60),
}

# Connexion Redis lazy-init
_redis: redis.Redis | None = None


async def _get_redis() -> redis.Redis:
    """Connexion Redis lazy avec pool persistant."""
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


def get_client_ip(request: Request) -> str:
    """Extrait l'IP client, en tenant compte du proxy Traefik."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


async def check_rate_limit(request: Request) -> None:
    """Vérifie et applique le rate limiting Redis. Lève HTTPException 429 si dépassé."""
    path = request.url.path

    # Trouver la limite applicable (match exact)
    limit_config = LIMITS.get(path)
    if not limit_config:
        return  # Pas de limite pour cette route

    max_req, window = limit_config
    ip = get_client_ip(request)
    key = f"rate:{ip}:{path}"

    try:
        r = await _get_redis()
        # INCR atomique + EXPIRE sur la première requête
        current = await r.incr(key)
        if current == 1:
            await r.expire(key, window)

        if current > max_req:
            raise HTTPException(
                status_code=429,
                detail="Trop de requêtes. Veuillez réessayer plus tard.",
            )
    except HTTPException:
        raise
    except Exception as e:
        # Fallback : si Redis est down, logger l'erreur et laisser passer
        logger.warning("Rate limiter Redis indisponible — requête autorisée: %s", e)
