"""
Service de gestion des consentements légaux — Flashback Restore.

Gère l'enregistrement, la vérification et la révocation des consentements :
- CGV + rétractation (checkout Stripe)
- RGPD biométrique + IA (upload photos)

Append-only : on ne modifie jamais une ligne, on en crée une nouvelle.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, and_, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Consentement

logger = logging.getLogger(__name__)

# Fenêtre de fraîcheur pour les consentements checkout (minutes)
CONSENT_FRESHNESS_MINUTES = 10

# Version des textes légaux actuellement en vigueur
CGV_VERSION = "v1.2-2026-05-19"
RETRACTATION_VERSION = "v1.0-2026-05-19"
RGPD_BIOMETRIQUE_VERSION = "v1.0-2026-05-19"
RGPD_IA_VERSION = "v1.0-2026-05-19"


async def enregistrer_consentement(
    session: AsyncSession,
    *,
    type_consentement: str,
    version_texte: str,
    utilisateur_id: Optional[str] = None,
    email: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    contexte: Optional[dict] = None,
) -> Consentement:
    """Enregistre un nouveau consentement (append-only).

    Args:
        session: Session SQLAlchemy async.
        type_consentement: 'cgv_checkout', 'renonciation_retractation',
                          'rgpd_biometrique', 'rgpd_ia'.
        version_texte: Version du texte accepté.
        utilisateur_id: ID de l'utilisateur (si authentifié).
        email: Email (fallback si non authentifié).
        ip: Adresse IP de l'utilisateur.
        user_agent: User-Agent du navigateur.
        contexte: Données contextuelles JSON (plan, session_id, etc.).

    Returns:
        L'objet Consentement créé.
    """
    consentement = Consentement(
        utilisateur_id=utilisateur_id,
        email=email,
        type_consentement=type_consentement,
        version_texte=version_texte,
        accepte=True,
        ip=ip,
        user_agent=user_agent,
        contexte=json.dumps(contexte) if contexte else None,
        accorde_le=datetime.now(timezone.utc),
    )
    session.add(consentement)
    await session.flush()
    logger.info(
        "Consentement enregistré : type=%s, user=%s, ip=%s, version=%s",
        type_consentement,
        utilisateur_id or email or "anon",
        ip,
        version_texte,
    )
    return consentement


async def consentement_actif(
    session: AsyncSession,
    *,
    utilisateur_id: Optional[str] = None,
    email: Optional[str] = None,
    type_consentement: str,
) -> bool:
    """Vérifie si un consentement est actuellement actif.

    Retourne True si la dernière ligne pour (user, type) a accepte=True
    et retire_le IS NULL.
    """
    conditions = [
        Consentement.type_consentement == type_consentement,
        Consentement.accepte == True,
        Consentement.retire_le.is_(None),
    ]
    if utilisateur_id:
        conditions.append(Consentement.utilisateur_id == utilisateur_id)
    elif email:
        conditions.append(Consentement.email == email)
    else:
        return False

    stmt = (
        select(Consentement)
        .where(and_(*conditions))
        .order_by(Consentement.accorde_le.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def consentements_checkout_recents(
    session: AsyncSession,
    *,
    email: str,
    fenetre_minutes: int = CONSENT_FRESHNESS_MINUTES,
) -> bool:
    """Vérifie que les consentements CGV ET rétractation existent
    pour cet email dans la fenêtre de temps configurée.
    """
    seuil = datetime.now(timezone.utc) - timedelta(minutes=fenetre_minutes)

    for t in ("cgv_checkout", "renonciation_retractation"):
        stmt = (
            select(Consentement)
            .where(
                Consentement.type_consentement == t,
                Consentement.email == email,
                Consentement.accepte == True,
                Consentement.retire_le.is_(None),
                Consentement.accorde_le >= seuil,
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is None:
            return False
    return True


async def retirer_consentement(
    session: AsyncSession,
    *,
    utilisateur_id: str,
    type_consentement: str,
) -> bool:
    """Révoque un consentement en marquant retire_le sur la dernière ligne active.

    Retourne True si une ligne a été révoquée, False si aucun consentement actif.
    """
    stmt = (
        select(Consentement)
        .where(
            Consentement.utilisateur_id == utilisateur_id,
            Consentement.type_consentement == type_consentement,
            Consentement.accepte == True,
            Consentement.retire_le.is_(None),
        )
        .order_by(Consentement.accorde_le.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    consentement = result.scalar_one_or_none()

    if consentement is None:
        return False

    consentement.retire_le = datetime.now(timezone.utc)
    await session.flush()
    logger.info(
        "Consentement révoqué : type=%s, user=%s",
        type_consentement,
        utilisateur_id,
    )
    return True


async def obtenir_etat_consentements(
    session: AsyncSession,
    *,
    utilisateur_id: str,
) -> dict:
    """Retourne l'état actif de tous les types de consentement pour un utilisateur."""
    types = ["cgv_checkout", "renonciation_retractation", "rgpd_biometrique", "rgpd_ia"]
    etat = {}
    for t in types:
        etat[t] = await consentement_actif(
            session, utilisateur_id=utilisateur_id, type_consentement=t
        )

    # Historique (10 dernières lignes, ordre chrono inverse)
    stmt = (
        select(Consentement)
        .where(Consentement.utilisateur_id == utilisateur_id)
        .order_by(Consentement.accorde_le.desc())
        .limit(10)
    )
    result = await session.execute(stmt)
    historique = []
    for c in result.scalars():
        historique.append({
            "id": c.id,
            "type": c.type_consentement,
            "accepte": c.accepte,
            "version": c.version_texte,
            "accorde_le": c.accorde_le.isoformat() if c.accorde_le else None,
            "retire_le": c.retire_le.isoformat() if c.retire_le else None,
            "ip_masquee": _masquer_ip(c.ip) if c.ip else None,
        })

    return {
        "consentements": etat,
        "historique": historique,
    }


def _masquer_ip(ip: str) -> str:
    """Masque le dernier octet d'une IP pour l'affichage utilisateur.
    Ex: 192.168.1.42 → 192.168.1.***
    """
    parts = ip.split(".")
    if len(parts) == 4:
        parts[-1] = "***"
        return ".".join(parts)
    return ip[: max(0, len(ip) - 4)] + "****"
