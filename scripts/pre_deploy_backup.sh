#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Script de backup pré-déploiement pour Flashback Restore
# À exécuter AVANT chaque déploiement pour garantir un point de rollback.
#
# Usage: bash scripts/pre_deploy_backup.sh [nom_optionnel]
# ---------------------------------------------------------------------------
set -euo pipefail

DB_SOURCE="${DB_SOURCE:-/opt/flashback-restore-monorepo/backend/flashback.db}"
DOSSIER_BACKUP="${DOSSIER_BACKUP:-/root/backups/flashback}"
HORODATAGE=$(date +'%Y%m%d_%H%M%S')
NOM_OPTIONNEL="${1:-}"
if [ -n "$NOM_OPTIONNEL" ]; then
    HORODATAGE="${HORODATAGE}_${NOM_OPTIONNEL}"
fi
FICHIER_BACKUP="predeploy_${HORODATAGE}.db.gz"

mkdir -p "$DOSSIER_BACKUP"

echo "📦 Backup pré-déploiement Flashback Restore..."
echo "   Source : $DB_SOURCE"
echo "   Cible  : $DOSSIER_BACKUP/$FICHIER_BACKUP"

# 1. WAL checkpoint (force l'écriture du WAL dans le fichier principal)
sqlite3 "$DB_SOURCE" "PRAGMA wal_checkpoint(TRUNCATE);"
echo "   ✅ WAL checkpoint forcé"

# 2. Backup avec sqlite3 .backup (copie consistante)
sqlite3 "$DB_SOURCE" ".backup '${DOSSIER_BACKUP}/predeploy_tmp_${HORODATAGE}.db'"

# 3. Compresser
gzip -c "${DOSSIER_BACKUP}/predeploy_tmp_${HORODATAGE}.db" > "${DOSSIER_BACKUP}/${FICHIER_BACKUP}"
rm "${DOSSIER_BACKUP}/predeploy_tmp_${HORODATAGE}.db"

# 4. Vérification d'intégrité
if gunzip -c "${DOSSIER_BACKUP}/${FICHIER_BACKUP}" | sqlite3 /dev/stdin "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "   ✅ Backup intègre (${FICHIER_BACKUP})"
else
    echo "   ❌ Backup CORROMPUE ! Vérifier immédiatement."
    exit 1
fi

# 5. Rotation : garder les 10 derniers backups pré-déploiement
ls -1t "${DOSSIER_BACKUP}"/predeploy_*.db.gz 2>/dev/null | tail -n +11 | xargs -r rm

echo "   📋 $(ls "${DOSSIER_BACKUP}"/predeploy_*.db.gz 2>/dev/null | wc -l) backups pré-déploiement conservés"
echo "✅ Backup pré-déploiement terminé."
