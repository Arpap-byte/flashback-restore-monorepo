"""
Service d'intégration avec Google Gemini.

Utilise le modèle gemini-2.5-flash pour :
- Analyser les défauts d'une photo ancienne
- Déterminer les paramètres de restauration optimaux

Toutes les interactions sont en français.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.models.schemas import AnalyseReponse, ParametresRestauration

logger = logging.getLogger(__name__)

# Client Gemini (initialisé paresseusement)
_client: Optional[genai.Client] = None


def _obtenir_client() -> genai.Client:
    """Retourne le client Gemini, initialisé si nécessaire."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


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

    # Appel à Gemini avec le prompt d'analyse
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            PROMPT_ANALYSE,
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1024,
        ),
    )

    texte_brut = response.text.strip() if response.text else ""

    # Nettoyage de la réponse (suppression des blocs markdown éventuels)
    if texte_brut.startswith("```"):
        texte_brut = texte_brut.split("\n", 1)[-1]
        if texte_brut.endswith("```"):
            texte_brut = texte_brut[:-3]
        texte_brut = texte_brut.strip()

    if texte_brut.startswith("```json"):
        texte_brut = texte_brut[7:].strip()
        if texte_brut.endswith("```"):
            texte_brut = texte_brut[:-3].strip()

    try:
        data = json.loads(texte_brut)
    except json.JSONDecodeError as e:
        logger.error(f"Réponse Gemini invalide : {texte_brut}")
        raise ValueError(
            f"Impossible de parser la réponse de Gemini : {e}"
        ) from e

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


async def obtenir_parametres_restauration(chemin_image: str) -> ParametresRestauration:
    """
    Demande à Gemini les paramètres optimaux de restauration pour une photo.

    Args:
        chemin_image: Chemin local vers le fichier image.

    Returns:
        Un objet ParametresRestauration avec les paramètres recommandés.

    Raises:
        Exception: Si l'API Gemini échoue.
    """
    logger.info(f"Obtention des paramètres de restauration pour : {chemin_image}")

    client = _obtenir_client()
    image_bytes = Path(chemin_image).read_bytes()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            PROMPT_RESTAURATION,
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
        ],
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=512,
        ),
    )

    texte_brut = response.text.strip() if response.text else ""

    # Nettoyage
    if texte_brut.startswith("```"):
        texte_brut = texte_brut.split("\n", 1)[-1]
        if texte_brut.endswith("```"):
            texte_brut = texte_brut[:-3]
        texte_brut = texte_brut.strip()
    if texte_brut.startswith("```json"):
        texte_brut = texte_brut[7:].strip()
        if texte_brut.endswith("```"):
            texte_brut = texte_brut[:-3].strip()

    try:
        data = json.loads(texte_brut)
    except json.JSONDecodeError as e:
        logger.error(f"Réponse Gemini invalide pour restauration : {texte_brut}")
        raise ValueError(
            f"Impossible de parser la réponse de Gemini : {e}"
        ) from e

    params = ParametresRestauration(
        luminosite=float(data.get("luminosite", 1.0)),
        contraste=float(data.get("contraste", 1.0)),
        saturation=float(data.get("saturation", 1.0)),
        nettete=float(data.get("nettete", 1.0)),
        debruitage=float(data.get("debruitage", 0.0)),
        correction_rouge=float(data.get("correction_rouge", 1.0)),
        correction_vert=float(data.get("correction_vert", 1.0)),
        correction_bleu=float(data.get("correction_bleu", 1.0)),
    )

    logger.info(f"Paramètres obtenus : luminosite={params.luminosite}, contraste={params.contraste}")
    return params
