# Architecture — Flashback Restore

> Documentation technique du système Flashback Restore.  
> Version 1.1.0 — Mai 2026

---

## 📐 Vue d'ensemble

Flashback Restore est une application SaaS de restauration et d'animation de photos par IA, organisée en **monorepo** :

```
                   ┌─────────────┐
                   │  Utilisateur │
                   └──────┬──────┘
                          │ HTTPS
                          ▼
              ┌───────────────────────┐
              │  Traefik :80, :443    │
              │  TLS + Reverse Proxy  │
              └───────┬───────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   /api/*       /uploads/*        /*
        │             │             │
        ▼             ▼             ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  FastAPI      │ │  Backend │ │  Next.js 15  │
│  :8000        │ │  Static  │ │  :8001       │
│  (systemd)    │ │  Files   │ │  (systemd)    │
└───┬───┬───┬───┘ └──────────┘ └──────────────┘
    │   │   │
    ▼   ▼   ▼
┌───────┐ ┌─────────┐ ┌───────────┐
│Redis  │ │PostgreSQL│ │Backblaze  │
│:6379  │ │:5432     │ │B2 (S3)    │
└───┬───┘ └─────────┘ └───────────┘
    │
    ▼
┌───────────┐
│ARQ Worker │  ← Jobs async (restauration, animation)
│systemd    │
└───────────┘
```

---

## 🧩 Composants

### 1. Frontend — Next.js 15 (TypeScript)

**Fichier systemd** : `flashback-landing.service`  
**Port** : 8001 (interne), exposé via Traefik sur 80/443  
**Répertoire** : `landing/`

| Page | Route | Protection |
|------|-------|------------|
| Accueil | `/` | Publique |
| Tarifs | `/pricing` | Publique |
| Dashboard | `/dashboard` | Clerk (middleware) |
| Restauration | `/restore` | Clerk (middleware) |
| Historique | `/historique` | Clerk (middleware) |

**Authentification** : Clerk avec `@clerk/nextjs`. Le middleware protège les routes `/dashboard`, `/restore`, `/historique`. Le token JWT Clerk est envoyé au backend via `api.ts`.

### 2. Backend — FastAPI (Python 3.13, async)

**Fichier systemd** : `flashback-backend.service`  
**Port** : 8000 (interne)  
**Répertoire** : `backend/`

| Endpoint | Méthode | Auth | Description |
|----------|---------|------|-------------|
| `/api/health` | GET | — | Health check (B2, Gemini, DB, Stripe) |
| `/api/upload` | POST | Clerk JWT | Upload photo → B2 |
| `/api/restore` | POST | Clerk JWT | Lancer restauration async (→ ARQ) |
| `/api/restore/{job_id}` | GET | Clerk JWT | Statut d'un job |
| `/api/user/me` | GET | Clerk JWT | Profil + crédits |
| `/api/webhooks/stripe` | POST | Stripe sig | Webhook Stripe (idempotent) |
| `/api/webhooks/clerk` | POST | Clerk sig | Webhook Clerk (sync utilisateurs) |

**Validation** :
- MIME type vérifié via `python-magic` (magic bytes, pas extension)
- Token Clerk vérifié via JWKS (RS256)
- Crédits consommés atomiquement (`SELECT ... FOR UPDATE`)

### 3. Worker ARQ — Jobs asynchrones

**Fichier systemd** : `flashback-worker-arq.service`  
**Exécutable** : `arq app.worker.WorkerSettings`

Le worker ARQ écoute la queue Redis et exécute les jobs en arrière-plan :
1. **restore_photo** : Télécharge la photo depuis B2 → appelle Gemini → upload le résultat vers B2 → met à jour la DB
2. **animate_photo** : Télécharge la photo restaurée depuis B2 → appelle D-ID → upload la vidéo vers B2 → met à jour la DB

Cela permet de ne **pas bloquer** les requêtes HTTP pendant les traitements IA (5-30s).

### 4. Traefik — Reverse Proxy

**Container Docker** : `traefik`  
**Fichier config** : `traefik/flashback-dynamic.yml`

Routes :
```yaml
flashback-api:      /api/*         → backend:8000   (priority 100)
flashback-uploads:  /uploads/*     → backend:8000   (priority 150)
flashback-landing:  /*             → landing:8001    (priority 50)
```

