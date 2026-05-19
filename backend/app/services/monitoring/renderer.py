"""
Rendu HTML et texte des rapports de monitoring.

Génère un email multipart avec :
- Version HTML (lisible mobile, sections colorées)
- Version texte brut (fallback pour clients basiques)

Ne mentionne jamais les fournisseurs tech : « notre IA » partout.
"""

from datetime import datetime, timezone, timedelta

# ── Helpers ──────────────────────────────────────────────

def _status_icon(ok: bool) -> str:
    """✅ ou ❌"""
    return "✅" if ok else "❌"


def _mask_email(email: str) -> str:
    """nicolas.archeny@live.com → nic***@live.com"""
    if not email or "@" not in email:
        return email or "—"
    local, domain = email.split("@", 1)
    if len(local) <= 3:
        return f"{local[:1]}***@{domain}"
    return f"{local[:3]}***@{domain}"


def _bar(pct: float, width: int = 15) -> str:
    """Barre de progression ASCII."""
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    color = "🟢" if pct < 60 else "🟡" if pct < 80 else "🔴"
    return f"{color} [{bar}] {pct:.0f}%"


def _tendance_sparkline(data: list[dict]) -> str:
    """Mini sparkline ASCII pour la tendance 7 jours."""
    if not data or len(data) < 2:
        return "Pas assez de données"

    values = [d["nb"] for d in data]
    if max(values) == 0:
        return "Aucune activité"

    chars = "▁▂▃▄▅▆▇█"
    max_val = max(values)
    result = ""
    for v in values:
        idx = min(int(v / max_val * (len(chars) - 1)), len(chars) - 1) if max_val > 0 else 0
        result += chars[idx]
    return result


# ── Rendu HTML ───────────────────────────────────────────

