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
    consommer_credits,
    obtenir_credits_restants,
    peut_animer as _db_peut_animer,
    rembourser_credit,
)

logger = logging.getLogger(__name__)


async def peut_restaurer(utilisateur_id: str, nb_credits: int = 1) -> tuple[bool, str]:
    """
    Vérifie si l'utilisateur peut effectuer une restauration.

    Vérifie que l'utilisateur dispose bien de nb_credits (essais + crédits payants).

    Args:
        utilisateur_id: Identifiant de l'utilisateur.
        nb_credits: Nombre de crédits requis (défaut: 1).

    Returns:
        tuple[bool, str]: (autorisé, raison du refus si non autorisé).
    """
    credits_info = await obtenir_credits_restants(utilisateur_id)
    total = (
        credits_info.get("credits", 0)
        + credits_info.get("credits_perpetuels", 0)
        + credits_info.get("essais_restants", 0)
    )
    if total >= nb_credits:
        return (True, "")
    return (
        False,
        f"Crédits insuffisants ({total} disponible(s), {nb_credits} requis). "
        "Achetez des crédits pour continuer.",
    )


async def peut_animer(utilisateur_id: str, nb_credits: int = 1) -> tuple[bool, str]:
    """
    Vérifie si l'utilisateur peut créer une animation.

    Deux conditions sont vérifiées :
    1. Disponibilité d'au moins nb_credits (essais + crédits payants).
    2. Respect de la limite mensuelle d'animations par forfait.

    Args:
        utilisateur_id: Identifiant de l'utilisateur.
        nb_credits: Nombre de crédits requis (défaut: 1).

    Returns:
        tuple[bool, str]: (autorisé, raison du refus si non autorisé).
    """
    # 1. Vérifier la disponibilité de crédits/essais
    credits_info = await obtenir_credits_restants(utilisateur_id)
    total = credits_info.get("essais_restants", 0) + credits_info.get("credits", 0)
    if total < nb_credits:
        return (
            False,
            f"Crédits insuffisants ({total} disponible(s), {nb_credits} requis). "
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


async def consommer_operation(
    utilisateur_id: str, type_operation: str, travail_id: str, nb_credits: int = 1
) -> None:
    """
    Consomme un ou plusieurs crédits/essais pour une opération.

    La priorité est donnée aux essais gratuits, puis aux crédits payants.
    Pour les animations, le compteur mensuel est également incrémenté.

    Args:
        utilisateur_id: Identifiant de l'utilisateur.
        type_operation: "restauration" ou "animation".
        travail_id: Identifiant du travail associé.
        nb_credits: Nombre de crédits à consommer (défaut: 1).

    Raises:
        RuntimeError: Si la consommation échoue (crédits/essais épuisés).
    """
    resultat = await consommer_credits(utilisateur_id, type_operation, travail_id, nb_credits)
    if not resultat["succes"]:
        raise RuntimeError(resultat.get("raison", "Crédits insuffisants"))

    # NOTE: l'enregistrement du compteur mensuel d'animations n'est PAS fait ici.
    # Il est appelé une seule fois dans la route /api/animate (avant la boucle
    # de consommation des crédits) pour éviter d'incrémenter N fois.
    logger.info(
        f"{nb_credits} crédit(s) consommé(s) pour {type_operation} "
        f"(essais={resultat['nb_essais']}, payants={resultat['nb_payants']}), "
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
