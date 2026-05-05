"""
Service d'intégration avec D-ID pour l'animation de portraits.

Permet de :
- Créer une animation « portrait parlant » à partir d'une photo
- Suivre l'état d'une animation en cours

Les animations sont de style « Harry Potter » : le visage sur la photo
s'anime et prononce un texte fourni.
"""

import logging
from typing import Optional

import httpx

from app.config import DID_API_KEY, DID_BASE_URL

logger = logging.getLogger(__name__)

# En-têtes HTTP réutilisables
_HEADERS = {
    "Authorization": f"Basic {DID_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


async def creer_animation(
    url_photo: str,
    texte: str = "Bonjour ! Je suis un souvenir restauré.",
    voix: Optional[str] = None,
) -> str:
    """
    Crée une animation D-ID « talking head » à partir d'une photo.

    Args:
        url_photo: URL publique de la photo à animer.
        texte: Texte que le portrait va prononcer.
        voix: Identifiant de la voix (optionnel, voix par défaut si absent).

    Returns:
        L'identifiant du travail D-ID (job ID).

    Raises:
        httpx.HTTPStatusError: Si l'API D-ID retourne une erreur HTTP.
        Exception: En cas d'erreur réseau ou inattendue.
    """
    logger.info(f"Création d'une animation D-ID pour : {url_photo}")

    corps = {
        "script": {
            "type": "text",
            "input": texte,
        },
        "source_url": url_photo,
    }

    if voix:
        corps["config"] = {"voice": {"voice_id": voix}}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{DID_BASE_URL}/talks",
            headers=_HEADERS,
            json=corps,
        )
        response.raise_for_status()
        data = response.json()

    job_id = data.get("id")
    if not job_id:
        raise RuntimeError("L'API D-ID n'a pas retourné d'identifiant de travail.")

    logger.info(f"Animation créée avec succès, job_id={job_id}")
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
