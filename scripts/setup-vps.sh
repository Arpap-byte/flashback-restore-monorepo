#!/usr/bin/env bash
# ============================================================
# Flashback Restore — Script de configuration VPS
# ============================================================
# Usage :
#   curl -sSL https://votre-serveur/setup-vps.sh | bash
#   ou
#   chmod +x scripts/setup-vps.sh && ./scripts/setup-vps.sh
#
# Ce script :
#   1. Installe Docker et Docker Compose si absents
#   2. Clone le dépôt Git
#   3. Configure le fichier .env
#   4. Lance le déploiement
# ============================================================
set -euo pipefail

# Configuration (modifiable)
REPO_URL="https://github.com/votre-org/flashback-restore-monorepo.git"
REPO_BRANCH="main"
APP_DIR="/opt/flashback-restore"

# Couleurs
ROUGE='\033[0;31m'
VERT='\033[0;32m'
JAUNE='\033[1;33m'
BLEU='\033[0;34m'
NC='\033[0m'

# -------------------------------------------------------------------
# Fonctions
# -------------------------------------------------------------------

afficher_banniere() {
    echo -e "${BLEU}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║     Flashback Restore — Installation VPS                ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

verifier_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${ROUGE}❌ Ce script doit être exécuté en tant que root (sudo).${NC}"
        exit 1
    fi
}

installer_docker() {
    echo -e "${JAUNE}[1/5] Installation de Docker...${NC}"

    if command -v docker &>/dev/null; then
        echo -e "${VERT}✅ Docker est déjà installé : $(docker --version)${NC}"
    else
        echo "📦 Installation de Docker..."

        # Détection de l'OS
        if [ -f /etc/os-release ]; then
            . /etc/os-release
        fi

        case "${ID:-}" in
            ubuntu|debian)
                apt-get update -qq
                apt-get install -y -qq \
                    ca-certificates \
                    curl \
                    gnupg \
                    lsb-release

                # Clé GPG officielle Docker
                mkdir -p /etc/apt/keyrings
                curl -fsSL https://download.docker.com/linux/${ID}/gpg | \
                    gpg --dearmor -o /etc/apt/keyrings/docker.gpg

                # Dépôt Docker
                echo \
                    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
                    https://download.docker.com/linux/${ID} \
                    $(lsb_release -cs) stable" | \
                    tee /etc/apt/sources.list.d/docker.list > /dev/null

                apt-get update -qq
                apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
                    docker-buildx-plugin docker-compose-plugin
                ;;
            *)
                echo -e "${ROUGE}❌ OS non supporté. Installez Docker manuellement :${NC}"
                echo "   https://docs.docker.com/engine/install/"
                exit 1
                ;;
        esac

        echo -e "${VERT}✅ Docker installé avec succès${NC}"
    fi

    # Vérifier Docker Compose
    echo -e "${JAUNE}[2/5] Vérification de Docker Compose...${NC}"
    if docker compose version &>/dev/null; then
        echo -e "${VERT}✅ Docker Compose (plugin) disponible${NC}"
    elif command -v docker-compose &>/dev/null; then
        echo -e "${VERT}✅ Docker Compose (standalone) disponible : $(docker-compose --version)${NC}"
    else
        echo -e "${ROUGE}❌ Docker Compose introuvable. Installation...${NC}"
        curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        echo -e "${VERT}✅ Docker Compose installé${NC}"
    fi

    # Démarrage du service Docker
    systemctl enable docker --now
}

cloner_depot() {
    echo -e "${JAUNE}[3/5] Clonage du dépôt...${NC}"

    if [ -d "$APP_DIR" ]; then
        echo "📂 Le répertoire $APP_DIR existe déjà. Mise à jour..."
        cd "$APP_DIR"
        git fetch origin
        git reset --hard "origin/$REPO_BRANCH"
        echo -e "${VERT}✅ Dépôt mis à jour${NC}"
    else
        mkdir -p "$(dirname "$APP_DIR")"
        git clone --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
        cd "$APP_DIR"
        echo -e "${VERT}✅ Dépôt cloné dans $APP_DIR${NC}"
    fi
}

configurer_env() {
    echo -e "${JAUNE}[4/5] Configuration du fichier .env...${NC}"

    cd "$APP_DIR"

    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
        else
            echo -e "${ROUGE}❌ .env.example introuvable.${NC}"
            exit 1
        fi
    fi

    # Génération d'une clé secrète si non configurée
    if ! grep -q "^SECRET_KEY=" .env || grep -q "^SECRET_KEY=change-me-in-production$" .env; then
        local nouvelle_cle=$(openssl rand -hex 32)
        sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${nouvelle_cle}/" .env
        echo -e "${VERT}✅ SECRET_KEY générée${NC}"
    fi

    # Message pour les clés API
    echo ""
    echo -e "${JAUNE}⚠️  N'oubliez pas de configurer vos clés API dans .env :${NC}"
    echo -e "   - ${BLEU}GEMINI_API_KEY${NC} (obligatoire)"
    echo -e "   - ${BLEU}DID_API_KEY${NC}    (optionnelle)"
    echo ""
    echo -e "   Éditez avec : ${BLEU}nano $APP_DIR/.env${NC}"
    echo ""

    # Pause pour laisser le temps de configurer
    read -r -p "Appuyez sur Entrée pour continuer le déploiement... "
}

deployer() {
    echo -e "${JAUNE}[5/5] Déploiement des conteneurs...${NC}"

    cd "$APP_DIR"

    # Rendre le script deploy.sh exécutable
    chmod +x scripts/deploy.sh 2>/dev/null || true

    # Déploiement
    if [ -f "scripts/deploy.sh" ]; then
        bash scripts/deploy.sh
    else
        docker compose up -d --build || docker-compose up -d --build
    fi
}

# -------------------------------------------------------------------
# Exécution principale
# -------------------------------------------------------------------

afficher_banniere
verifier_root
installer_docker
cloner_depot
configurer_env
deployer

echo ""
echo -e "${VERT}════════════════════════════════════════════════════════════${NC}"
echo -e "${VERT}✅ Installation terminée !${NC}"
echo ""
echo -e "  🏠 Landing : ${BLEU}http://$(hostname -I | awk '{print $1}')${NC}"
echo -e "  📡 API     : ${BLEU}http://$(hostname -I | awk '{print $1}')/api/${NC}"
echo -e "  📖 Docs    : ${BLEU}http://$(hostname -I | awk '{print $1}')/docs${NC}"
echo ""
echo -e "${JAUNE}⚠️  Si vous utilisez un pare-feu, ouvrez les ports 80 et 5050.${NC}"
echo -e "${VERT}════════════════════════════════════════════════════════════${NC}"
