"""
Routes de l'API Flaskback Restore.

Endpoints :
- POST /api/analyze   : Analyser les défauts d'une photo
- POST /api/restore   : Restaurer une photo ancienne
- POST /api/animate   : Créer une animation D-ID
- GET  /api/animate/{id} : Suivre le statut d'une animation
- GET  /api/health    : Vérifier la santé du service
"""

import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, ImageEnhance, ImageFilter

from app.config import DID_API_KEY, GEMINI_API_KEY, UPLOAD_DIR
from app.db.database import (
    creer_travail,
    mettre_a_jour_travail,
    obtenir_travail,
    obtenir_travail_par_job_externe,
)
from app.models.schemas import (
    AnalyseReponse,
    AnimationReponse,
    AnimationRequete,
    ParametresRestauration,
    RestaurationReponse,
    SanteReponse,
    StatutAnimation,
    StatutAnimationReponse,
)
from app.services.did_service import creer_animation, verifier_statut_animation
from app.services.gemini_service import analyser_photo, obtenir_parametres_restauration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Taille maximale des uploads : 20 Mo
TAILLE_MAX_UPLOAD = 20 * 1024 * 1024

# Formats d'image acceptés
FORMATS_ACCEPTES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}


# ---------------------------------------------------------------------------
# Santé
# ---------------------------------------------------------------------------

