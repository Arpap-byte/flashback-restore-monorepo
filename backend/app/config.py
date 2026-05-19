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
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in environment or .env file")

# Création automatique du répertoire d'upload
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --- API Gemini ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY must be set in environment or .env file")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-image-preview")

# --- Sécurité ---
SECRET_KEY: str = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set in environment or .env file")
AUTH_SECRET: str = os.getenv("AUTH_SECRET", "")
# --- Clerk JWT ---
CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
CLERK_ISSUER: str = os.getenv("CLERK_ISSUER", "")
CLERK_JWKS_URL: str = os.getenv("CLERK_JWKS_URL", "")
CLERK_AUDIENCE: str = os.getenv("CLERK_AUDIENCE", "")
# --- Admin ---
ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")
# Clé pour les endpoints admin (stats, etc.) — pas de valeur par défaut

# --- Stripe (paiements) ---
STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY", "")
# STRIPE_API_KEY can be empty if Stripe is not used; no hard error
STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
# Ne pas démarrer avec le placeholder : plante volontairement au boot
if not STRIPE_WEBHOOK_SECRET or STRIPE_WEBHOOK_SECRET == "whsec_placeholder":
    raise ValueError(
        "STRIPE_WEBHOOK_SECRET is missing or still set to 'whsec_placeholder'. "
        "Set your real Stripe webhook secret in .env before starting the server."
    )
STRIPE_PRICE_DECOUVERTE: str = os.getenv("STRIPE_PRICE_DECOUVERTE", "price_1TYBvHACw2Aur8P69PrMuS9F")
STRIPE_PRICE_PREMIUM: str = os.getenv("STRIPE_PRICE_PREMIUM", "price_1TYBvHACw2Aur8P61S6N9xWY")
STRIPE_PRICE_ANNUEL: str = os.getenv("STRIPE_PRICE_ANNUEL", "price_1TYBvHACw2Aur8P6UuX96v4Q")
STRIPE_PRICE_CREDITS_30: str = os.getenv("STRIPE_PRICE_CREDITS_30", "price_1TYBvIACw2Aur8P6cQZh1BDf")
STRIPE_PRICE_CREDITS_50: str = os.getenv("STRIPE_PRICE_CREDITS_50", "price_1TYBvIACw2Aur8P60j57vBLf")
STRIPE_PRICE_CREDITS_110: str = os.getenv("STRIPE_PRICE_CREDITS_110", "price_1TYBvIACw2Aur8P6O8uHYl64")

# --- Serveur ---
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

# --- URLs publiques ---
PUBLIC_BACKEND_URL: str = os.getenv("PUBLIC_BACKEND_URL", "http://localhost:8000")
ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")

# --- Sentry (observabilité) ---
SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

# --- Email (SMTP) ---
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM: str = os.getenv("SMTP_FROM", "")
SITE_URL: str = os.getenv("SITE_URL", "https://flashback-restore.com")

# Feature flag — consentements légaux obligatoires (P1.3 + P1.5)
ENFORCE_CONSENT: bool = os.getenv("ENFORCE_CONSENT", "false").lower() == "true"
