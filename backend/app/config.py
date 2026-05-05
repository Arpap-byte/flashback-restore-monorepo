"""
Configuration de l'application Flaskback Restore.

Charge les variables d'environnement et expose les paramètres
de configuration pour tous les services.
"""

import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "flashback.db"

# Création automatique du répertoire d'upload
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- API Gemini ---
GEMINI_API_KEY: str = os.getenv(
    "GEMINI_API_KEY",
    "AIzaSyC33Y8WS6_voVPaMY2RCIsy_35bkxdsV-w",
)
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- API D-ID ---
DID_API_KEY: str = os.getenv(
    "DID_API_KEY",
    "DID_API_KEY_PLACEHOLDER",
)
DID_BASE_URL: str = os.getenv(
    "DID_BASE_URL",
    "https://api.d-id.com",
)

# --- Sécurité ---
SECRET_KEY: str = os.getenv(
    "SECRET_KEY",
    "fe5cdce1484b7677d2c7dec478d57389ccbee8b1c999a13ca690b2deea001a09",
)

# --- Base de données ---
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://flashback:flashback@db:5432/flashback",
)

# --- Serveur ---
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
