# Architecture — Flashback Restore

> Documentation technique du système Flashback Restore.

---

## 📐 Vue d'ensemble

Flashback Restore est une application de restauration et d'animation de photos par IA, organisée en **monorepo** avec trois composants principaux :

```
┌─────────────────────────────────────────────────┐
│                    CLIENT                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Landing  │  │ App      │  │ Navigateur   │   │
│  │ Next.js  │  │ Flutter  │  │ (API Docs)   │   │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │             │               │            │
└───────┼─────────────┼───────────────┼────────────┘
        │             │               │
        ▼             ▼               ▼
┌─────────────────────────────────────────────────┐
│                   NGINX :80                      │
│              Reverse Proxy + Cache               │
└─────────────────────┬───────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   /api/*         /            /uploads/
        │             │             │
        ▼             ▼             │
┌──────────────┐ ┌──────────┐      │
│   BACKEND    │ │ LANDING  │      │
│   FastAPI    │ │ Next.js  │      │
│   :8000      │ │ :3000    │      │
└──┬───┬───┬──┘ └──────────┘      │
   │   │   │                       │
   ▼   ▼   ▼                       │
┌──────┐ ┌──────┐ ┌─────────────┐  │
│  DB  │ │Redis │ │ Stockage    │◄─┘
│PostgreSQL│   │ │ (Uploads)   │
│ :5432│ │:6379 │ │ Volume      │
└──────┘ └──────┘ └─────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌──────────┐
   │ Gemini  │ │  D-ID   │ │  Stockage │
   │  (IA)   │ │(Anim.)  │ │  Cloud    │
   └─────────┘ └─────────┘ └──────────┘
```

---

## 🔄 Flux de données

### Parcours utilisateur : Restauration + Animation

```
                            CLIENT
                              │
                    ① Téléversement photo
                              │
                              ▼
┌──────────────────────────────────────────────────┐
│                 BACKEND (FastAPI)                  │
│                                                    │
│  ② POST /api/analyze                               │
│     └─► Analyse de la photo par Gemini             │
│         └─► Détection : rayures, taches, pliures   │
│         └─► Retourne un rapport d'analyse          │
│                                                    │
│  ③ POST /api/restore                               │
│     └─► Restauration par Gemini                    │
│         └─► Correction des défauts détectés        │
│         └─► Amélioration de la qualité             │
│         └─► Retourne l'image restaurée             │
│                                                    │
│  ④ POST /api/animate                               │
│     └─► Envoi à D-ID pour animation                │
│         └─► Création d'un job d'animation          │
│         └─► Retourne un job_id                     │
│                                                    │
│  ⑤ GET /api/animate/{job_id}                       │
│     └─► Polling du statut du job D-ID              │
│         └─► Retourne l'URL de la vidéo animée      │
│                                                    │
└──────────────────────────────────────────────────┘
                              │
                              ▼
                            CLIENT
                    ⑥ Affichage du résultat
                       (image restaurée + vidéo)
```

### Détail des échanges

| Étape | Acteur         | Action                               | Entrée              | Sortie              |
|-------|----------------|--------------------------------------|---------------------|---------------------|
| ①     | Utilisateur    | Téléverse une photo ancienne         | Fichier image       | —                   |
| ②     | Gemini API     | Analyse les défauts de l'image       | Image + prompt      | Rapport d'analyse   |
| ③     | Gemini API     | Restaure l'image                     | Image + défauts     | Image restaurée     |
| ④     | D-ID API       | Crée un job d'animation faciale      | Image restaurée     | job_id              |
| ⑤     | D-ID API       | Vérifie le statut de l'animation     | job_id              | URL vidéo ou statut |
| ⑥     | Utilisateur    | Visualise le résultat                | —                   | —                   |

---

## 🔌 Contrat API (résumé)

Voir [API.md](API.md) pour la référence complète.

