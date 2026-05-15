"""
Routes utilisateur.

Endpoints :
- GET  /api/user/trials       : Essais gratuits restants
- GET  /api/user/me           : Informations utilisateur
- GET  /api/user/history      : Historique enrichi des travaux
- PUT  /api/user/preferences  : Modifier la rétention
- GET  /api/user/preferences  : Lire la rétention
- DELETE /api/user/history/{travail_id} : Supprimer un travail
- DELETE /api/user/history    : Supprimer tout l'historique
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth import exiger_utilisateur
from app.db.session import async_session
from app.db.queries import (
    ANIMATIONS_PAR_PLAN,
    lister_travaux_par_utilisateur,
    mettre_a_jour_retention,
    obtenir_essais_restants,
    obtenir_plan_utilisateur,
    obtenir_retention,
    obtenir_travail,
    obtenir_utilisateur_par_id,
    supprimer_travail as _supprimer_travail_db,
    supprimer_tous_travaux_utilisateur as _supprimer_tous_db,
)
from app.models.schemas import PreferencesRequete
from sqlalchemy import text as _sa_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/trials")
async def trials(utilisateur: dict = Depends(exiger_utilisateur)):
    """
    Retourne le nombre d'essais gratuits restants et le statut d'abonnement.
    Nécessite un token JWT valide.
    """
    essais = await obtenir_essais_restants(utilisateur["id"])
    if essais is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    return {
        "essais_restants": essais["essais_restants"],
        "est_abonne": essais["est_abonne"],
    }


@router.get("/me")
async def me(utilisateur: dict = Depends(exiger_utilisateur)):
    """
    Retourne les informations complètes de l'utilisateur courant
    (plan, crédits, animations, rétention, etc.).
    Nécessite un token JWT valide.
    """
    detail = await obtenir_utilisateur_par_id(utilisateur["id"])
    if detail is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    essais = await obtenir_essais_restants(utilisateur["id"]) or {
        "essais_restants": 0,
        "est_abonne": False,
    }

    plan = await obtenir_plan_utilisateur(utilisateur["id"])
    animations_limite = ANIMATIONS_PAR_PLAN.get(plan, 0)
    retention = await obtenir_retention(utilisateur["id"])

    # Compter photos restaurées et animations ce mois-ci
    debut_mois = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    async with async_session() as session:
        nb_restaurees = (
            await session.execute(
                _sa_text(
                    "SELECT COUNT(*) FROM travaux WHERE utilisateur_id = :uid AND type = 'restauration' AND cree_le >= :debut"
                ),
                {"uid": utilisateur["id"], "debut": debut_mois},
            )
        ).scalar() or 0

        nb_animations = (
            await session.execute(
                _sa_text(
                    "SELECT COUNT(*) FROM travaux WHERE utilisateur_id = :uid AND type = 'animation' AND cree_le >= :debut"
                ),
                {"uid": utilisateur["id"], "debut": debut_mois},
            )
        ).scalar() or 0

    return {
        "id": detail["id"],
        "email": detail["email"],
        "essais_restants": essais["essais_restants"],
        "est_abonne": essais["est_abonne"],
        "credits": detail.get("credits", 0),
        "plan": plan,
        "animations_utilisees": detail.get("animations_utilisees", 0),
        "animations_limite": animations_limite,
        "photos_restaurees_mois": nb_restaurees,
        "animations_creees": nb_animations,
        "retention_jours": retention,
        "derniere_activite": detail.get("derniere_activite"),
    }


# ---------------------------------------------------------------------------
# Préférences (rétention)
# ---------------------------------------------------------------------------


@router.put("/preferences")
async def preferences(
    body: PreferencesRequete,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Modifie les préférences de l'utilisateur (durée de conservation des photos).
    Valeurs acceptées : 7, 30, 90 (jours).
    """
    if body.retention_jours not in (7, 30, 90):
        raise HTTPException(
            status_code=400,
            detail="La durée de conservation doit être 7, 30 ou 90 jours.",
        )

    ok = await mettre_a_jour_retention(utilisateur["id"], body.retention_jours)
    if not ok:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    return {
        "message": "Préférences mises à jour.",
        "retention_jours": body.retention_jours,
    }


@router.get("/preferences")
async def lire_preferences(utilisateur: dict = Depends(exiger_utilisateur)):
    """Retourne les préférences de l'utilisateur (durée de conservation)."""
    retention = await obtenir_retention(utilisateur["id"])
    return {
        "retention_jours": retention,
        "options_disponibles": [7, 30, 90],
    }


# ---------------------------------------------------------------------------
# Historique des travaux
# ---------------------------------------------------------------------------


