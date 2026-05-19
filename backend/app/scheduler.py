"""
Planificateur de tâches backend — Flashback Restore.

Gère les jobs périodiques sans intervention humaine :
- Nettoyage quotidien des travaux expirés (3h UTC)
- Backup PostgreSQL quotidien + upload B2 (3h UTC)
- Rapport monitoring quotidien (5h et 16h UTC -> 7h et 18h Paris)
- Vérification alertes critiques (toutes les 15 min)

Les rapports de maintenance sont uploadés sur Google Drive.
Les rapports de monitoring sont envoyés par email à sebastien.archeny@gmail.com.

Intégré dans le cycle de vie FastAPI (startup/shutdown).
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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


# ── Jobs existants ───────────────────────────────────────

async def run_cleanup_job() -> dict:
    """Exécute le nettoyage et envoie le rapport sur Google Drive."""
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
        await exporter_rapport_cleanup(resultat)
    except Exception:
        logger.exception("❌ [Scheduler] Erreur lors du nettoyage quotidien")
        raise
    return resultat


async def run_backup_job() -> dict:
    """Exécute le backup PostgreSQL et envoie le rapport sur Google Drive."""
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
        await exporter_rapport_backup(resultat)
    except Exception:
        logger.exception("❌ [Scheduler] Erreur lors du backup quotidien")
        raise
    return resultat


# ── Nouveaux jobs — Monitoring ───────────────────────────

async def run_monitoring_report() -> dict:
    """Rapport de monitoring quotidien — envoyé par email à Seb."""
    from app.services.monitoring import run_daily_report

    logger.info("📊 [Scheduler] Génération du rapport de monitoring...")
    try:
        result = await run_daily_report()
        return result
    except Exception:
        logger.exception("❌ [Scheduler] Erreur lors du rapport de monitoring")
        raise


async def run_alert_check() -> dict:
    """Vérification des seuils d'alerte critiques."""
    from app.services.monitoring import run_alert_check as _run_alert_check

    try:
        result = await _run_alert_check()
        if result.get("alerts_fired", 0) > 0:
            logger.warning("🚨 [Scheduler] %s alerte(s) critique(s) détectée(s)", result["alerts_fired"])
        return result
    except Exception:
        logger.exception("❌ [Scheduler] Erreur lors de la vérification des alertes")
        raise


# ── Relance expiration abonnement (P3.4) ─────────────────

async def run_subscription_reminders():
    """
    Vérifie les abonnements expirant dans 3 jours et envoie un email
    de relance pour éviter les interruptions de service.
    """
    try:
        from app.services.stripe_service import obtenir_abonnement_stripe
        from app.db.queries import lister_utilisateurs_abonnes
        import smtplib
        from email.mime.text import MIMEText

        from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

        abonnes = await lister_utilisateurs_abonnes()
        if not abonnes:
            logger.info("📬 [Relances] Aucun abonné à vérifier")
            return {"relances_envoyees": 0}

        relances = 0
        for user in abonnes:
            stripe_customer_id = user.get("stripe_customer_id")
            if not stripe_customer_id:
                continue

            try:
                abo = await obtenir_abonnement_stripe(stripe_customer_id)
                fin_periode = abo.get("fin_periode")
                if not fin_periode:
                    continue

                # Vérifier si la fin de période est dans 3 jours (±12h)
                from datetime import datetime, timezone, timedelta
                maintenant = datetime.now(timezone.utc)
                fin = datetime.fromtimestamp(fin_periode, tz=timezone.utc)
                diff_jours = (fin - maintenant).total_seconds() / 86400

                if 2.5 <= diff_jours <= 3.5:  # fenêtre de ~24h autour de J-3
                    email = user.get("email")
                    if not email:
                        continue

                    msg = MIMEText(
                        f"""Bonjour,

Votre abonnement Flashback Restore arrive à échéance le {fin.strftime('%d/%m/%Y')}.

Pour éviter toute interruption de service, rendez-vous dans votre espace :
https://flashback-restore.com/dashboard

Vos crédits et photos seront préservés.

L'équipe Flashback Restore""",
                        "plain",
                        "utf-8",
                    )
                    msg["Subject"] = "[Flashback Restore] Votre abonnement expire bientôt"
                    msg["From"] = SMTP_FROM
                    msg["To"] = email

                    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
                        s.starttls()
                        s.login(SMTP_USER, SMTP_PASSWORD)
                        s.send_message(msg)

                    relances += 1
                    logger.info(f"📬 [Relances] Email envoyé à {email} (expire le {fin.strftime('%d/%m/%Y')})")

            except Exception as e:
                logger.warning(f"⚠️ [Relances] Erreur pour user={user.get('id')}: {e}")
                continue

        logger.info(f"📬 [Relances] {relances} email(s) de relance envoyé(s)")
        return {"relances_envoyees": relances}

    except Exception:
        logger.exception("❌ [Scheduler] Erreur lors des relances d'expiration")
        return {"relances_envoyees": 0}


# ── Démarrage / Arrêt ────────────────────────────────────

def demarrer_scheduler():
    """Démarre le planificateur avec tous les jobs."""
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = get_scheduler()

    # ── Job 1 : Nettoyage (3h UTC) ──
    scheduler.add_job(
        run_cleanup_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_quotidien",
        name="Nettoyage travaux expirés",
        replace_existing=True,
    )

    # ── Job 2 : Backup PostgreSQL (3h UTC) ──
    scheduler.add_job(
        run_backup_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="backup_quotidien",
        name="Backup PostgreSQL + B2",
        replace_existing=True,
    )

    # ── Job 3 : Rapport monitoring — matin (5h UTC = 7h Paris) ──
    scheduler.add_job(
        run_monitoring_report,
        trigger=CronTrigger(hour=5, minute=0),
        id="monitoring_matin",
        name="Rapport monitoring 7h (Paris)",
        replace_existing=True,
    )

    # ── Job 4 : Rapport monitoring — soir (16h UTC = 18h Paris) ──
    scheduler.add_job(
        run_monitoring_report,
        trigger=CronTrigger(hour=16, minute=0),
        id="monitoring_soir",
        name="Rapport monitoring 18h (Paris)",
        replace_existing=True,
    )

    # ── Job 5 : Vérification alertes critiques (toutes les 15 min) ──
    scheduler.add_job(
        run_alert_check,
        trigger=IntervalTrigger(minutes=15),
        id="alert_check",
        name="Vérification alertes critiques",
        replace_existing=True,
    )

    # ── Job 6 : Relances expiration abonnement (10h UTC = 12h Paris) ──
    scheduler.add_job(
        run_subscription_reminders,
        trigger=CronTrigger(hour=10, minute=0),
        id="subscription_reminders",
        name="Relances expiration abonnement (J-3)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "📅 Scheduler démarré — 6 jobs : cleanup (3h), backup (3h), "
        "monitoring (5h+16h), alertes (15min), relances abo (10h)"
    )


def arreter_scheduler():
    """Arrête proprement le planificateur."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("📅 Scheduler arrêté")
    _scheduler = None