def _render_html(snapshot: dict, alerts: list[dict], mode: str = "daily") -> str:
    """Génère le corps HTML du rapport."""
    services = snapshot.get("services", {})
    ssl_info = snapshot.get("ssl", {})
    db = snapshot.get("db", {})
    system = snapshot.get("system", {})
    arq = snapshot.get("arq", {})

    all_ok = services.get("all_ok", False)
    status_color = "#22c55e" if all_ok else "#f59e0b" if alerts else "#ef4444"
    status_text = "✅ Tout fonctionne" if all_ok else f"⚠️ {len(alerts)} point(s) d'attention" if alerts else "🔴 Problème détecté"

    date_fr = snapshot.get("date_fr", datetime.now().strftime("%d/%m/%Y"))

    # Services
    svc_rows = ""
    svc_list = [
        ("Backend API", services.get("flashback-backend", False), services.get("backend_latency_ms")),
        ("Worker ARQ", services.get("flashback-arq-worker", False), None),
        ("Site web", services.get("flashback-landing", False), None),
        ("Base de données", services.get("flashback-db", False), None),
        ("Proxy Traefik", services.get("traefik", False), None),
    ]
    for name, ok, latency in svc_list:
        icon = _status_icon(ok)
        extra = f" ({latency}ms)" if latency else ""
        svc_rows += f"""<tr>
            <td style="padding:6px 12px;border-bottom:1px solid #374151;">{name}</td>
            <td style="padding:6px 12px;border-bottom:1px solid #374151;">{icon}{extra}</td>
        </tr>"""

    # SSL
    ssl_days = ssl_info.get("days_left")
    ssl_expiry = ssl_info.get("expiry_date", "Inconnu")
    ssl_icon = "✅" if ssl_days and ssl_days > 14 else "⚠️" if ssl_days and ssl_days > 3 else "🔴"
    ssl_text = f"{ssl_days} jours" if ssl_days else "Inconnu"

    # Activité 24h
    t24 = db.get("travaux_24h", {})
    u_stats = db.get("utilisateurs", {})
    act_rows = f"""<tr><td style="padding:6px 12px;border-bottom:1px solid #374151;">Nouveaux inscrits</td><td style="padding:6px 12px;border-bottom:1px solid #374151;">{u_stats.get('nouveaux_24h', 0)}</td></tr>
<tr><td style="padding:6px 12px;border-bottom:1px solid #374151;">Utilisateurs actifs (7j)</td><td style="padding:6px 12px;border-bottom:1px solid #374151;">{u_stats.get('actifs_7j', 0)}</td></tr>
<tr><td style="padding:6px 12px;border-bottom:1px solid #374151;">Total utilisateurs</td><td style="padding:6px 12px;border-bottom:1px solid #374151;">{u_stats.get('total', 0)} (Premium: {u_stats.get('premium', 0)}, Gratuit: {u_stats.get('gratuit', 0)})</td></tr>
<tr style="background:#14532d40;"><td style="padding:6px 12px;border-bottom:1px solid #374151;">✅ Travaux réussis 24h</td><td style="padding:6px 12px;border-bottom:1px solid #374151;">{t24.get('succes_24h', 0)}</td></tr>
<tr style="background:#7f1d1d40;"><td style="padding:6px 12px;border-bottom:1px solid #374151;">❌ Erreurs 24h</td><td style="padding:6px 12px;border-bottom:1px solid #374151;">{t24.get('erreurs_24h', 0)}</td></tr>
<tr style="background:#713f1240;"><td style="padding:6px 12px;border-bottom:1px solid #374151;">⏳ En cours 24h</td><td style="padding:6px 12px;border-bottom:1px solid #374151;">{t24.get('en_cours_24h', 0)}</td></tr>"""

    # Travaux coincés
    stuck = db.get("travaux_coinces", [])
    stuck_rows = ""
    if stuck:
        for s in stuck:
            email_masked = _mask_email(s.get("email", ""))
            stuck_rows += f"""<tr>
                <td style="padding:4px 8px;border-bottom:1px solid #374151;font-size:12px;">{s.get('type', '?')}</td>
                <td style="padding:4px 8px;border-bottom:1px solid #374151;font-size:12px;">{email_masked}</td>
                <td style="padding:4px 8px;border-bottom:1px solid #374151;font-size:12px;">{s.get('cree_le', '?')}</td>
            </tr>"""
    else:
        stuck_rows = '<tr><td colspan="3" style="padding:8px;color:#6b7280;">Aucun travail coincé ✅</td></tr>'

    # Erreurs récentes
    errors = db.get("erreurs_recentes", [])
    err_rows = ""
    if errors:
        for e in errors:
            email_masked = _mask_email(e.get("email", ""))
            err_rows += f"""<tr>
                <td style="padding:4px 8px;border-bottom:1px solid #374151;font-size:12px;">{e.get('type', '?')}</td>
                <td style="padding:4px 8px;border-bottom:1px solid #374151;font-size:12px;">{email_masked}</td>
                <td style="padding:4px 8px;border-bottom:1px solid #374151;font-size:12px;">{e.get('cree_le', '?')}</td>
            </tr>"""
    else:
        err_rows = '<tr><td colspan="3" style="padding:8px;color:#6b7280;">Aucune erreur récente ✅</td></tr>'

    # Worker ARQ
    arq_status = "✅ Actif" if arq.get("worker_ok") else "⚠️ Non joignable"
    queue_size = arq.get("queue_size", "?")
    last_act = arq.get("last_activity", "Inconnu")

    # Système
    cpu = system.get("cpu", {})
    ram = system.get("ram", {})
    disk = system.get("disque", {})
    uploads = system.get("uploads", {})

    cpu_bar = _bar(cpu.get("pct", 0))
    ram_bar = _bar(ram.get("pct", 0), 15) if ram else "?"
    disk_bar = _bar(disk.get("pct", 0), 15) if disk else "?"

    # Tendance
    trend = db.get("tendance_7j", [])
    sparkline = _tendance_sparkline(trend)

    # Alerte critique ? Mode alerte = header rouge
    header_bg = "#7f1d1d" if mode == "alert" else "#1e293b"

    # ⚠️ Ne JAMAIS mentionner Gemini, Veo, D-ID, Stripe dans le rapport public
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Flashback Restore — Rapport monitoring</title>
</head>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#e2e8f0;">
<div style="max-width:640px;margin:0 auto;padding:24px 16px;">

