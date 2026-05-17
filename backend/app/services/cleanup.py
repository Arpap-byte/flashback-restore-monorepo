"""
Service de nettoyage des travaux expirés.

Pour chaque travail terminé ou en erreur, vérifie si sa date de création
dépasse la rétention configurée par son propriétaire. Supprime les 3
fichiers (original, résultat, animation) et l'enregistrement DB.

Contrairement à l'ancienne version (30 jours fixe), ce service utilise
la colonne utilisateurs.retention_jours (7, 30 ou 90 jours).
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from app.db.session import async_session
from app.models.db_models import Travail, Utilisateur
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def _nettoyer_async() -> dict:
    """
    Scanne les travaux terminés/en erreur et supprime ceux dont la date
    de création dépasse la rétention configurée par leur propriétaire.

    Returns:
        dict avec travaux_supprimes, fichiers_supprimes, espace_libere_octets, erreurs
    """
    maintenant = datetime.now(timezone.utc)
    fichiers_supprimes = 0
    espace_libere = 0
    travaux_supprimes = 0
    erreurs = 0

    async with async_session() as session:
        # Jointure travaux + utilisateurs pour obtenir la rétention
        stmt = (
            select(Travail, Utilisateur.retention_jours)
            .join(Utilisateur, Travail.utilisateur_id == Utilisateur.id)
            .where(Travail.statut.in_(['termine', 'erreur']))
        )
        result = await session.execute(stmt)
        rows = result.all()

        for travail, retention in rows:
            retention = retention or 30
            cree_le = travail.cree_le
            if cree_le.tzinfo is None:
                cree_le = cree_le.replace(tzinfo=timezone.utc)
            date_expiration = cree_le + timedelta(days=retention)

            if maintenant <= date_expiration:
                continue  # Pas encore expiré

            # Supprimer les 3 fichiers
            for chemin in [travail.chemin_photo, travail.chemin_resultat, travail.chemin_animation]:
                if chemin and os.path.isfile(chemin):
                    try:
                        taille = os.path.getsize(chemin)
                        os.remove(chemin)
                        fichiers_supprimes += 1
                        espace_libere += taille
                        logger.info(f"Supprimé : {os.path.basename(chemin)} ({taille} octets)")
                    except OSError as e:
                        erreurs += 1
                        logger.error(f"Erreur suppression {chemin}: {e}")

            # Supprimer l'enregistrement DB
            await session.delete(travail)
            travaux_supprimes += 1

        await session.commit()

    logger.info(
        f"Nettoyage terminé : {travaux_supprimes} travaux supprimés, "
        f"{fichiers_supprimes} fichiers ({espace_libere} octets), {erreurs} erreurs"
    )
    return {
        "travaux_supprimes": travaux_supprimes,
        "fichiers_supprimes": fichiers_supprimes,
        "espace_libere_octets": espace_libere,
        "erreurs": erreurs,
    }


async def nettoyer_uploads() -> dict:
    """Nettoie les travaux expirés (appelé par le endpoint admin /api/admin/cleanup)."""
    return await _nettoyer_async()


# ── Rapport Google Drive ──

GOOGLE_DRIVE_FOLDER = "Flashback Restore — Rapports"


async def exporter_rapport_cleanup(resultat: dict) -> str | None:
    """
    Génère le rapport de nettoyage et l'envoie sur Google Drive.

    Returns:
        L'ID du fichier Drive si uploadé, None sinon.
    """
    import json
    from datetime import datetime, timezone
    from pathlib import Path

    maintenant = datetime.now(timezone.utc)
    date_str = maintenant.strftime("%Y%m%d")

    rapport = {
        "type": "nettoyage_quotidien",
        "service": "Flashback Restore",
        "date": maintenant.isoformat(),
        "travaux_supprimes": resultat["travaux_supprimes"],
        "fichiers_supprimes": resultat["fichiers_supprimes"],
        "espace_libere_octets": resultat["espace_libere_octets"],
        "erreurs": resultat["erreurs"],
    }

    rapport_json = json.dumps(rapport, indent=2, ensure_ascii=False)

    # Sauvegarde locale
    rapport_dir = Path("/root/backups/flashback/rapports")
    rapport_dir.mkdir(parents=True, exist_ok=True)
    rapport_path = rapport_dir / f"rapport_cleanup_{date_str}.json"
    rapport_path.write_text(rapport_json, encoding="utf-8")

    # Upload Google Drive (si OAuth configuré)
    drive_id = await _upload_rapport_drive(rapport_json, f"cleanup_flashback_{date_str}.json")

    if drive_id:
        logger.info("📤 Rapport cleanup uploadé sur Drive: %s", drive_id)
    else:
        logger.info("📤 Rapport cleanup sauvegardé localement (Drive non configuré)")

    return drive_id


async def _upload_rapport_drive(content: str, filename: str) -> str | None:
    """
    Upload un fichier JSON sur Google Drive.

    Args:
        content: Contenu JSON (string)
        filename: Nom du fichier sur Drive

    Returns:
        File ID Drive, ou None si OAuth non configuré
    """
    from app.services.drive_utils import upload_json_to_drive
    return upload_json_to_drive(content, filename)