TLS via Let's Encrypt (ACME), certificats wildcard `*.flashback-restore.com`.

---

## 🗄️ Base de données

### SQLAlchemy async (SQLite / PostgreSQL)

Les modèles sont définis dans `backend/app/db/models.py`. L'accès se fait via **queries async** dans `backend/app/db/queries.py` (plus de `database.py` sync).

```python
# Exemple : consommation de crédit atomique
async def consommer_credit(user_id: str, quantite: int = 1) -> bool:
    async with get_session() as session:
        user = await session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        ...
```

**Migration SQLite → PostgreSQL** : le backend supporte les deux. Passer à PostgreSQL pour la production en changeant `DATABASE_URL`.

---

## ☁️ Stockage — Backblaze B2 (S3-compatible)

Le module `backend/app/storage.py` encapsule l'accès à B2 via `boto3` :

```python
from app.storage import uploader_fichier, telecharger_bytes, b2_est_disponible

# Upload
url = uploader_fichier("/tmp/photo.jpg", "photos/2026/05/abc.jpg")

# Download
data = telecharger_bytes("photos/2026/05/abc.jpg")
```

**Configuration** (`.env`) :
- `B2_ENDPOINT` — Endpoint S3 (ex: `s3.eu-central-003.backblazeb2.com`)
- `B2_KEY_ID` — Key ID de l'application B2
- `B2_APPLICATION_KEY` — Clé secrète
- `B2_BUCKET_NAME` — Nom du bucket
- `B2_CDN_URL` — Optionnel : URL CDN Cloudflare

**Sécurité** : bucket privé, chiffrement SSE-B2 activé, accès via clés d'application restreintes.

---

## 🔐 Sécurité

| Mesure | Implémentation |
|--------|---------------|
| Auth utilisateur | Clerk JWT (RS256, vérifié via JWKS) |
| Validation fichiers | `python-magic` (magic bytes) |
| Crédits atomiques | `SELECT ... FOR UPDATE` |
| Stripe idempotent | Table `stripe_events` |
| Rate limiting | Redis (token bucket) |
| Headers sécurité | HSTS, CSP, CORS restreint |
| /docs désactivé | Production uniquement |
| Logs anonymisés | Emails hashés |
| Firewall | UFW, ports minimums |

---

## 🚦 Flux de restauration (end-to-end)

```
1. User upload         POST /api/upload (multipart)
   ├── Vérifie token Clerk JWT
   ├── Valide MIME (magic bytes)
   ├── Upload vers B2 → retourne b2_key
   └── Response: {photo_id, b2_key}

2. User lance          POST /api/restore {photo_id}
   ├── Vérifie crédits disponibles (FOR UPDATE)
   ├── Consomme 1 crédit
   ├── Enqueue job ARQ → restore_photo(photo_id)
   └── Response: {job_id, status: "queued"}

3. ARQ Worker          restore_photo(photo_id)
   ├── Télécharge photo depuis B2
   ├── Appelle Gemini API (restauration)
   ├── Upload résultat vers B2
   ├── Met à jour DB (status, b2_key_restored)
   └── Si Premium+, enqueue animation

4. User poll           GET /api/restore/{job_id}
   └── Response: {status, restored_url?, video_url?}
```

---

## 📊 Dépendances externes

| Service | Utilisation | Fallback |
|---------|------------|----------|
| Gemini API | Restauration d'images | — (bloquant) |
| D-ID API | Animation faciale | Désactivé si indisponible |
| Stripe | Paiements | Mode test |
| Clerk | Authentification | — (bloquant) |
| Backblaze B2 | Stockage | Stockage local si B2 down |
| Redis | Queue + Cache | — (bloquant pour ARQ) |
| Sentry | Monitoring erreurs | Optionnel |

---

## 🔄 CI/CD

Le déploiement est manuel pour l'instant (pas de GitHub Actions actives) :

```bash
# Backend
cd backend && sudo systemctl restart flashback-backend

# Worker ARQ
pkill -f "arq app.worker" && \
  set -a; source ../.env; set +a && \
  arq app.worker.WorkerSettings &

# Frontend
cd landing && npm run build && sudo systemctl restart flashback-landing
```

---

*Documentation maintenue par l'équipe Flashback Restore.*
