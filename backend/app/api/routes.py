"""
Routes de l'API Flaskback Restore.

Endpoints :
- POST /api/analyze   : Analyser les défauts d'une photo
- POST /api/restore   : Restaurer une photo ancienne
- POST /api/animate   : Créer une animation
- GET  /api/animate/{id} : Suivre le statut d'une animation
- GET  /api/health    : Vérifier la santé du service (Gemini, D-ID, DB, Stripe)
- GET  /api/stats     : Statistiques globales (protégé par X-Admin-Key)
"""

import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from PIL import Image, ImageEnhance, ImageFilter

from app.config import DID_API_KEY, DID_BASE_URL, GEMINI_API_KEY, STRIPE_API_KEY, ADMIN_API_KEY, UPLOAD_DIR, PUBLIC_BACKEND_URL, SITE_URL
from app.auth import exiger_utilisateur
from app.db.database import (
    CREDITS_PAR_PLAN,
    compter_audit_logs,
    crediter_utilisateur,
    creer_abonnement,
    creer_travail,
    enregistrer_achat_credits,
    lister_audit_logs,
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
)
from app.services.credits import consommer_operation, peut_animer, peut_restaurer
from app.limiter import limiter
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
from app.services.did_service import creer_animation, verifier_statut_animation
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

router = APIRouter(prefix="/api")

# Taille maximale des uploads : 20 Mo
TAILLE_MAX_UPLOAD = 20 * 1024 * 1024

# Formats d'image acceptés
FORMATS_ACCEPTES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}


