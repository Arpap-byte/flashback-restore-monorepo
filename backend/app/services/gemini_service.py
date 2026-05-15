"""
Service d'intégration avec Google Gemini.

Utilise le modèle gemini-2.5-flash pour :
- Analyser les défauts d'une photo ancienne
- Déterminer les paramètres de restauration optimaux

Toutes les interactions sont en français.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from PIL import Image; Image.MAX_IMAGE_PIXELS = 50_000_000

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.models.schemas import AnalyseReponse, ParametresRestauration

logger = logging.getLogger(__name__)

# Modèle dédié à la génération d'images (restauration, colorisation)
GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image-preview"

# Client Gemini (initialisé paresseusement)
_client: Optional[genai.Client] = None


def _obtenir_client() -> genai.Client:
    """Retourne le client Gemini, initialisé si nécessaire."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _parser_json_gemini(texte_brut: str) -> dict:
    """
    Parse la réponse texte de Gemini en dictionnaire JSON.

    Gère le nettoyage des blocs markdown (```json ... ```) et applique
    un fallback robuste : extraction entre accolades, puis correction
    des sauts de ligne dans les chaînes.

    Args:
        texte_brut: Le texte brut retourné par l'API Gemini.

    Returns:
        Le dictionnaire parsé.

    Raises:
        ValueError: Si le texte ne contient aucun JSON valide.
    """
    texte = texte_brut.strip()

    # Nettoyage des blocs markdown éventuels
    if texte.startswith("```"):
        texte = texte.split("\n", 1)[-1]
        if texte.endswith("```"):
            texte = texte[:-3]
        texte = texte.strip()

    if texte.startswith("```json"):
        texte = texte[7:].strip()
        if texte.endswith("```"):
            texte = texte[:-3].strip()

    # Tentative de parser directement
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        pass

    # Fallback : extraire entre le premier { et le dernier }
    debut = texte.find("{")
    fin = texte.rfind("}")
    if debut >= 0 and fin > debut:
        fragment = texte[debut:fin + 1]
        try:
            return json.loads(fragment)
        except json.JSONDecodeError:
            pass

        # Nettoyage agressif : échapper les sauts de ligne dans les chaînes
        import re
        fragment = re.sub(
            r'(?<!\\)"(?:(?<!\\)(?:\\\\\\)*\\"|[^"\n])*"',
            lambda m: m.group(0).replace('\n', '\\n'),
            fragment,
        )
        try:
            return json.loads(fragment)
        except json.JSONDecodeError as e:
            logger.error(f"Réponse Gemini JSON invalide : {texte_brut[:500]}")
            raise ValueError(
                f"Impossible de parser la réponse de Gemini : {e}"
            ) from e
    else:
        logger.error(f"Réponse Gemini sans JSON : {texte_brut[:500]}")
        raise ValueError("Réponse de Gemini ne contient pas de JSON valide")


# ---------------------------------------------------------------------------
# Analyse des défauts
# ---------------------------------------------------------------------------

PROMPT_ANALYSE = """Tu es un expert en restauration de photographies anciennes.
Analyse cette photo et identifie tous les défauts visibles.

Retourne UNIQUEMENT un objet JSON valide, sans texte avant ni après, avec exactement cette structure :

{
  "rayures": true/false,
  "decoloration": true/false,
  "taches": true/false,
  "dechirures": true/false,
  "bruit": true/false,
  "etat_global": "excellent" | "bon" | "moyen" | "mauvais" | "tres_mauvais",
  "age_estime": "estimation en années (ex: 30-40 ans)",
  "recommandations": [
    "recommandation 1 en français",
    "recommandation 2 en français",
    ...
  ]
}

Sois précis et exhaustif dans ton analyse. Les recommandations doivent être
rédigées en français et être techniquement pertinentes pour la restauration."""


