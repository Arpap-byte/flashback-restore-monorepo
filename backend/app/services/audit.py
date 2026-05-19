"""
Service d'audit pour Flashback Restore.

Fournit des helpers pour enregistrer les événements de sécurité
(login, register, password reset, etc.) avec IP, User-Agent et résultat.
"""

import logging
from typing import Optional

from app.db.queries import enregistrer_audit as _db_audit

logger = logging.getLogger(__name__)


def extraire_ip_et_ua(request) -> tuple[str, str]:
    """
    Extrait l'adresse IP et le User-Agent d'une requête FastAPI.

    Gère les proxies (X-Forwarded-For, X-Real-IP).
    """
    ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.headers.get("x-real-ip", "")
        or (request.client.host if request.client else "inconnu")
    )
    ua = request.headers.get("user-agent", "inconnu")
    return ip, ua


async def log_auth(
    request,
    evenement: str,
    email: Optional[str] = None,
    utilisateur_id: Optional[str] = None,
    reussite: bool = True,
    detail: Optional[str] = None,
) -> str:
    """
    Enregistre un événement d'audit d'authentification.

    Extrait automatiquement IP et User-Agent de la requête.

    Args:
        request: Requête FastAPI.
        evenement: Type d'événement (login, register, oauth_login, etc.).
        email: Email de l'utilisateur.
        utilisateur_id: ID utilisateur si dispo.
        reussite: True = succès, False = échec.
        detail: Détail additionnel.

    Returns:
        ID de l'entrée d'audit.
    """
    ip, ua = extraire_ip_et_ua(request)

    # Masquage de l'email pour l'audit (RGPD)
    if email and "@" in email:
        email_masque = email[:3] + "***@" + email.split("@")[1]
    elif email:
        email_masque = email[:3] + "***"
    else:
        email_masque = None

    audit_id = await _db_audit(
        evenement=evenement,
        email=email_masque,
        utilisateur_id=utilisateur_id,
        ip=ip,
        user_agent=ua,
        reussite=reussite,
        detail=detail,
    )

    statut = "✓" if reussite else "✗"
    logger.info(f"[AUDIT] {statut} {evenement} | email={email_masque or '?'} | ip={ip} | {detail or ''}")

    return audit_id


async def log_webhook(
    request,
    evenement: str,
    clerk_id: Optional[str] = None,
    email: Optional[str] = None,
    reussite: bool = True,
) -> str:
    """
    Enregistre un événement d'audit pour les webhooks Clerk.

    Args:
        request: Requête FastAPI.
        evenement: Type d'événement (user.created, user.updated, user.deleted).
        clerk_id: ID Clerk de l'utilisateur concerné.
        email: Email de l'utilisateur.
        reussite: True = succès.

    Returns:
        ID de l'entrée d'audit.
    """
    detail = f"clerk_id={clerk_id}" if clerk_id else None
    return await log_auth(
        request,
        f"webhook_{evenement}",
        email=email,
        reussite=reussite,
        detail=detail,
    )


async def log_security_event(
    evenement: str,
    detail: Optional[str] = None,
) -> str:
    """
    Enregistre un événement de sécurité sans requête HTTP (ex: tâche de fond).

    Args:
        evenement: Type d'événement (webhook_signature_invalide, etc.).
        detail: Détail additionnel.

    Returns:
        ID de l'entrée d'audit.
    """
    # Pas de request → IP et UA fixes
    audit_id = await _db_audit(
        evenement=f"securite_{evenement}",
        ip="127.0.0.1",
        user_agent="hermes/internal",
        reussite=False,
        detail=detail,
    )

    logger.warning(f"[SECURITE] {evenement} | {detail or ''}")
    return audit_id
