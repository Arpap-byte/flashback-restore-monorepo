"""
Service de backup PostgreSQL — Flashback Restore.

Remplace le script shell infra/backup_pg.sh par une tâche Python intégrée
au backend, planifiée par le scheduler APScheduler.

Fonctionnalités :
- pg_dump compressé (gzip)
- Upload vers Backblaze B2
- Nettoyage local (rétention 30 jours)
- Nettoyage B2 (rétention 30 jours)
- Rapport exportable (JSON) pour Google Drive
"""

import asyncio
import gzip
import logging
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Configuration ──

BACKUP_DIR = Path("/root/backups/flashback/postgresql")
RETENTION_DAYS = 30
DB_NAME = "flashback"
DB_USER = "flashback"
B2_BUCKET = "flashback-restore"
B2_PATH = "backups/database"
B2_CLI = "/opt/flashback-restore-monorepo/backend/.venv/bin/b2"

# Google Drive (optionnel — actif seulement si OAuth configuré)
GOOGLE_DRIVE_FOLDER = "Flashback Restore — Rapports"
REPORT_EMAIL = "apexcyber.eu@gmail.com"


async def _run_cmd(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Exécute une commande shell et retourne (exit_code, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"Commande timeout après {timeout}s: {' '.join(cmd)}")

    return proc.returncode or -1, stdout.decode(errors="replace"), stderr.decode(errors="replace")


async def backup_postgresql() -> dict:
    """
    Effectue un backup PostgreSQL complet avec upload B2.

    Returns:
        dict avec les clés : timestamp, dump_fichier, dump_taille, b2_upload,
        erreurs, details
    """
    maintenant = datetime.now(timezone.utc)
    timestamp = maintenant.strftime("%Y%m%d_%H%M%S")
    erreurs = 0
    details = []

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    dump_file = BACKUP_DIR / f"flashback_{timestamp}.sql.gz"
    resultat = {
        "timestamp": maintenant.isoformat(),
        "dump_fichier": str(dump_file),
        "dump_taille": "0",
        "b2_upload": False,
        "erreurs": 0,
        "details": details,
    }

    # ── 1. Dump PostgreSQL ──
    logger.info("Dump PostgreSQL vers %s...", dump_file)
    try:
        dump_cmd = [
            "docker", "exec", "flashback-db",
            "pg_dump", "-U", DB_USER, "-d", DB_NAME,
        ]
        exit_code, stdout, stderr = await _run_cmd(dump_cmd, timeout=300)

        if exit_code != 0:
            logger.error("pg_dump failed (exit %s): %s", exit_code, stderr)
            resultat["erreurs"] += 1
            details.append(f"❌ pg_dump échoué (exit {exit_code})")
            return resultat

        # Compresser
        with gzip.open(dump_file, "wb") as f:
            f.write(stdout.encode())

        taille = dump_file.stat().st_size
        resultat["dump_taille"] = f"{taille / 1024 / 1024:.1f} MB"
        details.append(f"✅ Dump OK : {resultat['dump_taille']}")

        logger.info("Dump OK: %s", resultat["dump_taille"])

    except Exception as e:
        logger.exception("Erreur dump PostgreSQL")
        resultat["erreurs"] += 1
        details.append(f"❌ Exception dump: {e}")
        return resultat

    # ── 2. Upload B2 ──
    if os.path.isfile(B2_CLI) and os.access(B2_CLI, os.X_OK):
        b2_target = f"{B2_PATH}/flashback_{timestamp}.sql.gz"
        logger.info("Upload B2 → %s", b2_target)
        try:
            exit_code, stdout, stderr = await _run_cmd(
                [B2_CLI, "file", "upload", B2_BUCKET, str(dump_file), b2_target, "--quiet"],
                timeout=120,
            )
            if exit_code == 0:
                resultat["b2_upload"] = True
                details.append("✅ B2 upload OK")
            else:
                details.append(f"⚠️ B2 upload failed (exit {exit_code}): {stderr[:200]}")
                resultat["erreurs"] += 1
        except Exception as e:
            details.append(f"⚠️ B2 upload exception: {e}")
            resultat["erreurs"] += 1
    else:
        details.append("⚠️ b2 CLI absent — skip B2")

    # ── 3. Nettoyage local ──
    cutoff = maintenant - timedelta(days=RETENTION_DAYS)
    try:
        for old_file in BACKUP_DIR.glob("flashback_*.sql.gz"):
            mtime = datetime.fromtimestamp(old_file.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                old_file.unlink()
                details.append(f"🗑️ Supprimé local: {old_file.name}")
                logger.info("Supprimé vieux backup local: %s", old_file.name)
    except Exception as e:
        details.append(f"⚠️ Erreur nettoyage local: {e}")

    # ── 4. Nettoyage B2 ──
    if os.path.isfile(B2_CLI) and os.access(B2_CLI, os.X_OK):
        try:
            exit_code, stdout, stderr = await _run_cmd(
                [B2_CLI, "ls", "--long", f"b2://{B2_BUCKET}/{B2_PATH}/"],
                timeout=30,
            )
            if exit_code == 0:
                cutoff_str = cutoff.strftime("%Y-%m-%d")
                for line in stdout.strip().split("\n"):
                    parts = line.split()
                    if len(parts) >= 6:
                        file_ts = parts[4]  # timestamp field
                        file_path = parts[5] if len(parts) > 5 else ""
                        if file_ts < cutoff_str and file_path:
                            await _run_cmd(
                                [B2_CLI, "rm", f"b2://{B2_BUCKET}/{file_path}"],
                                timeout=30,
                            )
                            details.append(f"🗑️ Supprimé B2: {file_path}")
        except Exception as e:
            details.append(f"⚠️ Erreur nettoyage B2: {e}")

    logger.info("✅ Backup terminé — %s erreurs", resultat["erreurs"])
    return resultat


async def exporter_rapport_backup(resultat: dict) -> str | None:
    """
    Génère le rapport de backup et l'envoie sur Google Drive.

    Returns:
        L'ID du fichier Drive si uploadé, None sinon.
    """
    import json

    rapport = {
        "type": "backup_postgresql",
        "service": "Flashback Restore",
        "date": resultat["timestamp"],
        "dump_fichier": resultat["dump_fichier"],
        "dump_taille": resultat["dump_taille"],
        "b2_upload": resultat["b2_upload"],
        "erreurs": resultat["erreurs"],
        "details": resultat["details"],
    }

    rapport_json = json.dumps(rapport, indent=2, ensure_ascii=False)

    # Sauvegarde locale
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    rapport_path = BACKUP_DIR / f"rapport_backup_{date_str}.json"
    rapport_path.write_text(rapport_json, encoding="utf-8")

    # Upload Google Drive
    drive_id = await _upload_json_to_drive(
        rapport_json,
        filename=f"backup_flashback_{date_str}.json",
        folder=GOOGLE_DRIVE_FOLDER,
    )

    if drive_id:
        logger.info("📤 Rapport backup uploadé sur Drive: %s", drive_id)
    else:
        logger.warning("📤 Rapport backup sauvegardé localement uniquement (Drive non configuré)")

    return drive_id


async def _upload_json_to_drive(content: str, filename: str, folder: str) -> str | None:
    """
    Upload un fichier JSON sur Google Drive (si OAuth configuré).

    Args:
        content: Contenu JSON (string)
        filename: Nom du fichier sur Drive
        folder: Nom du dossier Drive (créé si absent)

    Returns:
        File ID Drive, ou None si non configuré
    """
    import tempfile

    # Vérifier si l'OAuth Google est configuré
    google_token = Path.home() / ".hermes" / "google_token.json"
    if not google_token.exists():
        logger.info("Google OAuth non configuré — skip upload Drive")
        return None

    gapi_script = (
        Path.home() / ".hermes" / "skills" / "productivity" / "google-workspace" / "scripts" / "google_api.py"
    )
    if not gapi_script.exists():
        logger.warning("Script google_api.py introuvable")
        return None

    # Écrire le contenu dans un fichier temporaire
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # TODO: Utiliser l'API Drive pour uploader le fichier
        # Pour l'instant, on sauvegarde localement et on log
        logger.info(
            "Rapport prêt pour Drive : %s (%s octets) → dossier '%s'",
            filename, len(content), folder,
        )
        return None  # Sera implémenté après setup OAuth

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