<!-- Header -->
<div style="background:{header_bg};border-radius:12px;padding:24px;margin-bottom:20px;text-align:center;">
    <h1 style="margin:0 0 8px 0;font-size:22px;color:#f1f5f9;">📊 Flashback Restore</h1>
    <p style="margin:0 0 12px 0;color:#94a3b8;font-size:14px;">{date_fr}</p>
    <div style="background:{status_color}20;border:1px solid {status_color};border-radius:8px;padding:12px;color:{status_color};font-size:16px;font-weight:600;">
        {status_text}
    </div>
</div>

<!-- 1. Services -->
<div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:16px;">
    <h2 style="margin:0 0 12px 0;font-size:16px;color:#f1f5f9;">🔌 Services</h2>
    <table style="width:100%;border-collapse:collapse;">
        {svc_rows}
    </table>
</div>

<!-- 2. SSL -->
<div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:16px;">
    <h2 style="margin:0 0 8px 0;font-size:16px;color:#f1f5f9;">🔒 Certificat SSL</h2>
    <p style="margin:0;font-size:15px;">{ssl_icon} Expire le <strong>{ssl_expiry}</strong> — <strong>{ssl_text}</strong> restants</p>
</div>

<!-- 3. Activité 24h -->
<div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:16px;">
    <h2 style="margin:0 0 12px 0;font-size:16px;color:#f1f5f9;">📈 Activité (24h)</h2>
    <table style="width:100%;border-collapse:collapse;">
        {act_rows}
    </table>
</div>

<!-- 4. Travaux coincés -->
<div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:16px;">
    <h2 style="margin:0 0 12px 0;font-size:16px;color:#eab308;">⏳ Travaux coincés (en_cours > 2h)</h2>
    <table style="width:100%;border-collapse:collapse;">
        <tr style="color:#94a3b8;font-size:12px;">
            <th style="text-align:left;padding:4px 8px;">Type</th>
            <th style="text-align:left;padding:4px 8px;">Utilisateur</th>
            <th style="text-align:left;padding:4px 8px;">Depuis</th>
        </tr>
        {stuck_rows}
    </table>
</div>

<!-- 5. Erreurs récentes -->
<div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:16px;">
    <h2 style="margin:0 0 12px 0;font-size:16px;color:#ef4444;">❌ Dernières erreurs</h2>
    <table style="width:100%;border-collapse:collapse;">
        <tr style="color:#94a3b8;font-size:12px;">
            <th style="text-align:left;padding:4px 8px;">Type</th>
            <th style="text-align:left;padding:4px 8px;">Utilisateur</th>
            <th style="text-align:left;padding:4px 8px;">Date</th>
        </tr>
        {err_rows}
    </table>
</div>

<!-- 6. Worker ARQ -->
<div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:16px;">
    <h2 style="margin:0 0 8px 0;font-size:16px;color:#f1f5f9;">⚙️ Worker ARQ</h2>
    <p style="margin:4px 0;font-size:14px;">Statut : {arq_status}</p>
    <p style="margin:4px 0;font-size:14px;">Taille queue : {queue_size}</p>
    <p style="margin:4px 0;font-size:14px;">Dernière activité : {last_act}</p>
</div>

