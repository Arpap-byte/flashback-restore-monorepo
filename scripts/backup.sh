#!/usr/bin/env bash
# ============================================================
# Flashback Restore — Script de sauvegarde de la base de données
# ============================================================
# Usage :
#   ./scripts/backup.sh              # Sauvegarde dans ./backups/
#   ./scripts/backup.sh /mon/dossier  # Sauvegarde dans un dossier spécifique
#
# Planification cron (tous les jours à 3h du matin) :
#   0 3 * * * /opt/flashback-restore/scripts/backup.sh /var/backups/flashback
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOSSIER_BACKUP="${1:-$REPO_ROOT/backups}"
HORODATAGE=$(date +"%Y-%m-%d_%H-%M-%S")
FICHIER_BACKUP="flashback_backup_${HORODATAGE}.sql"

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

# Vérifier si le conteneur PostgreSQL tourne
CONTENEUR="flashback-db"
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTENEUR}$"; then
    echo -e "${ROUGE}❌ Le conteneur PostgreSQL '$CONTENEUR' n'est pas en cours d'exécution.${NC}"
    echo -e "   Démarrez-le avec : ${BLEU}docker compose up -d db${NC}"
    exit 1
fi

echo -e "${JAUNE}📦 Sauvegarde de la base de données...${NC}"

# Export de la base
docker exec "$CONTENEUR" pg_dump \
    -U flashback \
    -d flashback \
    --clean \
    --if-exists \
    --no-owner \
    > "${DOSSIER_BACKUP}/${FICHIER_BACKUP}" 2>&1

# Vérification
if [ $? -eq 0 ] && [ -s "${DOSSIER_BACKUP}/${FICHIER_BACKUP}" ]; then
    # Compression
    gzip "${DOSSIER_BACKUP}/${FICHIER_BACKUP}"
    TAILLE=$(du -h "${DOSSIER_BACKUP}/${FICHIER_BACKUP}.gz" | cut -f1)

    echo -e "${VERT}✅ Sauvegarde réussie !${NC}"
    echo -e "   📁 Fichier : ${BLEU}${DOSSIER_BACKUP}/${FICHIER_BACKUP}.gz${NC}"
    echo -e "   📏 Taille  : ${TAILLE}"

    # Rotation : garder les 30 derniers backups
    NB_BACKUPS=$(ls -1 "${DOSSIER_BACKUP}"/flashback_backup_*.sql.gz 2>/dev/null | wc -l)
    if [ "$NB_BACKUPS" -gt 30 ]; then
        echo -e "${JAUNE}🔄 Rotation des sauvegardes (conservation des 30 plus récentes)...${NC}"
        ls -1t "${DOSSIER_BACKUP}"/flashback_backup_*.sql.gz | tail -n +31 | xargs rm -f
        echo -e "${VERT}✅ Nettoyage effectué${NC}"
    fi
else
    echo -e "${ROUGE}❌ Erreur lors de la sauvegarde.${NC}"
    rm -f "${DOSSIER_BACKUP}/${FICHIER_BACKUP}"
    exit 1
fi

echo ""
echo -e "${JAUNE}💡 Pour restaurer cette sauvegarde :${NC}"
echo -e "   ${BLEU}gunzip -c ${DOSSIER_BACKUP}/${FICHIER_BACKUP}.gz | docker exec -i flashback-db psql -U flashback -d flashback${NC}"
echo -e "${BLEU}════════════════════════════════════════════════════════════${NC}"
