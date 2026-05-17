"""
Planificateur de tâches backend — Flashback Restore.

Gère les jobs périodiques sans intervention humaine :
- Nettoyage quotidien des travaux expirés (3h UTC)
- Backup PostgreSQL quotidien + upload B2 (3h UTC)

Les rapports sont envoyés sur Google Drive (apexcyber.eu@gmail.com).

Intégré dans le cycle de vie FastAPI (startup/shutdown).
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Retourne l'instance unique du planificateur (créée au besoin)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,          # Évite l'empilement si un job précédent traîne
                "max_instances": 1,        # Une seule instance à la fois
                "misfire_grace_time": 300, # 5 min de tolérance
            },
        )
    return _scheduler


async def run_cleanup_job() -> dict:
    """
    Exécute le nettoyage et envoie le rapport sur Google Drive.
    Appelée directement par le scheduler — pas de HTTP.
    """
    from app.services.cleanup import nettoyer_uploads, exporter_rapport_cleanup

    logger.info("🧹 [Scheduler] Démarrage du nettoyage quotidien...")
    try:
        resultat = await nettoyer_uploads()
        logger.info(
            "✅ [Scheduler] Nettoyage terminé : %s travaux, %s fichiers, %s erreurs",
            resultat["travaux_supprimes"],
            resultat["fichiers_supprimes"],
            resultat["erreurs"],
        )

        # Export rapport + upload Drive
        await exporter_rapport_cleanup(resultat)

    except Exception:
        logger.exception("❌ [Scheduler] Erreur lors du nettoyage quotidien")
        raise

    return resultat


async def run_backup_job() -> dict:
    """
    Exécute le backup PostgreSQL et envoie le rapport sur Google Drive.
    """
    from app.services.backup import backup_postgresql, exporter_rapport_backup

    logger.info("💾 [Scheduler] Démarrage du backup PostgreSQL quotidien...")
    try:
        resultat = await backup_postgresql()
        logger.info(
            "✅ [Scheduler] Backup terminé : dump=%s, B2=%s, erreurs=%s",
            resultat["dump_taille"],
            "OK" if resultat["b2_upload"] else "SKIP",
            resultat["erreurs"],
        )

        # Export rapport + upload Drive
        await exporter_rapport_backup(resultat)

    except Exception:
        logger.exception("❌ [Scheduler] Erreur lors du backup quotidien")
        raise

    return resultat


def demarrer_scheduler():
    """Démarre le planificateur avec les 2 jobs quotidiens."""
    scheduler = get_scheduler()

    # ── Job 1 : Nettoyage ──
    scheduler.add_job(
        run_cleanup_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_quotidien",
        name="Nettoyage travaux expirés",
        replace_existing=True,
    )

    # ── Job 2 : Backup ──
    scheduler.add_job(
        run_backup_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="backup_quotidien",
        name="Backup PostgreSQL + B2",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("📅 Scheduler démarré — nettoyage + backup programmés à 3h UTC chaque jour")


def arreter_scheduler():
    """Arrête proprement le planificateur."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("📅 Scheduler arrêté")
    _scheduler = None
