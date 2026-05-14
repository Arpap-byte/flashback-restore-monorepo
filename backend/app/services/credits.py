"""
Service de gestion des crédits et essais gratuits.

Centralise la logique de vérification et consommation des crédits/essais
pour les opérations de restauration et d'animation.

Cas gérés :
- Crédits payants vs essais gratuits (priorité aux essais)
- Limite mensuelle d'animations par forfait
- Quota dépassé (crédits insuffisants, limite mensuelle atteinte)
"""

import logging

from app.db.queries import (
    consommer_credit,
    enregistrer_animation,
    obtenir_credits_restants,
    peut_animer as _db_peut_animer,
    rembourser_credit,
)

logger = logging.getLogger(__name__)


async def peut_restaurer(utilisateur_id: str) -> tuple[bool, str]:
    """
    Vérifie si l'utilisateur peut effectuer une restauration.

    Un crédit payant OU un essai gratuit est requis.

    Args:
        utilisateur_id: Identifiant de l'utilisateur.

    Returns:
        tuple[bool, str]: (autorisé, raison du refus si non autorisé).
    """
    credits_info = await obtenir_credits_restants(utilisateur_id)
    if credits_info["essais_restants"] > 0 or credits_info["credits"] > 0:
        return (True, "")
    return (False, "Crédits insuffisants. Achetez des crédits pour continuer.")


async def peut_animer(utilisateur_id: str) -> tuple[bool, str]:
    """
    Vérifie si l'utilisateur peut créer une animation.

    Deux conditions sont vérifiées :
    1. Disponibilité d'au moins 1 crédit payant OU 1 essai gratuit.
    2. Respect de la limite mensuelle d'animations par forfait.

    Args:
        utilisateur_id: Identifiant de l'utilisateur.

    Returns:
        tuple[bool, str]: (autorisé, raison du refus si non autorisé).
    """
    # 1. Vérifier la disponibilité de crédits/essais
    credits_info = await obtenir_credits_restants(utilisateur_id)
    if credits_info["essais_restants"] <= 0 and credits_info["credits"] <= 0:
        return (
            False,
            f"Crédits insuffisants (crédits restants : {credits_info['credits']}, "
            f"essais gratuits : {credits_info['essais_restants']}). "
            "Achetez des crédits pour continuer.",
        )

    # 2. Vérifier les limites d'animation par forfait
    verif = await _db_peut_animer(utilisateur_id)
    if not verif["autorise"]:
        return (
            False,
            f"{verif['raison']} "
            f"(crédits : {credits_info['credits']}, "
            f"essais : {credits_info['essais_restants']}, "
            f"animations utilisées : {verif.get('utilisees', '?')}/{verif.get('limite', '?')})",
        )

    return (True, "")


async def consommer_operation(utilisateur_id: str, type_operation: str, travail_id: str) -> None:
    """
    Consomme un crédit ou essai gratuit pour une opération.

    La priorité est donnée aux essais gratuits, puis aux crédits payants.
    Pour les animations, le compteur mensuel est également incrémenté.

    Args:
        utilisateur_id: Identifiant de l'utilisateur.
        type_operation: "restauration" ou "animation".
        travail_id: Identifiant du travail associé.

    Raises:
        RuntimeError: Si la consommation échoue (crédits/essais épuisés).
    """
    resultat = await consommer_credit(utilisateur_id, type_operation, travail_id)
    if not resultat["succes"]:
        raise RuntimeError(resultat.get("raison", "Crédits insuffisants"))

    # Pour les animations, incrémenter le compteur mensuel
    if type_operation == "animation":
        await enregistrer_animation(utilisateur_id)
        logger.info(
            f"Animation enregistrée pour utilisateur={utilisateur_id}, "
            f"travail={travail_id}"
        )
    else:
        logger.info(
            f"Crédit consommé pour {type_operation}, "
            f"utilisateur={utilisateur_id}, travail={travail_id}"
        )


async def rembourser_operation(utilisateur_id: str, travail_id: str) -> dict:
    """
    Rembourse un crédit/essai pour une opération annulée ou échouée.

    Utilisé quand le traitement externe (ex: Veo) échoue APRÈS
    que le crédit a été consommé (filtre sécurité, erreur API, etc.).

    Args:
        utilisateur_id: Identifiant de l'utilisateur.
        travail_id: Identifiant du travail associé à la consommation.

    Returns:
        dict: {"succes": bool, "type": "essai"|"credit"|"aucun", "message": str}
    """
    resultat = await rembourser_credit(utilisateur_id, travail_id)
    if resultat["succes"]:
        logger.info(
            f"Remboursement {resultat['type']} — "
            f"utilisateur={utilisateur_id}, travail={travail_id}"
        )
    else:
        logger.warning(
            f"Échec remboursement — utilisateur={utilisateur_id}, "
            f"travail={travail_id}: {resultat['message']}"
        )
    return resultat
