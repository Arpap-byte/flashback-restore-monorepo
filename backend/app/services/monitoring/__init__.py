"""
Monitoring quotidien — Flashback Restore.

Package modulaire pour la collecte de métriques, le rendu HTML/texte,
et l'envoi par email des rapports de santé du site.

Exports :
- run_daily_report() → rapport complet (7h et 18h, heure de Paris)
- run_alert_check()   → vérification seuils critiques (toutes les 15 min)
"""

from app.services.monitoring.collectors import collect_all, collect_critical_only
from app.services.monitoring.renderer import render_report
from app.services.monitoring.mailer import send_report
from app.services.monitoring.alerting import evaluate_alerts, dedup_alerts

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Destinataire des rapports et alertes
RECIPIENT = "sebastien.archeny@gmail.com"

# Seuils critiques
CRITICAL_SSL_DAYS = 3
WARNING_SSL_DAYS = 14
CRITICAL_DISK_PCT = 95
WARNING_DISK_PCT = 85
CRITICAL_RAM_PCT = 90
WARNING_RAM_PCT = 80
STUCK_JOB_HOURS = 2
ARQ_SILENT_MINUTES = 30


async def run_daily_report() -> dict:
    """
    Rapport quotidien complet — envoyé à 7h et 18h (heure de Paris).

    Collecte toutes les métriques, évalue les alertes, génère le HTML/texte,
    et envoie par email à sebastien.archeny@gmail.com.
    """
    logger.info("📊 [Monitoring] Démarrage du rapport quotidien...")
    try:
        snapshot = await collect_all()
        alerts = evaluate_alerts(snapshot)
        html_body, text_body = render_report(snapshot, alerts)
        success = await send_report(
            to=RECIPIENT,
            subject=f"📊 Flashback Restore — Rapport du {snapshot['date_fr']}",
            html_body=html_body,
            text_body=text_body,
        )
        logger.info(
            "✅ [Monitoring] Rapport envoyé : %s services, %s travaux, %s alertes",
            len(snapshot["services"]),
            snapshot["travaux"]["total_24h"],
            len(alerts),
        )
        return {"sent": success, "alerts": len(alerts), "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception:
        logger.exception("❌ [Monitoring] Erreur lors du rapport quotidien")
        # Tentative d'email d'urgence
        try:
            await send_report(
                to=RECIPIENT,
                subject="🚨 Flashback Restore — ÉCHEC du rapport de monitoring",
                html_body="<p>Le rapport de monitoring n'a pas pu être généré. Vérifiez les logs du backend.</p>",
                text_body="Le rapport de monitoring n'a pas pu être généré. Vérifiez les logs du backend.",
            )
        except Exception:
            logger.exception("❌ Email d'urgence également en échec")
        raise


async def run_alert_check() -> dict:
    """
    Vérification des seuils critiques — toutes les 15 minutes.

    Collecte uniquement les métriques critiques (services, ARQ, disque, SSL)
    et envoie un email d'alerte si un seuil est franchi (avec déduplication).
    """
    logger.debug("🔍 [Monitoring] Vérification alertes...")
    try:
        snapshot = await collect_critical_only()
        alerts = evaluate_alerts(snapshot)
        alerts = dedup_alerts(alerts)

        if alerts:
            html_body, text_body = render_report(snapshot, alerts, mode="alert")
            await send_report(
                to=RECIPIENT,
                subject=f"🚨 Flashback Restore — {len(alerts)} alerte(s) critique(s)",
                html_body=html_body,
                text_body=text_body,
            )
            logger.warning("🚨 [Monitoring] %s alerte(s) envoyée(s)", len(alerts))

        return {"alerts_fired": len(alerts), "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception:
        logger.exception("❌ [Monitoring] Erreur lors de la vérification des alertes")
        raise
