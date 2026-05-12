"""
Couche de compatibilité sync — enveloppe les requêtes async PostgreSQL
avec des signatures synchrones pour les imports existants.

Toute la logique métier est dans queries.py (async SQLAlchemy).
Ce fichier réexporte les fonctions avec des wrappers sync via asyncio.run().
"""
import asyncio
from typing import Optional

from app.config import DATABASE_URL

def _sync(coro):
    """Exécute une coroutine de façon synchrone, compatible avec event loop FastAPI."""
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)

from app.db.queries import (
    creer_travail as _async_creer_travail,
    mettre_a_jour_travail as _async_mettre_a_jour_travail,
    mettre_a_jour_activite as _async_mettre_a_jour_activite,
    obtenir_travail as _async_obtenir_travail,
    obtenir_travail_par_job_externe as _async_obtenir_travail_par_job_externe,
    lister_travaux_par_utilisateur as _async_lister_travaux_par_utilisateur,
    mettre_a_jour_job_externe_id as _async_mettre_a_jour_job_externe_id,
    creer_abonnement as _async_creer_abonnement,
    obtenir_abonnement as _async_obtenir_abonnement,
    mettre_a_jour_abonnement as _async_mettre_a_jour_abonnement,
    mettre_a_jour_attribution_credits as _async_mettre_a_jour_attribution_credits,
    creer_utilisateur as _async_creer_utilisateur,
    obtenir_utilisateur_par_email as _async_obtenir_utilisateur_par_email,
    obtenir_utilisateur_par_oauth as _async_obtenir_utilisateur_par_oauth,
    creer_utilisateur_oauth as _async_creer_utilisateur_oauth,
    obtenir_utilisateur_par_id as _async_obtenir_utilisateur_par_id,
    mettre_a_jour_derniere_connexion as _async_mettre_a_jour_derniere_connexion,
    decrementer_essais as _async_decrementer_essais,
    obtenir_essais_restants as _async_obtenir_essais_restants,
    lister_essais_gratuits as _async_lister_essais_gratuits,
    enregistrer_essai as _async_enregistrer_essai,
    crediter_utilisateur as _async_crediter_utilisateur,
    consommer_credit as _async_consommer_credit,
    enregistrer_achat_credits as _async_enregistrer_achat_credits,
    obtenir_credits_restants as _async_obtenir_credits_restants,
    obtenir_plan_utilisateur as _async_obtenir_plan_utilisateur,
    peut_animer as _async_peut_animer,
    enregistrer_animation as _async_enregistrer_animation,
    mettre_a_jour_plan_utilisateur as _async_mettre_a_jour_plan_utilisateur,
    mettre_a_jour_retention as _async_mettre_a_jour_retention,
    obtenir_retention as _async_obtenir_retention,
    mettre_a_jour_chemin_animation as _async_mettre_a_jour_chemin_animation,
    supprimer_travail as _async_supprimer_travail,
    supprimer_tous_travaux_utilisateur as _async_supprimer_tous_travaux_utilisateur,
    creer_token_reinitialisation as _async_creer_token_reinitialisation,
    verifier_token_reinitialisation as _async_verifier_token_reinitialisation,
    marquer_token_utilise as _async_marquer_token_utilise,
    changer_mot_de_passe as _async_changer_mot_de_passe,
    enregistrer_audit as _async_enregistrer_audit,
    lister_audit_logs as _async_lister_audit_logs,
    compter_audit_logs as _async_compter_audit_logs,
    CREDITS_PAR_PLAN,
    ANIMATIONS_PAR_PLAN,
    MODELE_RESTAURATION_PAR_PLAN,
    MODELE_ANIMATION_PAR_PLAN,
)

# ---------------------------------------------------------------------------
# Connexion sync pour les usages legacy (health check, stats, cleanup)
# ---------------------------------------------------------------------------

from sqlalchemy import create_engine as _create_sync_engine

# URL sync PostgreSQL pour compatibilité legacy
_SYNC_DB_URL = DATABASE_URL.replace("+asyncpg", "+psycopg2")
_sync_engine = None


def _obtenir_connexion():
    """Retourne une connexion PostgreSQL synchrone (compatibilité legacy)."""
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = _create_sync_engine(_SYNC_DB_URL, echo=False, pool_size=5)
    return _sync_engine.connect()


# ---------------------------------------------------------------------------
# Initialisation de la base (appelé par main.py au startup)
# ---------------------------------------------------------------------------

