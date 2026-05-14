"""
Service d'intégration avec Google Veo 3.1 pour l'animation de portraits.

Remplace le service D-ID. Utilise l'API Gemini Veo pour générer
des vidéos à partir d'une photo + prompt décrivant l'émotion.

Modèles :
- veo-3.1-lite-generate-preview  → 720p $0.05/s, 1080p $0.08/s
- veo-3.1-fast-generate-preview  → fallback si Lite overload (720p $0.10/s)
"""

import asyncio
import base64
import logging
import time as _time
from pathlib import Path
from typing import Optional

import httpx

from app.config import GEMINI_API_KEY, UPLOAD_DIR, PUBLIC_BACKEND_URL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Modèles Veo
# ---------------------------------------------------------------------------

VEO_MODEL_LITE = "veo-3.1-lite-generate-preview"
VEO_MODEL_FAST = "veo-3.1-fast-generate-preview"       # fallback si overload
VEO_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# ---------------------------------------------------------------------------
# Prompts par comportement (en anglais, Veo comprend mieux)
# ---------------------------------------------------------------------------

PROMPTS_PAR_COMPORTEMENT: dict[str, str] = {
    "naturel": (
        "Subtle natural micro-expressions on a still face, gentle breathing visible "
        "in the chest and shoulders, soft ambient light, photorealistic portrait, "
        "smooth cinematic motion, 24fps, shallow depth of field"
    ),
    "sourire": (
        "A warm genuine smile slowly spreading across the face, eyes crinkling softly "
        "with quiet joy, subtle natural head tilt, golden hour cinematic lighting, "
        "photorealistic portrait, smooth elegant motion, 24fps"
    ),
    "rire": (
        "A spontaneous joyful laugh, head tilting back slightly, eyes closing naturally, "
        "shoulders moving with laughter, warm golden lighting, candid happy moment, "
        "photorealistic, smooth natural motion, 24fps"
    ),
    "respirer": (
        "Gentle visible breathing, chest rising and falling subtly, calm serene expression, "
        "soft diffused natural light, photorealistic portrait, meditative smooth motion, "
        "24fps, shallow depth of field"
    ),
    "clin_oeil": (
        "A playful wink, one eye closing while the other stays open, slight mischievous "
        "smile forming, head tilting playfully, soft cinematic lighting, photorealistic "
        "portrait, smooth motion, 24fps"
    ),
    "salut": (
        "A friendly warm greeting, slight nod of the head, welcoming smile appearing, "
        "natural friendly expression, soft daylight, photorealistic portrait, smooth "
        "natural motion, 24fps"
    ),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _image_en_base64(chemin: str) -> tuple[str, str]:
    """Encode une image en base64 et retourne (b64, mime_type)."""
    path = Path(chemin)
    if not path.exists():
        raise FileNotFoundError(f"Image introuvable : {chemin}")

    suffix = path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime = mime_map.get(suffix, "image/jpeg")
    b64 = base64.b64encode(path.read_bytes()).decode()
    return b64, mime


async def _soumettre_veo(
    b64_image: str,
    mime_type: str,
    prompt: str,
    duree: int = 6,
    resolution: str = "720p",
    model: str = VEO_MODEL_LITE,
) -> str:
    """Soumet un job Veo et retourne le nom de l'opération."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.post(
            f"{VEO_BASE_URL}/models/{model}:predictLongRunning",
            params={"key": GEMINI_API_KEY},
            json={
                "instances": [{
                    "prompt": prompt,
                    "image": {
                        "bytesBase64Encoded": b64_image,
                        "mimeType": mime_type,
                    },
                }],
                "parameters": {
                    "durationSeconds": duree,
                    "resolution": resolution,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()

    op_name = data.get("name")
    if not op_name:
        raise RuntimeError(f"Veo n'a pas retourné d'operation name : {data}")
    return op_name


async def _poll_veo(
    op_name: str,
    timeout: int = 540,
    poll_delays: list[int] = [8, 12, 20, 30],
) -> dict:
    """Poll l'opération Veo jusqu'à complétion. Retourne la réponse finale."""
    debut = _time.monotonic()
    tentative = 0

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        while True:
            ecoule = _time.monotonic() - debut
            if ecoule >= timeout:
                raise TimeoutError(
                    f"Veo a pris trop de temps (> {timeout}s, écoulé={ecoule:.0f}s)"
                )

            resp = await client.get(
                f"{VEO_BASE_URL}/{op_name}",
                params={"key": GEMINI_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("done"):
                # Vérifier erreur
                err = data.get("error", {})
                if err:
                    msg = err.get("message", "Erreur inconnue Veo")
                    raise RuntimeError(f"Veo : {msg}")

                # Vérifier filtre de sécurité
                gvr = data.get("response", {}).get("generateVideoResponse", {})
                filtered = gvr.get("raiMediaFilteredCount", 0)
                if filtered:
                    reasons = gvr.get("raiMediaFilteredReasons", [])
                    raise RuntimeError(
                        f"Veo a filtré la vidéo (sécurité) : {reasons[0] if reasons else 'raison inconnue'}"
                    )

                return data

            delay = poll_delays[min(tentative, len(poll_delays) - 1)]
            tentative += 1
            logger.debug(
                f"Veo polling — tentative={tentative}, écoulé={ecoule:.0f}s, "
                f"prochain dans {delay}s"
            )
            await asyncio.sleep(delay)


async def _telecharger_video(file_id: str) -> bytes:
    """Télécharge la vidéo depuis l'API File de Gemini."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(
            f"{VEO_BASE_URL}/files/{file_id}:download",
            params={"key": GEMINI_API_KEY, "alt": "media"},
        )
        resp.raise_for_status()
        return resp.content


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

