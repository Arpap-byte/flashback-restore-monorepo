# Flashback Restore — Redonnez vie à vos souvenirs

![Flashback Restore](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.13+-blue?logo=python)
![Next.js](https://img.shields.io/badge/next.js-15-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/fastapi-0.115+-009688?logo=fastapi)
![Licence](https://img.shields.io/badge/licence-MIT-green)

**Flashback Restore** est une application SaaS de restauration et d'animation de photos anciennes par intelligence artificielle. Téléversez une photo abîmée, rayée ou décolorée, et notre IA la restaure, puis l'anime avec des expressions faciales réalistes — comme si le passé reprenait vie sous vos yeux.

> 🌐 **Production** : [flashback-restore.com](https://flashback-restore.com)

---

## ✨ Fonctionnalités

- 🖼️ **Analyse intelligente** — Détection des défauts (rayures, taches, décoloration, pliures)
- 🔧 **Restauration IA** — Correction des imperfections par IA générative
- 🎬 **Animation faciale** — La photo restaurée s'anime avec des expressions naturelles
- 💳 **Paiements Stripe** — 5 plans tarifaires (Découverte → Annuel Pro) + packs de crédits
- 🔐 **Authentification Clerk** — Email, Google, Facebook (JWT vérifié côté backend)
- 📊 **Dashboard utilisateur** — Crédits, historique des restaurations, abonnement
- ⚡ **File de tâches ARQ** — Restauration asynchrone via Redis (non-bloquant)
- ☁️ **Stockage Backblaze B2** — Photos et vidéos sur stockage objet S3-compatible

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Traefik (TLS/reverse proxy)          │
│                     Ports 80, 443                     │
├──────────────────────┬───────────────────────────────┤
│   Next.js (landing)  │    FastAPI (backend)           │
│   Port 8001          │    Port 8000 (4 workers)       │
│                      │                                │
│   • Pages SSR        │    • /api/health               │
│   • Clerk auth       │    • /api/upload               │
│   • Dashboard        │    • /api/restore              │
│   • Pricing          │    • /api/webhooks/stripe      │
│                      │    • Validation JWT Clerk      │
├──────────────────────┴───────────────────────────────┤
│   Redis :6379          PostgreSQL :5432               │
│   └─ Queue ARQ          └─ SQLAlchemy async            │
│   └─ Rate Limiter                                     │
├──────────────────────────────────────────────────────┤
│   ARQ Worker           Backblaze B2 (S3)              │
│   └─ Jobs async         └─ Photos/Vidéos              │
└──────────────────────────────────────────────────────┘
```

### Monorepo

```
flashback-restore-monorepo/
├── backend/              # API FastAPI (Python 3.13+)
│   ├── app/
│   │   ├── main.py       # Point d'entrée FastAPI
│   │   ├── storage.py    # Client S3/B2 (boto3)
│   │   ├── worker.py     # Worker ARQ (jobs async)
│   │   ├── api/          # Routes API (auth, upload, restore, stripe)
│   │   ├── db/           # Modèles SQLAlchemy + queries async
│   │   ├── services/     # Logique métier (credits, gemini, stripe)
│   │   └── models/       # Pydantic schemas
│   ├── tests/            # Tests unitaires
│   └── requirements.txt
├── landing/              # Frontend Next.js 15 (TypeScript)
│   ├── src/
│   │   ├── app/          # Pages (dashboard, restore, historique, pricing)
│   │   ├── components/   # Navbar, Pricing, etc.
│   │   └── lib/          # api.ts (fetch wrapper avec token Clerk)
│   ├── next.config.ts
│   └── middleware.ts     # Middleware Clerk (protège /dashboard, /restore, /historique)
├── traefik/              # Configuration reverse proxy
│   └── flashback-dynamic.yml
├── docs/                 # Documentation technique
└── README.md
```

### Stack technique

| Composant         | Technologie                    | Port    |
|-------------------|--------------------------------|---------|
| Reverse Proxy     | Traefik (Docker)               | 80, 443 |
| Frontend          | Next.js 15 (TypeScript)        | 8001    |
| Backend API       | FastAPI (Python 3.13, async)   | 8000    |
| Base de données   | SQLite (dev) / PostgreSQL (prod)| 5432    |
| Cache / Queue     | Redis 7 (ARQ)                  | 6379    |
| Stockage objet    | Backblaze B2 (S3-compatible)   | —       |
| Authentification  | Clerk (JWT)                    | —       |
| Paiements         | Stripe (Checkout + Webhooks)   | —       |
| IA                | Gemini API + D-ID API          | —       |
| Monitoring        | Sentry (optionnel)             | —       |
| Déploiement       | Systemd + GitHub               | —       |

---

## 🚀 Démarrage rapide

### Prérequis

- Python 3.13+
- Node.js 20+
- Redis 7+
- Clés API : Gemini, D-ID, Stripe, Clerk, Backblaze B2

### 1. Cloner le projet

```bash
git clone git@github.com:Arpap-byte/flashback-restore-monorepo.git
cd flashback-restore-monorepo
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditez `.env` et renseignez **toutes** les variables. Les sections critiques :

```env
# API IA
GEMINI_API_KEY=votre-clé
DID_API_KEY=votre-clé

# Auth (Clerk)
CLERK_ISSUER=https://votre-app.clerk.accounts.dev
CLERK_JWKS_URL=https://votre-app.clerk.accounts.dev/.well-known/jwks.json

# Stockage (B2)
B2_ENDPOINT=s3.eu-central-003.backblazeb2.com
B2_KEY_ID=votre-key-id
B2_APPLICATION_KEY=votre-application-key
B2_BUCKET_NAME=flashback-restore

# Paiements (Stripe)
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 3. Installer les dépendances

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../landing
npm install
```

### 4. Lancer en développement

```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — Backend + Worker ARQ
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
arq app.worker.WorkerSettings

# Terminal 3 — Frontend
cd landing
npm run dev
```

### 5. Vérifier

```bash
curl http://localhost:8000/api/health
# → {"statut":"OK","b2_disponible":true,...}
```

---

## 📦 Déploiement production (VPS Hostinger)

Le déploiement utilise **systemd** pour les services bare-metal.

### Services systemd

| Service                    | Description                      |
|----------------------------|----------------------------------|
| `flashback-backend.service` | FastAPI sur :8000               |
| `flashback-landing.service` | Next.js sur :8001               |
| `flashback-worker-arq.service` | Worker ARQ (jobs async)      |

### Déploiement continu

```bash
# Backend — après modifications
cd /opt/flashback-restore-monorepo/backend
source .venv/bin/activate
sudo systemctl restart flashback-backend

# Worker ARQ — après modifications
kill $(pgrep -f "arq app.worker") 2>/dev/null
cd /opt/flashback-restore-monorepo/backend
set -a; source ../.env; set +a
arq app.worker.WorkerSettings &

# Frontend — après modifications
cd /opt/flashback-restore-monorepo/landing
npm run build
sudo systemctl restart flashback-landing
```

---

## 📖 Documentation

- [Architecture détaillée](docs/ARCHITECTURE.md)
- [Référence API](docs/API.md)
- [Plans d'implémentation](docs/plans/)

---

## 🔒 Sécurité

- ✅ JWT Clerk vérifié côté backend (RS256, JWKS)
- ✅ Validation MIME des fichiers uploadés (magic bytes via python-magic)
- ✅ Crédits atomiques (SELECT FOR UPDATE)
- ✅ Webhooks Stripe idempotents (table stripe_events)
- ✅ Headers de sécurité (CORS, HSTS, CSP)
- ✅ /docs désactivé en production
- ✅ Emails hashés dans les logs
- ✅ Rate limiting Redis
- ✅ UFW firewall sur le VPS

---

## 🤝 Contribuer

1. Forkez le projet
2. Créez une branche : `git checkout -b feature/ma-fonctionnalite`
3. Committez : `git commit -m "feat: ajout de X"`
4. Poussez : `git push origin feature/ma-fonctionnalite`
5. Ouvrez une Pull Request

---

## 📝 Licence

MIT. Voir [LICENSE](LICENSE).

---

*« Chaque photo a une histoire. Nous lui redonnons une voix. »*
