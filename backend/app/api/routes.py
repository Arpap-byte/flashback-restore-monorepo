"""
Routes de l'API Flaskback Restore.

Endpoints :
- POST /api/analyze   : Analyser les défauts d'une photo
- POST /api/restore   : Restaurer une photo ancienne (non-bloquant via ARQ)
- POST /api/animate   : Créer une animation (non-bloquant via ARQ)
- GET  /api/animate/{id} : Suivre le statut d'une animation
- GET  /api/job/{job_id} : Statut d'un job ARQ (restauration/animation)
- GET  /api/health    : Vérifier la santé du service (IA, animation, DB, Stripe)
- GET  /api/stats     : Statistiques globales (protégé par X-Admin-Key)
"""

import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import magic
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from PIL import Image, ImageEnhance, ImageFilter

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job as ArqJob, JobStatus as ArqJobStatus

from app.config import GEMINI_API_KEY, STRIPE_API_KEY, ADMIN_API_KEY, UPLOAD_DIR, PUBLIC_BACKEND_URL, SITE_URL
from app.auth import creer_token_telechargement, exiger_utilisateur
from app.db.queries import (
    CREDITS_PAR_PLAN,
    compter_audit_logs,
    crediter_utilisateur,
    creer_abonnement,
    creer_travail,
    enregistrer_achat_credits,
    enregistrer_animation,
    lister_audit_logs,
    marquer_stripe_event_traite,
    mettre_a_jour_abonnement,
    mettre_a_jour_activite,
    mettre_a_jour_attribution_credits,
    mettre_a_jour_chemin_animation,
    mettre_a_jour_job_externe_id,
    mettre_a_jour_plan_utilisateur,
    mettre_a_jour_travail,
    obtenir_abonnement,
    obtenir_travail,
    obtenir_travail_par_job_externe,
    obtenir_utilisateur_par_email,
    stripe_event_deja_traite,
)
from app.services.credits import consommer_operation, peut_animer, peut_restaurer
from app.models.schemas import (
    AnalyseReponse,
    AnimationReponse,
    AnimationRequete,
    CheckoutReponse,
    CheckoutRequete,
    EtatAbonnement,
    ParametresRestauration,
    RestaurationReponse,
    SanteReponse,
    StatsReponse,
    StatutAnimation,
    StatutAnimationReponse,
    WebhookReponse,
)
from app.services.gemini_service import (
    analyser_photo,
    coloriser_photo,
    restaurer_photo_ia,
)
from app.services.stripe_service import (
    creer_session_paiement,
    creer_session_paiement_credits,
    obtenir_abonnement_stripe,
    traiter_webhook,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Grille tarifaire — résolutions et crédits
# ---------------------------------------------------------------------------

TARIF_RESTAURATION: dict[str, int] = {
    "720p": 1,
    "1080p": 2,
    "4k": 4,
}

TARIF_COLORISATION: dict[str, int] = {
    "720p": 1,
    "1080p": 1,
    "4k": 1,
}

TARIF_ANIMATION: dict[str, int] = {
    "720p": 10,
    "1080p": 20,
}

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Pool ARQ (connexion Redis) — initialisé paresseusement
# ---------------------------------------------------------------------------

_arq_pool = None
_arq_pool_lock = None  # sera initialisé si besoin


async def _get_arq_pool():
    """Retourne le pool ARQ connecté à Redis (singleton)."""
    global _arq_pool
    if _arq_pool is not None:
        return _arq_pool
    _arq_pool = await create_pool(RedisSettings(host='localhost', port=6379))
    return _arq_pool

# Taille maximale des uploads : 20 Mo
TAILLE_MAX_UPLOAD = 20 * 1024 * 1024

# Formats d'image acceptés (Content-Type)
FORMATS_ACCEPTES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}

# Types MIME vérifiés par magic bytes (validation de contenu réelle)
MAGIC_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/tiff'
}

# Signatures de fichiers image (magic numbers) — fallback si python-magic
# détecte un faux type (ex: application/json pour des images exotiques)
_SIGNATURES_IMAGE: dict[bytes, str] = {
    b'\xff\xd8\xff': 'image/jpeg',       # JPEG
    b'\x89PNG': 'image/png',             # PNG
    b'GIF8': 'image/gif',                # GIF
    b'RIFF': 'image/webp',               # WebP (vérification supplémentaire)
    b'MM\x00*': 'image/tiff',            # TIFF big-endian
    b'II*\x00': 'image/tiff',            # TIFF little-endian
}


def _valider_signature_image(contenu: bytes) -> Optional[str]:
    """Vérifie si les premiers octets correspondent à un format image connu.

    Retourne le type MIME si reconnu, None sinon.
    Fallback quand python-magic se trompe.
    """
    if len(contenu) < 8:
        return None
    for signature, mime in _SIGNATURES_IMAGE.items():
        if contenu.startswith(signature):
            # Vérification WebP : doit avoir 'WEBP' aux octets 8-11
            if signature == b'RIFF':
                if len(contenu) >= 12 and contenu[8:12] == b'WEBP':
                    return mime
                continue  # RIFF mais pas WebP → ne pas matcher
            return mime
    return None


def _valider_upload_par_contenu(contenu: bytes) -> bool:
    """Vérifie le vrai type MIME du fichier via magic bytes (python-magic).

    Fallback sur la signature binaire si python-magic se trompe.
    """
    detected = magic.from_buffer(contenu, mime=True)
    if detected in MAGIC_MIME_TYPES:
        return True

    # Fallback : python-magic peut se tromper (ex: application/json
    # pour une image). On vérifie la signature binaire directement.
    fallback_mime = _valider_signature_image(contenu)
    if fallback_mime is not None:
        logger.warning(
            f"python-magic a détecté '{detected}' mais la signature binaire "
            f"indique '{fallback_mime}' — accepté via fallback"
        )
        return True

    return False


