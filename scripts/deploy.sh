#!/usr/bin/env bash
# ============================================================
# Flashback Restore — Script de déploiement Docker
# ============================================================
# Usage :
#   ./scripts/deploy.sh
#
# Prérequis :
#   - Docker et Docker Compose installés
#   - Fichier .env correctement configuré
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Couleurs pour le terminal
ROUGE='\033[0;31m'
VERT='\033[0;32m'
JAUNE='\033[1;33m'
BLEU='\033[0;34m'
NC='\033[0m' # Pas de couleur

# -------------------------------------------------------------------
# Fonctions utilitaires
# -------------------------------------------------------------------

afficher_banniere() {
    echo -e "${BLEU}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║       Flashback Restore — Déploiement Docker            ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

verifier_env() {
    echo -e "${JAUNE}[1/5] Vérification des variables d'environnement...${NC}"

    if [ ! -f ".env" ]; then
        echo -e "${ROUGE}❌ Fichier .env introuvable.${NC}"
        echo -e "   Copiez .env.example → .env et remplissez les clés API :"
        echo -e "   ${BLEU}cp .env.example .env${NC}"
        exit 1
    fi

    # Charger les variables du .env
    set -a
    source .env
    set +a

    # Vérifications
    local erreurs=0

    if [ -z "${GEMINI_API_KEY:-}" ] || [ "$GEMINI_API_KEY" = "your-gemini-api-key-here" ]; then
        echo -e "${ROUGE}⚠️  GEMINI_API_KEY non configurée${NC}"
        erreurs=$((erreurs + 1))
    fi

    if [ -z "${DID_API_KEY:-}" ] || [ "$DID_API_KEY" = "DID_API_KEY_PLACEHOLDER" ]; then
        echo -e "${JAUNE}⚠️  DID_API_KEY non configurée (optionnelle pour la restauration seule)${NC}"
    fi

    if [ -z "${SECRET_KEY:-}" ]; then
        echo -e "${ROUGE}⚠️  SECRET_KEY non configurée${NC}"
        erreurs=$((erreurs + 1))
    fi

    if [ $erreurs -gt 0 ]; then
        echo -e "${ROUGE}❌ $erreurs variable(s) obligatoire(s) manquante(s).${NC}"
        echo -e "   Éditez le fichier ${BLEU}.env${NC} puis réessayez."
        exit 1
    fi

    echo -e "${VERT}✅ Variables d'environnement OK${NC}"
}

nettoyer_conteneurs() {
    echo -e "${JAUNE}[2/5] Arrêt des conteneurs existants...${NC}"
    docker compose down --remove-orphans 2>/dev/null || docker-compose down --remove-orphans 2>/dev/null || true
    echo -e "${VERT}✅ Conteneurs arrêtés${NC}"
}

construire_images() {
    echo -e "${JAUNE}[3/5] Construction des images Docker...${NC}"
    docker compose build --pull 2>/dev/null || docker-compose build --pull 2>/dev/null
    echo -e "${VERT}✅ Images construites${NC}"
}

demarrer_services() {
    echo -e "${JAUNE}[4/5] Démarrage des services...${NC}"
    docker compose up -d 2>/dev/null || docker-compose up -d 2>/dev/null
    echo -e "${VERT}✅ Services démarrés${NC}"
}

afficher_statut() {
    echo -e "${JAUNE}[5/5] Statut des services :${NC}"
    echo ""

    # Vérifier quel binaire docker compose est disponible
    if docker compose version &>/dev/null; then
        local COMPOSE="docker compose"
    else
        local COMPOSE="docker-compose"
    fi

    $COMPOSE ps

    echo ""
    echo -e "${BLEU}════════════════════════════════════════════════════════════${NC}"
    echo -e "${VERT}✅ Déploiement terminé !${NC}"
    echo ""
    echo -e "  🏠 Landing : ${BLEU}http://localhost${NC}"
    echo -e "  📡 API     : ${BLEU}http://localhost/api/${NC}"
    echo -e "  📖 Docs    : ${BLEU}http://localhost/docs${NC}"
    echo -e "  🗄️  PgAdmin : ${BLEU}http://localhost:5050${NC}"
    echo ""
    echo -e "${JAUNE}Pour voir les logs :${NC}"
    echo -e "  ${BLEU}$COMPOSE logs -f backend${NC}"
    echo ""
    echo -e "${JAUNE}Pour arrêter :${NC}"
    echo -e "  ${BLEU}$COMPOSE down${NC}"
    echo -e "${BLEU}════════════════════════════════════════════════════════════${NC}"
}

# -------------------------------------------------------------------
# Exécution principale
# -------------------------------------------------------------------

afficher_banniere
verifier_env
nettoyer_conteneurs
construire_images
demarrer_services
afficher_statut
