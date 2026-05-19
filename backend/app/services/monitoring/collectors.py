"""
Collecteurs de métriques — Flashback Restore.

Deux niveaux de collecte :
- collect_all() → rapport complet (quotidien)
- collect_critical_only() → métriques critiques uniquement (alertes 15 min)

Chaque collecteur est indépendant : si l'un échoue, les autres continuent.
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime, timezone, timedelta

import psutil

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────

async def _run(*args: str, timeout: float = 5.0) -> str:
    """Exécute une commande shell avec timeout."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode("utf-8", errors="replace").strip()
    except asyncio.TimeoutError:
        return ""
    except Exception as e:
        logger.warning("Commande échouée: %s — %s", " ".join(args), e)
        return ""


async def _db_query(query: str, params: dict | None = None) -> list[dict]:
    """Exécute une requête SQL read-only sur PostgreSQL et retourne les résultats."""
    try:
        from app.db.session import async_session
        from sqlalchemy import text as sa_text

        async with async_session() as session:
            result = await session.execute(sa_text(query), params or {})
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.warning("Requête DB échouée: %s — %s", query[:80], e)
        return []


# ── Collecteurs ──────────────────────────────────────────

async def collect_services() -> dict:
    """État des services systemd et conteneurs Docker."""
    services = {}

    # Services systemd
    for svc in ["flashback-backend", "flashback-arq-worker", "flashback-landing"]:
        out = await _run("systemctl", "is-active", svc)
        services[svc] = out == "active"

    # Conteneurs Docker
    for container in ["flashback-db", "traefik"]:
        out = await _run("docker", "inspect", "-f", "{{.State.Status}}", container)
        services[container] = out == "running"

    # Health check backend
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            t0 = datetime.now()
            r = await client.get("http://localhost:8000/api/health")
            elapsed = (datetime.now() - t0).total_seconds()
            services["backend_health"] = r.status_code == 200
            services["backend_latency_ms"] = round(elapsed * 1000)
    except Exception:
        services["backend_health"] = False
        services["backend_latency_ms"] = None

    # Health check frontend
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:8001/")
            services["frontend_health"] = r.status_code == 200
    except Exception:
        services["frontend_health"] = False

    # Tous les services OK ?
    services["all_ok"] = all(v for k, v in services.items() if isinstance(v, bool))

    return services