def _valider_upload(fichier: UploadFile, contenu: bytes, nom_par_defaut: str = "photo.jpg") -> str:
    """
    Valide le type MIME et la taille d'un fichier uploadé, puis retourne
    un nom de fichier sécurisé.

    Effectue une double validation :
    1. Content-Type déclaré par le client (vérification rapide)
    2. Magic bytes du contenu réel (protection anti-MIME spoofing)

    Args:
        fichier: Le fichier uploadé depuis FastAPI.
        contenu: Les bytes du fichier (déjà lus).
        nom_par_defaut: Nom par défaut si fichier.filename est None.

    Returns:
        Un nom de fichier sécurisé à utiliser pour la sauvegarde.

    Raises:
        HTTPException(400): Si le format MIME ou la taille est invalide.
    """
    if fichier.content_type and fichier.content_type not in FORMATS_ACCEPTES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non accepté : {fichier.content_type}. "
                   f"Formats acceptés : {', '.join(FORMATS_ACCEPTES)}",
        )
    if len(contenu) > TAILLE_MAX_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux ({len(contenu)} octets). "
                   f"Taille maximale : {TAILLE_MAX_UPLOAD} octets.",
        )
    # Validation par magic bytes (protection anti-MIME spoofing)
    if not _valider_upload_par_contenu(contenu):
        detected = magic.from_buffer(contenu, mime=True)
        logger.warning(
            "Fichier rejeté — magic bytes: %s, signature binaire: %s, taille: %d, "
            "nom: %s, aperçu contenu: %s",
            detected,
            _valider_signature_image(contenu),
            len(contenu),
            fichier.filename or nom_par_defaut,
            contenu[:200],
        )
        if detected == "application/json":
            raise HTTPException(
                status_code=400,
                detail="Contenu JSON reçu au lieu d'une image. "
                       "Votre token d'accès a peut-être expiré — "
                       "veuillez rafraîchir la page et réessayer. "
                       f"Formats acceptés : {', '.join(MAGIC_MIME_TYPES)}",
            )
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier invalide détecté : {detected}. "
                   f"Formats acceptés : {', '.join(MAGIC_MIME_TYPES)}",
        )
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', fichier.filename or nom_par_defaut)[:80]
    return f"{uuid.uuid4().hex}_{safe_name}"

# URLs de redirection Stripe (frontend)
URL_SUCCES_STRIPE = f"{SITE_URL}/abonnement/succes"
URL_ANNULATION_STRIPE = f"{SITE_URL}/abonnement/annulation"


# ---------------------------------------------------------------------------
# Santé
# ---------------------------------------------------------------------------

@router.get("/health", response_model=SanteReponse)
async def sante(request: Request):
    """
    Vérification de l'état du service.

    Teste RÉELLEMENT la connectivité aux services externes :
    - IA de restauration : appel API pour lister les modèles (timeout 5s)
    - Animation : vérifie que la clé API est configurée
    - Base de données : exécute un SELECT 1 sur SQLite
    - Stripe : vérifie que la clé API est configurée
    """
    import httpx

    # --- Test Gemini : appel réel à l'API de listage des modèles ---
    gemini_ok = False
    if GEMINI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": GEMINI_API_KEY},
                )
                gemini_ok = response.status_code == 200
        except Exception as e:
            logger.warning(f"Test de connectivité Gemini échoué : {e}")

    # --- Test Base de données : SELECT 1 via SQLAlchemy async ---
    db_ok = False
    try:
        from app.db.session import async_session
        from sqlalchemy import text as _sa_text
        async with async_session() as session:
            await session.execute(_sa_text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.warning(f"Test de connectivité DB échoué : {e}")

    # --- Test Stripe : vérification simple de la présence de la clé ---
    stripe_ok = bool(STRIPE_API_KEY)

    # --- Test B2 : vérification du bucket via S3 API ---
    b2_ok = False
    try:
        from app.storage import b2_est_disponible
        b2_ok = b2_est_disponible()
    except Exception as e:
        logger.warning(f"Test de connectivité B2 échoué : {e}")

    return SanteReponse(
        statut="OK",
        version="1.0.0",
        gemini_disponible=gemini_ok,
        db_disponible=db_ok,
        stripe_disponible=stripe_ok,
        b2_disponible=b2_ok,
    )


# ---------------------------------------------------------------------------
# Statistiques (Admin)
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=StatsReponse)
async def statistiques(request: Request):
    """
    Retourne les statistiques globales de l'application.

    **Protégé par token admin** : nécessite l'en-tête X-Admin-Key.
    """
    # Vérification du token admin
    admin_key = request.headers.get("X-Admin-Key")
    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé. Token admin requis.")

    # Requêtes de statistiques
    nb_utilisateurs = nb_restaurations = nb_animations = 0
    try:
        from app.db.session import async_session
        from sqlalchemy import text as _sa_text
        async with async_session() as session:
            nb_utilisateurs = (await session.execute(_sa_text("SELECT COUNT(*) FROM utilisateurs"))).fetchone()[0]
            nb_restaurations = (await session.execute(_sa_text("SELECT COUNT(*) FROM travaux WHERE type = 'restauration'"))).fetchone()[0]
            nb_animations = (await session.execute(_sa_text("SELECT COUNT(*) FROM travaux WHERE type = 'animation'"))).fetchone()[0]
    except Exception as e:
        logger.exception(f"Erreur lors de la récupération des statistiques : {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la récupération des statistiques.",
        )

    return StatsReponse(
        nombre_total_utilisateurs=nb_utilisateurs,
        nombre_total_restaurations=nb_restaurations,
        nombre_total_animations=nb_animations,
    )


@router.get("/audit-logs")
async def consulter_audit_logs(
    request: Request,
    email: str = None,
    evenement: str = None,
    reussite: bool = None,
    limite: int = 50,
    offset: int = 0,
):
    """
    Retourne les logs d'audit de sécurité (authentification).

    **Protégé par token admin** : nécessite l'en-tête X-Admin-Key.

    Filtres optionnels :
    - email : filtrer par email d'utilisateur
    - evenement : filtrer par type (login, register, oauth_*, forgot_password, reset_password)
    - reussite : true = succès, false = échecs
    - limite / offset : pagination
    """
    admin_key = request.headers.get("X-Admin-Key")
    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé. Token admin requis.")

    logs = await lister_audit_logs(
        email=email,
        evenement=evenement,
        reussite=reussite,
        limite=min(limite, 200),
        offset=offset,
    )
    total = await compter_audit_logs(
        email=email,
        evenement=evenement,
        reussite=reussite,
    )
    return {
        "total": total,
        "limite": limite,
        "offset": offset,
        "logs": logs,
    }


# ---------------------------------------------------------------------------
# Nettoyage des uploads (Admin)
# ---------------------------------------------------------------------------

@router.post("/admin/cleanup")
async def declencher_nettoyage(request: Request):
    """
    Déclenche le nettoyage des travaux expirés.

    Pour chaque travail terminé/en erreur, vérifie si sa date de création
    dépasse la rétention configurée par son propriétaire (7j, 30j ou 90j),
    puis supprime les 3 fichiers (original, résultat, animation).

    **Protégé par token admin** : nécessite l'en-tête X-Admin-Key.
    """
    admin_key = request.headers.get("X-Admin-Key")
    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé. Token admin requis.")

    from app.services.cleanup import nettoyer_uploads
    resultat = await nettoyer_uploads()
    return resultat


# ---------------------------------------------------------------------------
# Dashboard Admin
# ---------------------------------------------------------------------------