| Méthode | Endpoint                  | Description                        |
|---------|---------------------------|------------------------------------|
| `POST`  | `/api/analyze`            | Analyser une photo (défauts)       |
| `POST`  | `/api/restore`            | Restaurer une photo                |
| `POST`  | `/api/animate`            | Créer une animation faciale        |
| `GET`   | `/api/animate/{job_id}`   | Statut d'un job d'animation        |
| `GET`   | `/api/health`             | Vérification de santé              |

---

## 🧱 Choix techniques

### Backend — FastAPI (Python)

| Choix            | Justification                                               |
|------------------|-------------------------------------------------------------|
| **FastAPI**      | Performant, typage natif, documentation OpenAPI automatique |
| **PostgreSQL**   | Base relationnelle robuste, support JSON, mature            |
| **Redis**        | Cache rapide, queue de jobs, stockage de session            |
| **Celery**       | (Optionnel) Tâches asynchrones pour les traitements longs   |
| **Gemini API**   | Meilleure analyse visuelle, prompts flexibles, gratuit tier |
| **D-ID API**     | Leader de l'animation faciale, SDK simple, qualité HD       |

### Landing — Next.js 14

| Choix           | Justification                                        |
|-----------------|------------------------------------------------------|
| **Next.js 14**  | App Router, Server Components, SEO optimisé           |
| **TypeScript**  | Typage statique, meilleure maintenabilité             |
| **Tailwind CSS**| Styling rapide, design system cohérent                |

### Infrastructure

| Choix           | Justification                                        |
|-----------------|------------------------------------------------------|
| **Docker**      | Environnement reproductible, CI/CD natif              |
| **Nginx**       | Reverse proxy léger, cache, compression              |
| **GitHub Actions**| CI/CD intégré, gratuit pour projets publics          |
| **GHCR**        | Registre Docker intégré à GitHub, sans frais         |

---

## 📁 Structure des dossiers

```
flashback-restore-monorepo/
├── backend/
│   ├── api/                  # Routes FastAPI
│   │   ├── analyze.py        # POST /api/analyze
│   │   ├── restore.py        # POST /api/restore
│   │   ├── animate.py        # POST /api/animate, GET /api/animate/{id}
│   │   └── health.py         # GET /api/health
│   ├── services/             # Logique métier
│   │   ├── gemini.py         # Client Gemini
│   │   ├── did_client.py     # Client D-ID
│   │   └── image_processor.py
│   ├── models/               # Modèles SQLAlchemy
│   ├── schemas/              # Schémas Pydantic
│   ├── main.py               # Point d'entrée
│   ├── requirements.txt
│   └── Dockerfile
│
├── landing/
│   ├── app/                  # App Router Next.js 14
│   │   ├── page.tsx          # Page d'accueil
│   │   ├── layout.tsx        # Layout racine
│   │   └── api/              # API Routes (proxies)
│   ├── components/           # Composants React
│   ├── public/               # Assets statiques
│   ├── package.json
│   └── Dockerfile
│
├── app/                      # Application Flutter (à venir)
├── docs/                     # Documentation
├── nginx/                    # Configuration Nginx
├── .github/workflows/        # CI/CD
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔒 Sécurité

- **Clés API** stockées dans les variables d'environnement uniquement
- **Toutes les requêtes** passent par HTTPS en production
- **Rate limiting** sur les endpoints sensibles (à implémenter)
- **Validation des fichiers** : types MIME, taille max, scan antivirus (à implémenter)
- **CORS** configuré pour n'autoriser que les origines de confiance
- **Secrets GitHub** pour les variables sensibles en CI/CD

---

## 📈 Évolutivité prévue

- **File d'attente** : Redis + Celery pour les jobs longs (animation, restauration batch)
- **Stockage cloud** : S3/Cloudflare R2 pour les fichiers uploadés
- **CDN** : Cloudflare pour la distribution des assets statiques et vidéos
- **Monitoring** : Sentry pour les erreurs, Prometheus/Grafana pour les métriques
- **Scaling horizontal** : Le backend est stateless, prêt pour du scaling horizontal