async def analyser_photo(chemin_image: str) -> AnalyseReponse:
    """
    Analyse une photo ancienne pour détecter ses défauts.

    Args:
        chemin_image: Chemin local vers le fichier image à analyser.

    Returns:
        Un objet AnalyseReponse contenant tous les défauts détectés.

    Raises:
        Exception: Si l'API Gemini échoue ou retourne une réponse invalide.
    """
    logger.info(f"Analyse de la photo : {chemin_image}")

    client = _obtenir_client()

    # Lecture de l'image
    image_bytes = Path(chemin_image).read_bytes()

    # Appel à Gemini avec le prompt d'analyse (offloadé hors de l'event loop)
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=GEMINI_MODEL,
        contents=[
            PROMPT_ANALYSE,
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=4096,
        ),
    )

    texte_brut = response.text.strip() if response.text else ""
    data = _parser_json_gemini(texte_brut)

    # Normalisation de l'état global
    etat = data.get("etat_global", "moyen")
    etats_valides = {"excellent", "bon", "moyen", "mauvais", "tres_mauvais"}
    if etat not in etats_valides:
        # Tentative de traduction automatique
        correspondance = {
            "very good": "excellent",
            "good": "bon",
            "average": "moyen",
            "bad": "mauvais",
            "very bad": "tres_mauvais",
            "très bon": "excellent",
            "très mauvais": "tres_mauvais",
            "excellent": "excellent",
            "bon": "bon",
            "moyen": "moyen",
            "mauvais": "mauvais",
        }
        etat = correspondance.get(etat.lower(), "moyen")

    analyse = AnalyseReponse(
        rayures=bool(data.get("rayures", False)),
        decoloration=bool(data.get("decoloration", False)),
        taches=bool(data.get("taches", False)),
        dechirures=bool(data.get("dechirures", False)),
        bruit=bool(data.get("bruit", False)),
        etat_global=etat,
        age_estime=str(data.get("age_estime", "Inconnu")),
        recommandations=data.get("recommandations", []),
    )

    logger.info(f"Analyse terminée : état={analyse.etat_global}")
    return analyse


# ---------------------------------------------------------------------------
# Paramètres de restauration
# ---------------------------------------------------------------------------

PROMPT_RESTAURATION = """Tu es un expert en restauration numérique de photographies.
Analyse cette photo et détermine les paramètres optimaux pour la restaurer.

Retourne UNIQUEMENT un objet JSON valide, sans texte avant ni après, avec exactement cette structure :

{
  "luminosite": 1.0,
  "contraste": 1.0,
  "saturation": 1.0,
  "nettete": 1.0,
  "debruitage": 0.0,
  "correction_rouge": 1.0,
  "correction_vert": 1.0,
  "correction_bleu": 1.0
}

Règles :
- luminosite : 0.5 à 2.0. Augmente si la photo est trop sombre.
- contraste : 0.5 à 2.0. Augmente si l'image est plate/délavée.
- saturation : 0.0 à 2.0. 1.0 = pas de changement. Augmente si les couleurs sont fades.
- nettete : 0.5 à 3.0. 1.0 = pas de changement. Augmente si l'image est floue.
- debruitage : 0.0 à 1.0. 0.0 = aucun débruitage. Augmente si l'image est granuleuse/bruitée.
- correction_rouge/vert/bleu : 0.5 à 2.0. Ajuste pour corriger une dominante de couleur.

Sois précis. Une photo très abîmée nécessite des corrections plus fortes."""


# ---------------------------------------------------------------------------
# Colorisation
# ---------------------------------------------------------------------------

PROMPT_COLORISATION = (
    "Colorize this black and white photograph with historically accurate colors. "
    "Preserve every detail and texture exactly — no blurring, smoothing, or alteration. "
    "Use natural skin tones (not orange), realistic fabric colors (navy, charcoal, cream, beige), "
    "period-appropriate palette. Avoid color bleeding, halos, oversaturation. "
    "Return ONLY the colorized image. No text."
)


