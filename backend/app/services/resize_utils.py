"""
Fonctions de redimensionnement avec préservation du ratio d'aspect.

Évite l'écrasement/déformation des sujets en utilisant une approche
"fit within bounds" avec letterboxing (bandes noires).
"""

import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

# Résolutions cibles (largeur, hauteur)
RESOLUTIONS = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
}


def resize_fit(
    chemin_image: str,
    resolution: str,
    chemin_sortie: str | None = None,
    couleur_fond: tuple[int, int, int] = (0, 0, 0),
) -> None:
    """
    Redimensionne une image à la résolution cible en préservant
    le ratio d'aspect. Les zones vides sont remplies avec la couleur
    de fond (noir par défaut = letterboxing).

    Contrairement à Image.resize() qui déforme l'image pour remplir
    exactement les dimensions cibles, cette fonction ajuste l'image
    pour qu'elle tienne entièrement dans le cadre sans déformation.

    Exemple :
        Source 400×277 (ratio 1.44) → cible 1920×1080 (ratio 1.78)
        Résultat : 1559×1080 centré dans un canvas 1920×1080
        (bandes noires à gauche et à droite)

    Args:
        chemin_image: Image source (modifiée sur place si pas de chemin_sortie)
        resolution: "720p", "1080p", "4k"
        chemin_sortie: Chemin de sortie (si None, modifie l'image sur place)
        couleur_fond: Couleur RGB du fond (défaut: noir)
    """
    if resolution not in RESOLUTIONS:
        logger.warning("Résolution inconnue '%s', fallback 720p", resolution)
        resolution = "720p"

    largeur_cible, hauteur_cible = RESOLUTIONS[resolution]
    sortie = chemin_sortie or chemin_image
    source = Image.open(chemin_image).convert("RGB")
    src_w, src_h = source.size

    if src_w <= 0 or src_h <= 0:
        logger.error("Dimensions source invalides: %dx%d", src_w, src_h)
        return

    # Calculer le facteur d'échelle qui préserve le ratio
    # On prend le MIN pour que l'image tienne entièrement dans le cadre
    ratio_cible = largeur_cible / hauteur_cible
    ratio_source = src_w / src_h

    if ratio_source > ratio_cible:
        # L'image est plus large que la cible → contraindre par la largeur
        nouvelle_largeur = largeur_cible
        nouvelle_hauteur = int(largeur_cible / ratio_source)
    else:
        # L'image est plus haute que la cible → contraindre par la hauteur
        nouvelle_hauteur = hauteur_cible
        nouvelle_largeur = int(hauteur_cible * ratio_source)

    logger.debug(
        "Resize fit: %dx%d (ratio %.3f) → %dx%d (ratio %.3f) → canvas %dx%d",
        src_w, src_h, ratio_source,
        nouvelle_largeur, nouvelle_hauteur, ratio_source,
        largeur_cible, hauteur_cible,
    )

    # Redimensionner l'image en préservant le ratio
    img_resized = source.resize(
        (nouvelle_largeur, nouvelle_hauteur), Image.LANCZOS
    )

    # Créer le canvas de la taille cible et centrer l'image
    canvas = Image.new("RGB", (largeur_cible, hauteur_cible), couleur_fond)
    offset_x = (largeur_cible - nouvelle_largeur) // 2
    offset_y = (hauteur_cible - nouvelle_hauteur) // 2
    canvas.paste(img_resized, (offset_x, offset_y))

    # Sauvegarder
    canvas.save(sortie, "JPEG", quality=95)

    taille_finale = Path(sortie).stat().st_size
    logger.info(
        "Resize fit %s: %dx%d → %dx%d (canvas %dx%d, %d KB, ratio préservé)",
        resolution,
        src_w, src_h,
        nouvelle_largeur, nouvelle_hauteur,
        largeur_cible, hauteur_cible,
        taille_finale // 1024,
    )


def resize_fit_png_temp(chemin_source: str, resolution: str) -> str:
    """
    Redimensionne une image en préservant le ratio, retourne
    un chemin temporaire PNG (utilisé comme entrée pour FSRCNN).

    Args:
        chemin_source: Image source
        resolution: Résolution cible

    Returns:
        Chemin du fichier PNG temporaire
    """
    import tempfile

    source = Image.open(chemin_source).convert("RGB")
    src_w, src_h = source.size

    if resolution not in RESOLUTIONS:
        resolution = "720p"

    largeur_cible, hauteur_cible = RESOLUTIONS[resolution]

    # Même logique de ratio
    ratio_cible = largeur_cible / hauteur_cible
    ratio_source = src_w / src_h

    if ratio_source > ratio_cible:
        nouvelle_largeur = largeur_cible
        nouvelle_hauteur = int(largeur_cible / ratio_source)
    else:
        nouvelle_hauteur = hauteur_cible
        nouvelle_largeur = int(hauteur_cible * ratio_source)

    img_resized = source.resize(
        (nouvelle_largeur, nouvelle_hauteur), Image.LANCZOS
    )

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img_resized.save(tmp.name, "PNG")
    return tmp.name
