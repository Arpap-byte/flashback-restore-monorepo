#!/usr/bin/env bash
# ============================================================
# Flashback Restore — Script de sauvegarde de la base de données
# ============================================================
# Usage :
#   ./scripts/backup.sh              # Sauvegarde dans /root/backups/flashback/
#   ./scripts/backup.sh /mon/dossier  # Sauvegarde dans un dossier spécifique
#
# Planification cron (tous les jours à 3h du matin) :
#   0 3 * * * root /root/flashback-restore-monorepo/scripts/backup.sh 2>&1 | logger -t flashback-backup
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOSSIER_BACKUP="${1:-/root/backups/flashback}"
HORODATAGE=$(date +"%Y-%m-%d_%H-%M-%S")
FICHIER_BACKUP="flashback_backup_${HORODATAGE}.db.gz"

# Chemins source (SQLite)
DB_SOURCE="${REPO_ROOT}/backend/flashback.db"

# Couleurs
ROUGE='\033[0;31m'
VERT='\033[0;32m'
JAUNE='\033[1;33m'
BLEU='\033[0;34m'
NC='\033[0m'

# -------------------------------------------------------------------
# Exécution
# -------------------------------------------------------------------

echo -e "${BLEU}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLEU}  Flashback Restore — Sauvegarde Base de Données           ${NC}"
echo -e "${BLEU}════════════════════════════════════════════════════════════${NC}"
echo ""

# Création du dossier de backup
mkdir -p "$DOSSIER_BACKUP"

# Vérifier que le fichier SQLite existe
if [ ! -f "$DB_SOURCE" ]; then
    echo -e "${ROUGE}❌ Le fichier SQLite '$DB_SOURCE' n'existe pas.${NC}"
    echo -e "   Vérifiez que le backend a bien démarré et créé la base."
    exit 1
fi

echo -e "${JAUNE}📦 Sauvegarde de la base de données SQLite...${NC}"

# Copie et compression du fichier SQLite
if cp "$DB_SOURCE" "${DOSSIER_BACKUP}/flashback_tmp_${HORODATAGE}.db" 2>/dev/null; then
    gzip -c "${DOSSIER_BACKUP}/flashback_tmp_${HORODATAGE}.db" > "${DOSSIER_BACKUP}/${FICHIER_BACKUP}"
    rm -f "${DOSSIER_BACKUP}/flashback_tmp_${HORODATAGE}.db"
    TAILLE=$(du -h "${DOSSIER_BACKUP}/${FICHIER_BACKUP}" | cut -f1)

    echo -e "${VERT}✅ Sauvegarde réussie !${NC}"
    echo -e "   📁 Fichier : ${BLEU}${DOSSIER_BACKUP}/${FICHIER_BACKUP}${NC}"
    echo -e "   📏 Taille  : ${TAILLE}"

    # Rotation : garder les 30 derniers backups
    NB_BACKUPS=$(ls -1 "${DOSSIER_BACKUP}"/flashback_backup_*.db.gz 2>/dev/null | wc -l)
    if [ "$NB_BACKUPS" -gt 30 ]; then
        echo -e "${JAUNE}🔄 Rotation des sauvegardes (conservation des 30 plus récentes)...${NC}"
        ls -1t "${DOSSIER_BACKUP}"/flashback_backup_*.db.gz | tail -n +31 | xargs rm -f
        echo -e "${VERT}✅ Nettoyage effectué${NC}"
    fi
else
    echo -e "${ROUGE}❌ Erreur lors de la copie du fichier SQLite.${NC}"
    exit 1
fi

echo ""
echo -e "${JAUNE}💡 Pour restaurer cette sauvegarde :${NC}"
echo -e "   ${BLEU}gunzip -c ${DOSSIER_BACKUP}/${FICHIER_BACKUP} > ${DB_SOURCE}${NC}"
echo -e "${BLEU}════════════════════════════════════════════════════════════${NC}"