@router.get("/admin/dashboard")
async def dashboard_admin(request: Request):
    """
    Retourne les métriques agrégées pour le dashboard administrateur.

    **Protégé par token admin** : nécessite l'en-tête X-Admin-Key.
    """
    admin_key = request.headers.get("X-Admin-Key")
    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    from app.db.session import async_session
    from sqlalchemy import text as _sa_text

    maintenant = datetime.now(timezone.utc)
    il_y_a_7j = maintenant - timedelta(days=7)
    il_y_a_30j = maintenant - timedelta(days=30)

    async with async_session() as session:
        # --- Utilisateurs ---
        total_utilisateurs = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM utilisateurs")
        )).fetchone()[0]

        actifs_7j = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM utilisateurs WHERE derniere_activite >= :seuil"),
            {"seuil": il_y_a_7j}
        )).fetchone()[0]

        actifs_30j = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM utilisateurs WHERE derniere_activite >= :seuil"),
            {"seuil": il_y_a_30j}
        )).fetchone()[0]

        par_plan_rows = (await session.execute(
            _sa_text("SELECT plan, COUNT(*) as nb FROM utilisateurs GROUP BY plan ORDER BY nb DESC")
        )).fetchall()

        # --- Travaux ---
        total_travaux = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM travaux")
        )).fetchone()[0]

        photos_stockees = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM travaux WHERE statut IN ('termine', 'erreur')")
        )).fetchone()[0]

        par_type_rows = (await session.execute(
            _sa_text("SELECT type, COUNT(*) as nb FROM travaux GROUP BY type ORDER BY nb DESC")
        )).fetchall()

        par_statut_rows = (await session.execute(
            _sa_text("SELECT statut, COUNT(*) as nb FROM travaux GROUP BY statut ORDER BY nb DESC")
        )).fetchall()

        # --- Stockage ---
        espace_rows = (await session.execute(
            _sa_text("""
                SELECT COALESCE(SUM(COALESCE(taille_original, 0)), 0)
                     + COALESCE(SUM(COALESCE(taille_resultat, 0)), 0)
                     as total_octets
                FROM travaux
                WHERE statut IN ('termine', 'erreur')
            """)
        )).fetchone()
        espace_total_octets = espace_rows[0] if espace_rows else 0

        top5_rows = (await session.execute(
            _sa_text("""
                SELECT u.email,
                       COALESCE(SUM(COALESCE(t.taille_original, 0)), 0)
                     + COALESCE(SUM(COALESCE(t.taille_resultat, 0)), 0) as espace_octets
                FROM travaux t
                JOIN utilisateurs u ON t.utilisateur_id = u.id
                WHERE t.statut IN ('termine', 'erreur')
                GROUP BY u.email
                ORDER BY espace_octets DESC
                LIMIT 5
            """)
        )).fetchall()

        # --- Crédits ---
        credits_rows = (await session.execute(
            _sa_text("""
                SELECT
                    COALESCE(SUM(credits), 0) as total_distribues,
                    COALESCE((SELECT SUM(credits_utilises) FROM consommation_credits), 0) as total_consommes
                FROM utilisateurs
            """)
        )).fetchone()

        credits_actifs = (await session.execute(
            _sa_text("SELECT COALESCE(SUM(credits), 0) FROM utilisateurs")
        )).fetchone()[0]

    return {
        "utilisateurs": {
            "total": total_utilisateurs,
            "actifs_7j": actifs_7j,
            "actifs_30j": actifs_30j,
            "par_plan": {row[0] or "inconnu": row[1] for row in par_plan_rows},
        },
        "travaux": {
            "total": total_travaux,
            "photos_stockees": photos_stockees,
            "par_type": {row[0]: row[1] for row in par_type_rows},
            "par_statut": {row[0]: row[1] for row in par_statut_rows},
        },
        "stockage": {
            "espace_total_octets": espace_total_octets,
            "espace_total_mb": round(espace_total_octets / (1024 * 1024), 2),
            "top5_utilisateurs": [
                {"email": row[0], "espace_mb": round(row[1] / (1024 * 1024), 2)}
                for row in top5_rows
            ],
        },
        "credits": {
            "total_distribues": credits_rows[0] if credits_rows else 0,
            "total_consommes": credits_rows[1] if credits_rows else 0,
            "credits_actifs": credits_actifs,
        },
    }


# ---------------------------------------------------------------------------
# Admin — Détails drill-down
# ---------------------------------------------------------------------------

@router.get("/admin/utilisateurs")
async def admin_liste_utilisateurs(
    request: Request,
    plan: Optional[str] = None,
    limite: int = 50,
):
    """
    Liste détaillée des utilisateurs pour le dashboard admin.

    **Protégé par token admin**.
    """
    admin_key = request.headers.get("X-Admin-Key")
    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    from app.db.session import async_session
    from sqlalchemy import text as _sa_text

    async with async_session() as session:
        if plan:
            rows = (await session.execute(
                _sa_text("""
                    SELECT u.id, u.email, u.plan, u.credits,
                           u.derniere_activite, u.cree_le, u.essais_restants,
                           COALESCE(c.credits_utilises, 0) as credits_utilises
                    FROM utilisateurs u
                    LEFT JOIN (
                        SELECT utilisateur_id, SUM(credits_utilises) as credits_utilises
                        FROM consommation_credits
                        GROUP BY utilisateur_id
                    ) c ON u.id = c.utilisateur_id
                    WHERE u.plan = :plan
                    ORDER BY u.cree_le DESC
                    LIMIT :limite
                """),
                {"plan": plan, "limite": limite}
            )).fetchall()
        else:
            rows = (await session.execute(
                _sa_text("""
                    SELECT u.id, u.email, u.plan, u.credits,
                           u.derniere_activite, u.cree_le, u.essais_restants,
                           COALESCE(c.credits_utilises, 0) as credits_utilises
                    FROM utilisateurs u
                    LEFT JOIN (
                        SELECT utilisateur_id, SUM(credits_utilises) as credits_utilises
                        FROM consommation_credits
                        GROUP BY utilisateur_id
                    ) c ON u.id = c.utilisateur_id
                    ORDER BY u.cree_le DESC
                    LIMIT :limite
                """),
                {"limite": limite}
            )).fetchall()

    return {
        "total": len(rows),
        "utilisateurs": [
            {
                "id": r[0],
                "email": r[1],
                "plan": r[2] or "gratuit",
                "credits": r[3] or 0,
                "derniere_activite": r[4].isoformat() if r[4] and hasattr(r[4], 'isoformat') else (r[4] or None),
                "cree_le": r[5].isoformat() if r[5] and hasattr(r[5], 'isoformat') else (r[5] or None),
                "essais_restants": r[6] or 0,
                "credits_utilises": r[7] if len(r) > 7 else 0,
            }
            for r in rows
        ]
    }


