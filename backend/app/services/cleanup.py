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
            date_expiration = travail.cree_le + timedelta(days=retention)

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


def nettoyer_uploads() -> dict:
    """Wrapper sync pour le endpoint admin /api/admin/cleanup."""
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_nettoyer_async())