<!-- 7. Système -->
<div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:16px;">
    <h2 style="margin:0 0 12px 0;font-size:16px;color:#f1f5f9;">🖥️ Système</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <tr>
            <td style="padding:8px;border-bottom:1px solid #374151;">CPU</td>
            <td style="padding:8px;border-bottom:1px solid #374151;">{cpu_bar}<br><span style="font-size:11px;color:#94a3b8;">Load: {cpu.get('load_1m', '?')} / {cpu.get('load_5m', '?')} / {cpu.get('load_15m', '?')}</span></td>
        </tr>
        <tr>
            <td style="padding:8px;border-bottom:1px solid #374151;">RAM</td>
            <td style="padding:8px;border-bottom:1px solid #374151;">{ram_bar}<br><span style="font-size:11px;color:#94a3b8;">{ram.get('used_gb', '?')} Go / {ram.get('total_gb', '?')} Go</span></td>
        </tr>
        <tr>
            <td style="padding:8px;border-bottom:1px solid #374151;">Disque</td>
            <td style="padding:8px;border-bottom:1px solid #374151;">{disk_bar}<br><span style="font-size:11px;color:#94a3b8;">{disk.get('used_gb', '?')} Go / {disk.get('total_gb', '?')} Go</span></td>
        </tr>
        <tr>
            <td style="padding:8px;">Uploads</td>
            <td style="padding:8px;"><span style="font-size:11px;">{uploads.get('taille_mb', '?')} Mo — {uploads.get('fichiers', '?')} fichiers</span></td>
        </tr>
    </table>
</div>

<!-- 8. Tendance 7j -->
<div style="background:#1e293b;border-radius:10px;padding:16px;margin-bottom:16px;">
    <h2 style="margin:0 0 8px 0;font-size:16px;color:#f1f5f9;">📊 Tendance 7 jours</h2>
    <p style="margin:0;font-size:28px;letter-spacing:4px;">{sparkline}</p>
    <p style="margin:4px 0 0 0;font-size:12px;color:#94a3b8;">Travaux par jour — {sum(d['nb'] for d in trend)} au total sur 7 jours</p>
</div>

<!-- Footer -->
<div style="text-align:center;padding:16px;color:#475569;font-size:12px;">
    <p style="margin:0;">Généré automatiquement — <a href="https://flashback-restore.com" style="color:#3b82f6;">flashback-restore.com</a></p>
    <p style="margin:4px 0 0 0;">Notre IA de restauration photo et d'animation</p>
</div>

