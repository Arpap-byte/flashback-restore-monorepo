"""
Routes de gestion des consentements légaux — Flashback Restore.

Endpoints :
- POST /api/consents/checkout  : CGV + rétractation avant paiement
- POST /api/consents/biometric  : RGPD biométrique + IA avant upload
- GET  /api/consents/me         : État des consentements de l'utilisateur
- DELETE /api/consents/biometric : Révocation du consentement biométrique
"""

import logging
from datetime import timezone, datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import exiger_utilisateur
from app.db.session import async_session
from app.services.consent_service import (
    CGV_VERSION,
    RETRACTATION_VERSION,
    RGPD_BIOMETRIQUE_VERSION,
    RGPD_IA_VERSION,
    consentement_actif,
    consentements_checkout_recents,
    enregistrer_consentement,
    obtenir_etat_consentements,
    retirer_consentement,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consents", tags=["Consentements"])


def _extraire_ip(request: Request) -> str:
    """Extrait l'IP réelle du client (gère le proxy Traefik)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "inconnue"


def _extraire_ua(request: Request) -> str:
    """Extrait le User-Agent du navigateur."""
    return request.headers.get("User-Agent", "inconnu")[:512]


# ── POST /api/consents/checkout ──────────────────────────

@router.post("/checkout")
async def consentement_checkout(request: Request):
    """
    Enregistre les consentements CGV et rétractation avant paiement.

    Accepte un utilisateur authentifié (via JWT) OU un email non authentifié.
    Retourne { ok: true, consent_id }.
    """
    body = await request.json()
    email = body.get("email", "").strip().lower()
    plan = body.get("plan", "inconnu")
    cgv_version = body.get("cgv_version", CGV_VERSION)
    retractation_version = body.get("retractation_version", RETRACTATION_VERSION)

    if not email:
        raise HTTPException(status_code=400, detail="Email requis pour le consentement checkout.")

    # Essayer d'obtenir l'utilisateur authentifié (optionnel)
    utilisateur_id = None
    try:
        utilisateur = await exiger_utilisateur.__wrapped__(request) if False else None
    except Exception:
        pass

    ip = _extraire_ip(request)
    ua = _extraire_ua(request)
    contexte = {"plan": plan, "source": "checkout"}

    async with async_session() as session:
        async with session.begin():
            c1 = await enregistrer_consentement(
                session,
                type_consentement="cgv_checkout",
                version_texte=cgv_version,
                utilisateur_id=utilisateur_id,
                email=email,
                ip=ip,
                user_agent=ua,
                contexte=contexte,
            )
            c2 = await enregistrer_consentement(
                session,
                type_consentement="renonciation_retractation",
                version_texte=retractation_version,
                utilisateur_id=utilisateur_id,
                email=email,
                ip=ip,
                user_agent=ua,
                contexte=contexte,
            )

    logger.info(
        "Consentements checkout enregistrés : email=%s, plan=%s, ip=%s",
        email, plan, ip,
    )
    return {
        "ok": True,
        "consent_id": c1.id,
        "consentements": [
            {"id": c1.id, "type": "cgv_checkout"},
            {"id": c2.id, "type": "renonciation_retractation"},
        ],
    }


# ── POST /api/consents/biometric ─────────────────────────

@router.post("/biometric")
async def consentement_biometric(
    request: Request,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Enregistre les consentements RGPD biométrique et IA.
    Authentification JWT obligatoire.
    """
    body = await request.json() if await request.body() else {}
    biometrique_version = body.get("rgpd_biometrique_version", RGPD_BIOMETRIQUE_VERSION)
    ia_version = body.get("rgpd_ia_version", RGPD_IA_VERSION)

    utilisateur_id = utilisateur.get("id")
    ip = _extraire_ip(request)
    ua = _extraire_ua(request)
    contexte = {"source": "rgpd_modal"}

    async with async_session() as session:
        async with session.begin():
            await enregistrer_consentement(
                session,
                type_consentement="rgpd_biometrique",
                version_texte=biometrique_version,
                utilisateur_id=utilisateur_id,
                ip=ip,
                user_agent=ua,
                contexte=contexte,
            )
            await enregistrer_consentement(
                session,
                type_consentement="rgpd_ia",
                version_texte=ia_version,
                utilisateur_id=utilisateur_id,
                ip=ip,
                user_agent=ua,
                contexte=contexte,
            )

    logger.info("Consentements RGPD enregistrés : user=%s", utilisateur_id)
    return {"ok": True, "message": "Consentements RGPD enregistrés."}


# ── GET /api/consents/me ─────────────────────────────────

@router.get("/me")
async def mes_consentements(
    request: Request,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """Retourne l'état de tous les consentements de l'utilisateur connecté."""
    utilisateur_id = utilisateur.get("id")
    if not utilisateur_id:
        raise HTTPException(status_code=401, detail="Utilisateur non identifié.")

    async with async_session() as session:
        etat = await obtenir_etat_consentements(session, utilisateur_id=utilisateur_id)

    return etat


# ── DELETE /api/consents/biometric ───────────────────────

@router.delete("/biometric")
async def revoquer_consentement_biometric(
    request: Request,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Révoque le consentement biométrique et IA.
    Les futurs uploads seront bloqués jusqu'à nouveau consentement.
    """
    utilisateur_id = utilisateur.get("id")
    if not utilisateur_id:
        raise HTTPException(status_code=401, detail="Utilisateur non identifié.")

    async with async_session() as session:
        async with session.begin():
            ok1 = await retirer_consentement(
                session,
                utilisateur_id=utilisateur_id,
                type_consentement="rgpd_biometrique",
            )
            ok2 = await retirer_consentement(
                session,
                utilisateur_id=utilisateur_id,
                type_consentement="rgpd_ia",
            )

    if not ok1 and not ok2:
        raise HTTPException(
            status_code=404, detail="Aucun consentement biométrique actif à révoquer."
        )

    logger.info("Consentements RGPD révoqués : user=%s", utilisateur_id)
    return {"ok": True, "message": "Consentements RGPD révoqués. Les futurs uploads nécessiteront un nouveau consentement."}