@router.get("/admin/travaux")
async def admin_liste_travaux(
    request: Request,
    type: Optional[str] = None,
    statut: Optional[str] = None,
    limite: int = 50,
):
    """
    Liste détaillée des travaux pour le dashboard admin.

    **Protégé par token admin**.
    Filtres optionnels : type (restauration, animation, colorisation, analyse),
    statut (termine, en_cours, erreur, cree).
    """
    admin_key = request.headers.get("X-Admin-Key")
    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    from app.db.session import async_session
    from sqlalchemy import text as _sa_text

    async with async_session() as session:
        query = """
            SELECT t.id, t.type, t.statut, t.cree_le, t.taille_original,
                   t.taille_resultat, t.message_erreur, u.email as user_email
            FROM travaux t
            LEFT JOIN utilisateurs u ON t.utilisateur_id = u.id
            WHERE 1=1
        """
        params = {"limite": limite}

        if type:
            query += " AND t.type = :type"
            params["type"] = type
        if statut:
            query += " AND t.statut = :statut"
            params["statut"] = statut

        query += " ORDER BY t.cree_le DESC LIMIT :limite"

        rows = (await session.execute(_sa_text(query), params)).fetchall()

    return {
        "total": len(rows),
        "travaux": [
            {
                "id": r[0],
                "type": r[1],
                "statut": r[2],
                "cree_le": r[3].isoformat() if r[3] and hasattr(r[3], 'isoformat') else (r[3] or None),
                "taille_original": r[4],
                "taille_resultat": r[5],
                "message_erreur": r[6],
                "email_utilisateur": r[7],
            }
            for r in rows
        ]
    }


@router.get("/admin/utilisateurs/{user_id}")
async def admin_detail_utilisateur(
    request: Request,
    user_id: str,
):
    """
    Détail complet d'un utilisateur : infos, travaux, stockage utilisé.

    **Protégé par token admin**.
    """
    admin_key = request.headers.get("X-Admin-Key")
    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")

    from app.db.session import async_session
    from sqlalchemy import text as _sa_text

    async with async_session() as session:
        # Infos utilisateur
        user_row = (await session.execute(
            _sa_text("""
                SELECT id, email, plan, credits, derniere_activite, cree_le,
                       essais_restants
                FROM utilisateurs WHERE id = :uid
            """),
            {"uid": user_id}
        )).fetchone()

        if not user_row:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")

        # Crédits consommés
        credits_consommes = (await session.execute(
            _sa_text("""
                SELECT COALESCE(SUM(credits_utilises), 0)
                FROM consommation_credits
                WHERE utilisateur_id = :uid
            """),
            {"uid": user_id}
        )).fetchone()[0]

        # Travaux : compteur par type et statut
        travaux_rows = (await session.execute(
            _sa_text("""
                SELECT type, statut, COUNT(*) as nb
                FROM travaux
                WHERE utilisateur_id = :uid
                GROUP BY type, statut
                ORDER BY nb DESC
            """),
            {"uid": user_id}
        )).fetchall()

        # Stockage
        stockage_row = (await session.execute(
            _sa_text("""
                SELECT
                    COALESCE(SUM(COALESCE(taille_original, 0)), 0) as stock_original,
                    COALESCE(SUM(COALESCE(taille_resultat, 0)), 0) as stock_resultat,
                    COUNT(*) as total_travaux,
                    COUNT(CASE WHEN type = 'restauration' THEN 1 END) as nb_photos,
                    COUNT(CASE WHEN type = 'animation' THEN 1 END) as nb_videos
                FROM travaux
                WHERE utilisateur_id = :uid AND statut = 'termine'
            """),
            {"uid": user_id}
        )).fetchone()

        # Derniers travaux
        derniers_rows = (await session.execute(
            _sa_text("""
                SELECT id, type, statut, cree_le, taille_original,
                       taille_resultat, message_erreur
                FROM travaux
                WHERE utilisateur_id = :uid
                ORDER BY cree_le DESC
                LIMIT 20
            """),
            {"uid": user_id}
        )).fetchall()

    stock_original = stockage_row[0] or 0
    stock_resultat = stockage_row[1] or 0

    return {
        "utilisateur": {
            "id": user_row[0],
            "email": user_row[1],
            "plan": user_row[2] or "gratuit",
            "credits": user_row[3] or 0,
            "credits_consommes": credits_consommes,
            "derniere_activite": user_row[4].isoformat() if user_row[4] and hasattr(user_row[4], 'isoformat') else (user_row[4] or None),
            "cree_le": user_row[5].isoformat() if user_row[5] and hasattr(user_row[5], 'isoformat') else (user_row[5] or None),
            "essais_restants": user_row[6] or 0,
        },
        "stockage": {
            "original_mb": round(stock_original / (1024 * 1024), 2),
            "resultat_mb": round(stock_resultat / (1024 * 1024), 2),
            "total_mb": round((stock_original + stock_resultat) / (1024 * 1024), 2),
            "nb_photos": stockage_row[3] or 0,
            "nb_videos": stockage_row[4] or 0,
            "total_travaux_termines": stockage_row[2] or 0,
        },
        "travaux_par_type": [
            {"type": r[0], "statut": r[1], "nb": r[2]}
            for r in travaux_rows
        ],
        "derniers_travaux": [
            {
                "id": r[0],
                "type": r[1],
                "statut": r[2],
                "cree_le": r[3].isoformat() if r[3] and hasattr(r[3], 'isoformat') else (r[3] or None),
                "taille_original": r[4],
                "taille_resultat": r[5],
                "message_erreur": r[6],
            }
            for r in derniers_rows
        ],
    }


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalyseReponse)
async def analyser(
    request: Request,
    fichier: UploadFile = File(...),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Analyse une photo ancienne pour détecter ses défauts.

    L'image est analysée par IA pour identifier rayures, décoloration,
    taches, déchirures, bruit et fournit des recommandations de restauration.

    Args:
        fichier: Le fichier image à analyser (JPEG, PNG, WebP, TIFF).

    Returns:
        Un rapport d'analyse complet en français.
    """
    # Validation et sauvegarde
    contenu = await fichier.read()
    nom_fichier = _valider_upload(fichier, contenu)
    chemin = UPLOAD_DIR / nom_fichier
    chemin.write_bytes(contenu)

    # Suivi dashboard admin
    await mettre_a_jour_activite(utilisateur["id"])

    # Création du travail dans la base
    travail_id = await creer_travail("analyse", chemin_photo=str(chemin), utilisateur_id=utilisateur["id"])
    await mettre_a_jour_travail(travail_id, statut="en_cours", taille_original=len(contenu))

    try:
        resultat = await analyser_photo(str(chemin))
        await mettre_a_jour_travail(
            travail_id,
            statut="termine",
            resultat_json=resultat.model_dump_json(),
        )
        return resultat
    except Exception as e:
        logger.exception(f"Erreur lors de l'analyse : {e}")
        await mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse : {str(e)}",
        )


# ---------------------------------------------------------------------------
# Restauration
# ---------------------------------------------------------------------------

@router.post("/restore")
async def restaurer(
    request: Request,
    fichier: UploadFile = File(...),
    coloriser: bool = Form(False),
    resolution: str = Form("720p"),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Restaure une photo ancienne en utilisant l'intelligence artificielle.

    **Non-bloquant** : le traitement est délégué à un worker ARQ.
    La réponse immédiate contient un job_id pour suivre la progression.

    Processus (exécuté par le worker) :
    1. La photo est analysée pour détecter ses défauts.
    2. L'IA restaure l'image.
    3. Si coloriser=True, l'image est colorisée.
    4. Le travail est mis à jour avec le résultat.

    **Authentification requise** : un crédit (ou 2 si colorisation) est consommé.

    Args:
        fichier: Le fichier image à restaurer (JPEG, PNG, WebP, TIFF).
        coloriser: Si True, applique une colorisation après restauration
                   (consomme 1 crédit supplémentaire).

    Returns:
        job_id pour suivre la progression + message de confirmation.
    """
    # Valider la résolution
    if resolution not in TARIF_RESTAURATION:
        raise HTTPException(status_code=400, detail=f"Résolution invalide : {resolution}. Options : 720p, 1080p, 4k")

    nb_credits_total = TARIF_RESTAURATION[resolution]
    if coloriser:
        nb_credits_total += TARIF_COLORISATION[resolution]

    # Vérifier les crédits AVANT de sauvegarder le fichier
    for i in range(nb_credits_total):
        peut, raison = await peut_restaurer(utilisateur["id"])
        if not peut:
            raise HTTPException(status_code=402, detail=raison)

    # Validation et sauvegarde
    contenu = await fichier.read()
    nom_original = _valider_upload(fichier, contenu)
    chemin_original = UPLOAD_DIR / nom_original
    chemin_original.write_bytes(contenu)

    # Upload vers B2 (stockage cloud redondant)
    try:
        from app.storage import uploader_bytes, generer_cle_distant, b2_est_disponible
        if b2_est_disponible():
            cle = generer_cle_distant("photos", nom_original, utilisateur["id"])
            uploader_bytes(contenu, cle, fichier.content_type or "image/jpeg")
    except Exception as e:
        logger.warning("Échec upload B2 (fallback local): %s", e)

    # Suivi dashboard admin
    await mettre_a_jour_activite(utilisateur["id"])

    # Création du travail
    travail_id = await creer_travail("restauration", chemin_photo=str(chemin_original), utilisateur_id=utilisateur["id"])
    await mettre_a_jour_travail(travail_id, statut="en_cours", taille_original=len(contenu))

    # Délégation au worker ARQ (non-bloquant) AVANT consommation des crédits
    # pour garantir l'atomicité : si l'enqueue échoue, aucun crédit n'est perdu.
    try:
        pool = await _get_arq_pool()
        job = await pool.enqueue_job(
            'restauration_job',
            utilisateur["id"],
            str(chemin_original),
            coloriser,
            travail_id,
            nb_credits_total,
            resolution,
        )
    except Exception as e:
        logger.exception(f"Erreur lors de l'envoi du job ARQ (restauration) : {e}")
        await mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=f"Service de traitement indisponible ({e})",
        )
        raise HTTPException(status_code=503, detail="Service de traitement indisponible. Aucun crédit débité.")

    # Consommation des crédits (seulement après enqueue réussie)
    for i in range(nb_credits_total):
        await consommer_operation(utilisateur["id"], "restauration", travail_id)

    # Stocker le job_id ARQ dans le travail pour le suivi
    await mettre_a_jour_travail(
        travail_id,
        resultat_json=json.dumps({"arq_job_id": job.job_id, "coloriser": coloriser, "resolution": resolution}),
    )
    return {
        "message": "Traitement de restauration en cours.",
        "job_id": job.job_id,
        "travail_id": travail_id,
    }


