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

from app.db.database import (
    consommer_credit,
    enregistrer_animation,
    obtenir_credits_restants,
    peut_animer as _db_peut_animer,
)

logger = logging.getLogger(__name__)


def peut_restaurer(utilisateur_id: str) -> tuple[bool, str]:
    """
    Vérifie si l'utilisateur peut effectuer une restauration.

    Un crédit payant OU un essai gratuit est requis.

    Args:
        utilisateur_id: Identifiant de l'utilisateur.

    Returns:
        tuple[bool, str]: (autorisé, raison du refus si non autorisé).
    """
    credits_info = obtenir_credits_restants(utilisateur_id)
    if credits_info["essais_restants"] > 0 or credits_info["credits"] > 0:
        return (True, "")
    return (False, "Crédits insuffisants. Achetez des crédits pour continuer.")


def peut_animer(utilisateur_id: str) -> tuple[bool, str]:
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
    credits_info = obtenir_credits_restants(utilisateur_id)
    if credits_info["essais_restants"] <= 0 and credits_info["credits"] <= 0:
        return (False, "Crédits insuffisants. Achetez des crédits pour continuer.")

    # 2. Vérifier les limites d'animation par forfait
    verif = _db_peut_animer(utilisateur_id)
    if not verif["autorise"]:
        return (False, verif["raison"])

    return (True, "")


def consommer_operation(utilisateur_id: str, type_operation: str, travail_id: str) -> None:
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
    resultat = consommer_credit(utilisateur_id, type_operation, travail_id)
    if not resultat["succes"]:
        raise RuntimeError(resultat.get("raison", "Crédits insuffisants"))

    # Pour les animations, incrémenter le compteur mensuel
    if type_operation == "animation":
        enregistrer_animation(utilisateur_id)
        logger.info(
            f"Animation enregistrée pour utilisateur={utilisateur_id}, "
            f"travail={travail_id}"
        )
    else:
        logger.info(
            f"Crédit consommé pour {type_operation}, "
            f"utilisateur={utilisateur_id}, travail={travail_id}"
        )
