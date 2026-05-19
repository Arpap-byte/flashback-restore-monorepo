"""
Routes webhook Clerk — synchronisation cycle de vie utilisateur.

Endpoints :
- POST /api/webhooks/clerk  — Reçoit les événements Clerk (user.created/updated/deleted)

Sécurité : signature Svix obligatoire (header svix-id, svix-timestamp, svix-signature).
Pas d'authentification JWT (Clerk n'envoie pas de token utilisateur).
"""

import logging
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import DEBUG
from app.limiter import limiter
from app.services.clerk_account import ensure_compte, supprimer_compte
from app.services.audit import log_webhook

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

CLERK_WEBHOOK_SECRET = os.getenv("CLERK_WEBHOOK_SECRET", "")

# ---------------------------------------------------------------------------
# Vérification de la signature Svix
# ---------------------------------------------------------------------------


def _verifier_signature(request: Request, payload: bytes) -> dict:
    """
    Vérifie la signature Svix du webhook Clerk.

    La signature est HMAC SHA-256 du corps brut (bytes).
    Ne JAMAIS ré-sérialiser le JSON (casserait la signature).

    En mode DEBUG, accepte les requêtes sans signature pour les tests.

    Raises:
        HTTPException(401) si signature invalide
        HTTPException(400) si headers manquants
    """
    if DEBUG and not CLERK_WEBHOOK_SECRET:
        logger.warning("Webhook Clerk non sécurisé : mode DEBUG sans CLERK_WEBHOOK_SECRET")
        # En dev, accepter sans signature pour les tests
        return {}

    if not CLERK_WEBHOOK_SECRET:
        logger.error("CLERK_WEBHOOK_SECRET non configuré — webhook Clerk désactivé")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    svix_id = request.headers.get("svix-id", "")
    svix_timestamp = request.headers.get("svix-timestamp", "")
    svix_signature = request.headers.get("svix-signature", "")

    if not all([svix_id, svix_timestamp, svix_signature]):
        raise HTTPException(
            status_code=400,
            detail="Missing Svix headers (svix-id, svix-timestamp, svix-signature)",
        )

    try:
        from svix.webhooks import Webhook, WebhookVerificationError

        wh = Webhook(CLERK_WEBHOOK_SECRET)
        return wh.verify(payload, {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        })
    except ImportError:
        logger.critical("Librairie 'svix' non installée — impossible de vérifier les webhooks")
        raise HTTPException(status_code=500, detail="Webhook verification unavailable")
    except WebhookVerificationError as e:
        logger.warning("Signature webhook Clerk invalide: svix-id=%s, erreur=%s", svix_id, e)
        # Audit de sécurité
        from app.services.audit import log_security_event
        import asyncio
        asyncio.create_task(log_security_event(
            "webhook_signature_invalide",
            detail=f"svix-id={svix_id}, timestamp={svix_timestamp}",
        ))
        raise HTTPException(status_code=401, detail="Invalid signature")


# ---------------------------------------------------------------------------
# Route webhook
# ---------------------------------------------------------------------------


@router.post("/clerk")
@limiter.limit("60/minute")
async def clerk_webhook(request: Request):
    """
    Webhook Clerk — événements cycle de vie utilisateur.

    Événements traités :
    - user.created  → Crée le compte PostgreSQL (si pas déjà fait)
    - user.updated  → Sync email
    - user.deleted  → Soft-delete / anonymise

    Sécurité : signature Svix HMAC SHA-256 du corps brut.
    Idempotence : ON CONFLICT DO NOTHING sur toutes les opérations.
    """
    # 1. Lire le raw body AVANT tout parsing JSON
    payload = await request.body()

    # 2. Vérifier la signature Svix
    try:
        _verifier_signature(request, payload)
    except HTTPException:
        raise  # 401/400 déjà levé

    # 3. Parser le JSON
    import json

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type", "")
    event_data = event.get("data", {})
    clerk_id = event_data.get("id", "")

    if not clerk_id:
        logger.warning("Webhook Clerk sans clerk_id: type=%s", event_type)
        return JSONResponse(status_code=200, content={"status": "ignored", "reason": "no clerk_id"})

    # 4. Router par type d'événement
    if event_type == "user.created":
        await _handle_user_created(clerk_id, event_data, request)

    elif event_type == "user.updated":
        await _handle_user_updated(clerk_id, event_data, request)

    elif event_type == "user.deleted":
        await _handle_user_deleted(clerk_id, request)

    else:
        logger.debug("Webhook Clerk ignoré: type=%s clerk_id=%s", event_type, clerk_id)
        return JSONResponse(
            status_code=200,
            content={"status": "ignored", "reason": f"unhandled event type: {event_type}"},
        )

    return JSONResponse(status_code=200, content={"status": "ok"})


# ---------------------------------------------------------------------------
# Handlers par type d'événement
# ---------------------------------------------------------------------------


async def _handle_user_created(clerk_id: str, data: dict, request: Request):
    """Crée le compte PostgreSQL pour un nouvel utilisateur Clerk."""
    email = _extraire_email(data)

    if not email:
        logger.error(
            "user.created sans email valide: clerk_id=%s emails=%s",
            clerk_id,
            [e.get("email_address", "?") for e in data.get("email_addresses", [])],
        )
        return

    result = await ensure_compte(clerk_id, email)

    if result:
        logger.info("user.created traité: clerk_id=%s email=%s local_id=%s",
                     clerk_id, email, result["id"])
        await log_webhook(request, "user.created", clerk_id=clerk_id, email=email, reussite=True)
    else:
        logger.error("user.created échec: clerk_id=%s email=%s", clerk_id, email)
        await log_webhook(request, "user.created", clerk_id=clerk_id, email=email, reussite=False)


async def _handle_user_updated(clerk_id: str, data: dict, request: Request):
    """Synchronise l'email si changé côté Clerk (user.updated)."""
    email = _extraire_email(data)

    if not email:
        logger.warning("user.updated sans email: clerk_id=%s", clerk_id)
        return

    # Utiliser ensure_compte en mode upsert (crée si absent, update sinon)
    result = await ensure_compte(clerk_id, email, mettre_a_jour_email=True)

    if result:
        logger.info("user.updated traité: clerk_id=%s email=%s", clerk_id, email)
        await log_webhook(request, "user.updated", clerk_id=clerk_id, email=email, reussite=True)


async def _handle_user_deleted(clerk_id: str, request: Request):
    """Soft-delete du compte utilisateur (anonymisation)."""
    ok = await supprimer_compte(clerk_id)
    if ok:
        logger.info("user.deleted traité: clerk_id=%s", clerk_id)
        await log_webhook(request, "user.deleted", clerk_id=clerk_id, reussite=True)
    else:
        logger.warning("user.deleted ignoré (compte introuvable): clerk_id=%s", clerk_id)
        # Ne pas logguer en échec — c'est normal si le webhook arrive
        # avant que le compte ait été créé (possible en edge case)


def _extraire_email(data: dict) -> str:
    """
    Extrait le premier email non-placeholder des données Clerk.

    Clerk renvoie email_addresses : [{"email_address": "...", "id": "...", ...}]
    On prend TOUJOURS le premier email vérifié (Clerk garantit qu'il y en a un).
    """
    email_addresses = data.get("email_addresses", [])
    for entry in email_addresses:
        addr = entry.get("email_address", "")
        if addr and not addr.endswith("@placeholder.local"):
            return addr
    # Fallback : premier email même si placeholder (ne devrait pas arriver)
    if email_addresses:
        return email_addresses[0].get("email_address", "")
    return ""
