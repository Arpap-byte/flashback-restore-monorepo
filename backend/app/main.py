"""
Point d'entrée de l'application FastAPI Flaskback Restore.

Démarre le serveur uvicorn et configure les middlewares, le logging,
et le montage des routes.
"""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import DEBUG, UPLOAD_DIR
from app.db.database import initialiser_base

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
        "Analyse les défauts, restaure les images avec Gemini + Pillow, "
        "et crée des animations de portraits parlants avec D-ID."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes API
# ---------------------------------------------------------------------------

app.include_router(router)

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
    initialiser_base()
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