async def collect_ssl() -> dict:
    """Expiration du certificat SSL via pipe openssl."""
    import ssl as _ssl_module
    import socket

    days_left = None
    expiry_date = None

    try:
        # Approche Python native : plus fiable que subprocess + pipe
        ctx = _ssl_module.create_default_context()
        with socket.create_connection(("flashback-restore.com", 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname="flashback-restore.com") as ssock:
                cert = ssock.getpeercert()
                not_after = cert.get("notAfter")
                if not_after:
                    expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                    days_left = (expiry - datetime.now(timezone.utc)).days
                    expiry_date = expiry.strftime("%d/%m/%Y")
    except Exception as e:
        logger.warning("SSL check échoué: %s", e)

    return {
        "days_left": days_left,
        "expiry_date": expiry_date,
        "ok": days_left is not None and days_left > 3,
    }


async def collect_db_metrics() -> dict:
    """Métriques base de données : utilisateurs, travaux, erreurs."""
    # Utilisateurs
    users = await _db_query("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE cree_le >= NOW() - INTERVAL '24 hours') as nouveaux_24h,
            COUNT(*) FILTER (WHERE derniere_activite >= NOW() - INTERVAL '7 days') as actifs_7j,
            COUNT(*) FILTER (WHERE plan = 'premium') as premium,
            COUNT(*) FILTER (WHERE plan = 'gratuit') as gratuit
        FROM utilisateurs
    """)
    user_stats = users[0] if users else {}

    # Travaux 24h
    travaux = await _db_query("""
        SELECT
            COUNT(*) as total_24h,
            COUNT(*) FILTER (WHERE statut = 'termine') as succes_24h,
            COUNT(*) FILTER (WHERE statut = 'erreur') as erreurs_24h,
            COUNT(*) FILTER (WHERE statut = 'en_cours') as en_cours_24h,
            COUNT(*) FILTER (WHERE statut = 'en_attente') as en_attente_24h
        FROM travaux
        WHERE cree_le >= NOW() - INTERVAL '24 hours'
    """)
    travaux_stats = travaux[0] if travaux else {}

    # Travaux coincés (en_cours depuis >2h)
    stuck = await _db_query("""
        SELECT t.id, t.type, t.statut, t.cree_le::timestamp(0) as cree_le,
               u.email
        FROM travaux t
        JOIN utilisateurs u ON t.utilisateur_id = u.id
        WHERE t.statut = 'en_cours'
          AND t.cree_le < NOW() - INTERVAL '2 hours'
        ORDER BY t.cree_le
    """)

    # Erreurs récentes (5 dernières)
    errors = await _db_query("""
        SELECT t.type, t.statut, t.cree_le::timestamp(0) as cree_le,
               u.email
        FROM travaux t
        JOIN utilisateurs u ON t.utilisateur_id = u.id
        WHERE t.statut = 'erreur'
        ORDER BY t.cree_le DESC
        LIMIT 5
    """)

    # Travaux 7 jours (pour tendance)
    trend = await _db_query("""
        SELECT DATE(cree_le) as jour, COUNT(*) as nb
        FROM travaux
        WHERE cree_le >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(cree_le)
        ORDER BY jour
    """)

    # Crédits
    credits = await _db_query("""
        SELECT
            COALESCE(SUM(credits), 0) as total_distribues
        FROM utilisateurs
    """)
    credits_stats = credits[0] if credits else {}

    # Stockage
    storage = await _db_query("""
        SELECT
            COALESCE(SUM(taille_original), 0) as total_original_octets,
            COALESCE(SUM(taille_resultat), 0) as total_resultat_octets,
            COUNT(*) FILTER (WHERE chemin_animation IS NOT NULL) as nb_animations
        FROM travaux
    """)
    storage_stats = storage[0] if storage else {}

    return {
        "utilisateurs": user_stats,
        "travaux_24h": travaux_stats,
        "travaux_coinces": [dict(r) for r in stuck],
        "erreurs_recentes": [dict(r) for r in errors],
        "tendance_7j": [dict(r) for r in trend],
        "credits": credits_stats,
        "stockage": storage_stats,
    }


async def collect_system() -> dict:
    """Métriques système : CPU, RAM, disque."""
    # CPU
    load1, load5, load15 = psutil.getloadavg()
    cpu_pct = psutil.cpu_percent(interval=0.1)

    # RAM
    mem = psutil.virtual_memory()

    # Disque
    disk_root = psutil.disk_usage("/")

    # Uploads
    uploads_path = "/opt/flashback-restore-monorepo/backend/uploads"
    uploads_size_mb = 0
    uploads_files = 0
    if os.path.exists(uploads_path):
        total_size = 0
        for dirpath, _, filenames in os.walk(uploads_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                    uploads_files += 1
                except OSError:
                    pass
        uploads_size_mb = round(total_size / (1024 * 1024), 1)

    # Connexions PostgreSQL actives
    pg_conns = await _db_query("SELECT COUNT(*) as nb FROM pg_stat_activity WHERE state = 'active'")
    pg_active = pg_conns[0]["nb"] if pg_conns else 0

    return {
        "cpu": {
            "load_1m": round(load1, 2),
            "load_5m": round(load5, 2),
            "load_15m": round(load15, 2),
            "pct": cpu_pct,
        },
        "ram": {
            "total_gb": round(mem.total / (1024**3), 1),
            "used_gb": round(mem.used / (1024**3), 1),
            "free_gb": round(mem.available / (1024**3), 1),
            "pct": mem.percent,
        },
        "disque": {
            "total_gb": round(disk_root.total / (1024**3), 1),
            "used_gb": round(disk_root.used / (1024**3), 1),
            "free_gb": round(disk_root.free / (1024**3), 1),
            "pct": disk_root.percent,
        },
        "uploads": {
            "taille_mb": uploads_size_mb,
            "fichiers": uploads_files,
        },
        "postgresql": {
            "connexions_actives": pg_active,
        },
    }


async def collect_arq_worker() -> dict:
    """État du worker ARQ et taille de la queue Redis."""
    # Dernière activité du worker (via logs journalctl)
    last_activity = None
    out = await _run(
        "journalctl", "-u", "flashback-arq-worker",
        "--since", "2 hours ago", "--no-pager", "-n", "5",
    )
    if out:
        # Cherche un timestamp dans les logs
        for line in out.split("\n"):
            if line.strip():
                # Format journalctl: "mai 19 04:20:15 hostname ..."
                last_activity = "Récent" if len(out.split("\n")) > 0 else "Inconnu"
                break

    # Taille queue Redis
    queue_size = None
    try:
        import redis.asyncio as redis
        r = redis.Redis(host="localhost", port=6379, db=0, socket_connect_timeout=3)
        queue_size = await r.llen("arq:queue")
        await r.close()
    except Exception:
        queue_size = None

    # Jobs en erreur récents dans les logs worker
    error_lines = []
    out_err = await _run(
        "journalctl", "-u", "flashback-arq-worker",
        "--since", "24 hours ago", "--no-pager",
        "-p", "err", "-n", "10",
    )

    worker_ok = queue_size is not None

    return {
        "worker_ok": worker_ok,
        "queue_size": queue_size,
        "last_activity": last_activity,
        "recent_errors": error_lines[:5],
    }


# ── Fonctions de collecte principale ─────────────────────

async def _collect_all_impl() -> dict:
    """Collecte parallèle de toutes les métriques."""
    services, ssl, db, system, arq = await asyncio.gather(
        collect_services(),
        collect_ssl(),
        collect_db_metrics(),
        collect_system(),
        collect_arq_worker(),
        return_exceptions=True,
    )

    now = datetime.now(timezone.utc)
    now_paris = now + timedelta(hours=2)  # UTC+2 (CEST)

    return {
        "timestamp": now.isoformat(),
        "date_fr": now_paris.strftime("%A %d %B %Y à %Hh%M").replace(
            "Monday", "Lundi").replace("Tuesday", "Mardi").replace("Wednesday", "Mercredi"
        ).replace("Thursday", "Jeudi").replace("Friday", "Vendredi"
        ).replace("Saturday", "Samedi").replace("Sunday", "Dimanche"
        ).replace("January", "janvier").replace("February", "février").replace("March", "mars"
        ).replace("April", "avril").replace("May", "mai").replace("June", "juin"
        ).replace("July", "juillet").replace("August", "août").replace("September", "septembre"
        ).replace("October", "octobre").replace("November", "novembre").replace("December", "décembre"),
        "services": services if not isinstance(services, Exception) else {"error": str(services)},
        "ssl": ssl if not isinstance(ssl, Exception) else {"error": str(ssl)},
        "db": db if not isinstance(db, Exception) else {"error": str(db)},
        "system": system if not isinstance(system, Exception) else {"error": str(system)},
        "arq": arq if not isinstance(arq, Exception) else {"error": str(arq)},
    }


async def collect_all() -> dict:
    """Collecte complète avec fallback si une section échoue."""
    try:
        return await _collect_all_impl()
    except Exception as e:
        logger.exception("Échec de la collecte complète")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date_fr": datetime.now().strftime("%d/%m/%Y"),
            "error": str(e),
            "services": {},
            "ssl": {},
            "db": {},
            "system": {},
            "arq": {},
        }


async def collect_critical_only() -> dict:
    """Collecte légère pour les alertes toutes les 15 minutes."""
    services, _, _, system, _ = await asyncio.gather(
        collect_services(),
        collect_ssl(),
        asyncio.sleep(0),  # skip DB pour les alertes rapides
        collect_system(),
        collect_arq_worker(),
        return_exceptions=True,
    )

    now = datetime.now(timezone.utc)

    return {
        "timestamp": now.isoformat(),
        "date_fr": now.strftime("%d/%m/%Y %H:%M"),
        "services": services if not isinstance(services, Exception) else {"error": str(services)},
        "ssl": _s if not isinstance(_s := None, Exception) else {},
        "system": system if not isinstance(system, Exception) else {},
        "arq": _a if not isinstance(_a := None, Exception) else {},
    }
