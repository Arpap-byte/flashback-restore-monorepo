"""
Configuration de l'application Flaskback Restore.

Charge les variables d'environnement et expose les paramètres
de configuration pour tous les services.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent

# Charge les variables d'environnement depuis .env
load_dotenv(BASE_DIR.parent / ".env")
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "flashback.db"

# Création automatique du répertoire d'upload
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- API Gemini ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set in environment or .env file")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- API D-ID ---
DID_API_KEY: str = os.getenv("DID_API_KEY", "")
if not DID_API_KEY:
    raise RuntimeError("DID_API_KEY must be set in environment or .env file")
DID_BASE_URL: str = os.getenv(
    "DID_BASE_URL",
    "https://api.d-id.com",
)

# --- Sécurité ---
SECRET_KEY: str = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in environment or .env file")
AUTH_SECRET: str = os.getenv("AUTH_SECRET", "")
INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY")
if not INTERNAL_API_KEY:
    raise RuntimeError("INTERNAL_API_KEY must be set in environment or .env file")

# --- Stripe (paiements) ---
STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY", "")
# STRIPE_API_KEY can be empty if Stripe is not used; no hard error
STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
STRIPE_PRICE_DECOUVERTE: str = os.getenv("STRIPE_PRICE_DECOUVERTE", "price_decouverte_monthly")
STRIPE_PRICE_PREMIUM: str = os.getenv("STRIPE_PRICE_PREMIUM", "price_premium_monthly")
STRIPE_PRICE_ANNUEL: str = os.getenv("STRIPE_PRICE_ANNUEL", "price_premium_yearly")
STRIPE_PRICE_CREDITS_30: str = os.getenv("STRIPE_PRICE_CREDITS_30", "price_credits_30")
STRIPE_PRICE_CREDITS_50: str = os.getenv("STRIPE_PRICE_CREDITS_50", "price_credits_50")
STRIPE_PRICE_CREDITS_110: str = os.getenv("STRIPE_PRICE_CREDITS_110", "price_credits_110")

# --- Serveur ---
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