def initialiser_base():
    """
    Initialise la base de données PostgreSQL via Alembic.
    Crée les tables si nécessaire puis exécute les migrations.
    
    Détecte automatiquement si on est dans un event loop asyncio ou non.
    """
    import asyncio
    from app.db.queries import init_db as _async_init_db
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Pas de loop en cours → _sync()
        return _sync(_async_init_db())
    else:
        # Loop en cours (FastAPI) → on retourne la coroutine pour être awaitée
        # On ne peut pas faire _sync() ici, donc on lève une erreur
        # indiquant que l'appelant doit faire await
        raise RuntimeError(
            "initialiser_base() ne peut pas être appelée depuis un event loop asyncio. "
            "Utilisez 'await init_db()' depuis app.db.queries ou app.db.session."
        )


# ---------------------------------------------------------------------------
# Travaux (jobs) — wrappers sync
# ---------------------------------------------------------------------------

def creer_travail(
    type_travail: str,
    chemin_photo: Optional[str] = None,
    job_externe_id: Optional[str] = None,
    utilisateur_id: Optional[str] = None,
) -> str:
    return _sync(_async_creer_travail(type_travail, chemin_photo, job_externe_id, utilisateur_id))


def mettre_a_jour_travail(
    travail_id: str,
    statut: Optional[str] = None,
    chemin_resultat: Optional[str] = None,
    resultat_json: Optional[str] = None,
    message_erreur: Optional[str] = None,
    taille_original: Optional[int] = None,
    taille_resultat: Optional[int] = None,
) -> bool:
    return _sync(_async_mettre_a_jour_travail(travail_id, statut, chemin_resultat, resultat_json, message_erreur, taille_original, taille_resultat))


def obtenir_travail(travail_id: str) -> Optional[dict]:
    return _sync(_async_obtenir_travail(travail_id))


def obtenir_travail_par_job_externe(job_externe_id: str) -> Optional[dict]:
    return _sync(_async_obtenir_travail_par_job_externe(job_externe_id))


def lister_travaux_par_utilisateur(utilisateur_id: str, limite: int = 50) -> list[dict]:
    return _sync(_async_lister_travaux_par_utilisateur(utilisateur_id, limite))


def mettre_a_jour_job_externe_id(travail_id: str, job_externe_id: str) -> bool:
    return _sync(_async_mettre_a_jour_job_externe_id(travail_id, job_externe_id))


# ---------------------------------------------------------------------------
# Abonnements (Stripe) — wrappers sync
# ---------------------------------------------------------------------------

def creer_abonnement(
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    statut: str = "actif",
    plan: Optional[str] = None,
    email_utilisateur: Optional[str] = None,
    derniere_attribution: Optional[str] = None,
) -> str:
    return _sync(_async_creer_abonnement(
        stripe_customer_id, stripe_subscription_id, statut, plan, email_utilisateur, derniere_attribution))


def obtenir_abonnement(
    abonnement_id: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
) -> Optional[dict]:
    return _sync(_async_obtenir_abonnement(abonnement_id, stripe_customer_id, stripe_subscription_id))


def mettre_a_jour_abonnement(
    abonnement_id: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    statut: Optional[str] = None,
    plan: Optional[str] = None,
    email_utilisateur: Optional[str] = None,
) -> bool:
    return _sync(_async_mettre_a_jour_abonnement(
        abonnement_id, stripe_customer_id, stripe_subscription_id, statut, plan, email_utilisateur))


def mettre_a_jour_attribution_credits(stripe_subscription_id: str, date_iso: str) -> bool:
    return _sync(_async_mettre_a_jour_attribution_credits(stripe_subscription_id, date_iso))


# ---------------------------------------------------------------------------
# Utilisateurs (auth) — wrappers sync
# ---------------------------------------------------------------------------

def creer_utilisateur(email: str, password_hash: str) -> Optional[str]:
    return _sync(_async_creer_utilisateur(email, password_hash))


def obtenir_utilisateur_par_email(email: str) -> Optional[dict]:
    return _sync(_async_obtenir_utilisateur_par_email(email))


def obtenir_utilisateur_par_oauth(provider: str, provider_id: str) -> Optional[dict]:
    return _sync(_async_obtenir_utilisateur_par_oauth(provider, provider_id))


def creer_utilisateur_oauth(email: str, provider: str, provider_id: str) -> Optional[str]:
    return _sync(_async_creer_utilisateur_oauth(email, provider, provider_id))


def obtenir_utilisateur_par_id(utilisateur_id: str) -> Optional[dict]:
    return _sync(_async_obtenir_utilisateur_par_id(utilisateur_id))


def mettre_a_jour_derniere_connexion(utilisateur_id: str) -> bool:
    return _sync(_async_mettre_a_jour_derniere_connexion(utilisateur_id))


def mettre_a_jour_activite(utilisateur_id: str) -> bool:
    return _sync(_async_mettre_a_jour_activite(utilisateur_id))


def decrementer_essais(utilisateur_id: str) -> int:
    return _sync(_async_decrementer_essais(utilisateur_id))