</div>
</body>
</html>"""
    return html


# ── Rendu texte ──────────────────────────────────────────

def _render_text(snapshot: dict, alerts: list[dict], mode: str = "daily") -> str:
    """Version texte brut du rapport."""
    services = snapshot.get("services", {})
    ssl_info = snapshot.get("ssl", {})
    db = snapshot.get("db", {})
    system = snapshot.get("system", {})
    arq = snapshot.get("arq", {})

    date_fr = snapshot.get("date_fr", datetime.now().strftime("%d/%m/%Y"))

    all_ok = services.get("all_ok", False)
    status_line = "✅ Tout fonctionne" if all_ok else f"⚠️ {len(alerts)} point(s) d'attention"

    lines = [
        f"═══════════════════════════════════════",
        f"  FLASHBACK RESTORE — RAPPORT MONITORING",
        f"  {date_fr}",
        f"═══════════════════════════════════════",
        f"",
        f"  {status_line}",
        f"",
        f"── Services ──────────────────────────",
        f"  Backend API       : {_status_icon(services.get('flashback-backend', False))}",
        f"  Worker ARQ        : {_status_icon(services.get('flashback-arq-worker', False))}",
        f"  Site web          : {_status_icon(services.get('flashback-landing', False))}",
        f"  Base de données   : {_status_icon(services.get('flashback-db', False))}",
        f"  Proxy Traefik     : {_status_icon(services.get('traefik', False))}",
        f"",
        f"── SSL ───────────────────────────────",
    ]

    ssl_days = ssl_info.get("days_left")
    ssl_expiry = ssl_info.get("expiry_date", "Inconnu")
    ssl_icon = "✅" if ssl_days and ssl_days > 14 else "⚠️" if ssl_days and ssl_days > 3 else "🔴"
    lines.append(f"  {ssl_icon} Expire le {ssl_expiry} ({ssl_days} jours)")

    # Activité
    t24 = db.get("travaux_24h", {})
    u_stats = db.get("utilisateurs", {})
    lines.extend([
        f"",
        f"── Activité 24h ──────────────────────",
        f"  Nouveaux inscrits : {u_stats.get('nouveaux_24h', 0)}",
        f"  Actifs 7 jours    : {u_stats.get('actifs_7j', 0)}",
        f"  Total utilisateurs: {u_stats.get('total', 0)} (P:{u_stats.get('premium', 0)} G:{u_stats.get('gratuit', 0)})",
        f"  Travaux réussis  : {t24.get('succes_24h', 0)}",
        f"  Erreurs          : {t24.get('erreurs_24h', 0)}",
        f"  En cours         : {t24.get('en_cours_24h', 0)}",
    ])

    # Travaux coincés
    stuck = db.get("travaux_coinces", [])
    if stuck:
        lines.append(f"")
        lines.append(f"── Travaux coincés ({len(stuck)}) ────────")
        for s in stuck:
            lines.append(f"  {s.get('type','?')} | {_mask_email(s.get('email',''))} | {s.get('cree_le','?')}")
    else:
        lines.append(f"  Aucun travail coincé ✅")

    # Erreurs
    errors = db.get("erreurs_recentes", [])
    if errors:
        lines.append(f"")
        lines.append(f"── Dernières erreurs ─────────────────")
        for e in errors:
            lines.append(f"  {e.get('type','?')} | {_mask_email(e.get('email',''))} | {e.get('cree_le','?')}")

    # ARQ
    lines.extend([
        f"",
        f"── Worker ARQ ────────────────────────",
        f"  Statut  : {'✅ Actif' if arq.get('worker_ok') else '⚠️ Non joignable'}",
        f"  Queue   : {arq.get('queue_size', '?')}",
    ])

    # Système
    cpu = system.get("cpu", {})
    ram = system.get("ram", {})
    disk = system.get("disque", {})
    uploads = system.get("uploads", {})
    lines.extend([
        f"",
        f"── Système ───────────────────────────",
        f"  CPU    : {_bar(cpu.get('pct', 0))} Load: {cpu.get('load_1m','?')}/{cpu.get('load_5m','?')}/{cpu.get('load_15m','?')}",
        f"  RAM    : {_bar(ram.get('pct', 0))} {ram.get('used_gb','?')}/{ram.get('total_gb','?')} Go",
        f"  Disque : {_bar(disk.get('pct', 0))} {disk.get('used_gb','?')}/{disk.get('total_gb','?')} Go",
        f"  Uploads: {uploads.get('taille_mb','?')} Mo ({uploads.get('fichiers','?')} fichiers)",
    ])

    # Tendance
    trend = db.get("tendance_7j", [])
    if trend:
        sparkline = _tendance_sparkline(trend)
        total_7j = sum(d['nb'] for d in trend)
        lines.extend([
            f"",
            f"── Tendance 7j ───────────────────────",
            f"  {sparkline}  ({total_7j} travaux)",
        ])

    lines.extend([
        f"",
        f"──────────────────────────────────────",
        f"  flashback-restore.com",
        f"  Notre IA de restauration et d'animation",
        f"──────────────────────────────────────",
    ])

    return "\n".join(lines)


# ── Point d'entrée ──────────────────────────────────────

def render_report(snapshot: dict, alerts: list[dict], mode: str = "daily") -> tuple[str, str]:
    """
    Retourne (html_body, text_body).

    mode='daily' → rapport complet
    mode='alert' → version compacte pour alerte critique
    """
    html = _render_html(snapshot, alerts, mode)
    text = _render_text(snapshot, alerts, mode)
    return html, text
