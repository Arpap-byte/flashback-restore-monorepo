"""
Worker ARQ pour les traitements longs (restauration IA, animation D-ID).

Exécuté indépendamment du serveur HTTP via :
    arq app.worker.WorkerSettings

Les jobs sont déposés dans Redis par les routes FastAPI et exécutés
de façon asynchrone par le worker, libérant ainsi les workers HTTP.
"""

import json
import logging
from pathlib import Path

from arq.connections import RedisSettings
from arq import create_pool

from app.config import DID_BASE_URL, GEMINI_API_KEY, GEMINI_MODEL, PUBLIC_BACKEND_URL, UPLOAD_DIR
from app.db.queries import (
    mettre_a_jour_travail,
    mettre_a_jour_job_externe_id,
    mettre_a_jour_chemin_animation,
)
from app.models.schemas import AnalyseReponse, RestaurationReponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job : Restauration IA (analyse + restauration + colorisation optionnelle)
# ---------------------------------------------------------------------------

async def restauration_job(
    ctx: dict,
    utilisateur_id: int,
    chemin_original: str,
    coloriser: bool,
    travail_id: int,
    nb_credits_total: int,
) -> dict:
    """
    Exécute le pipeline complet de restauration dans le worker ARQ.

    Étapes :
    1. Analyse des défauts (Gemini)
    2. Restauration IA (Gemini Image Model)
    3. Colorisation optionnelle (Gemini ou Pillow fallback)
    4. Mise à jour du travail en base (statut + résultat)

    Returns:
        dict avec les clés : message, url_image, credits_consommes
    """
    from app.services.gemini_service import (
        analyser_photo,
        restaurer_photo_ia,
        coloriser_photo,
    )

    chemin_original_path = Path(chemin_original)
    nom_base = chemin_original_path.name.split('_')[0]

    logger.info(
        f"[ARQ] Démarrage restauration — travail_id={travail_id}, "
        f"fichier={chemin_original}, coloriser={coloriser}"
    )

    try:
        # Étape 1 : Analyse des défauts
        analyse = await analyser_photo(chemin_original)

        # Étape 2 : Restauration IA
        nom_restaure = f"{nom_base}_restaure.jpg"
        chemin_restaure = UPLOAD_DIR / nom_restaure
        await restaurer_photo_ia(chemin_original, str(chemin_restaure))

        url_image = f"/uploads/{nom_restaure}"
        chemin_final = chemin_restaure

        if coloriser:
            # Sauvegarder la version restaurée comme entrée séparée dans l'historique
            await mettre_a_jour_travail(
                travail_id,
                statut="termine",
                chemin_resultat=str(chemin_restaure),
                taille_resultat=chemin_restaure.stat().st_size,
                resultat_json=json.dumps({
                    "analyse": analyse.model_dump(),
                    "colorise": False,
                    "credits_consommes": 1,
                    "etape": "restauration",
                }),
            )

            # Créer un nouveau travail pour la colorisation
            from app.db.queries import creer_travail as _creer_travail
            travail_color_id = await _creer_travail(
                "colorisation",
                chemin_photo=str(chemin_restaure),
                utilisateur_id=utilisateur_id,
            )
            await mettre_a_jour_travail(
                travail_color_id,
                statut="en_cours",
                taille_original=chemin_restaure.stat().st_size,
            )

            # Étape 3 : Colorisation
            nom_colorise = f"{nom_base}_colorized.jpg"
            chemin_colorise = UPLOAD_DIR / nom_colorise
            await coloriser_photo(str(chemin_restaure), str(chemin_colorise))
            url_image = f"/uploads/{nom_colorise}"
            chemin_final = chemin_colorise

            # Mettre à jour le travail de colorisation
            travail_id = travail_color_id  # pour les étapes suivantes
            nb_credits_restant = nb_credits_total - 1
        else:
            nb_credits_restant = nb_credits_total

        # Succès : upload B2 + mise à jour du travail
        # Upload du résultat vers B2 (stockage cloud redondant)
        url_b2 = None
        try:
            from app.storage import uploader_bytes, generer_cle_distant, b2_est_disponible
            if b2_est_disponible():
                cle = generer_cle_distant("resultats", chemin_final.name)
                url_b2 = uploader_bytes(chemin_final.read_bytes(), cle, "image/jpeg")
                logger.info("Résultat uploadé vers B2: %s", url_b2)
        except Exception as e:
            logger.warning("Échec upload B2 résultat (fallback local): %s", e)

        resultat_json = json.dumps({
            "analyse": analyse.model_dump(),
            "colorise": coloriser,
            "credits_consommes": nb_credits_total,
            "url_b2": url_b2,
        })
        await mettre_a_jour_travail(
            travail_id,
            statut="termine",
            chemin_resultat=str(chemin_final),
            taille_resultat=chemin_final.stat().st_size,
            resultat_json=resultat_json,
        )

        logger.info(f"[ARQ] Restauration terminée — travail_id={travail_id}")
        return {
            "message": "Photo restaurée avec succès !"
                       + (" (colorisée)" if coloriser else ""),
            "url_image": url_image,
            "credits_consommes": nb_credits_total,
        }

    except Exception as e:
        logger.exception(f"[ARQ] Erreur restauration — travail_id={travail_id} : {e}")
        await mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=str(e),
        )
        raise


# ---------------------------------------------------------------------------
# Job : Animation D-ID
# ---------------------------------------------------------------------------

async def animation_job(
    ctx: dict,
    utilisateur_id: int,
    chemin_original: str,
    texte: str,
    travail_id: int,
) -> dict:
    """
    Crée une animation D-ID dans le worker ARQ.

    Le fichier est déjà sauvegardé par le handler HTTP.
    Le job appelle l'API D-ID et met à jour le travail en base.

    Returns:
        dict avec les clés : message, job_id (D-ID)
    """
    from app.services.did_service import creer_animation

    nom_fichier = Path(chemin_original).name
    logger.info(
        f"[ARQ] Démarrage animation — travail_id={travail_id}, "
        f"fichier={chemin_original}"
    )

    try:
        # Construction de l'URL publique
        url_photo = f"{PUBLIC_BACKEND_URL}/uploads/{nom_fichier}"

        # Appel à l'API D-ID
        job_did = await creer_animation(url_photo, texte=texte)

        # Association du job D-ID au travail local
        await mettre_a_jour_travail(
            travail_id,
            statut="en_cours",
            resultat_json=json.dumps({"job_did": job_did}),
        )
        await mettre_a_jour_job_externe_id(travail_id, job_did)

        logger.info(
            f"[ARQ] Animation créée — travail_id={travail_id}, "
            f"job_did={job_did}"
        )
        return {
            "message": "Animation créée avec succès. Vous pouvez suivre sa progression.",
            "job_id": job_did,
        }

    except Exception as e:
        logger.exception(f"[ARQ] Erreur animation — travail_id={travail_id} : {e}")
        await mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=str(e),
        )
        raise


# ---------------------------------------------------------------------------
# Configuration du worker ARQ
# ---------------------------------------------------------------------------

class WorkerSettings:
    """
    Configuration du worker ARQ.

    Utilisé par : arq app.worker.WorkerSettings
    """
    functions = [restauration_job, animation_job]
    redis_settings = RedisSettings(host='localhost', port=6379)
    max_jobs = 10  # Limite de jobs concurrents par worker
    job_timeout = 600  # Timeout max par job (10 minutes, D-ID peut être lent)
    keep_result = 3600  # Garde les résultats 1h dans Redis
