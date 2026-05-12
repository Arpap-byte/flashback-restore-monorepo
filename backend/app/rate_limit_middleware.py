"""
Rate limiter custom en mémoire avec TTL.
Simple, fiable, sans dépendance externe.
"""
import time
import threading
from collections import defaultdict
from fastapi import Request, HTTPException

_lock = threading.Lock()
_requests: dict[str, list[float]] = defaultdict(list)

# Config: (route_path, max_requests, window_seconds)
LIMITS = {
    "/api/auth/register": (5, 60),
    "/api/auth/login": (5, 60),
    "/api/auth/forgot-password": (3, 60),
    "/api/health": (10, 60),
    "/api/analyze": (10, 60),
    "/api/restore": (10, 60),
    "/api/animate": (10, 60),
}


def get_client_ip(request: Request) -> str:
    """Extrait l'IP client, en tenant compte du proxy Traefik."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def check_rate_limit(request: Request) -> None:
    """Vérifie et applique le rate limiting. Lève HTTPException 429 si dépassé."""
    path = request.url.path

    # Trouver la limite applicable (match exact ou préfixe)
    limit_config = None
    for route_path, cfg in LIMITS.items():
        if path == route_path or (
            route_path.endswith("/") and path.startswith(route_path)
        ):
            limit_config = cfg
            break

    if not limit_config:
        return  # Pas de limite pour cette route

    max_req, window = limit_config
    ip = get_client_ip(request)
    key = f"{ip}:{path}"
    now = time.time()

    with _lock:
        # Nettoyer les anciennes requêtes
        _requests[key] = [t for t in _requests[key] if now - t < window]

        if len(_requests[key]) >= max_req:
            raise HTTPException(
                status_code=429,
                detail="Trop de requêtes. Veuillez réessayer plus tard.",
            )

        _requests[key].append(now)
