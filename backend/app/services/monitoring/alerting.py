"""
Système d'alertes avec seuils et déduplication — Flashback Restore.

Les alertes critiques sont envoyées immédiatement (toutes les 15 min).
Les warnings sont inclus dans le rapport quotidien.

Déduplication : une alerte déjà envoyée dans les 6h n'est pas renvoyée.
"""

import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# ── Déduplication (in-memory, reset au redémarrage du backend) ──

_alert_state: dict[str, datetime] = {}
_DEDUP_HOURS = 6


def _should_send(alert_id: str) -> bool:
    """Vérifie si l'alerte doit être envoyée (pas déjà envoyée dans les 6h)."""
    last_sent = _alert_state.get(alert_id)
    if last_sent is None:
        return True
    return (datetime.now(timezone.utc) - last_sent) > timedelta(hours=_DEDUP_HOURS)


def _mark_sent(alert_id: str) -> None:
    """Marque une alerte comme envoyée."""
    _alert_state[alert_id] = datetime.now(timezone.utc)


# ── Évaluation des seuils ────────────────────────────────

def evaluate_alerts(snapshot: dict) -> list[dict]:
    """
    Évalue tous les seuils et retourne la liste des alertes déclenchées.

    Chaque alerte = {id, level, message, type}
    """
    alerts = []
    services = snapshot.get("services", {})
    ssl_info = snapshot.get("ssl") or {}
    db = snapshot.get("db", {})
    system = snapshot.get("system", {})
    arq = snapshot.get("arq", {})

    # ── CRITIQUE : Services down ──
    if not services:
        alerts.append({
            "id": "collector_failure",
            "level": "CRITIQUE",
            "message": "Impossible de collecter l'état des services",
            "type": "system",
        })
    else:
        for svc_name in ["flashback-backend", "flashback-arq-worker", "flashback-landing"]:
            if svc_name in services and not services[svc_name]:
                alerts.append({
                    "id": f"service_{svc_name}",
                    "level": "CRITIQUE",
                    "message": f"Service INACTIF : {svc_name}",
                    "type": "service",
                })

        for container in ["flashback-db", "traefik"]:
            if container in services and not services[container]:
                alerts.append({
                    "id": f"container_{container}",
                    "level": "CRITIQUE",
                    "message": f"Conteneur Docker DOWN : {container}",
                    "type": "service",
                })

        # Backend health endpoint
        if not services.get("backend_health", True):
            alerts.append({
                "id": "backend_health",
                "level": "CRITIQUE",
                "message": "Endpoint /api/health du backend ne répond pas",
                "type": "service",
            })

        # Frontend
        if not services.get("frontend_health", True):
            alerts.append({
                "id": "frontend_health",
                "level": "CRITIQUE",
                "message": "Frontend Next.js ne répond pas (200)",
                "type": "service",
            })

    # ── SSL ──
    ssl_days = ssl_info.get("days_left")
    if ssl_days is not None:
        if ssl_days <= 3:
            alerts.append({
                "id": "ssl_expiring",
                "level": "CRITIQUE",
                "message": f"Certificat SSL expire dans {ssl_days} jours !",
                "type": "ssl",
            })
        elif ssl_days <= 14:
            alerts.append({
                "id": "ssl_warning",
                "level": "WARNING",
                "message": f"Certificat SSL expire dans {ssl_days} jours",
                "type": "ssl",
            })

    # ── Travaux coincés ──
    stuck = db.get("travaux_coinces", [])
    if isinstance(stuck, list) and len(stuck) > 0:
        level = "CRITIQUE" if len(stuck) >= 5 else "WARNING"
        alerts.append({
            "id": "stuck_jobs",
            "level": level,
            "message": f"{len(stuck)} travail(aux) bloqué(s) en 'en_cours' depuis >2h",
            "type": "jobs",
        })

    # ── Erreurs jobs ──
    t24 = db.get("travaux_24h", {})
    if isinstance(t24, dict):
        total_24h = t24.get("total_24h", 0)
        erreurs_24h = t24.get("erreurs_24h", 0)
        if total_24h > 0 and (erreurs_24h / total_24h) > 0.2:
            alerts.append({
                "id": "high_error_rate",
                "level": "WARNING",
                "message": f"Taux d'erreur élevé : {erreurs_24h}/{total_24h} travaux en erreur (24h)",
                "type": "jobs",
            })

    # ── ARQ Worker ──
    if not arq.get("worker_ok", True):
        alerts.append({
            "id": "arq_worker_down",
            "level": "CRITIQUE",
            "message": "Worker ARQ non joignable — les jobs asynchrones ne sont pas traités",
            "type": "worker",
        })

    # ── Système ──
    disk = system.get("disque", {})
    if isinstance(disk, dict):
        disk_pct = disk.get("pct", 0)
        if disk_pct >= 95:
            alerts.append({
                "id": "disk_critical",
                "level": "CRITIQUE",
                "message": f"Espace disque critique : {disk_pct}% utilisé",
                "type": "system",
            })
        elif disk_pct >= 85:
            alerts.append({
                "id": "disk_warning",
                "level": "WARNING",
                "message": f"Espace disque élevé : {disk_pct}% utilisé",
                "type": "system",
            })

    ram = system.get("ram", {})
    if isinstance(ram, dict):
        ram_pct = ram.get("pct", 0)
        if ram_pct >= 90:
            alerts.append({
                "id": "ram_critical",
                "level": "CRITIQUE",
                "message": f"Mémoire RAM critique : {ram_pct}% utilisée",
                "type": "system",
            })
        elif ram_pct >= 80:
            alerts.append({
                "id": "ram_warning",
                "level": "WARNING",
                "message": f"Mémoire RAM élevée : {ram_pct}% utilisée",
                "type": "system",
            })

    return alerts


def dedup_alerts(alerts: list[dict]) -> list[dict]:
    """
    Filtre les alertes déjà envoyées récemment.
    Marque les nouvelles comme envoyées.
    """
    filtered = []
    for alert in alerts:
        alert_id = alert.get("id")
        if alert_id and _should_send(alert_id):
            filtered.append(alert)
            _mark_sent(alert_id)

    skipped = len(alerts) - len(filtered)
    if skipped > 0:
        logger.debug("Déduplication : %s alerte(s) ignorée(s) (déjà envoyées)", skipped)

    return filtered