async def creer_animation_veo(
    chemin_photo: str,
    comportement: str = "naturel",
    duree: int = 6,
    resolution: str = "720p",
) -> tuple[str, str]:
    """
    Crée une animation faciale via Veo 3.1.

    Args:
        chemin_photo: Chemin local de la photo à animer.
        comportement: Type de micro-expression (naturel, sourire, rire, etc.).
        duree: Durée en secondes (4-8).
        resolution: "720p" ou "1080p".

    Returns:
        Tuple (chemin_video_local, url_video_relative).
    """
    prompt = PROMPTS_PAR_COMPORTEMENT.get(comportement, PROMPTS_PAR_COMPORTEMENT["naturel"])
    b64_image, mime_type = _image_en_base64(chemin_photo)

    logger.info(
        f"Veo animation — comportement={comportement}, "
        f"resolution={resolution}, duree={duree}s"
    )

    # Essayer Lite d'abord, fallback Fast si overload
    data = None
    modele = VEO_MODEL_LITE
    for modele in [VEO_MODEL_LITE, VEO_MODEL_FAST]:
        try:
            op_name = await _soumettre_veo(
                b64_image, mime_type, prompt,
                duree=duree, resolution=resolution, model=modele,
            )
            logger.info(f"Veo job soumis — model={modele}, op={op_name}")

            data = await _poll_veo(op_name)
            break  # succès → sortir de la boucle

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and modele == VEO_MODEL_LITE:
                logger.warning("Veo Lite overload, fallback Fast…")
                continue
            raise
        except RuntimeError as e:
            msg = str(e)
            # "high demand" = overload → fallback
            if "high demand" in msg.lower() and modele == VEO_MODEL_LITE:
                logger.warning("Veo Lite high demand, fallback Fast…")
                continue
            raise

    # Extraire l'URI de la vidéo depuis la réponse
    if data is None:
        raise RuntimeError("Veo n'a retourné aucune réponse (tous les modèles ont échoué)")
    gvr = data["response"]["generateVideoResponse"]
    samples = gvr.get("generatedSamples", [])
    if not samples:
        raise RuntimeError("Veo n'a pas généré de vidéo (aucun sample)")

    video = samples[0].get("video", {})
    uri = video.get("uri", "")
    if not uri:
        raise RuntimeError("Veo n'a pas retourné d'URI vidéo")

    # Télécharger la vidéo
    file_id = uri.rstrip("/").split("/")[-1].split(":")[0]
    logger.info(f"Veo download — file_id={file_id}")

    video_bytes = await _telecharger_video(file_id)

    # Sauvegarder localement
    stem = Path(chemin_photo).stem
    nom_fichier = f"{stem}_veo.mp4"
    chemin_local = UPLOAD_DIR / nom_fichier
    chemin_local.write_bytes(video_bytes)

    url_relative = f"/uploads/{nom_fichier}"
    logger.info(
        f"Veo animation sauvegardée — {chemin_local} "
        f"({len(video_bytes)} octets), model={modele}"
    )

    return str(chemin_local), url_relative


async def verifier_statut_animation_veo(op_name: str) -> dict:
    """
    Vérifie le statut d'une opération Veo en cours.
    Gardé pour compatibilité avec le pattern de l'ancienne API.
    En pratique, le worker fait le polling lui-même.

    Returns:
        {"statut": "en_cours" | "termine" | "erreur", "url_video": ..., "message": ...}
    """
    try:
        data = await _poll_veo(op_name, timeout=10)
        gvr = data["response"]["generateVideoResponse"]
        samples = gvr.get("generatedSamples", [])
        if samples:
            uri = samples[0].get("video", {}).get("uri", "")
            return {"statut": "termine", "url_video": uri}
        return {"statut": "termine", "url_video": None}
    except RuntimeError as e:
        return {"statut": "erreur", "message": str(e)}
    except Exception as e:
        return {"statut": "en_cours", "message": str(e)}
