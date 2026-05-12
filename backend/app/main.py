"""
Point d'entrée de l'application FastAPI Flaskback Restore.

Démarre le serveur uvicorn et configure les middlewares, le logging,
et le montage des routes.
"""

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.routes import router
from app.api.user import router as user_router
from app.config import DEBUG, UPLOAD_DIR, ALLOWED_ORIGINS, ENVIRONMENT
from app.db.database import initialiser_base
from app.db.session import init_db as async_initialiser_base
from app.rate_limit_middleware import check_rate_limit

# ---------------------------------------------------------------------------
# Rate limiting — voir middleware HTTP plus bas
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Configuration du logging
# ---------------------------------------------------------------------------

_format = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_handler_console = logging.StreamHandler(sys.stdout)
_handler_console.setFormatter(_format)
_handler_console.setLevel(logging.DEBUG if DEBUG else logging.INFO)

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO, handlers=[_handler_console])
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Initialisation de l'application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Flashback Restore API",
    description=(
        "API de restauration de photos anciennes par IA. "
        "Analyse les défauts, restaure les images par IA, "
        "et crée des animations de portraits parlants."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting — middleware HTTP custom (voir rate_limit_middleware.py)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        check_rate_limit(request)
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
        )
    return await call_next(request)

# ---------------------------------------------------------------------------
# Middleware CORS
# ---------------------------------------------------------------------------

# Origines autorisées : depuis .env en production, sinon fallback dev
if ALLOWED_ORIGINS.strip():
    _cors_origins = [o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()]
else:
    _cors_origins = [
        "http://localhost:3000",
        "http://localhost:8001",
        "https://flashback-restore.com",
        "https://www.flashback-restore.com",
    ]

# En production, NE PAS inclure localhost
if ENVIRONMENT == "production":
    _cors_origins = [o for o in _cors_origins if "localhost" not in o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Middleware de sécurité (headers)
# ---------------------------------------------------------------------------

@app.middleware("http")
async def ajouter_headers_securite(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=63072000"
    return response


@app.middleware("http")
async def ajouter_cache_control_uploads(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/uploads/"):
        response.headers["Cache-Control"] = "public, max-age=86400"
    return response


# ---------------------------------------------------------------------------
# Routes API
# ---------------------------------------------------------------------------

app.include_router(router)
app.include_router(auth_router)
app.include_router(user_router)

# ---------------------------------------------------------------------------
# Fichiers statiques (uploads)
# ---------------------------------------------------------------------------

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ---------------------------------------------------------------------------
# Événements de cycle de vie
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def demarrage():
    """Initialise la base de données au démarrage."""
    logger.info("Démarrage de Flashback Restore API...")
    await async_initialiser_base()
    logger.info(f"Répertoire d'upload : {UPLOAD_DIR}")
    logger.info("Base de données initialisée.")
    logger.info("API prête à recevoir des requêtes.")


@app.on_event("shutdown")
async def arret():
    """Nettoyage à l'arrêt."""
    logger.info("Arrêt de Flashback Restore API.")


# ---------------------------------------------------------------------------
# Point d'entrée pour uvicorn
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="debug" if DEBUG else "info",
    )