# ---------------------------------------------------------------------------
# Colorisation standalone
# ---------------------------------------------------------------------------

@router.post("/colorize", response_model=RestaurationReponse)
async def coloriser_standalone(
    request: Request,
    fichier: UploadFile = File(...),
    resolution: str = Form("720p"),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Colorise une photo déjà restaurée (ou toute photo N&B).

    **Authentification requise** : crédits selon la résolution.

    Args:
        fichier: La photo à coloriser (JPEG, PNG, WebP, TIFF).
        resolution: Qualité de sortie (720p, 1080p, 4k).

    Returns:
        L'URL de l'image colorisée et le nombre de crédits consommés.
    """
    # Valider la résolution
    if resolution not in TARIF_COLORISATION:
        raise HTTPException(status_code=400, detail=f"Résolution invalide : {resolution}. Options : 720p, 1080p, 4k")

    nb_credits = TARIF_COLORISATION[resolution]

    # Validation et sauvegarde
    contenu = await fichier.read()
    nom_original = _valider_upload(fichier, contenu)
    chemin_original = UPLOAD_DIR / nom_original
    chemin_original.write_bytes(contenu)

    # Upload vers B2 (stockage cloud redondant)
    try:
        from app.storage import uploader_bytes, generer_cle_distant, b2_est_disponible
        if b2_est_disponible():
            cle = generer_cle_distant("photos", nom_original, utilisateur["id"])
            uploader_bytes(contenu, cle, fichier.content_type or "image/jpeg")
    except Exception as e:
        logger.warning("Échec upload B2 (fallback local): %s", e)

    # Suivi dashboard admin
    await mettre_a_jour_activite(utilisateur["id"])

    nom_base = nom_original.split('_')[0]

    # Création du travail
    travail_id = await creer_travail("colorisation", chemin_photo=str(chemin_original), utilisateur_id=utilisateur["id"])
    await mettre_a_jour_travail(travail_id, statut="en_cours", taille_original=len(contenu))

    # Vérification des crédits
    for i in range(nb_credits):
        peut, raison = await peut_restaurer(utilisateur["id"])
        if not peut:
            await mettre_a_jour_travail(travail_id, statut="erreur", message_erreur=raison)
            raise HTTPException(status_code=402, detail=raison)
        await consommer_operation(utilisateur["id"], "colorisation", travail_id)

    try:
        nom_colorise = f"{nom_base}_colorized.jpg"
        chemin_colorise = UPLOAD_DIR / nom_colorise
        await coloriser_photo(str(chemin_original), str(chemin_colorise))

        resultat = RestaurationReponse(
            message="Photo colorisée avec succès !",
            analyse=None,  # type: ignore — pas d'analyse pour la colorisation standalone
            url_image=f"/uploads/{nom_colorise}",
            credits_consommes=nb_credits,
        )
        await mettre_a_jour_travail(
            travail_id,
            statut="termine",
            chemin_resultat=str(chemin_colorise),
            taille_resultat=chemin_colorise.stat().st_size,
            resultat_json=json.dumps({"colorise": True, "credits_consommes": nb_credits, "resolution": resolution}),
        )
        return resultat

    except Exception as e:
        logger.exception(f"Erreur lors de la colorisation : {e}")
        await mettre_a_jour_travail(travail_id, statut="erreur", message_erreur=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la colorisation : {str(e)}")


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------

@router.post("/animate")
async def animer(
    request: Request,
    fichier: UploadFile = File(...),
    comportement: str = Form("naturel"),
    resolution: str = Form("720p"),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Crée une animation faciale sans parole via Google Veo 3.1.

    **Non-bloquant** : le traitement est délégué à un worker ARQ.
    La réponse immédiate contient un job_id pour suivre la progression.

    **Authentification requise** : un crédit ou essai gratuit est consommé.

    Args:
        fichier: La photo du visage à animer.
        comportement: Type d'expression (« sourire », « rire », « respirer »,
                      « clin_oeil », « salut », « naturel »). Défaut: « naturel ».
        resolution: "720p" (défaut) ou "1080p".

    Returns:
        job_id pour suivre la progression + message de confirmation.
    """
    # Validation de la résolution
    if resolution not in ("720p", "1080p"):
        raise HTTPException(status_code=400, detail="Résolution invalide. Choisir '720p' ou '1080p'.")

    # Validation et sauvegarde
    contenu = await fichier.read()
    nom_fichier = _valider_upload(fichier, contenu, nom_par_defaut="portrait.jpg")
    chemin = UPLOAD_DIR / nom_fichier
    chemin.write_bytes(contenu)

    # Suivi dashboard admin
    await mettre_a_jour_activite(utilisateur["id"])

    # Création du travail
    travail_id = await creer_travail("animation", chemin_photo=str(chemin), utilisateur_id=utilisateur["id"])
    await mettre_a_jour_travail(travail_id, statut="en_cours", taille_original=len(contenu))

    # Vérification des crédits et de la limite d'animations par forfait (sans consommer)
    nb_credits_anim = TARIF_ANIMATION.get(resolution, 10)
    for i in range(nb_credits_anim):
        peut, raison = await peut_animer(utilisateur["id"])
        if not peut:
            await mettre_a_jour_travail(
                travail_id,
                statut="erreur",
                message_erreur=raison,
            )
            raise HTTPException(status_code=403, detail=raison)

    # Délégation au worker ARQ (non-bloquant) AVANT consommation
    # Atomicité : si l'enqueue échoue, aucun crédit n'est perdu.
    try:
        pool = await _get_arq_pool()
        job = await pool.enqueue_job(
            'animation_job',
            utilisateur["id"],
            str(chemin),
            comportement,
            travail_id,
            resolution,
        )
    except Exception as e:
        logger.exception(f"Erreur lors de l'envoi du job ARQ (animation) : {e}")
        await mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=f"Service de traitement indisponible ({e})",
        )
        raise HTTPException(status_code=503, detail="Service de traitement indisponible. Aucun crédit débité.")

    # Enregistrer l'animation (une seule fois, pas par crédit)
    await enregistrer_animation(utilisateur["id"])

    # Consommation des crédits (seulement après enqueue réussie)
    for i in range(nb_credits_anim):
        await consommer_operation(utilisateur["id"], "animation", travail_id)

    # Sauvegarder l'ID du job ARQ pour le suivi
    await mettre_a_jour_job_externe_id(travail_id, job.job_id)
    return {
        "message": "Traitement d'animation en cours.",
        "job_id": job.job_id,
        "travail_id": travail_id,
    }


