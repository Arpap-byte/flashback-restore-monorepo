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
# Préfixe commun — contraintes de fidélité à la photo originale
# Appliqué à TOUS les prompts. Cadrage positif (pas de "DO NOT").
# Effet de récence via SUFFIX_FIDELITE en fin de prompt.
# ---------------------------------------------------------------------------

PREFIX_FIDELITE = (
    "Static locked camera, fixed composition, identical background and lighting "
    "as the original photo. The background, setting, and decor remain completely "
    "unchanged — exactly as in the input image. No camera movement of any kind: "
    "no pan, no zoom, no dolly, no tracking. Same framing, no crop. "
    "Only the person moves"
)

SUFFIX_FIDELITE = "Background and lighting identical to the input photo, fixed camera"

# ---------------------------------------------------------------------------
# Prompts par comportement — ÉPURÉS de toute référence à la lumière/décor
# ---------------------------------------------------------------------------

PROMPTS_PAR_COMPORTEMENT: dict[str, str] = {
    "naturel": (
        "Subtle natural micro-expressions on the face, gentle breathing visible "
        "in the chest and shoulders, the person remains still and calm, "
        "photorealistic portrait, natural subtle motion"
    ),
    "sourire": (
        "A warm genuine smile slowly spreading across the face, eyes crinkling softly "
        "with quiet joy, subtle natural head tilt, "
        "photorealistic portrait, gentle natural motion"
    ),
    "rire": (
        "A spontaneous joyful laugh, slight natural head tilt, eyes closing naturally, "
        "shoulders moving gently with laughter, "
        "photorealistic, gentle natural motion"
    ),
    "respirer": (
        "Gentle visible breathing, chest rising and falling subtly, calm serene expression, "
        "photorealistic portrait, meditative gentle motion"
    ),
    "clin_oeil": (
        "A playful wink, one eye closing while the other stays open, a slight mischievous "
        "smile forming, subtle head tilt, "
        "photorealistic portrait, gentle motion"
    ),
    "salut": (
        "A friendly warm greeting, slight nod of the head, welcoming smile appearing, "
        "natural friendly expression, "
        "photorealistic portrait, gentle natural motion"
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


def _nettoyer_message_veo(msg: str) -> str:
    """Nettoie le message d'erreur Veo pour l'utilisateur final.

    - Tronque les suffixes inutiles en anglais (Contact Gemini API support, etc.)
    - Traduit les messages d'erreur courants en français.
    - Limite la longueur à 200 caractères max.
    """
    suffixes_a_tronquer = [
        "If the problem persists, please contact Gemini API support",
        "If the problem persists, contact Gemini API support",
        "Please try again in a few minutes",
        "If this error persists",
        "Please try again later",
        "Please retry",
    ]
    for suffix in suffixes_a_tronquer:
        idx = msg.lower().find(suffix.lower())
        if idx != -1:
            msg = msg[:idx].strip().rstrip(".,; ")
            break

    # Traductions de messages d'erreur Veo/Gemini courants
    traductions = {
        "Video generation failed due to an internal server issue":
            "Échec de génération (erreur serveur interne)",
        "The model is currently overloaded":
            "Le modèle est actuellement surchargé",
        "The model is overloaded":
            "Le modèle est surchargé",
        "Resource has been exhausted":
            "Quota épuisé",
    }
    msg_clean = msg.strip()
    for en, fr in traductions.items():
        if msg_clean.lower().startswith(en.lower()):
            msg_clean = fr + msg_clean[len(en):]
            break

    # Tronquer à 200 caractères max
    if len(msg_clean) > 200:
        msg_clean = msg_clean[:197] + "..."

    return msg_clean


def _erreur_recuperable_veo(msg: str) -> bool:
    """Détermine si une erreur Veo mérite un fallback vers le modèle Fast.

    Erreurs récupérables :
    - "high demand" / overload
    - "internal server issue"
    - "server error"
    - messages traduits correspondants

    Erreurs NON récupérables (on ne retente pas) :
    - Filtre de sécurité / contenu filtré → la photo elle-même est rejetée
    - Erreur 4xx (sauf 429 déjà traité) → bug dans notre requête
    """
    msg_lower = msg.lower()
    motifs_recuperables = [
        "high demand",
        "internal server",
        "server error",
        "currently overloaded",
        "currently unavailable",
        "temporarily unavailable",
        "erreur serveur",
        "surchargé",
    ]
    for motif in motifs_recuperables:
        if motif in msg_lower:
            return True
    return False


async def _uploader_image_gemini(chemin: str) -> tuple[str, str]:
    """Upload l'image vers l'API File de Gemini et retourne (file_uri, mime_type).

    Veo 3.1 exige que l'image soit d'abord uploadée via l'API File,
    puis référencée par son fileUri dans la requête predictLongRunning.
    """
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
    mime_type = mime_map.get(suffix, "image/jpeg")

    # Étape 1 : obtenir une URL d'upload signée
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        init_resp = await client.post(
            f"https://generativelanguage.googleapis.com/upload/v1beta/files",
            params={"key": GEMINI_API_KEY},
            headers={"X-Goog-Upload-Protocol": "resumable",
                     "X-Goog-Upload-Command": "start",
                     "X-Goog-Upload-Header-Content-Type": mime_type,
                     "X-Goog-Upload-Header-Slug": path.name},
        )
        init_resp.raise_for_status()
        upload_url = init_resp.headers.get("X-Goog-Upload-URL")
        if not upload_url:
            raise RuntimeError(
                f"Gemini Files: pas d'URL d'upload dans la réponse. "
                f"Status={init_resp.status_code}, body={init_resp.text[:200]}"
            )

    # Étape 2 : uploader les bytes
    image_bytes = path.read_bytes()
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        upload_resp = await client.post(
            upload_url,
            params={"key": GEMINI_API_KEY},
            headers={"X-Goog-Upload-Command": "upload, finalize",
                     "X-Goog-Upload-Offset": "0",
                     "Content-Type": mime_type},
            content=image_bytes,
        )
        upload_resp.raise_for_status()
        file_info = upload_resp.json()

    file_name = file_info.get("file", {}).get("name")
    if not file_name:
        raise RuntimeError(
            f"Gemini Files: pas de 'name' dans la réponse. "
            f"body={upload_resp.text[:200]}"
        )

    file_uri = f"https://generativelanguage.googleapis.com/v1beta/{file_name}"
    logger.info(
        f"Gemini Files upload — {path.name} → {file_name} "
        f"({len(image_bytes)} octets)"
    )
    return file_uri, mime_type


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
                # 1. Vérifier le filtre de sécurité AVANT l'erreur générique.
                #    "internal server issue" masque souvent un rejet de sécurité.
                gvr = data.get("response", {}).get("generateVideoResponse", {})
                filtered = gvr.get("raiMediaFilteredCount", 0)
                if filtered:
                    reasons = gvr.get("raiMediaFilteredReasons", [])
                    logger.error(
                        f"Veo réponse filtrée (sécurité) — "
                        f"raiMediaFilteredCount={filtered}, "
                        f"reasons={reasons}, "
                        f"body_complet={data}"
                    )
                    raise RuntimeError(
                        f"Veo : contenu filtré — {reasons[0] if reasons else 'raison inconnue'}"
                    )

                # 2. Puis vérifier l'erreur générique
                err = data.get("error", {})
                if err:
                    msg = err.get("message", "Erreur inconnue Veo")
                    logger.error(
                        f"Veo réponse erreur — "
                        f"code={err.get('code')}, "
                        f"message={msg}, "
                        f"body_complet={data}"
                    )
                    user_msg = _nettoyer_message_veo(msg)
                    raise RuntimeError(f"Veo : {user_msg}")

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
    prompt_base = PROMPTS_PAR_COMPORTEMENT.get(comportement, PROMPTS_PAR_COMPORTEMENT["naturel"])
    prompt = f"{PREFIX_FIDELITE}. {prompt_base}. {SUFFIX_FIDELITE}."
    b64_image, mime_type = _image_en_base64(chemin_photo)

    # Journaliser la taille de l'image source (les images > 6 Mo peuvent causer
    # des erreurs serveur Veo)
    image_path = Path(chemin_photo)
    taille_mo = image_path.stat().st_size / (1024 * 1024)
    logger.info(
        f"Veo animation — comportement={comportement}, "
        f"resolution={resolution}, duree={duree}s, "
        f"image={image_path.name} ({taille_mo:.1f} Mo)"
    )
    if taille_mo > 5:
        logger.warning(
            f"Veo image source volumineuse ({taille_mo:.1f} Mo) — "
            f"peut causer des erreurs serveur. "
            f"Limite recommandée : 5 Mo pour 720p."
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
            if modele == VEO_MODEL_LITE:
                if e.response.status_code == 429:
                    logger.warning("Veo Lite overload (429), fallback Fast…")
                    continue
                if e.response.status_code >= 500:
                    logger.warning(
                        f"Veo Lite erreur serveur ({e.response.status_code}), fallback Fast…"
                    )
                    continue
            raise
        except RuntimeError as e:
            msg = str(e)
            if modele == VEO_MODEL_LITE and _erreur_recuperable_veo(msg):
                logger.warning(f"Veo Lite erreur récupérable, fallback Fast : {msg}")
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
