# Infrastructure — Flashback Restore

## Services

| Service | Fichier systemd | Port |
|---------|----------------|------|
| Backend FastAPI | `systemd/flashback-backend.service` | 8000 |
| Landing Next.js | `systemd/flashback-landing.service` | 8001 |
| Worker ARQ | `systemd/flashback-arq-worker.service` | — |

## Déploiement depuis zéro

### 1. Prérequis VPS
```bash
# Ubuntu/Debian
apt install python3.13 python3.13-venv nodejs npm redis-server docker.io

# Créer l'utilisateur de service
useradd -m -s /bin/bash flashback
```

### 2. Cloner le repo
```bash
cd /opt
git clone git@github.com:Arpap-byte/flashback-restore-monorepo.git
chown -R flashback:flashback flashback-restore-monorepo
```

### 3. Configurer l'environnement
```bash
cp .env.example .env
# Éditer .env avec les vraies clés API
```

### 4. Installer les dépendances
```bash
# Backend
cd /opt/flashback-restore-monorepo/backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd /opt/flashback-restore-monorepo/landing
npm install
npm run build
```

### 5. Installer les services systemd
```bash
cp /opt/flashback-restore-monorepo/infra/systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable flashback-backend flashback-landing flashback-arq-worker
```

### 6. Lancer Traefik
```bash
cd /opt/flashback-restore-monorepo/infra/traefik
cp .env.example .env  # Éditer avec DOMAIN + LETSENCRYPT_EMAIL
mkdir -p traefik
docker compose up -d
```

### 7. Démarrer les services
```bash
systemctl start flashback-backend flashback-landing flashback-arq-worker
```

### 8. Vérifier
```bash
curl https://flashback-restore.com/api/health
```
