#!/bin/bash
# Backup PostgreSQL Flashback Restore → B2
# Cron: 0 3 * * * /opt/flashback-restore-monorepo/infra/backup_pg.sh
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/root/backups/flashback/postgresql"
RETENTION_DAYS=30
DB_NAME="flashback"
DB_USER="flashback"
B2_CLI="/opt/flashback-restore-monorepo/backend/.venv/bin/b2"
B2_BUCKET="flashback-restore"
B2_PATH="backups/database"

mkdir -p "$BACKUP_DIR"

# 1. Dump PostgreSQL
DUMP_FILE="$BACKUP_DIR/flashback_${TIMESTAMP}.sql.gz"
echo "[$(date)] Dumping PostgreSQL..."
docker exec flashback-db pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$DUMP_FILE"

if [ ! -s "$DUMP_FILE" ]; then
    echo "❌ Dump vide — abort"
    exit 1
fi
echo "[$(date)] Dump OK: $(du -h "$DUMP_FILE" | cut -f1)"

# Backup n8n
N8N_DUMP_FILE="/root/backups/n8n_$(date +%Y%m%d_%H%M%S).sql.gz"
mkdir -p "$(dirname "$N8N_DUMP_FILE")"
echo "[$(date)] Dumping n8n PostgreSQL..."
docker exec postgres pg_dump -U n8n -d n8n | gzip > "$N8N_DUMP_FILE"
if [ -s "$N8N_DUMP_FILE" ]; then
    echo "[$(date)] n8n Dump OK: $(du -h "$N8N_DUMP_FILE" | cut -f1)"
else
    echo "[$(date)] ⚠️ n8n Dump vide ou échoué (non-bloquant)"
fi

# 2. Upload vers Backblaze B2
if [ -x "$B2_CLI" ]; then
    echo "[$(date)] Uploading to B2..."
    if $B2_CLI file upload "$B2_BUCKET" "$DUMP_FILE" "$B2_PATH/flashback_${TIMESTAMP}.sql.gz" --quiet 2>/dev/null; then
        echo "[$(date)] B2 upload OK"
    else
        echo "[$(date)] ⚠️ B2 upload failed (non-bloquant)"
    fi
else
    echo "[$(date)] ⚠️ b2 CLI not found — skip B2 upload"
fi

# 3. Nettoyage local (rétention 30 jours)
echo "[$(date)] Cleaning local backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "flashback_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# 4. Nettoyage B2 (vieux fichiers) — syntaxe B2 CLI v4.x
if [ -x "$B2_CLI" ]; then
    echo "[$(date)] Cleaning B2 backups older than ${RETENTION_DAYS} days..."
    CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d 2>/dev/null || echo "")
    if [ -n "$CUTOFF_DATE" ]; then
        $B2_CLI ls --long "b2://${B2_BUCKET}/${B2_PATH}/" 2>/dev/null | while read -r _ _ _ _ timestamp _ filepath; do
            if [ -n "$filepath" ] && [[ "$timestamp" < "$CUTOFF_DATE" ]]; then
                $B2_CLI rm "b2://${B2_BUCKET}/${filepath}" 2>/dev/null || true
            fi
        done
    fi
fi

echo "[$(date)] ✅ Backup terminé."