def _vers_url(chemin: str | None, utilisateur_id: str) -> str | None:
    """Convertit un chemin absolu en URL publique relative avec token de téléchargement."""
    if not chemin:
        return None
    from app.auth import creer_token_telechargement

    nom_fichier = os.path.basename(chemin)
    url = f"/uploads/{nom_fichier}"
    token_dl = creer_token_telechargement(utilisateur_id)
    url += f"?token_dl={token_dl}"
    return url


@router.get("/history")
async def history(
    utilisateur: dict = Depends(exiger_utilisateur),
    limite: int = 50,
    request: Request = None,  # type: ignore[assignment]
):
    """
    Retourne l'historique enrichi des travaux de l'utilisateur connecté.
    
    Chaque travail inclut :
    - URLs des 3 versions (original, résultat, animation) avec token d'accès
    - Tailles de fichiers
    - Date d'expiration calculée selon la rétention configurée
    """
    # Générer un token de téléchargement dédié pour les URLs
    from app.auth import creer_token_telechargement

    token_dl = creer_token_telechargement(utilisateur["id"])

    travaux = await lister_travaux_par_utilisateur(utilisateur["id"], limite)
    retention = await obtenir_retention(utilisateur["id"])

    resultat = []
    for t in travaux:
        cree_le = t.get("cree_le")
        expire_le = None
        if cree_le:
            if isinstance(cree_le, str):
                cree_dt = datetime.fromisoformat(cree_le.replace("Z", "+00:00"))
            else:
                cree_dt = cree_le
            expire_dt = cree_dt + timedelta(days=retention)
            expire_le = expire_dt.isoformat()

        resultat.append({
            "id": t["id"],
            "type": t["type"],
            "statut": t["statut"],
            "url_original": _vers_url(t.get("chemin_photo"), utilisateur["id"]),
            "url_resultat": _vers_url(t.get("chemin_resultat"), utilisateur["id"]),
            "url_animation": _vers_url(t.get("chemin_animation"), utilisateur["id"]),
            "taille_original": t.get("taille_original"),
            "taille_resultat": t.get("taille_resultat"),
            "message_erreur": t.get("message_erreur"),
            "cree_le": cree_le.isoformat() if hasattr(cree_le, 'isoformat') else str(cree_le) if cree_le else None,
            "expire_le": expire_le,
        })

    return {
        "travaux": resultat,
        "retention_jours": retention,
        "total": len(resultat),
    }


# ---------------------------------------------------------------------------
# Suppression de travaux
# ---------------------------------------------------------------------------


@router.delete("/history/{travail_id}")
async def supprimer_travail_endpoint(
    travail_id: str,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Supprime un travail spécifique et tous ses fichiers associés
    (photo originale, résultat, animation). L'utilisateur doit être
    propriétaire du travail.
    """
    travail = await obtenir_travail(travail_id)
    if travail is None:
        raise HTTPException(status_code=404, detail="Travail introuvable.")
    if travail.get("utilisateur_id") != utilisateur["id"]:
        raise HTTPException(status_code=403, detail="Ce travail ne vous appartient pas.")

    # Supprimer les fichiers physiques
    fichiers_supprimes = []
    for champ in ["chemin_photo", "chemin_resultat", "chemin_animation"]:
        chemin = travail.get(champ)
        if chemin and os.path.isfile(chemin):
            try:
                os.remove(chemin)
                fichiers_supprimes.append(champ)
            except OSError as e:
                logger.warning(f"Impossible de supprimer {chemin}: {e}")

    # Supprimer l'enregistrement en base
    await _supprimer_travail_db(travail_id)

    return {
        "message": "Travail supprimé.",
        "fichiers_supprimes": fichiers_supprimes,
    }


@router.delete("/history")
async def supprimer_tout_historique(
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Supprime TOUS les travaux de l'utilisateur et leurs fichiers associés.
    ⚠️ Action irréversible.
    """
    # Récupérer tous les travaux pour supprimer les fichiers
    tous_les_travaux = await lister_travaux_par_utilisateur(utilisateur["id"], limite=10000)

    fichiers_supprimes = 0
    for travail in tous_les_travaux:
        for champ in ["chemin_photo", "chemin_resultat", "chemin_animation"]:
            chemin = travail.get(champ)
            if chemin and os.path.isfile(chemin):
                try:
                    os.remove(chemin)
                    fichiers_supprimes += 1
                except OSError:
                    pass

    nb_supprimes = await _supprimer_tous_db(utilisateur["id"])

    return {
        "message": f"{nb_supprimes} travaux supprimés.",
        "travaux_supprimes": nb_supprimes,
        "fichiers_supprimes": fichiers_supprimes,
    }
