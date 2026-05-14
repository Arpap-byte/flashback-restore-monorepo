"""
Requêtes SQLAlchemy asynchrones — Phase 2 de migration PostgreSQL.

Convertit toutes les fonctions de database.py (SQLite brut) en SQLAlchemy 2.0 async.
Mêmes noms, mêmes signatures que database.py.

Pattern: async def fonction(...): async with async_session() as session: ...
"""

import uuid
import time as _time_module
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, select, text, update

from app.db.session import async_session
from app.models.db_models import (
    Abonnement,
    AchatCredits,
    AuditLog,
    ConsommationCredits,
    EssaiGratuit,
    ReinitialisationMdp,
    StripeEvent,
    Travail,
    Utilisateur,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Retourne le timestamp UTC avec timezone."""
    return datetime.now(timezone.utc)


def _mois_courant() -> str:
    """Retourne le mois courant au format YYYY-MM."""
    return _utcnow().strftime("%Y-%m")


def _new_uuid() -> str:
    """Génère un UUID v4."""
    return str(uuid.uuid4())


def _row_to_dict(row) -> Optional[dict]:
    """Convertit une instance ORM en dictionnaire, ou None."""
    if row is None:
        return None
    # Si c'est déjà un dict (résultat .mappings()), retourner tel quel
    if isinstance(row, dict):
        return row
    # Instance ORM: convertir les colonnes en dict
    result = {}
    for col in row.__table__.columns:
        val = getattr(row, col.key)
        # Convertir datetime en chaîne ISO pour compatibilité ascendante
        if isinstance(val, datetime):
            val = val.isoformat()
        result[col.key] = val
    return result


def _rows_to_dicts(rows) -> list[dict]:
    """Convertit une liste d'instances ORM en liste de dictionnaires."""
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Constantes (mêmes que database.py)
# ---------------------------------------------------------------------------

# Mapping plan → crédits mensuels
CREDITS_PAR_PLAN: dict[str, int] = {
    "gratuit": 0,
    "decouverte": 10,
    "premium": 100,
    "annuel": 100,
    "pro": -1,  # -1 = illimité
}

# Limites d'animation par forfait (par mois)
ANIMATIONS_PAR_PLAN: dict[str, int] = {
    "gratuit": 0,
    "decouverte": 2,
    "premium": 25,
    "annuel": 25,
    "pro": -1,
}

# Mapping des modèles de restauration par forfait
MODELE_RESTAURATION_PAR_PLAN: dict[str, str] = {
    "gratuit": "imagen-4-fast",
    "decouverte": "imagen-4-standard",
    "premium": "imagen-4-standard",
    "annuel": "imagen-4-standard",
    "pro": "imagen-4-batch",
}

# Mapping des modèles d'animation par forfait
MODELE_ANIMATION_PAR_PLAN: dict[str, str] = {
    "gratuit": None,
    "decouverte": "veo-3.1-fast",
    "premium": "veo-3.1-lite",
    "annuel": "veo-3.1-lite",
    "pro": "veo-3.1-standard-batch",
}

# Cache de plan utilisateur (évite des requêtes répétées)
_plan_cache: dict[str, tuple[float, str]] = {}


# ===================================================================
# Travaux (jobs)
# ===================================================================


async def creer_travail(
    type_travail: str,
    chemin_photo: Optional[str] = None,
    job_externe_id: Optional[str] = None,
    utilisateur_id: Optional[str] = None,
) -> str:
    """Crée une nouvelle entrée de travail et retourne son ID."""
    travail_id = _new_uuid()
    maintenant = _utcnow()
    async with async_session() as session:
        travail = Travail(
            id=travail_id,
            type=type_travail,
            statut="cree",
            chemin_photo=chemin_photo,
            job_externe_id=job_externe_id,
            utilisateur_id=utilisateur_id,
            cree_le=maintenant,
            modifie_le=maintenant,
        )
        session.add(travail)
        await session.commit()
    return travail_id


async def mettre_a_jour_travail(
    travail_id: str,
    statut: Optional[str] = None,
    chemin_resultat: Optional[str] = None,
    resultat_json: Optional[str] = None,
    message_erreur: Optional[str] = None,
    taille_original: Optional[int] = None,
    taille_resultat: Optional[int] = None,
) -> bool:
    """Met à jour le statut et les champs d'un travail existant."""
    valeurs = {"modifie_le": _utcnow()}
    if statut is not None:
        valeurs["statut"] = statut
    if chemin_resultat is not None:
        valeurs["chemin_resultat"] = chemin_resultat
    if resultat_json is not None:
        valeurs["resultat_json"] = resultat_json
    if message_erreur is not None:
        valeurs["message_erreur"] = message_erreur
    if taille_original is not None:
        valeurs["taille_original"] = taille_original
    if taille_resultat is not None:
        valeurs["taille_resultat"] = taille_resultat

    async with async_session() as session:
        stmt = update(Travail).where(Travail.id == travail_id).values(**valeurs)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def mettre_a_jour_activite(utilisateur_id: str) -> bool:
    """Met à jour la date de dernière activité d'un utilisateur (dashboard admin)."""
    async with async_session() as session:
        stmt = (
            update(Utilisateur)
            .where(Utilisateur.id == utilisateur_id)
            .values(derniere_activite=_utcnow())
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def obtenir_travail(travail_id: str) -> Optional[dict]:
    """Récupère un travail par son ID."""
    async with async_session() as session:
        stmt = select(Travail).where(Travail.id == travail_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return _row_to_dict(row)


async def obtenir_travail_par_job_externe(job_externe_id: str) -> Optional[dict]:
    """Récupère un travail par son ID externe (ex: job D-ID)."""
    async with async_session() as session:
        stmt = select(Travail).where(Travail.job_externe_id == job_externe_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return _row_to_dict(row)


async def lister_travaux_par_utilisateur(
    utilisateur_id: str, limite: int = 50
) -> list[dict]:
    """Liste les travaux d'un utilisateur, du plus récent au plus ancien."""
    async with async_session() as session:
        stmt = (
            select(Travail)
            .where(Travail.utilisateur_id == utilisateur_id)
            .order_by(Travail.cree_le.desc())
            .limit(limite)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return _rows_to_dicts(rows)


async def mettre_a_jour_job_externe_id(
    travail_id: str, job_externe_id: str
) -> bool:
    """Met à jour le job_externe_id d'un travail existant."""
    async with async_session() as session:
        stmt = (
            update(Travail)
            .where(Travail.id == travail_id)
            .values(job_externe_id=job_externe_id, modifie_le=_utcnow())
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


# ===================================================================
# Abonnements (Stripe)
# ===================================================================


async def creer_abonnement(
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    statut: str = "actif",
    plan: Optional[str] = None,
    email_utilisateur: Optional[str] = None,
    derniere_attribution: Optional[str] = None,
    session=None,
) -> str:
    """Crée un nouvel abonnement dans la base locale.

    Si session est fournie, utilise cette session sans committer
    (permet l'atomicité multi-opérations).
    """
    async def _do(sess):
        abonnement_id = _new_uuid()
        maintenant = _utcnow()
        abo = Abonnement(
            id=abonnement_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            statut=statut,
            plan=plan,
            email_utilisateur=email_utilisateur,
            derniere_attribution_credits=derniere_attribution,
            cree_le=maintenant,
            modifie_le=maintenant,
        )
        sess.add(abo)
        return abonnement_id

    if session is not None:
        return await _do(session)
    async with async_session() as session:
        result = await _do(session)
        await session.commit()
        return result


async def obtenir_abonnement(
    abonnement_id: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
) -> Optional[dict]:
    """Récupère un abonnement par ID local, ID client Stripe ou ID abonnement Stripe."""
    async with async_session() as session:
        if abonnement_id:
            stmt = select(Abonnement).where(Abonnement.id == abonnement_id)
        elif stripe_subscription_id:
            stmt = select(Abonnement).where(
                Abonnement.stripe_subscription_id == stripe_subscription_id
            )
        elif stripe_customer_id:
            stmt = (
                select(Abonnement)
                .where(Abonnement.stripe_customer_id == stripe_customer_id)
                .order_by(Abonnement.cree_le.desc())
                .limit(1)
            )
        else:
            return None
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return _row_to_dict(row)


async def mettre_a_jour_abonnement(
    abonnement_id: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    statut: Optional[str] = None,
    plan: Optional[str] = None,
    email_utilisateur: Optional[str] = None,
) -> bool:
    """Met à jour les informations d'un abonnement existant."""
    valeurs = {"modifie_le": _utcnow()}
    if statut is not None:
        valeurs["statut"] = statut
    if plan is not None:
        valeurs["plan"] = plan
    if email_utilisateur is not None:
        valeurs["email_utilisateur"] = email_utilisateur

    if abonnement_id:
        clause = Abonnement.id == abonnement_id
    elif stripe_subscription_id:
        clause = Abonnement.stripe_subscription_id == stripe_subscription_id
    elif stripe_customer_id:
        clause = Abonnement.stripe_customer_id == stripe_customer_id
    else:
        return False

    async with async_session() as session:
        stmt = update(Abonnement).where(clause).values(**valeurs)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def mettre_a_jour_attribution_credits(
    stripe_subscription_id: str, date_iso: str
) -> bool:
    """Met à jour la date de dernière attribution de crédits pour un abonnement."""
    async with async_session() as session:
        stmt = (
            update(Abonnement)
            .where(Abonnement.stripe_subscription_id == stripe_subscription_id)
            .values(
                derniere_attribution_credits=date_iso,
                modifie_le=_utcnow(),
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


# ===================================================================
# Utilisateurs (auth)
# ===================================================================


async def creer_utilisateur(email: str, password_hash: str) -> Optional[str]:
    """Crée un nouvel utilisateur. Retourne l'ID ou None si l'email existe déjà."""
    utilisateur_id = _new_uuid()
    maintenant = _utcnow()
    async with async_session() as session:
        # Vérifier si l'email existe déjà
        stmt = select(Utilisateur.id).where(Utilisateur.email == email)
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            return None

        user = Utilisateur(
            id=utilisateur_id,
            email=email,
            password_hash=password_hash,
            essais_restants=3,
            est_abonne=0,
            cree_le=maintenant,
            derniere_connexion=maintenant,
        )
        session.add(user)
        await session.commit()
    return utilisateur_id


async def obtenir_utilisateur_par_email(email: str) -> Optional[dict]:
    """Récupère un utilisateur par son email."""
    async with async_session() as session:
        stmt = select(Utilisateur).where(Utilisateur.email == email)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return _row_to_dict(row)


async def obtenir_utilisateur_par_oauth(
    provider: str, provider_id: str
) -> Optional[dict]:
    """Récupère un utilisateur par son compte OAuth."""
    async with async_session() as session:
        stmt = select(Utilisateur).where(
            and_(
                Utilisateur.oauth_provider == provider,
                Utilisateur.oauth_provider_id == provider_id,
            )
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return _row_to_dict(row)


async def creer_utilisateur_oauth(
    email: str, provider: str, provider_id: str
) -> Optional[str]:
    """Crée un utilisateur lié à un compte OAuth (Google/Facebook/etc)."""
    utilisateur_id = _new_uuid()
    maintenant = _utcnow()
    async with async_session() as session:
        user = Utilisateur(
            id=utilisateur_id,
            email=email,
            password_hash="",
            essais_restants=3,
            credits=0,
            est_abonne=0,
            oauth_provider=provider,
            oauth_provider_id=provider_id,
            cree_le=maintenant,
            derniere_connexion=maintenant,
        )
        session.add(user)
        try:
            await session.commit()
        except Exception:
            # IntegrityError (email déjà existant)
            await session.rollback()
            return None
    return utilisateur_id


async def obtenir_utilisateur_par_id(utilisateur_id: str) -> Optional[dict]:
    """Récupère un utilisateur par son ID."""
    async with async_session() as session:
        stmt = select(Utilisateur).where(Utilisateur.id == utilisateur_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return _row_to_dict(row)


async def mettre_a_jour_derniere_connexion(utilisateur_id: str) -> bool:
    """Met à jour la date de dernière connexion."""
    async with async_session() as session:
        stmt = (
            update(Utilisateur)
            .where(Utilisateur.id == utilisateur_id)
            .values(derniere_connexion=_utcnow())
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def mettre_a_jour_email(utilisateur_id: str, nouvel_email: str) -> bool:
    """Met à jour l'email d'un utilisateur (ex: placeholder → email réel Clerk)."""
    async with async_session() as session:
        stmt = (
            update(Utilisateur)
            .where(Utilisateur.id == utilisateur_id)
            .values(email=nouvel_email)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def decrementer_essais(utilisateur_id: str) -> int:
    """Décrémente le compteur d'essais. Retourne le nombre restant."""
    async with async_session() as session:
        # UPDATE atomique : décrémente seulement si essais_restants > 0
        stmt = (
            update(Utilisateur)
            .where(
                and_(
                    Utilisateur.id == utilisateur_id,
                    Utilisateur.essais_restants > 0,
                )
            )
            .values(essais_restants=Utilisateur.essais_restants - 1)
            .returning(Utilisateur.essais_restants)
        )
        result = await session.execute(stmt)
        await session.commit()
        row = result.fetchone()
        if row is not None:
            return row[0]

        # Si aucune ligne modifiée (essais déjà à 0), récupérer la valeur actuelle
        stmt2 = select(Utilisateur.essais_restants).where(
            Utilisateur.id == utilisateur_id
        )
        result2 = await session.execute(stmt2)
        val = result2.scalar_one_or_none()
        return val if val is not None else 0


async def obtenir_essais_restants(utilisateur_id: str) -> Optional[dict]:
    """Récupère les essais restants et le statut d'abonnement."""
    async with async_session() as session:
        stmt = select(
            Utilisateur.essais_restants, Utilisateur.est_abonne
        ).where(Utilisateur.id == utilisateur_id)
        result = await session.execute(stmt)
        row = result.one_or_none()
        if row:
            return {
                "essais_restants": row.essais_restants,
                "est_abonne": bool(row.est_abonne),
            }
        return None


async def lister_essais_gratuits(
    utilisateur_id: str, limite: int = 20
) -> list[dict]:
    """Liste les essais gratuits d'un utilisateur."""
    async with async_session() as session:
        stmt = (
            select(EssaiGratuit)
            .where(EssaiGratuit.utilisateur_id == utilisateur_id)
            .order_by(EssaiGratuit.cree_le.desc())
            .limit(limite)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return _rows_to_dicts(rows)


async def enregistrer_essai(
    utilisateur_id: str, type_travail: str, travail_id: str
) -> str:
    """Enregistre un essai gratuit."""
    essai_id = _new_uuid()
    maintenant = _utcnow()
    async with async_session() as session:
        essai = EssaiGratuit(
            id=essai_id,
            utilisateur_id=utilisateur_id,
            type_travail=type_travail,
            travail_id=travail_id,
            cree_le=maintenant,
        )
        session.add(essai)
        await session.commit()
    return essai_id


# ===================================================================
# Crédits
# ===================================================================


async def crediter_utilisateur(utilisateur_id: str, nombre: int, session=None) -> int:
    """Ajoute des crédits à un utilisateur. Retourne le nouveau solde.

    Si session est fournie, utilise cette session sans committer
    (permet l'atomicité multi-opérations).
    """
    async def _do(sess):
        stmt = (
            update(Utilisateur)
            .where(Utilisateur.id == utilisateur_id)
            .values(credits=Utilisateur.credits + nombre)
            .returning(Utilisateur.credits)
        )
        result = await sess.execute(stmt)
        row = result.fetchone()
        return row[0] if row else 0

    if session is not None:
        return await _do(session)
    async with async_session() as session:
        result = await _do(session)
        await session.commit()
        return result


async def consommer_credit(
    utilisateur_id: str, type_operation: str, travail_id: str
) -> dict:
    """
    Consomme un crédit pour une opération.
    Priorité : essais gratuits puis crédits payants.

    Utilise SELECT ... FOR UPDATE pour verrouiller la ligne utilisateur
    et éviter les race conditions (ex: double consommation sous charge).
    """
    async with async_session() as session:
        async with session.begin():
            # Récupérer crédits et essais AVEC verrou de ligne
            stmt = select(
                Utilisateur.credits, Utilisateur.essais_restants
            ).where(Utilisateur.id == utilisateur_id).with_for_update()
            result = await session.execute(stmt)
            user = result.one_or_none()
            if not user:
                return {
                    "succes": False,
                    "raison": "Utilisateur introuvable",
                }

            credits = user.credits
            essais = user.essais_restants

            # Priorité aux essais gratuits
            if essais > 0:
                await session.execute(
                    update(Utilisateur)
                    .where(Utilisateur.id == utilisateur_id)
                    .values(essais_restants=Utilisateur.essais_restants - 1)
                )
                essai_id = _new_uuid()
                maintenant = _utcnow()
                session.add(
                    EssaiGratuit(
                        id=essai_id,
                        utilisateur_id=utilisateur_id,
                        type_travail=type_operation,
                        travail_id=travail_id,
                        cree_le=maintenant,
                    )
                )
                return {
                    "succes": True,
                    "type": "essai",
                    "credits_restants": credits,
                    "essais_restants": essais - 1,
                }

            # Puis crédits payants
            if credits > 0:
                await session.execute(
                    update(Utilisateur)
                    .where(Utilisateur.id == utilisateur_id)
                    .values(credits=Utilisateur.credits - 1)
                )
                conso_id = _new_uuid()
                maintenant = _utcnow()
                session.add(
                    ConsommationCredits(
                        id=conso_id,
                        utilisateur_id=utilisateur_id,
                        travail_id=travail_id,
                        type_operation=type_operation,
                        credits_utilises=1,
                        cree_le=maintenant,
                    )
                )
                return {
                    "succes": True,
                    "type": "credit",
                    "credits_restants": credits - 1,
                    "essais_restants": 0,
                }

            # Plus rien
            return {
                "succes": False,
                "raison": "Plus de crédits ni d'essais gratuits",
            }


async def rembourser_credit(utilisateur_id: str, travail_id: str) -> dict:
    """
    Rembourse un crédit/essai consommé pour un travail.

    Vérifie si le travail a consommé un essai gratuit ou un crédit
    payant, et annule la consommation. L'incrémentation du compteur
    d'animations est également annulée.

    Returns:
        {"succes": True/False, "type": "essai"|"credit"|"aucun", "message": ...}
    """
    async with async_session() as session:
        async with session.begin():
            # 1. Vérifier si c'était un essai gratuit
            stmt_essai = select(EssaiGratuit).where(
                and_(
                    EssaiGratuit.utilisateur_id == utilisateur_id,
                    EssaiGratuit.travail_id == travail_id,
                )
            )
            result_essai = await session.execute(stmt_essai)
            essai = result_essai.scalar_one_or_none()

            if essai:
                # Rembourser l'essai
                await session.delete(essai)
                await session.execute(
                    update(Utilisateur)
                    .where(Utilisateur.id == utilisateur_id)
                    .values(essais_restants=Utilisateur.essais_restants + 1)
                )
                # Annuler l'incrémentation du compteur d'animations
                await session.execute(
                    update(Utilisateur)
                    .where(
                        and_(
                            Utilisateur.id == utilisateur_id,
                            Utilisateur.animations_utilisees > 0,
                        )
                    )
                    .values(animations_utilisees=Utilisateur.animations_utilisees - 1)
                )
                return {
                    "succes": True,
                    "type": "essai",
                    "message": "Essai gratuit remboursé",
                }

            # 2. Vérifier si c'était un crédit payant
            stmt_credit = select(ConsommationCredits).where(
                and_(
                    ConsommationCredits.utilisateur_id == utilisateur_id,
                    ConsommationCredits.travail_id == travail_id,
                )
            )
            result_credit = await session.execute(stmt_credit)
            conso = result_credit.scalar_one_or_none()

            if conso:
                credits_utilises = conso.credits_utilises
                await session.delete(conso)
                await session.execute(
                    update(Utilisateur)
                    .where(Utilisateur.id == utilisateur_id)
                    .values(credits=Utilisateur.credits + credits_utilises)
                )
                # Annuler l'incrémentation du compteur d'animations
                await session.execute(
                    update(Utilisateur)
                    .where(
                        and_(
                            Utilisateur.id == utilisateur_id,
                            Utilisateur.animations_utilisees > 0,
                        )
                    )
                    .values(animations_utilisees=Utilisateur.animations_utilisees - 1)
                )
                return {
                    "succes": True,
                    "type": "credit",
                    "message": f"{credits_utilises} crédit(s) remboursé(s)",
                }

            # Aucune consommation trouvée
            return {
                "succes": False,
                "type": "aucun",
                "message": "Aucune consommation trouvée pour ce travail",
            }


async def enregistrer_achat_credits(
    utilisateur_id: str,
    stripe_session_id: str,
    nombre_credits: int,
    montant_euros: float,
    session=None,
) -> str:
    """Enregistre un achat de crédits. Retourne l'ID de l'achat.

    Si session est fournie, utilise cette session sans committer
    (permet l'atomicité multi-opérations).
    """
    async def _do(sess):
        achat_id = _new_uuid()
        maintenant = _utcnow()
        achat = AchatCredits(
            id=achat_id,
            utilisateur_id=utilisateur_id,
            stripe_session_id=stripe_session_id,
            nombre_credits=nombre_credits,
            montant_euros=montant_euros,
            cree_le=maintenant,
        )
        sess.add(achat)
        return achat_id

    if session is not None:
        return await _do(session)
    async with async_session() as session:
        result = await _do(session)
        await session.commit()
        return result


async def obtenir_credits_restants(utilisateur_id: str) -> dict:
    """Retourne les crédits et essais d'un utilisateur."""
    async with async_session() as session:
        stmt = select(
            Utilisateur.credits, Utilisateur.essais_restants
        ).where(Utilisateur.id == utilisateur_id)
        result = await session.execute(stmt)
        row = result.one_or_none()
        if row:
            return {"credits": row.credits, "essais_restants": row.essais_restants}
        return {"credits": 0, "essais_restants": 0}


# ===================================================================
# Réinitialisation de mot de passe
# ===================================================================


async def creer_token_reinitialisation(
    utilisateur_id: str, token: str, duree_minutes: int = 30
) -> str:
    """Crée un token de réinitialisation de mot de passe. Stocke uniquement le hash SHA-256 du token."""
    import hashlib
    maintenant = _utcnow()
    expire = maintenant + timedelta(minutes=duree_minutes)
    token_id = _new_uuid()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    async with async_session() as session:
        entry = ReinitialisationMdp(
            id=token_id,
            utilisateur_id=utilisateur_id,
            token=token_hash,  # Stocker le hash, pas le token brut
            expire_le=expire,
            utilise=0,
            cree_le=maintenant,
        )
        session.add(entry)
        await session.commit()
    return token_id


async def verifier_token_reinitialisation(token: str) -> Optional[dict]:
    """Vérifie un token de réinitialisation (comparaison par hash SHA-256). Retourne l'entrée si valide, None sinon."""
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    async with async_session() as session:
        stmt = select(ReinitialisationMdp).where(
            and_(
                ReinitialisationMdp.token == token_hash,
                ReinitialisationMdp.utilise == 0,
            )
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return None
        entry = _row_to_dict(row)
        # Vérifier expiration
        expire = row.expire_le
        if isinstance(expire, str):
            expire = datetime.fromisoformat(expire)
        # S'assurer que expire est timezone-aware pour la comparaison
        if expire.tzinfo is None:
            expire = expire.replace(tzinfo=timezone.utc)
        if _utcnow() > expire:
            return None
        return entry


async def marquer_token_utilise(token: str, session=None) -> bool:
    """Marque un token comme utilisé.

    Si session est fournie, utilise cette session sans committer
    (permet l'atomicité multi-opérations).
    """
    async def _do(sess):
        stmt = (
            update(ReinitialisationMdp)
            .where(ReinitialisationMdp.token == token)
            .values(utilise=1)
        )
        result = await sess.execute(stmt)
        return result.rowcount > 0

    if session is not None:
        return await _do(session)
    async with async_session() as session:
        result = await _do(session)
        await session.commit()
        return result


async def changer_mot_de_passe(utilisateur_id: str, nouveau_hash: str, session=None) -> bool:
    """Change le mot de passe d'un utilisateur.

    Si session est fournie, utilise cette session sans committer
    (permet l'atomicité multi-opérations).
    """
    async def _do(sess):
        stmt = (
            update(Utilisateur)
            .where(Utilisateur.id == utilisateur_id)
            .values(password_hash=nouveau_hash)
        )
        result = await sess.execute(stmt)
        return result.rowcount > 0

    if session is not None:
        return await _do(session)
    async with async_session() as session:
        result = await _do(session)
        await session.commit()
        return result


# ===================================================================
# Suivi des animations mensuelles (par forfait)
# ===================================================================


async def obtenir_plan_utilisateur(utilisateur_id: str) -> str:
    """Retourne le plan actuel d'un utilisateur (gratuit, decouverte, premium, annuel, pro)."""
    maintenant = _time_module.time()
    if utilisateur_id in _plan_cache:
        ts, plan_cache = _plan_cache[utilisateur_id]
        if maintenant - ts < 60:
            return plan_cache

    async with async_session() as session:
        stmt = select(Utilisateur.plan, Utilisateur.est_abonne).where(
            Utilisateur.id == utilisateur_id
        )
        result = await session.execute(stmt)
        row = result.one_or_none()
        if not row:
            plan = "gratuit"
        elif row.est_abonne and row.plan and row.plan != "gratuit":
            plan = row.plan
        else:
            plan = "gratuit"
        _plan_cache[utilisateur_id] = (maintenant, plan)
        return plan


async def peut_animer(utilisateur_id: str) -> dict:
    """
    Vérifie si l'utilisateur peut créer une animation.

    Returns:
        {"autorise": True/False, "raison": "...", "utilisees": N, "limite": N}
    """
    plan = await obtenir_plan_utilisateur(utilisateur_id)
    limite = ANIMATIONS_PAR_PLAN.get(plan, 0)

    # Blocage strict pour le plan gratuit
    if limite == 0:
        return {
            "autorise": False,
            "raison": (
                "Les animations ne sont pas disponibles en forfait Gratuit. "
                "Passez à un forfait payant pour débloquer cette fonctionnalité."
            ),
            "utilisees": 0,
            "limite": 0,
        }

    # Pro : illimité
    if limite == -1:
        return {"autorise": True, "raison": "", "utilisees": 0, "limite": -1}

    mois = _mois_courant()
    async with async_session() as session:
        stmt = select(
            Utilisateur.animations_utilisees,
            Utilisateur.mois_animation_courant,
        ).where(Utilisateur.id == utilisateur_id)
        result = await session.execute(stmt)
        row = result.one_or_none()
        if not row:
            return {
                "autorise": False,
                "raison": "Utilisateur introuvable.",
                "utilisees": 0,
                "limite": limite,
            }

        utilisees = row.animations_utilisees or 0
        mois_enregistre = row.mois_animation_courant

        # Réinitialiser le compteur si on change de mois
        if mois_enregistre != mois:
            await session.execute(
                update(Utilisateur)
                .where(Utilisateur.id == utilisateur_id)
                .values(animations_utilisees=0, mois_animation_courant=mois)
            )
            await session.commit()
            utilisees = 0

        if utilisees >= limite:
            return {
                "autorise": False,
                "raison": (
                    f"Limite d'animations atteinte ({limite} par mois). "
                    "Réessayez le mois prochain."
                ),
                "utilisees": utilisees,
                "limite": limite,
            }

        return {
            "autorise": True,
            "raison": "",
            "utilisees": utilisees,
            "limite": limite,
        }


async def enregistrer_animation(utilisateur_id: str) -> dict:
    """
    Incrémente le compteur d'animations mensuelles.

    Returns:
        {"succes": True/False, "utilisees": N, "limite": N}
    """
    plan = await obtenir_plan_utilisateur(utilisateur_id)
    limite = ANIMATIONS_PAR_PLAN.get(plan, 0)
    mois = _mois_courant()

    async with async_session() as session:
        # Lire l'état actuel
        stmt = select(
            Utilisateur.animations_utilisees,
            Utilisateur.mois_animation_courant,
        ).where(Utilisateur.id == utilisateur_id)
        result = await session.execute(stmt)
        row = result.one_or_none()
        if not row:
            return {"succes": False, "utilisees": 0, "limite": limite}

        mois_enregistre = row.mois_animation_courant
        if mois_enregistre != mois:
            # Nouveau mois → reset à 1
            await session.execute(
                update(Utilisateur)
                .where(Utilisateur.id == utilisateur_id)
                .values(animations_utilisees=1, mois_animation_courant=mois)
            )
        else:
            # Incrémenter
            await session.execute(
                update(Utilisateur)
                .where(Utilisateur.id == utilisateur_id)
                .values(
                    animations_utilisees=Utilisateur.animations_utilisees + 1
                )
            )
        await session.commit()

        # Relire la nouvelle valeur
        stmt2 = select(Utilisateur.animations_utilisees).where(
            Utilisateur.id == utilisateur_id
        )
        result2 = await session.execute(stmt2)
        val = result2.scalar_one_or_none()
        return {
            "succes": True,
            "utilisees": val if val is not None else 0,
            "limite": limite,
        }


async def mettre_a_jour_plan_utilisateur(utilisateur_id: str, plan: str, session=None) -> bool:
    """Met à jour le plan d'un utilisateur (appelé lors de la souscription Stripe).

    Si session est fournie, utilise cette session sans committer
    (permet l'atomicité multi-opérations).
    """
    async def _do(sess):
        stmt = (
            update(Utilisateur)
            .where(Utilisateur.id == utilisateur_id)
            .values(plan=plan, est_abonne=1)
        )
        result = await sess.execute(stmt)
        return result.rowcount > 0

    if session is not None:
        return await _do(session)
    async with async_session() as session:
        result = await _do(session)
        await session.commit()
        return result


# ===================================================================
# Audit logs (sécurité)
# ===================================================================


async def enregistrer_audit(
    evenement: str,
    email: Optional[str] = None,
    utilisateur_id: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    reussite: bool = True,
    detail: Optional[str] = None,
) -> str:
    """Enregistre un événement d'audit (login, register, reset password, etc.)."""
    audit_id = _new_uuid()
    maintenant = _utcnow()
    async with async_session() as session:
        entry = AuditLog(
            id=audit_id,
            evenement=evenement,
            email=email,
            utilisateur_id=utilisateur_id,
            ip=ip,
            user_agent=user_agent,
            reussite=1 if reussite else 0,
            detail=detail,
            cree_le=maintenant,
        )
        session.add(entry)
        await session.commit()
    return audit_id


async def lister_audit_logs(
    email: Optional[str] = None,
    evenement: Optional[str] = None,
    reussite: Optional[bool] = None,
    limite: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Liste les logs d'audit avec filtres optionnels."""
    async with async_session() as session:
        conditions = []
        if email:
            conditions.append(AuditLog.email == email)
        if evenement:
            conditions.append(AuditLog.evenement == evenement)
        if reussite is not None:
            conditions.append(AuditLog.reussite == (1 if reussite else 0))

        stmt = select(AuditLog)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(AuditLog.cree_le.desc()).limit(limite).offset(offset)

        result = await session.execute(stmt)
        rows = result.scalars().all()
        return _rows_to_dicts(rows)


async def compter_audit_logs(
    email: Optional[str] = None,
    evenement: Optional[str] = None,
    reussite: Optional[bool] = None,
) -> int:
    """Compte le nombre de logs d'audit correspondant aux filtres."""
    async with async_session() as session:
        conditions = []
        if email:
            conditions.append(AuditLog.email == email)
        if evenement:
            conditions.append(AuditLog.evenement == evenement)
        if reussite is not None:
            conditions.append(AuditLog.reussite == (1 if reussite else 0))

        stmt = select(func.count()).select_from(AuditLog)
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await session.execute(stmt)
        count = result.scalar_one()
        return count


# ===================================================================
# Alias (noms alternatifs mentionnés dans le cahier des charges)
# ===================================================================

# Auth
trouver_utilisateur_par_email = obtenir_utilisateur_par_email
obtenir_utilisateur = obtenir_utilisateur_par_id
maj_derniere_connexion = mettre_a_jour_derniere_connexion
mettre_a_jour_mot_de_passe = changer_mot_de_passe
stocker_token_reinitialisation = creer_token_reinitialisation
valider_token_reinitialisation = verifier_token_reinitialisation

# Travaux
obtenir_travaux_utilisateur = lister_travaux_par_utilisateur

# Essais
enregistrer_essai_gratuit = enregistrer_essai

# Abonnements
maj_statut_abonnement = mettre_a_jour_abonnement
attribuer_credits_abonnement = mettre_a_jour_attribution_credits

# Audit
consulter_audit_logs = lister_audit_logs


# ===================================================================
# Fonction composite : creer_ou_maj_abonnement
# ===================================================================


async def creer_ou_maj_abonnement(
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    statut: str = "actif",
    plan: Optional[str] = None,
    email_utilisateur: Optional[str] = None,
    derniere_attribution: Optional[str] = None,
) -> str:
    """
    Crée un abonnement ou met à jour l'existant.
    Retourne l'ID de l'abonnement (créé ou existant).
    """
    # Chercher un abonnement existant
    existing = await obtenir_abonnement(
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
    )
    if existing:
        await mettre_a_jour_abonnement(
            abonnement_id=existing["id"],
            statut=statut,
            plan=plan,
            email_utilisateur=email_utilisateur,
        )
        return existing["id"]
    else:
        return await creer_abonnement(
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            statut=statut,
            plan=plan,
            email_utilisateur=email_utilisateur,
            derniere_attribution=derniere_attribution,
        )


# ===================================================================
# Rétention & Préférences (migration 12/05/2026)
# ===================================================================


async def mettre_a_jour_retention(utilisateur_id: str, retention_jours: int) -> bool:
    """Met à jour la durée de rétention des fichiers d'un utilisateur."""
    async with async_session() as session:
        stmt = (
            update(Utilisateur)
            .where(Utilisateur.id == utilisateur_id)
            .values(retention_jours=retention_jours)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def obtenir_retention(utilisateur_id: str) -> int:
    """Récupère la durée de rétention (7, 30, ou 90 jours), défaut 30."""
    async with async_session() as session:
        stmt = select(Utilisateur.retention_jours).where(Utilisateur.id == utilisateur_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return row if row is not None else 30


# ===================================================================
# Chemin animation & Suppression travaux (migration 12/05/2026)
# ===================================================================


async def mettre_a_jour_chemin_animation(travail_id: str, chemin_animation: str) -> bool:
    """Enregistre le chemin/URL de l'animation terminée pour un travail."""
    async with async_session() as session:
        stmt = (
            update(Travail)
            .where(Travail.id == travail_id)
            .values(chemin_animation=chemin_animation, modifie_le=_utcnow())
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def supprimer_travail(travail_id: str) -> bool:
    """Supprime un travail de la base (sans toucher aux fichiers)."""
    async with async_session() as session:
        stmt = select(Travail).where(Travail.id == travail_id)
        result = await session.execute(stmt)
        travail = result.scalar_one_or_none()
        if travail is None:
            return False
        await session.delete(travail)
        await session.commit()
        return True


async def supprimer_tous_travaux_utilisateur(utilisateur_id: str) -> int:
    """Supprime tous les travaux d'un utilisateur. Retourne le nombre supprimé."""
    async with async_session() as session:
        stmt = select(Travail).where(Travail.utilisateur_id == utilisateur_id)
        result = await session.execute(stmt)
        travaux = result.scalars().all()
        count = len(travaux)
        for t in travaux:
            await session.delete(t)
        await session.commit()
        return count


# ===================================================================
# Stripe Events (idempotence des webhooks)
# ===================================================================


async def stripe_event_deja_traite(event_id: str) -> bool:
    """Vérifie si un événement Stripe a déjà été traité."""
    async with async_session() as session:
        stmt = select(StripeEvent.id).where(StripeEvent.event_id == event_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def marquer_stripe_event_traite(event_id: str, type_evenement: str, session=None) -> str:
    """Marque un événement Stripe comme traité. Retourne l'ID local.

    Si session est fournie, utilise cette session sans committer
    (permet l'atomicité multi-opérations).
    """
    async def _do(sess):
        stripe_event_id = _new_uuid()
        maintenant = _utcnow()
        entry = StripeEvent(
            id=stripe_event_id,
            event_id=event_id,
            type_evenement=type_evenement,
            traite_le=maintenant,
        )
        sess.add(entry)
        return stripe_event_id

    if session is not None:
        return await _do(session)
    async with async_session() as session:
        result = await _do(session)
        await session.commit()
        return result
