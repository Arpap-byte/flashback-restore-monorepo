"""
Routes utilisateur.

Endpoints :
- GET /api/user/trials  : Récupérer les essais gratuits restants
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import exiger_utilisateur
from app.db.database import lister_travaux_par_utilisateur, obtenir_essais_restants

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/trials")
async def trials(utilisateur: dict = Depends(exiger_utilisateur)):
    """
    Retourne le nombre d'essais gratuits restants et le statut d'abonnement.
    Nécessite un token JWT valide.
    """
    essais = obtenir_essais_restants(utilisateur["id"])
    if essais is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    return {
        "essais_restants": essais["essais_restants"],
        "est_abonne": essais["est_abonne"],
    }


@router.get("/history")
async def history(
    utilisateur: dict = Depends(exiger_utilisateur),
    limite: int = 50,
):
    """
    Retourne l'historique des travaux de l'utilisateur connecté.

    Les travaux sont triés du plus récent au plus ancien.
    Nécessite un token JWT valide.
    """
    travaux = lister_travaux_par_utilisateur(utilisateur["id"], limite)
    return {
        "travaux": [
            {
                "id": t["id"],
                "type": t["type"],
                "statut": t["statut"],
                "chemin_photo": t.get("chemin_photo"),
                "chemin_resultat": t.get("chemin_resultat"),
                "message_erreur": t.get("message_erreur"),
                "cree_le": t["cree_le"],
            }
            for t in travaux
        ]
    }