def obtenir_essais_restants(utilisateur_id: str) -> Optional[dict]:
    return _sync(_async_obtenir_essais_restants(utilisateur_id))


def lister_essais_gratuits(utilisateur_id: str, limite: int = 20) -> list[dict]:
    return _sync(_async_lister_essais_gratuits(utilisateur_id, limite))


def enregistrer_essai(utilisateur_id: str, type_travail: str, travail_id: str) -> str:
    return _sync(_async_enregistrer_essai(utilisateur_id, type_travail, travail_id))


# ---------------------------------------------------------------------------
# Crédits — wrappers sync
# ---------------------------------------------------------------------------

def crediter_utilisateur(utilisateur_id: str, nombre: int) -> int:
    return _sync(_async_crediter_utilisateur(utilisateur_id, nombre))


def consommer_credit(utilisateur_id: str, type_operation: str, travail_id: str) -> dict:
    return _sync(_async_consommer_credit(utilisateur_id, type_operation, travail_id))


def enregistrer_achat_credits(utilisateur_id: str, stripe_session_id: str, nombre_credits: int, montant_euros: float) -> str:
    return _sync(_async_enregistrer_achat_credits(utilisateur_id, stripe_session_id, nombre_credits, montant_euros))


def obtenir_credits_restants(utilisateur_id: str) -> dict:
    return _sync(_async_obtenir_credits_restants(utilisateur_id))


def obtenir_plan_utilisateur(utilisateur_id: str) -> str:
    return _sync(_async_obtenir_plan_utilisateur(utilisateur_id))


def peut_animer(utilisateur_id: str) -> dict:
    return _sync(_async_peut_animer(utilisateur_id))


def enregistrer_animation(utilisateur_id: str) -> dict:
    return _sync(_async_enregistrer_animation(utilisateur_id))


def mettre_a_jour_plan_utilisateur(utilisateur_id: str, plan: str) -> bool:
    return _sync(_async_mettre_a_jour_plan_utilisateur(utilisateur_id, plan))


# ---------------------------------------------------------------------------
# Réinitialisation de mot de passe — wrappers sync
# ---------------------------------------------------------------------------

def creer_token_reinitialisation(utilisateur_id: str, token: str, duree_minutes: int = 30) -> str:
    return _sync(_async_creer_token_reinitialisation(utilisateur_id, token, duree_minutes))


def verifier_token_reinitialisation(token: str) -> Optional[dict]:
    return _sync(_async_verifier_token_reinitialisation(token))


def marquer_token_utilise(token: str) -> bool:
    return _sync(_async_marquer_token_utilise(token))


def changer_mot_de_passe(utilisateur_id: str, nouveau_hash: str) -> bool:
    return _sync(_async_changer_mot_de_passe(utilisateur_id, nouveau_hash))


# ---------------------------------------------------------------------------
# Audit logs — wrappers sync
# ---------------------------------------------------------------------------

def enregistrer_audit(
    evenement: str,
    email: Optional[str] = None,
    utilisateur_id: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    reussite: bool = True,
    detail: Optional[str] = None,
) -> str:
    return _sync(_async_enregistrer_audit(evenement, email, utilisateur_id, ip, user_agent, reussite, detail))


def lister_audit_logs(
    email: Optional[str] = None,
    evenement: Optional[str] = None,
    reussite: Optional[bool] = None,
    limite: int = 100,
    offset: int = 0,
) -> list[dict]:
    return _sync(_async_lister_audit_logs(email, evenement, reussite, limite, offset))


def compter_audit_logs(
    email: Optional[str] = None,
    evenement: Optional[str] = None,
    reussite: Optional[bool] = None,
) -> int:
    return _sync(_async_compter_audit_logs(email, evenement, reussite))


# ---------------------------------------------------------------------------
# Rétention & Préférences — wrappers sync (migration 12/05/2026)
# ---------------------------------------------------------------------------


def mettre_a_jour_retention(utilisateur_id: str, retention_jours: int) -> bool:
    return _sync(_async_mettre_a_jour_retention(utilisateur_id, retention_jours))


def obtenir_retention(utilisateur_id: str) -> int:
    return _sync(_async_obtenir_retention(utilisateur_id))


# ---------------------------------------------------------------------------
# Chemin animation & Suppression — wrappers sync (migration 12/05/2026)
# ---------------------------------------------------------------------------


def mettre_a_jour_chemin_animation(travail_id: str, chemin_animation: str) -> bool:
    return _sync(_async_mettre_a_jour_chemin_animation(travail_id, chemin_animation))


def supprimer_travail(travail_id: str) -> bool:
    return _sync(_async_supprimer_travail(travail_id))


def supprimer_tous_travaux_utilisateur(utilisateur_id: str) -> int:
    return _sync(_async_supprimer_tous_travaux_utilisateur(utilisateur_id))
