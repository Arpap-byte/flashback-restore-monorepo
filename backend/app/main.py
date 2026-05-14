"""
Point d'entrée de l'application FastAPI Flaskback Restore.

Démarre le serveur uvicorn et configure les middlewares, le logging,
et le montage des routes.
"""

import logging
import os
import sys

from typing import Optional

import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.api.auth import router as auth_router
from app.api.routes import router
from app.api.user import router as user_router
from app.auth import decoder_token, _trouver_ou_creer_utilisateur
from app.config import DEBUG, UPLOAD_DIR, ALLOWED_ORIGINS, ENVIRONMENT, SENTRY_DSN
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
# Initialisation de Sentry (observabilité — optionnel)
# ---------------------------------------------------------------------------

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
    )
    logger.info("Sentry initialisé (environnement : %s)", ENVIRONMENT)
else:
    logger.info("Sentry désactivé (SENTRY_DSN non défini)")

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
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None if os.getenv("ENVIRONMENT") == "production" else "/redoc",
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
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://js.stripe.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://*.clerk.accounts.dev https://api.clerk.com; "
        "frame-src 'self' https://*.clerk.accounts.dev https://js.stripe.com"
    )
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.middleware("http")
async def ajouter_cache_control_uploads(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/uploads/"):
        response.headers["Cache-Control"] = "no-store, private"
    return response


# ---------------------------------------------------------------------------
# Routes API
# ---------------------------------------------------------------------------

app.include_router(router)
app.include_router(auth_router)
app.include_router(user_router)

# ---------------------------------------------------------------------------
# Fichiers uploads — protégé par authentification + ownership
# ---------------------------------------------------------------------------

# IMPORTANT : Les uploads NE SONT PLUS publics.
# Le montage StaticFiles a été remplacé par un endpoint protégé.


@app.get("/uploads/{filename:path}")
async def servir_upload_protege(
    filename: str,
    request: Request,
    token: Optional[str] = Query(None, description="JWT token alternatif au header Authorization"),
):
    """
    Sert un fichier uploadé UNIQUEMENT à son propriétaire.

    - Accepte l'authentification via header Authorization Bearer OU query param ?token=
    - Si le header Authorization est présent, il est utilisé en priorité
    - Sinon, le query parameter 'token' est utilisé comme fallback (pour les balises <img>)
    - Vérification que le fichier appartient à l'utilisateur connecté
    - Les admins (X-Admin-Key) peuvent accéder aux fichiers orphelins
    """
    from pathlib import Path as _Path

    from fastapi.responses import FileResponse
    from sqlalchemy import text as _sa_text

    from app.config import ADMIN_API_KEY
    from app.db.session import async_session

    chemin = (_Path(UPLOAD_DIR) / filename).resolve()
    upload_root = _Path(UPLOAD_DIR).resolve()

    # Anti directory traversal
    if not str(chemin).startswith(str(upload_root)):
        raise HTTPException(status_code=403, detail="Chemin interdit.")
    if not chemin.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable.")

    # --- Authentification : header Authorization (prioritaire) ou query param token ---
    utilisateur: Optional[dict] = None
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        # Essayer le header Authorization en premier
        try:
            payload = decoder_token(auth_header[7:])
            utilisateur = await _trouver_ou_creer_utilisateur(payload)
        except Exception:
            pass  # On essaiera le query param ensuite

    if utilisateur is None and token:
        # Fallback : token JWT passé en query parameter (pour <img src>)
        try:
            payload = decoder_token(token)
            utilisateur = await _trouver_ou_creer_utilisateur(payload)
        except Exception:
            pass

    if utilisateur is None:
        raise HTTPException(status_code=401, detail="Authentification requise.")

    # Vérifier ownership
    async with async_session() as session:
        row = (await session.execute(
            _sa_text("""
                SELECT utilisateur_id FROM travaux
                WHERE chemin_photo = :c OR chemin_resultat = :c
                   OR chemin_animation = :c
                LIMIT 1
            """),
            {"c": str(chemin)}
        )).fetchone()

    if row is None:
        # Fichier orphelin — admin only
        admin_key = request.headers.get("X-Admin-Key")
        if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
            raise HTTPException(status_code=403, detail="Accès non autorisé.")
    elif row[0] != utilisateur["id"]:
        raise HTTPException(status_code=403, detail="Ce fichier ne vous appartient pas.")

    return FileResponse(str(chemin))


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
    from app.db.session import close_db

    await close_db()
    logger.info("Moteur DB fermé proprement.")


# ---------------------------------------------------------------------------
# Endpoint de test Sentry (développement uniquement)
# ---------------------------------------------------------------------------

@app.get("/api/sentry-test")
async def sentry_test():
    """Endpoint de test : déclenche une exception pour vérifier Sentry."""
    raise Exception("Test Sentry — si SENTRY_DSN est configuré, cette erreur remonte dans Sentry")


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