def _valider_upload(fichier: UploadFile, contenu: bytes, nom_par_defaut: str = "photo.jpg") -> str:
    """
    Valide le type MIME et la taille d'un fichier uploadé, puis retourne
    un nom de fichier sécurisé.

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
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', fichier.filename or nom_par_defaut)[:80]
    return f"{uuid.uuid4().hex}_{safe_name}"

# URLs de redirection Stripe (frontend)
URL_SUCCES_STRIPE = f"{SITE_URL}/abonnement/succes"
URL_ANNULATION_STRIPE = f"{SITE_URL}/abonnement/annulation"


# ---------------------------------------------------------------------------
# Santé
# ---------------------------------------------------------------------------

@router.get("/health", response_model=SanteReponse)
@limiter.limit("10/minute")
async def sante(request: Request):
    """
    Vérification de l'état du service.

    Teste RÉELLEMENT la connectivité aux services externes :
    - Gemini : appel API pour lister les modèles (timeout 5s)
    - D-ID : vérifie que la clé API est configurée
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

    # --- Test D-ID : vérification simple de la présence de la clé ---
    did_ok = bool(DID_API_KEY)

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

    return SanteReponse(
        statut="OK",
        version="1.0.0",
        gemini_disponible=gemini_ok,
        did_disponible=did_ok,
        db_disponible=db_ok,
        stripe_disponible=stripe_ok,
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

    logs = lister_audit_logs(
        email=email,
        evenement=evenement,
        reussite=reussite,
        limite=min(limite, 200),
        offset=offset,
    )
    total = compter_audit_logs(
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
    resultat = nettoyer_uploads()
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
# Analyse
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalyseReponse)
@limiter.limit("10/minute")
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
    mettre_a_jour_activite(utilisateur["id"])

    # Création du travail dans la base
    travail_id = creer_travail("analyse", chemin_photo=str(chemin), utilisateur_id=utilisateur["id"])
    mettre_a_jour_travail(travail_id, statut="en_cours", taille_original=len(contenu))

    try:
        resultat = await analyser_photo(str(chemin))
        mettre_a_jour_travail(
            travail_id,
            statut="termine",
            resultat_json=resultat.model_dump_json(),
        )
        return resultat
    except Exception as e:
        logger.exception(f"Erreur lors de l'analyse : {e}")
        mettre_a_jour_travail(
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

def _appliquer_restauration_pillow(
    chemin_source: str,
    chemin_destination: str,
    params: ParametresRestauration,
) -> None:
    """
    Applique les paramètres de restauration à une image avec Pillow.

    Étapes :
    1. Ajustement de la luminosité
    2. Ajustement du contraste
    3. Ajustement de la saturation
    4. Ajustement de la netteté (filtre unsharp mask)
    5. Débruitage (filtre median)
    6. Correction des canaux de couleur (rouge, vert, bleu)
    """
    image = Image.open(chemin_source).convert("RGB")
    logger.info(
        f"Restauration de {chemin_source} — "
        f"taille={image.size}, params={params.model_dump()}"
    )

    # 1. Luminosité
    if params.luminosite != 1.0:
        ameliorateur = ImageEnhance.Brightness(image)
        image = ameliorateur.enhance(params.luminosite)

    # 2. Contraste
    if params.contraste != 1.0:
        ameliorateur = ImageEnhance.Contrast(image)
        image = ameliorateur.enhance(params.contraste)

    # 3. Saturation
    if params.saturation != 1.0:
        ameliorateur = ImageEnhance.Color(image)
        image = ameliorateur.enhance(params.saturation)

    # 4. Netteté (unsharp mask ou sharpen)
    if params.nettete > 1.0:
        ameliorateur = ImageEnhance.Sharpness(image)
        image = ameliorateur.enhance(params.nettete)
    elif params.nettete < 1.0:
        # Flou léger si nettete < 1
        rayon = int((1.0 - params.nettete) * 2)
        image = image.filter(ImageFilter.GaussianBlur(radius=max(1, rayon)))

    # 5. Débruitage (filtre médian)
    if params.debruitage > 0.1:
        # Taille du kernel : 1, 3 ou 5 selon l'intensité
        taille = 3 if params.debruitage < 0.5 else 5
        image = image.filter(ImageFilter.MedianFilter(size=taille))

    # 6. Correction des canaux de couleur
    if (
        params.correction_rouge != 1.0
        or params.correction_vert != 1.0
        or params.correction_bleu != 1.0
    ):
        r, g, b = image.split()
        r = r.point(lambda p: min(255, int(p * params.correction_rouge)))
        g = g.point(lambda p: min(255, int(p * params.correction_vert)))
        b = b.point(lambda p: min(255, int(p * params.correction_bleu)))
        image = Image.merge("RGB", (r, g, b))

    # Sauvegarde
    image.save(chemin_destination, quality=95)
    logger.info(f"Image restaurée sauvegardée : {chemin_destination}")


@router.post("/restore", response_model=RestaurationReponse)
@limiter.limit("10/minute")
async def restaurer(
    request: Request,
    fichier: UploadFile = File(...),
    coloriser: bool = Form(False),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Restaure une photo ancienne en utilisant l'intelligence artificielle.

    Processus :
    1. La photo est d'abord analysée pour détecter ses défauts.
    2. L'IA détermine les paramètres de restauration optimaux.
    3. Pillow applique ces paramètres (luminosité, contraste, saturation,
       netteté, débruitage, correction colorimétrique).
    4. Si coloriser=True, l'image est colorisée (Gemini avec fallback Pillow).
    5. L'image restaurée (et éventuellement colorisée) est retournée.

    **Authentification requise** : un crédit (ou 2 si colorisation) est consommé.

    Args:
        fichier: Le fichier image à restaurer (JPEG, PNG, WebP, TIFF).
        coloriser: Si True, applique une colorisation après restauration
                   (consomme 1 crédit supplémentaire).

    Returns:
        L'analyse, les paramètres appliqués, le chemin de l'image finale,
        et le nombre de crédits consommés.
    """
    nb_credits_total = 1  # restauration de base = 1 crédit
    if coloriser:
        nb_credits_total = 2

    # Vérifier les crédits AVANT de sauvegarder le fichier
    for i in range(nb_credits_total):
        peut, raison = peut_restaurer(utilisateur["id"])
        if not peut:
            raise HTTPException(status_code=402, detail=raison)

    # Validation et sauvegarde
    contenu = await fichier.read()
    nom_original = _valider_upload(fichier, contenu)
    chemin_original = UPLOAD_DIR / nom_original
    chemin_original.write_bytes(contenu)

    # Suivi dashboard admin
    mettre_a_jour_activite(utilisateur["id"])

    # Base du nom pour fichiers dérivés (UUID)
    nom_base = nom_original.split('_')[0]

    # Création du travail
    travail_id = creer_travail("restauration", chemin_photo=str(chemin_original), utilisateur_id=utilisateur["id"])
    mettre_a_jour_travail(travail_id, statut="en_cours", taille_original=len(contenu))

    # Consommation des crédits (déjà vérifiés avant la sauvegarde du fichier)
    for i in range(nb_credits_total):
        consommer_operation(utilisateur["id"], "restauration", travail_id)

    try:
        # Étape 1 : Analyse des défauts
        analyse = await analyser_photo(str(chemin_original))

        # Étape 2 : Restauration IA (Gemini Image Model)
        nom_restaure = f"{nom_base}_restaure.jpg"
        chemin_restaure = UPLOAD_DIR / nom_restaure
        await restaurer_photo_ia(str(chemin_original), str(chemin_restaure))

        # Étape 4 : Colorisation (optionnelle)
        url_image = f"/uploads/{nom_restaure}"
        if coloriser:
            nom_colorise = f"{nom_base}_colorized.jpg"
            chemin_colorise = UPLOAD_DIR / nom_colorise
            await coloriser_photo(str(chemin_restaure), str(chemin_colorise))
            url_image = f"/uploads/{nom_colorise}"
            chemin_restaure = chemin_colorise  # pour le résultat final

        # Succès
        resultat = RestaurationReponse(
            message="Photo restaurée avec succès !"
                    + (" (colorisée)" if coloriser else ""),
            analyse=analyse,
            url_image=url_image,
            credits_consommes=nb_credits_total,
        )
        mettre_a_jour_travail(
            travail_id,
            statut="termine",
            chemin_resultat=str(chemin_restaure),
            taille_resultat=chemin_restaure.stat().st_size,
            resultat_json=json.dumps({
                "analyse": analyse.model_dump(),
                "colorise": coloriser,
                "credits_consommes": nb_credits_total,
            }),
        )
        return resultat

    except Exception as e:
        logger.exception(f"Erreur lors de la restauration : {e}")
        mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la restauration : {str(e)}",
        )


# ---------------------------------------------------------------------------
# Colorisation standalone
# ---------------------------------------------------------------------------

@router.post("/colorize", response_model=RestaurationReponse)
@limiter.limit("5/minute")
async def coloriser_standalone(
    request: Request,
    fichier: UploadFile = File(...),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Colorise une photo déjà restaurée (ou toute photo N&B).

    **Authentification requise** : 1 crédit est consommé.

    Args:
        fichier: La photo à coloriser (JPEG, PNG, WebP, TIFF).

    Returns:
        L'URL de l'image colorisée et le nombre de crédits consommés.
    """
    # Validation et sauvegarde
    contenu = await fichier.read()
    nom_original = _valider_upload(fichier, contenu)
    chemin_original = UPLOAD_DIR / nom_original
    chemin_original.write_bytes(contenu)

    # Suivi dashboard admin
    mettre_a_jour_activite(utilisateur["id"])

    nom_base = nom_original.split('_')[0]

    # Création du travail
    travail_id = creer_travail("colorisation", chemin_photo=str(chemin_original), utilisateur_id=utilisateur["id"])
    mettre_a_jour_travail(travail_id, statut="en_cours", taille_original=len(contenu))

    # Vérification des crédits
    peut, raison = peut_restaurer(utilisateur["id"])
    if not peut:
        mettre_a_jour_travail(travail_id, statut="erreur", message_erreur=raison)
        raise HTTPException(status_code=402, detail=raison)
    consommer_operation(utilisateur["id"], "colorisation", travail_id)

    try:
        nom_colorise = f"{nom_base}_colorized.jpg"
        chemin_colorise = UPLOAD_DIR / nom_colorise
        await coloriser_photo(str(chemin_original), str(chemin_colorise))

        resultat = RestaurationReponse(
            message="Photo colorisée avec succès !",
            analyse=None,  # type: ignore — pas d'analyse pour la colorisation standalone
            url_image=f"/uploads/{nom_colorise}",
            credits_consommes=1,
        )
        mettre_a_jour_travail(
            travail_id,
            statut="termine",
            chemin_resultat=str(chemin_colorise),
            taille_resultat=chemin_colorise.stat().st_size,
            resultat_json=json.dumps({"colorise": True, "credits_consommes": 1}),
        )
        return resultat

    except Exception as e:
        logger.exception(f"Erreur lors de la colorisation : {e}")
        mettre_a_jour_travail(travail_id, statut="erreur", message_erreur=str(e))
        raise HTTPException(status_code=500, detail=f"Erreur lors de la colorisation : {str(e)}")


# ---------------------------------------------------------------------------
# Animation (D-ID)
# ---------------------------------------------------------------------------

@router.post("/animate", response_model=AnimationReponse)
@limiter.limit("10/minute")
async def animer(
    request: Request,
    fichier: UploadFile = File(...),
    texte: str = Form("Bonjour ! Je suis un souvenir restauré."),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Crée une animation de portrait parlant (style Harry Potter).

    La photo est sauvegardée localement puis envoyée au service d'animation pour générer
    une vidéo où le visage s'anime et prononce le texte fourni.

    **Authentification requise** : un crédit ou essai gratuit est consommé.

    **Important** : Pour que le service d'animation puisse accéder à la photo, celle-ci doit
    être accessible via une URL publique. En développement, utilisez un
    service comme ngrok ou déployez le backend sur un serveur public.

    Args:
        fichier: La photo du visage à animer.
        texte: Le texte que le portrait va prononcer (français).

    Returns:
        L'identifiant du travail d'animation pour suivi ultérieur.
    """
    # Validation et sauvegarde
    contenu = await fichier.read()
    nom_fichier = _valider_upload(fichier, contenu, nom_par_defaut="portrait.jpg")
    chemin = UPLOAD_DIR / nom_fichier
    chemin.write_bytes(contenu)

    # Suivi dashboard admin
    mettre_a_jour_activite(utilisateur["id"])

    # Création du travail
    travail_id = creer_travail("animation", chemin_photo=str(chemin), utilisateur_id=utilisateur["id"])
    mettre_a_jour_travail(travail_id, statut="en_cours", taille_original=len(contenu))

    # Vérification des crédits et de la limite d'animations par forfait
    peut, raison = peut_animer(utilisateur["id"])
    if not peut:
        mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=raison,
        )
        raise HTTPException(status_code=403, detail=raison)

    # Consommer le crédit/essai (et incrémenter le compteur d'animations)
    consommer_operation(utilisateur["id"], "animation", travail_id)

    try:
        # Construction de l'URL publique de la photo
        # En production, utilisez l'URL réelle de votre serveur
        url_photo = f"{PUBLIC_BACKEND_URL}/uploads/{nom_fichier}"

        job_did = await creer_animation(url_photo, texte=texte)

        # Association du job D-ID au travail local
        # job_externe_id is stored in résultat_json and updated via a direct SQL call
        mettre_a_jour_travail(
            travail_id,
            statut="en_cours",
            resultat_json=json.dumps({"job_did": job_did}),
        )
        # Also update the job_externe_id column separately
        mettre_a_jour_job_externe_id(travail_id, job_did)

        return AnimationReponse(
            message="Animation créée avec succès. Vous pouvez suivre sa progression.",
            job_id=job_did,
        )

    except Exception as e:
        logger.exception(f"Erreur lors de la création d'animation : {e}")
        mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création d'animation : {str(e)}",
        )


@router.get("/animate/{job_id}", response_model=StatutAnimationReponse)
async def statut_animation(
    job_id: str,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Vérifie le statut d'une animation.

    **Authentification requise** : l'utilisateur doit être propriétaire du travail.

    Interroge le service d'animation pour connaître l'avancement d'une animation.
    Lorsque le statut est « done », l'URL de la vidéo est retournée.

    Args:
        job_id: L'identifiant du travail d'animation (retourné par POST /api/animate).

    Returns:
        Le statut actuel et l'URL de la vidéo si terminée.
    """
    # Vérifier que le job appartient à l'utilisateur
    travail = obtenir_travail_par_job_externe(job_id)
    if travail is None:
        raise HTTPException(status_code=404, detail="Travail introuvable.")
    if travail.get("utilisateur_id") != utilisateur["id"]:
        raise HTTPException(status_code=403, detail="Ce travail ne vous appartient pas.")
    try:
        data = await verifier_statut_animation(job_id)

        # Correspondance des statuts D-ID vers nos statuts
        correspondance_statut = {
            "created": StatutAnimation.EN_ATTENTE,
            "started": StatutAnimation.EN_COURS,
            "processing": StatutAnimation.EN_COURS,
            "done": StatutAnimation.TERMINE,
            "error": StatutAnimation.ERREUR,
        }
        statut_interne = correspondance_statut.get(
            data["statut"], StatutAnimation.EN_ATTENTE
        )

        # Mise à jour du travail local
        travail = obtenir_travail_par_job_externe(job_id)
        if travail:
            if statut_interne == StatutAnimation.TERMINE:
                url_video = data.get("url_video")
                mettre_a_jour_travail(
                    travail["id"],
                    statut="termine",
                    chemin_resultat=url_video,
                    resultat_json=json.dumps(data),
                )
                # Sauvegarder aussi dans chemin_animation pour l'historique
                if url_video:
                    mettre_a_jour_chemin_animation(travail["id"], url_video)
            elif statut_interne == StatutAnimation.ERREUR:
                mettre_a_jour_travail(
                    travail["id"],
                    statut="erreur",
                    message_erreur=data.get("message", "Erreur inconnue"),
                )

        return StatutAnimationReponse(
            job_id=job_id,
            statut=statut_interne,
            url_video=data.get("url_video"),
            message=data.get("message"),
        )

    except Exception as e:
        logger.exception(f"Erreur lors du suivi d'animation : {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du suivi d'animation : {str(e)}",
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

                utilisateur = obtenir_utilisateur_par_email(email) if email else None
                if utilisateur:
                    crediter_utilisateur(utilisateur["id"], nb_credits)
                    enregistrer_achat_credits(
                        utilisateur["id"], session_id, nb_credits, montant
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

                # Créer l'abonnement en base avec le plan et l'email
                creer_abonnement(
                    stripe_customer_id=stripe_customer_id,
                    stripe_subscription_id=stripe_subscription_id,
                    statut="actif",
                    plan=plan,
                    email_utilisateur=email,
                    derniere_attribution=maintenant,
                )

                # Créditer l'utilisateur avec l'allocation mensuelle
                nb_credits = CREDITS_PAR_PLAN.get(plan, 0)
                if nb_credits > 0 and email:
                    utilisateur = obtenir_utilisateur_par_email(email)
                    if utilisateur:
                        crediter_utilisateur(utilisateur["id"], nb_credits)
                        mettre_a_jour_plan_utilisateur(utilisateur["id"], plan)
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
                abo = obtenir_abonnement(stripe_subscription_id=stripe_subscription_id)
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
                        utilisateur = obtenir_utilisateur_par_email(email)
                        if utilisateur:
                            crediter_utilisateur(utilisateur["id"], nb_credits)
                            mettre_a_jour_plan_utilisateur(utilisateur["id"], plan)
                            mettre_a_jour_attribution_credits(stripe_subscription_id, maintenant)
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
            mettre_a_jour_abonnement(
                stripe_subscription_id=donnees.get("id"),
                statut="resilie",
            )
            logger.info(f"Abonnement résilié : {donnees.get('id')}")
        except Exception as e:
            logger.exception(f"Erreur mise à jour abonnement : {e}")

    elif type_evenement == "customer.subscription.updated":
        # Abonnement modifié
        try:
            mettre_a_jour_abonnement(
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
            mettre_a_jour_abonnement(
                stripe_customer_id=donnees.get("customer"),
                statut="impaye",
            )
        except Exception as e:
            logger.exception(f"Erreur mise à jour abonnement impayé : {e}")

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