async def coloriser_photo(chemin_image: str, chemin_sortie: str) -> str:
    """
    Colorise une photo via Gemini Image Model (image→image),
    avec fallback Pillow amélioré en cas d'échec.

    Args:
        chemin_image: Chemin local vers l'image à coloriser.
        chemin_sortie: Chemin local où sauvegarder l'image colorisée.

    Returns:
        Le chemin de l'image colorisée (identique à chemin_sortie).

    Raises:
        Exception: Si ni Gemini ni Pillow ne peut produire une image.
    """
    logger.info(f"Tentative de colorisation ({GEMINI_IMAGE_MODEL}) pour : {chemin_image}")

    # --- Essai 1 : Gemini Image Model (image → image) ---
    try:
        import base64
        import httpx

        image_bytes = Path(chemin_image).read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as http_client:
            response = await http_client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL}:generateContent",
                headers={"x-goog-api-key": GEMINI_API_KEY},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": PROMPT_COLORISATION},
                                {
                                    "inlineData": {
                                        "mimeType": "image/jpeg",
                                        "data": image_b64,
                                    }
                                },
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 8192,
                        "responseModalities": ["IMAGE"],
                    },
                },
            )

            if response.status_code == 200:
                data = response.json()
                # Extraire l'image de la réponse Gemini
                for candidate in data.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        if "inlineData" in part:
                            img_data = base64.b64decode(part["inlineData"]["data"])
                            Path(chemin_sortie).write_bytes(img_data)
                            taille = len(img_data)
                            logger.info(
                                f"Colorisation Gemini réussie : {chemin_sortie} "
                                f"({taille} octets)"
                            )
                            return chemin_sortie

                # Statut 200 mais pas d'image inline
                logger.warning(
                    f"Gemini colorisation : réponse 200 mais aucune image inline trouvée. "
                    f"Réponse brute (300 premiers) : {response.text[:300]}"
                )
            else:
                logger.warning(
                    f"Gemini colorisation échouée "
                    f"(status={response.status_code}, body={response.text[:300]}), "
                    f"fallback Pillow"
                )
    except Exception as e:
        logger.warning(
            f"Gemini colorisation exception : {e}, fallback Pillow"
        )

    # --- Fallback : Pillow colorisation améliorée ---
    _colorisation_pillow(chemin_image, chemin_sortie)
    logger.info(f"Colorisation Pillow appliquée : {chemin_sortie}")
    return chemin_sortie


