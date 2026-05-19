"""
Service de synchronisation des comptes Clerk ⇄ PostgreSQL.

Point d'entrée unique pour créer/maintenir les comptes utilisateurs
à partir des événements Clerk (webhook) ou du premier login (JWT).

Utilisé par :
- POST /api/webhooks/clerk    (création anticipée, sync email, suppression)
- _trouver_ou_creer_utilisateur (auth.py — fallback si webhook pas encore arrivé)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError

from app.db.session import async_session
from app.models.db_models import Utilisateur

logger = logging.getLogger(__name__)

# Valeurs par défaut pour les nouveaux comptes Clerk
DEFAUT_PLAN = "gratuit"
DEFAUT_CREDITS = 0
DEFAUT_ESSAIS = 3
DEFAUT_RETENTION = 30  # jours


async def ensure_compte(
    clerk_id: str,
    email: str,
    *,
    mettre_a_jour_email: bool = False,
) -> Optional[dict]:
    """
    Assurance idempotente qu'un compte PostgreSQL existe pour un utilisateur Clerk.

    - Cherche d'abord par oauth_provider_id (clerk_id)
    - Puis par email (fallback)
    - Si rien trouvé : INSERT avec ON CONFLICT (email) DO NOTHING
      suivi d'un re-read (un INSERT concurrent peut avoir gagné)
    - Si mettre_a_jour_email=True et l'email a changé → UPDATE

    Race condition safe : les deux chemins (webhook + /auth/me) peuvent
    s'exécuter en parallèle sans corruption.

    Args:
        clerk_id: ID Clerk de l'utilisateur (ex: "user_3DunO7...")
        email: Adresse email primaire vérifiée
        mettre_a_jour_email: Si True, met à jour l'email si différent

    Returns:
        dict utilisateur {"id", "email", ...} ou None si échec
    """
    email_lower = email.lower() if email else None
    if not email_lower:
        logger.error("ensure_compte appelé sans email pour clerk_id=%s", clerk_id)
        return None

    async with async_session() as session:
        async with session.begin():
            # 1. Chercher l'utilisateur existant
            utilisateur = await _trouver_par_clerk_id(session, clerk_id)
            if not utilisateur:
                # Fallback par email (ex: compte créé par un autre chemin)
                utilisateur = await _trouver_par_email(session, email_lower)

            if utilisateur:
                # 2. Utilisateur existant : mettre à jour si nécessaire
                needs_update = False

                # Lier le clerk_id si manquant (ex: compte créé via register local
                # puis l'utilisateur se connecte via Clerk avec le même email)
                if not utilisateur.oauth_provider_id:
                    utilisateur.oauth_provider = "clerk"
                    utilisateur.oauth_provider_id = clerk_id
                    needs_update = True
                    logger.info(
                        "Compte existant lié à Clerk: email=%s clerk_id=%s",
                        email_lower, clerk_id,
                    )

                # Mettre à jour l'email si demandé et différent
                if (
                    mettre_a_jour_email
                    and utilisateur.email.lower() != email_lower
                ):
                    ancien = utilisateur.email
                    utilisateur.email = email_lower
                    needs_update = True
                    logger.info(
                        "Email mis à jour (sync Clerk): %s → %s",
                        ancien, email_lower,
                    )

                if needs_update:
                    await session.flush()

                return _utilisateur_to_dict(utilisateur)

            # 3. Aucun compte : créer
            return await _creer_compte(session, clerk_id, email_lower)


async def supprimer_compte(clerk_id: str) -> bool:
    """
    Soft-delete d'un compte utilisateur (suppression Clerk → anonymisation).

    Ne supprime PAS la ligne (garder les jobs/factures pour conformité).
    Anonymise l'email et désactive le compte.

    Returns:
        True si un compte a été anonymisé, False si aucun trouvé
    """
    async with async_session() as session:
        async with session.begin():
            utilisateur = await _trouver_par_clerk_id(session, clerk_id)
            if not utilisateur:
                logger.warning("supprimer_compte: clerk_id=%s introuvable", clerk_id)
                return False

            # Anonymiser
            now = datetime.now(timezone.utc)
            utilisateur.email = f"anonymise+{utilisateur.id[:8]}@flashback-restore.com"
            utilisateur.password_hash = "DELETED"
            utilisateur.oauth_provider = None
            utilisateur.oauth_provider_id = None
            utilisateur.est_abonne = 0
            utilisateur.derniere_activite = now
            await session.flush()

            logger.info(
                "Compte Clerk anonymisé: clerk_id=%s local_id=%s email=%s",
                clerk_id, utilisateur.id, utilisateur.email,
            )
            return True


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------


async def _trouver_par_clerk_id(session, clerk_id: str) -> Optional[Utilisateur]:
    """Cherche un utilisateur par son oauth_provider_id Clerk."""
    result = await session.execute(
        select(Utilisateur).where(
            Utilisateur.oauth_provider == "clerk",
            Utilisateur.oauth_provider_id == clerk_id,
        )
    )
    return result.scalar_one_or_none()


async def _trouver_par_email(session, email: str) -> Optional[Utilisateur]:
    """Cherche un utilisateur par email (fallback)."""
    result = await session.execute(
        select(Utilisateur).where(Utilisateur.email == email)
    )
    return result.scalar_one_or_none()


async def _creer_compte(
    session, clerk_id: str, email: str
) -> Optional[dict]:
    """
    Crée un nouvel utilisateur avec les valeurs par défaut.

    Utilise PostgreSQL ON CONFLICT pour l'idempotence.
    En cas de conflit, re-lit le compte créé par la requête concurrente.
    """
    now = datetime.now(timezone.utc)

    stmt = (
        pg_insert(Utilisateur)
        .values(
            email=email,
            password_hash="",  # Comptes Clerk : pas de login local
            essais_restants=DEFAUT_ESSAIS,
            credits=DEFAUT_CREDITS,
            est_abonne=0,
            plan=DEFAUT_PLAN,
            retention_jours=DEFAUT_RETENTION,
            oauth_provider="clerk",
            oauth_provider_id=clerk_id,
            cree_le=now,
            derniere_connexion=now,
        )
        .on_conflict_do_nothing(index_elements=["email"])
    )

    await session.execute(stmt)
    await session.flush()

    # Re-lire (INSERT a pu être ignoré si conflit → relire le gagnant)
    utilisateur = await _trouver_par_clerk_id(session, clerk_id)
    if not utilisateur:
        # Fallback par email
        utilisateur = await _trouver_par_email(session, email)

    if utilisateur:
        logger.info("Compte Clerk créé/lu: email=%s clerk_id=%s id=%s",
                     email, clerk_id, utilisateur.id)
        return _utilisateur_to_dict(utilisateur)

    logger.error("Échec création compte Clerk: email=%s clerk_id=%s", email, clerk_id)
    return None


def _utilisateur_to_dict(u: Utilisateur) -> dict:
    """Convertit un objet Utilisateur en dict compatible avec le code existant."""
    return {
        "id": u.id,
        "email": u.email,
        "password_hash": u.password_hash,
        "essais_restants": u.essais_restants,
        "credits": u.credits,
        "est_abonne": u.est_abonne,
        "plan": u.plan,
        "retention_jours": u.retention_jours,
        "oauth_provider": u.oauth_provider,
        "oauth_provider_id": u.oauth_provider_id,
        "cree_le": u.cree_le,
        "derniere_connexion": u.derniere_connexion,
        "derniere_activite": u.derniere_activite,
    }