@router.get("/animate/{job_id}", response_model=StatutAnimationReponse)
async def statut_animation(
    job_id: str,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    [DÉPRÉCIÉ] Vérifie le statut d'une animation via l'ID du job ARQ.

    **Préférez /api/animate/travail/{travail_id}** qui est plus fiable et
    ne dépend pas de l'ID de job ARQ (éphémère). Cet endpoint est conservé
    pour rétrocompatibilité.

    Interroge **la base de données locale** (le worker ARQ Veo met à jour
    le statut côté serveur). Aucun appel à l'API D-ID n'est effectué.

    Args:
        job_id: L'identifiant du job ARQ (retourné par POST /api/animate).

    Returns:
        Le statut actuel et l'URL de la vidéo si terminée.
    """
    # Chercher le travail par job_externe_id (ARQ job_id)
    travail = await obtenir_travail_par_job_externe(job_id)
    if travail is None:
        raise HTTPException(status_code=404, detail="Travail introuvable.")
    if travail.get("utilisateur_id") != utilisateur["id"]:
        raise HTTPException(status_code=403, detail="Ce travail ne vous appartient pas.")

    # Mapping statut DB → statut frontend (même logique que /animate/travail/{travail_id})
    statut_db = travail.get("statut", "cree")
    correspondance = {
        "cree": StatutAnimation.EN_ATTENTE,
        "en_cours": StatutAnimation.EN_COURS,
        "termine": StatutAnimation.TERMINE,
        "erreur": StatutAnimation.ERREUR,
    }
    statut_frontend = correspondance.get(statut_db, StatutAnimation.EN_ATTENTE)

    url_video = None
    if statut_frontend == StatutAnimation.TERMINE:
        chemin_local = travail.get("chemin_animation")
        if chemin_local:
            nom_fichier = Path(chemin_local).name
            url_video = f"/uploads/{nom_fichier}"
        else:
            url_video = travail.get("chemin_resultat")

    return StatutAnimationReponse(
        job_id=job_id,
        statut=statut_frontend,
        url_video=url_video,
        message=travail.get("message_erreur") if statut_frontend == StatutAnimation.ERREUR else None,
    )


@router.get("/animate/travail/{travail_id}")
async def statut_animation_par_travail(
    travail_id: str,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Vérifie le statut d'une animation directement depuis la base de données.

    Contrairement à /animate/{job_id}, cet endpoint ne fait PAS d'appel à
    le worker ARQ (qui gère le polling côté serveur).

    **Résilient à la fermeture du navigateur** : la vidéo est sauvegardée
    même si l'utilisateur quitte la page pendant le traitement.

    Args:
        travail_id: L'identifiant du travail (retourné par POST /api/animate).

    Returns:
        Le statut actuel et l'URL de la vidéo si terminée.
    """
    travail = await obtenir_travail(travail_id)
    if travail is None:
        raise HTTPException(status_code=404, detail="Travail introuvable.")
    if travail.get("utilisateur_id") != utilisateur["id"]:
        raise HTTPException(status_code=403, detail="Ce travail ne vous appartient pas.")

    # Mapping statut DB → statut frontend
    statut_db = travail.get("statut", "cree")
    correspondance = {
        "cree": StatutAnimation.EN_ATTENTE,
        "en_cours": StatutAnimation.EN_COURS,
        "termine": StatutAnimation.TERMINE,
        "erreur": StatutAnimation.ERREUR,
    }
    statut_frontend = correspondance.get(statut_db, StatutAnimation.EN_ATTENTE)

    # Progression estimée
    progression = {
        StatutAnimation.EN_ATTENTE: 15,
        StatutAnimation.EN_COURS: 50,
        StatutAnimation.TERMINE: 100,
        StatutAnimation.ERREUR: 0,
    }.get(statut_frontend, 0)

    url_video = None
    if statut_frontend == StatutAnimation.TERMINE:
        # Priorité : fichier local → URL D-ID → chemin_resultat
        chemin_local = travail.get("chemin_animation")
        if chemin_local:
            # Transformer chemin absolu en URL relative /uploads/...
            from pathlib import Path as _Path
            nom_fichier = _Path(chemin_local).name
            token_dl = creer_token_telechargement(utilisateur["id"])
            url_video = f"/uploads/{nom_fichier}?token={token_dl}"
        else:
            url_video = travail.get("chemin_resultat")

    return {
        "status": statut_frontend.value if hasattr(statut_frontend, 'value') else statut_frontend,
        "progress": progression,
        "url_video": url_video,
        "message": travail.get("message_erreur") if statut_frontend == StatutAnimation.ERREUR else None,
        "travail_id": travail_id,
    }


# ---------------------------------------------------------------------------
# Statut des jobs ARQ (restauration, animation)
# ---------------------------------------------------------------------------

@router.get("/job/{job_id}")
async def statut_job_arq(
    job_id: str,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Vérifie le statut d'un job ARQ (restauration ou animation).

    **Authentification requise** (le job_id étant opaque, l'auth est la seule
    protection — l'utilisateur doit connaître son job_id).

    Retourne :
    - statut: "en_attente" | "en_cours" | "termine" | "erreur" | "introuvable"
    - resultat: le résultat du job si terminé (optionnel)
    - message: message d'erreur si erreur (optionnel)
    """
    try:
        pool = await _get_arq_pool()
        arq_job = ArqJob(job_id, pool)
        arq_status = await arq_job.status()

        if arq_status == ArqJobStatus.not_found:
            return {
                "job_id": job_id,
                "statut": "introuvable",
                "message": "Job introuvable ou expiré.",
            }

        statut_map = {
            ArqJobStatus.queued: "en_attente",
            ArqJobStatus.in_progress: "en_cours",
            ArqJobStatus.complete: "termine",
        }
        statut = statut_map.get(arq_status, str(arq_status))

        response_data = {
            "job_id": job_id,
            "statut": statut,
        }

        if arq_status == ArqJobStatus.complete:
            try:
                resultat = await arq_job.result(timeout=0.5)
                response_data["resultat"] = resultat
            except Exception:
                response_data["resultat"] = None
        elif arq_status == ArqJobStatus.not_found:
            response_data["message"] = "Job introuvable ou expiré."

        return response_data

    except Exception as e:
        logger.exception(f"Erreur lors de la vérification du job ARQ {job_id} : {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la vérification du job : {str(e)}",
        )


# ---------------------------------------------------------------------------
# Stripe — Paiements et abonnements
# ---------------------------------------------------------------------------

@router.post("/stripe/create-checkout", response_model=CheckoutReponse)
async def creer_checkout(requete: CheckoutRequete):
    """
    Crée une session de paiement Stripe Checkout.

    Le client choisit un plan parmi « decouverte », « premium » ou « annuel ».
    Une session Stripe est créée et l'URL de paiement est retournée.

    Args:
        requete: Contient le plan choisi et l'email de l'utilisateur.

    Returns:
        L'URL de la session Checkout Stripe.
    """
    try:
        resultat = await creer_session_paiement(
            plan=requete.plan,
            email_utilisateur=requete.email_utilisateur,
            url_succes=URL_SUCCES_STRIPE,
            url_annulation=URL_ANNULATION_STRIPE,
        )
        return CheckoutReponse(
            checkout_url=resultat["checkout_url"],
            session_id=resultat["session_id"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur création checkout : {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la création de la session de paiement.",
        )


@router.post("/stripe/create-credit-checkout", response_model=CheckoutReponse)
async def creer_checkout_credits(requete: CheckoutRequete):
    """
    Crée une session de paiement Stripe Checkout pour acheter des crédits.

    Le client choisit un pack de crédits parmi « 30 », « 50 » ou « 110 ».
    Une session Stripe en mode paiement unique est créée.

    Args:
        requete: Contient le plan (30, 50, 110) et l'email de l'utilisateur.

    Returns:
        L'URL de la session Checkout Stripe.
    """
    try:
        resultat = await creer_session_paiement_credits(
            plan=requete.plan,
            email=requete.email_utilisateur,
            url_succes=URL_SUCCES_STRIPE,
            url_annulation=URL_ANNULATION_STRIPE,
        )
        return CheckoutReponse(
            checkout_url=resultat["checkout_url"],
            session_id=resultat["session_id"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur création checkout crédits : {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la création de la session de paiement crédits.",
        )


@router.post("/stripe/webhook", response_model=WebhookReponse)
async def webhook_stripe(request: Request):
    """
    Reçoit les événements webhook de Stripe.

    Traite les événements tels que :
    - checkout.session.completed : Paiement validé → création d'abonnement
    - customer.subscription.deleted : Abonnement résilié
    - customer.subscription.updated : Abonnement modifié
    - invoice.payment_failed : Échec de paiement

    Args:
        request: La requête HTTP entrante (corps brut + en-tête Stripe-Signature).

    Returns:
        Le type d'événement reçu et un message de confirmation.
    """
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(
            status_code=400,
            detail="En-tête « Stripe-Signature » manquant.",
        )

    corps = await request.body()

    try:
        resultat = await traiter_webhook(corps, signature)
    except ValueError:
        raise HTTPException(status_code=400, detail="Corps de webhook invalide.")
    except Exception as e:
        logger.exception(f"Erreur webhook : {e}")
        raise HTTPException(
            status_code=400,
            detail="Signature de webhook invalide.",
        )

    type_evenement = resultat["type"]
    donnees = resultat["data"]
    event_id = resultat.get("event_id", "")

    # --- Protection anti-doublon (idempotence des webhooks Stripe) ---
    if event_id and await stripe_event_deja_traite(event_id):
        logger.info(f"Webhook Stripe déjà traité, ignoré : event_id={event_id}")
        return WebhookReponse(
            type_evenement=type_evenement,
            message=f"Événement « {type_evenement} » déjà traité (idempotent).",
        )

    # --- Traitement selon le type d'événement ---

    if type_evenement == "checkout.session.completed":
        # Paiement réussi : vérifier si c'est un achat de crédits ou un abonnement
        metadata = donnees.get("metadata", {})

        if metadata.get("type") == "credits":
            # --- Achat de crédits (paiement unique) ---
            try:
                email = metadata.get("email")
                nb_credits = int(metadata.get("credits", 0))
                session_id = donnees.get("id")
                montant = (donnees.get("amount_total") or 0) / 100.0

                utilisateur = await obtenir_utilisateur_par_email(email) if email else None
                if utilisateur:
                    from app.db.session import async_session
                    async with async_session() as session:
                        async with session.begin():
                            await crediter_utilisateur(utilisateur["id"], nb_credits, session=session)
                            await enregistrer_achat_credits(
                                utilisateur["id"], session_id, nb_credits, montant, session=session
                            )
                    logger.info(
                        f"Crédits ajoutés : email={email}, credits={nb_credits}, "
                        f"montant={montant}€, session={session_id}"
                    )
                else:
                    logger.warning(
                        f"Utilisateur introuvable pour créditation webhook : "
                        f"email={email}, credits={nb_credits}"
                    )
            except Exception as e:
                logger.exception(f"Erreur créditation webhook : {e}")
        else:
            # --- Abonnement (subscription) ---
            try:
                plan = metadata.get("plan", "inconnu")
                email = metadata.get("email_utilisateur", "")
                stripe_customer_id = donnees.get("customer")
                stripe_subscription_id = donnees.get("subscription")
                maintenant = datetime.now(timezone.utc).isoformat()

                # Session unique pour l'atomicité abonnement + crédits + plan
                from app.db.session import async_session
                async with async_session() as session:
                    async with session.begin():
                        # Créer l'abonnement en base
                        await creer_abonnement(
                            stripe_customer_id=stripe_customer_id,
                            stripe_subscription_id=stripe_subscription_id,
                            statut="actif",
                            plan=plan,
                            email_utilisateur=email,
                            derniere_attribution=maintenant,
                            session=session,
                        )

                        # Créditer l'utilisateur avec l'allocation mensuelle
                        nb_credits = CREDITS_PAR_PLAN.get(plan, 0)
                        if nb_credits > 0 and email:
                            utilisateur = await obtenir_utilisateur_par_email(email)
                            if utilisateur:
                                await crediter_utilisateur(utilisateur["id"], nb_credits, session=session)
                                await mettre_a_jour_plan_utilisateur(utilisateur["id"], plan, session=session)
                                logger.info(
                                    f"Crédits d'abonnement ajoutés : email={email}, "
                                    f"plan={plan}, credits={nb_credits}, "
                                    f"subscription={stripe_subscription_id}"
                                )
                            else:
                                logger.warning(
                                    f"Utilisateur introuvable pour crédits abonnement : email={email}"
                                )
                        else:
                            logger.warning(f"Plan inconnu ou sans email : plan={plan}, email={email}")

                    # ← commit atomique à la sortie du session.begin()

                logger.info(
                    f"Abonnement créé : client={stripe_customer_id}, "
                    f"subscription={stripe_subscription_id}, plan={plan}"
                )
            except Exception as e:
                logger.exception(f"Erreur création abonnement en base : {e}")

    elif type_evenement == "invoice.paid":
        # --- Paiement de facture (renouvellement mensuel/annuel) ---
        try:
            stripe_subscription_id = donnees.get("subscription")
            if not stripe_subscription_id:
                logger.warning("invoice.paid sans subscription_id, ignoré")
            else:
                # Récupérer l'abonnement local
                abo = await obtenir_abonnement(stripe_subscription_id=stripe_subscription_id)
                if not abo:
                    logger.warning(
                        f"Abonnement introuvable pour invoice.paid : {stripe_subscription_id}"
                    )
                else:
                    plan = abo.get("plan", "")
                    email = abo.get("email_utilisateur", "")
                    derniere_attr = abo.get("derniere_attribution_credits")
                    maintenant = datetime.now(timezone.utc).isoformat()

                    nb_credits = CREDITS_PAR_PLAN.get(plan, 0)
                    if nb_credits > 0 and email:
                        utilisateur = await obtenir_utilisateur_par_email(email)
                        if utilisateur:
                            await crediter_utilisateur(utilisateur["id"], nb_credits)
                            await mettre_a_jour_plan_utilisateur(utilisateur["id"], plan)
                            await mettre_a_jour_attribution_credits(stripe_subscription_id, maintenant)
                            logger.info(
                                f"Crédits renouvelés (invoice.paid) : email={email}, "
                                f"plan={plan}, credits={nb_credits}, "
                                f"subscription={stripe_subscription_id}, "
                                f"dernière_attr={derniere_attr}"
                            )
                        else:
                            logger.warning(
                                f"Utilisateur introuvable pour renouvellement : email={email}"
                            )
                    else:
                        logger.info(
                            f"invoice.paid traité sans crédits : plan={plan}, "
                            f"subscription={stripe_subscription_id}"
                        )
        except Exception as e:
            logger.exception(f"Erreur traitement invoice.paid : {e}")

    elif type_evenement == "customer.subscription.deleted":
        # Abonnement résilié
        try:
            await mettre_a_jour_abonnement(
                stripe_subscription_id=donnees.get("id"),
                statut="resilie",
            )
            logger.info(f"Abonnement résilié : {donnees.get('id')}")
        except Exception as e:
            logger.exception(f"Erreur mise à jour abonnement : {e}")

    elif type_evenement == "customer.subscription.updated":
        # Abonnement modifié
        try:
            await mettre_a_jour_abonnement(
                stripe_subscription_id=donnees.get("id"),
                statut=donnees.get("status", "actif"),
            )
            logger.info(
                f"Abonnement mis à jour : {donnees.get('id')} → "
                f"statut={donnees.get('status')}"
            )
        except Exception as e:
            logger.exception(f"Erreur mise à jour abonnement : {e}")

    elif type_evenement == "invoice.payment_failed":
        # Échec de paiement
        logger.warning(
            f"Échec de paiement : client={donnees.get('customer')}"
        )
        try:
            await mettre_a_jour_abonnement(
                stripe_customer_id=donnees.get("customer"),
                statut="impaye",
            )
        except Exception as e:
            logger.exception(f"Erreur mise à jour abonnement impayé : {e}")

    # Marquer l'événement comme traité (idempotence)
    if event_id:
        await marquer_stripe_event_traite(event_id, type_evenement)

    return WebhookReponse(
        type_evenement=type_evenement,
        message=f"Événement « {type_evenement} » traité avec succès.",
    )


@router.get("/stripe/subscription/{customer_id}", response_model=EtatAbonnement)
async def consulter_abonnement(
    customer_id: str,
    request: Request,
):
    """
    Récupère l'état de l'abonnement d'un client Stripe.

    **Protégé par token admin** : nécessite l'en-tête X-Admin-Key.

    Args:
        customer_id: L'identifiant client Stripe (ex: « cus_xxxx »).

    Returns:
        Les informations détaillées de l'abonnement.
    """
    admin_key = request.headers.get("X-Admin-Key")
    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")
    try:
        abonnement = await obtenir_abonnement_stripe(customer_id)
        return EtatAbonnement(**abonnement)

    except Exception as e:
        logger.exception(f"Erreur consultation abonnement : {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la consultation de l'abonnement.",
        )
