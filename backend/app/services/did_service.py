"""
Service d'intégration avec D-ID pour l'animation de portraits.

Permet de :
- Créer une animation « portrait vivant » à partir d'une photo
- Suivre l'état d'une animation en cours

Les animations sont des micro-expressions naturelles (respiration, sourire, rire)
sans parole — style « photo qui prend vie » en 5 secondes max.
"""

import logging
from typing import Optional

import httpx

from app.config import DID_API_KEY, DID_BASE_URL, PUBLIC_BACKEND_URL

# URL du fichier audio silencieux (5 secondes) pour les animations sans parole
SILENCE_AUDIO_URL = f"{PUBLIC_BACKEND_URL}/uploads/silence_5s.wav"

logger = logging.getLogger(__name__)

# En-têtes HTTP réutilisables
_HEADERS = {
    "Authorization": f"Basic {DID_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Mapping des comportements FR → expressions D-ID (anglais obligatoire)
COMPORTEMENT_VERS_EXPRESSION: dict[str, str] = {
    "naturel": "neutral",
    "sourire": "happy",
    "rire": "happy",
    "respirer": "neutral",
    "clin_oeil": "surprise",
    "salut": "happy",
}

# Intensité par comportement (certains sont plus marqués)
INTENSITE_PAR_COMPORTEMENT: dict[str, float] = {
    "naturel": 0.3,
    "sourire": 0.6,
    "rire": 0.8,
    "respirer": 0.2,
    "clin_oeil": 0.7,
    "salut": 0.5,
}


async def creer_animation(
    url_photo: str,
    comportement: str = "naturel",
    duree_sec: int = 5,
) -> str:
    """
    Crée une animation faciale D-ID sans parole.

    Args:
        url_photo: URL publique de la photo à animer.
        comportement: Type de micro-expression (« sourire », « rire »,
                      « respirer », « clin_oeil », « salut », « naturel »).
        duree_sec: Durée cible en secondes (défaut 5s).

    Returns:
        L'identifiant du travail D-ID (job ID).
    """
    # Traduction FR → EN pour l'API D-ID
    expression_en = COMPORTEMENT_VERS_EXPRESSION.get(comportement, "neutral")
    intensite = INTENSITE_PAR_COMPORTEMENT.get(comportement, 0.4)

    logger.info(
        f"Création animation D-ID sans parole : comportement={comportement} "
        f"→ expression={expression_en}, intensité={intensite}, "
        f"photo={url_photo}"
    )

    corps: dict = {
        "script": {
            "type": "audio",
            "audio_url": SILENCE_AUDIO_URL,  # 5s de silence → pas de parole
        },
        "source_url": url_photo,
        "config": {
            "result_format": "mp4",
            "stitch": True,
            "driver_expressions": {
                "expressions": [
                    {
                        "expression": expression_en,
                        "start_frame": 0,
                        "intensity": intensite,
                    }
                ]
            },
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{DID_BASE_URL}/talks",
            headers=_HEADERS,
            json=corps,
        )
        # En cas d'erreur 400, log le corps de la réponse pour diagnostic
        if response.status_code >= 400:
            logger.error(
                f"D-ID API error {response.status_code}: {response.text[:500]}"
            )
        response.raise_for_status()
        data = response.json()

    job_id = data.get("id")
    if not job_id:
        raise RuntimeError("L'API D-ID n'a pas retourné d'identifiant de travail.")

    logger.info(f"Animation sans parole créée, job_id={job_id}")
    return job_id


async def verifier_statut_animation(job_id: str) -> dict:
    """
    Vérifie le statut d'une animation D-ID.

    Args:
        job_id: L'identifiant du travail D-ID.

    Returns:
        Un dictionnaire contenant :
        - statut: "created" | "started" | "done" | "error"
        - url_video: URL de la vidéo si statut == "done" (optionnel)
        - message: Message d'erreur si statut == "error" (optionnel)

    Raises:
        httpx.HTTPStatusError: Si l'API D-ID retourne une erreur HTTP.
    """
    logger.info(f"Vérification du statut de l'animation : {job_id}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{DID_BASE_URL}/talks/{job_id}",
            headers=_HEADERS,
        )
        response.raise_for_status()
        data = response.json()

    statut_did = data.get("status", "unknown")
    resultat: dict = {"statut": statut_did}

    if statut_did == "done":
        resultat["url_video"] = data.get("result_url") or data.get("url")
    elif statut_did == "error":
        resultat["message"] = data.get("error", {}).get("description", "Erreur inconnue")

    logger.info(f"Statut animation {job_id} : {statut_did}")
    return resultat