def _colorisation_pillow(chemin_source: str, chemin_destination: str) -> None:
    """
    Applique une colorisation automatique via Pillow (fallback).

    Détecte si l'image est en niveaux de gris :
    - Si oui : applique une teinte sépia chaude avec variation de tons
      (les images N&B ne réagissent pas à la saturation).
    - Si non (déjà en couleur) : boost saturation + contraste + réchauffement.
    """
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    image = Image.open(chemin_source).convert("RGB")
    pixels = image.load()
    largeur, hauteur = image.size

    # --- Détection niveaux de gris ---
    # Échantillonne jusqu'à 5000 pixels pour déterminer si l'image est N&B
    echantillon_max = 5000
    pas_x = max(1, largeur // 70)
    pas_y = max(1, hauteur // 70)
    nb_pixels, nb_gris = 0, 0
    seuil_gris = 8  # tolérance pour considérer un pixel comme « gris »

    for y in range(0, hauteur, pas_y):
        for x in range(0, largeur, pas_x):
            if nb_pixels >= echantillon_max:
                break
            r, g, b = pixels[x, y][:3]
            if abs(r - g) <= seuil_gris and abs(g - b) <= seuil_gris and abs(r - b) <= seuil_gris:
                nb_gris += 1
            nb_pixels += 1
        if nb_pixels >= echantillon_max:
            break

    ratio_gris = nb_gris / max(nb_pixels, 1)
    est_nb = ratio_gris > 0.92  # >92% des pixels sont dans une plage de gris

    if est_nb:
        logger.info(
            f"Image détectée comme N&B (ratio gris={ratio_gris:.2f}), "
            f"application teinte sépia"
        )
        # Conversion en niveaux de gris puis application d'une teinte sépia
        # via transformation par canal (opérations C-level rapides)
        gris = image.convert("L")

        # Sépia classique : boost rouge, modéré vert, réduit bleu
        r = gris.point(lambda p: min(255, int(p * 1.08 + 18)))
        g = gris.point(lambda p: min(255, int(p * 0.95 + 8)))
        b = gris.point(lambda p: min(255, int(p * 0.72)))

        image = Image.merge("RGB", (r, g, b))

        # Léger boost contraste pour faire ressortir la teinte
        ameliorateur = ImageEnhance.Contrast(image)
        image = ameliorateur.enhance(1.15)

        # Légère netteté
        ameliorateur = ImageEnhance.Sharpness(image)
        image = ameliorateur.enhance(1.1)
    else:
        logger.info(
            f"Image déjà en couleur (ratio gris={ratio_gris:.2f}), "
            f"boost saturation + réchauffement"
        )
        # 1. Auto-contraste (égalisation d'histogramme)
        image = ImageOps.autocontrast(image, cutoff=2)

        # 2. Boost saturation
        ameliorateur = ImageEnhance.Color(image)
        image = ameliorateur.enhance(2.0)

        # 3. Léger boost contraste
        ameliorateur = ImageEnhance.Contrast(image)
        image = ameliorateur.enhance(1.15)

        # 4. Réchauffement : booster rouge, réduire bleu
        r, g, b = image.split()
        r = r.point(lambda p: min(255, int(p * 1.08)))
        b = b.point(lambda p: min(255, int(p * 0.92)))
        image = Image.merge("RGB", (r, g, b))

        # 5. Légère netteté
        ameliorateur = ImageEnhance.Sharpness(image)
        image = ameliorateur.enhance(1.2)

    image.save(chemin_destination, quality=95)


# ---------------------------------------------------------------------------
# Restauration IA par Gemini Image Model
# ---------------------------------------------------------------------------

PROMPT_RESTAURATION_IA = (
    "Restaure cette photo ancienne en haute qualité. "
    "Actions obligatoires : "
    "1. Supprime complètement toutes les pliures, fissures et marques de pliage sur l'image. "
    "2. Élimine toutes les rayures, taches, poussières et défauts de vieillissement. "
    "3. Corrige tout le flou — rends chaque détail parfaitement net et précis. "
    "4. Améliore le contraste, la luminosité et la profondeur. "
    "5. Restaure les textures, les visages et l'arrière-plan avec précision. "
    "6. Conserve le style et l'ambiance d'origine. "
    "Ne retourne QUE l'image restaurée. Aucun texte."
)


async def restaurer_photo_ia(chemin_image: str, chemin_sortie: str) -> str:
    """
    Restaure une photo via Gemini Image Model (image→image),
    avec fallback Pillow avancé en cas d'échec.

    Args:
        chemin_image: Chemin local vers l'image à restaurer.
        chemin_sortie: Chemin local où sauvegarder l'image restaurée.

    Returns:
        Le chemin de l'image restaurée.
    """
    logger.info(f"Restauration IA ({GEMINI_IMAGE_MODEL}) pour : {chemin_image}")

    # --- Essai 1 : Gemini Image Model ---
    try:
        import base64
        import httpx

        image_bytes = Path(chemin_image).read_bytes()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as http_client:
            response = await http_client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL}:generateContent",
                headers={"x-goog-api-key": GEMINI_API_KEY},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": PROMPT_RESTAURATION_IA},
                                {
                                    "inlineData": {
                                        "mimeType": "image/jpeg",
                                        "data": image_b64,
                                    }
                                },
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 8192,
                        "responseModalities": ["IMAGE"],
                    },
                },
            )

            if response.status_code == 200:
                data = response.json()
                for candidate in data.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        if "inlineData" in part:
                            img_data = base64.b64decode(part["inlineData"]["data"])
                            Path(chemin_sortie).write_bytes(img_data)
                            taille = len(img_data)
                            logger.info(
                                f"Restauration IA réussie : {chemin_sortie} "
                                f"({taille} octets)"
                            )
                            return chemin_sortie

            logger.warning(
                f"Gemini restauration IA échouée "
                f"(status={response.status_code}, body={response.text[:300]}), "
                f"fallback Pillow"
            )
    except Exception as e:
        logger.warning(
            f"Gemini restauration IA exception : {e}, fallback Pillow"
        )

    # --- Fallback : Pillow avancé ---
    _restauration_pillow_avancee(chemin_image, chemin_sortie)
    logger.info(f"Restauration Pillow avancée : {chemin_sortie}")
    return chemin_sortie


def _restauration_pillow_avancee(chemin_source: str, chemin_destination: str) -> None:
    """
    Restauration avancée via Pillow (fallback si Gemini échoue).

    Applique : auto-contraste, débruitage, netteté agressive,
    correction de contraste/luminosité, UnsharpMask.
    """
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    image = Image.open(chemin_source).convert("RGB")

    # 1. Auto-contraste
    image = ImageOps.autocontrast(image, cutoff=3)

    # 2. Débruitage léger
    image = image.filter(ImageFilter.MedianFilter(size=3))

    # 3. Netteté agressive (×2.5)
    ameliorateur = ImageEnhance.Sharpness(image)
    image = ameliorateur.enhance(2.5)

    # 4. Contraste
    ameliorateur = ImageEnhance.Contrast(image)
    image = ameliorateur.enhance(1.25)

    # 5. Luminosité
    ameliorateur = ImageEnhance.Brightness(image)
    image = ameliorateur.enhance(1.05)

    # 6. UnsharpMask pour les détails fins
    image = image.filter(
        ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=2)
    )

    image.save(chemin_destination, quality=95)