@router.get("/health", response_model=SanteReponse)
async def sante():
    """
    Vérification de l'état du service.

    Retourne le statut de l'API et la disponibilité des services externes
    (Gemini et D-ID).
    """
    gemini_ok = bool(GEMINI_API_KEY and GEMINI_API_KEY != "placeholder")
    did_ok = bool(DID_API_KEY and DID_API_KEY != "DID_API_KEY_PLACEHOLDER")

    return SanteReponse(
        statut="OK",
        version="1.0.0",
        gemini_disponible=gemini_ok,
        did_disponible=did_ok,
    )


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalyseReponse)
async def analyser(fichier: UploadFile = File(...)):
    """
    Analyse une photo ancienne pour détecter ses défauts.

    L'image est envoyée à Gemini qui identifie rayures, décoloration,
    taches, déchirures, bruit et fournit des recommandations de restauration.

    Args:
        fichier: Le fichier image à analyser (JPEG, PNG, WebP, TIFF).

    Returns:
        Un rapport d'analyse complet en français.
    """
    # Validation
    if fichier.content_type and fichier.content_type not in FORMATS_ACCEPTES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non accepté : {fichier.content_type}. "
                   f"Formats acceptés : {', '.join(FORMATS_ACCEPTES)}",
        )

    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux ({len(contenu)} octets). "
                   f"Taille maximale : {TAILLE_MAX_UPLOAD} octets.",
        )

    # Sauvegarde du fichier
    nom_fichier = f"{uuid.uuid4()}_{fichier.filename or 'photo.jpg'}"
    chemin = UPLOAD_DIR / nom_fichier
    chemin.write_bytes(contenu)

    # Création du travail dans la base
    travail_id = creer_travail("analyse", chemin_photo=str(chemin))
    mettre_a_jour_travail(travail_id, statut="en_cours")

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
async def restaurer(fichier: UploadFile = File(...)):
    """
    Restaure une photo ancienne en utilisant l'IA Gemini et Pillow.

    Processus :
    1. La photo est d'abord analysée pour détecter ses défauts.
    2. Gemini détermine les paramètres de restauration optimaux.
    3. Pillow applique ces paramètres (luminosité, contraste, saturation,
       netteté, débruitage, correction colorimétrique).
    4. L'image restaurée est retournée.

    Args:
        fichier: Le fichier image à restaurer (JPEG, PNG, WebP, TIFF).

    Returns:
        L'analyse, les paramètres appliqués, et le chemin de l'image restaurée.
    """
    # Validation
    if fichier.content_type and fichier.content_type not in FORMATS_ACCEPTES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non accepté : {fichier.content_type}. "
                   f"Formats acceptés : {', '.join(FORMATS_ACCEPTES)}",
        )

    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux ({len(contenu)} octets). "
                   f"Taille maximale : {TAILLE_MAX_UPLOAD} octets.",
        )

    # Sauvegarde du fichier original
    nom_base = uuid.uuid4().hex
    nom_original = f"{nom_base}_{fichier.filename or 'photo.jpg'}"
    chemin_original = UPLOAD_DIR / nom_original
    chemin_original.write_bytes(contenu)

    # Création du travail
    travail_id = creer_travail("restauration", chemin_photo=str(chemin_original))
    mettre_a_jour_travail(travail_id, statut="en_cours")

    try:
        # Étape 1 : Analyse des défauts
        analyse = await analyser_photo(str(chemin_original))

        # Étape 2 : Paramètres de restauration
        params = await obtenir_parametres_restauration(str(chemin_original))

        # Étape 3 : Application avec Pillow
        nom_restaure = f"{nom_base}_restaure.jpg"
        chemin_restaure = UPLOAD_DIR / nom_restaure
        _appliquer_restauration_pillow(
            str(chemin_original),
            str(chemin_restaure),
            params,
        )

        # Succès
        resultat = RestaurationReponse(
            message="Photo restaurée avec succès !",
            analyse=analyse,
            parametres=params,
            url_image=f"/uploads/{nom_restaure}",
        )
        mettre_a_jour_travail(
            travail_id,
            statut="termine",
            chemin_resultat=str(chemin_restaure),
            resultat_json=json.dumps({
                "analyse": analyse.model_dump(),
                "parametres": params.model_dump(),
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
# Animation (D-ID)
# ---------------------------------------------------------------------------

@router.post("/animate", response_model=AnimationReponse)
async def animer(
    fichier: UploadFile = File(...),
    texte: str = Form("Bonjour ! Je suis un souvenir restauré."),
):
    """
    Crée une animation de portrait parlant (style Harry Potter) avec D-ID.

    La photo est sauvegardée localement puis envoyée à D-ID pour générer
    une vidéo où le visage s'anime et prononce le texte fourni.

    **Important** : Pour que D-ID puisse accéder à la photo, celle-ci doit
    être accessible via une URL publique. En développement, utilisez un
    service comme ngrok ou déployez le backend sur un serveur public.

    Args:
        fichier: La photo du visage à animer.
        texte: Le texte que le portrait va prononcer (français).

    Returns:
        L'identifiant du travail D-ID pour suivi ultérieur.
    """
    # Validation
    if fichier.content_type and fichier.content_type not in FORMATS_ACCEPTES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non accepté : {fichier.content_type}.",
        )

    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail="Fichier trop volumineux.",
        )

    # Sauvegarde
    nom_fichier = f"{uuid.uuid4().hex}_{fichier.filename or 'portrait.jpg'}"
    chemin = UPLOAD_DIR / nom_fichier
    chemin.write_bytes(contenu)

    # Création du travail
    travail_id = creer_travail("animation", chemin_photo=str(chemin))
    mettre_a_jour_travail(travail_id, statut="en_cours")

    try:
        # Construction de l'URL publique de la photo
        # En production, utilisez l'URL réelle de votre serveur
        url_photo = f"http://localhost:8000/uploads/{nom_fichier}"

        job_did = await creer_animation(url_photo, texte=texte)

        # Association du job D-ID au travail local
        mettre_a_jour_travail(
            travail_id,
            statut="en_cours",
            job_externe_id=job_did,
            resultat_json=json.dumps({"job_did": job_did}),
        )

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
async def statut_animation(job_id: str):
    """
    Vérifie le statut d'une animation D-ID.

    Interroge l'API D-ID pour connaître l'avancement d'une animation.
    Lorsque le statut est « done », l'URL de la vidéo est retournée.

    Args:
        job_id: L'identifiant du travail D-ID (retourné par POST /api/animate).

    Returns:
        Le statut actuel et l'URL de la vidéo si terminée.
    """
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
                mettre_a_jour_travail(
                    travail["id"],
                    statut="termine",
                    chemin_resultat=data.get("url_video"),
                    resultat_json=json.dumps(data),
                )
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
