"""
Service d'audit pour Flashback Restore.

Fournit des helpers pour enregistrer les événements de sécurité
(login, register, password reset, etc.) avec IP, User-Agent et résultat.
"""

import logging
from typing import Optional

from app.db.database import enregistrer_audit as _db_audit

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


def log_auth(
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

    audit_id = _db_audit(
        evenement=evenement,
        email=email,
        utilisateur_id=utilisateur_id,
        ip=ip,
        user_agent=ua,
        reussite=reussite,
        detail=detail,
    )

    statut = "✓" if reussite else "✗"
    logger.info(f"[AUDIT] {statut} {evenement} | email={email or '?'} | ip={ip} | {detail or ''}")

    return audit_id
