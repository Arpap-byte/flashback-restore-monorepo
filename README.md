# Flashback Restore — Redonnez vie à vos souvenirs

![Flashback Restore](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python)
![Next.js](https://img.shields.io/badge/next.js-14-black?logo=next.js)
![Flutter](https://img.shields.io/badge/flutter-3.x-blue?logo=flutter)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker)
![Licence](https://img.shields.io/badge/licence-MIT-green)

**Flashback Restore** est une application de restauration et d'animation de photos anciennes par intelligence artificielle. Téléversez une photo abîmée, rayée ou décolorée, et notre IA la restaure, puis l'anime avec des expressions faciales réalistes — comme si le passé reprenait vie sous vos yeux.

---

## ✨ Fonctionnalités

- 🖼️ **Analyse intelligente** — Détection des défauts (rayures, taches, décoloration, pliures)
- 🔧 **Restauration IA** — Correction des imperfections grâce à Google Gemini
- 🎬 **Animation faciale** — La photo restaurée s'anime avec des expressions naturelles (via D-ID)
- 🌐 **Landing page** — Site vitrine moderne avec Next.js 14
- 📱 **Application mobile** — App Flutter pour iOS et Android (à venir)

---

## 🏗️ Architecture

```
flashback-restore-monorepo/
├── backend/          # API FastAPI (Python) — Restauration & animation
├── landing/          # Site vitrine Next.js 14 (TypeScript)
├── app/              # Application mobile Flutter (à venir)
├── docs/             # Documentation technique
├── nginx/            # Configuration du reverse proxy
├── .github/          # CI/CD GitHub Actions
├── docker-compose.yml
└── README.md
```

### Stack technique

| Composant     | Technologie               | Port |
|---------------|---------------------------|------|
| Backend API   | FastAPI (Python 3.11+)    | 8000 |
| Landing Page  | Next.js 14 (TypeScript)   | 3000 |
| Base de données| PostgreSQL 16            | 5432 |
| Cache         | Redis 7                   | 6379 |
| Reverse Proxy | Nginx                     | 80   |
| IA            | Google Gemini + D-ID      | —    |

---

## 🚀 Démarrage rapide

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) et Docker Compose v2
- Clés API Google Gemini et D-ID

### 1. Cloner le projet

```bash
git clone https://github.com/arpap-byte/flashback-restore-monorepo.git
cd flashback-restore-monorepo
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditez `.env` et renseignez vos clés API :

```env
GEMINI_API_KEY=votre-clé-gemini
DID_API_KEY=votre-clé-d-id
```

### 3. Lancer l'environnement de développement

```bash
docker compose up -d
```

### 4. Accéder aux services

| Service         | URL                             |
|-----------------|---------------------------------|
| Landing page    | http://localhost                 |
| API (Swagger)   | http://localhost/api/docs        |
| API (ReDoc)     | http://localhost/redoc           |
| Backend (direct) | http://localhost:8000           |
| Landing (direct) | http://localhost:3000           |

### 5. Vérifier que tout fonctionne

```bash
curl http://localhost/api/health
# → {"status": "healthy", "version": "1.0.0"}
```

---

## 🧪 Développement

### Backend (Python/FastAPI)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Landing (Next.js)

```bash
cd landing
npm install
npm run dev
```

### Lancer les tests

```bash
# Backend
cd backend && pytest --cov=. -v

# Landing
cd landing && npm run build
```

---

## 📦 Déploiement

Le déploiement est automatisé via **GitHub Actions**.

### Environnements

- **Staging** — Déclenché automatiquement sur `main`
- **Production** — À configurer (déclenchement manuel ou via tag)

### Images Docker

Les images sont publiées sur **GitHub Container Registry** :

```
ghcr.io/arpap-byte/flashback-backend:latest
ghcr.io/arpap-byte/flashback-landing:latest
```

### Déploiement manuel

```bash
# Build local
docker compose build

# Push vers un registre
docker tag flashback-backend ghcr.io/arpap-byte/flashback-backend:latest
docker push ghcr.io/arpap-byte/flashback-backend:latest
```

---

## 📖 Documentation

- [Architecture détaillée](docs/ARCHITECTURE.md)
- [Référence API](docs/API.md)

---

## 🤝 Contribuer

1. Forkez le projet
2. Créez une branche : `git checkout -b feature/ma-fonctionnalite`
3. Committez vos changements : `git commit -m "feat: ajout de ma fonctionnalité"`
4. Poussez : `git push origin feature/ma-fonctionnalite`
5. Ouvrez une Pull Request

### Conventions de commits

Nous suivons [Conventional Commits](https://www.conventionalcommits.org/fr/) :

- `feat:` — Nouvelle fonctionnalité
- `fix:` — Correction de bug
- `docs:` — Documentation
- `style:` — Formatage, point-virgules manquants…
- `refactor:` — Refactorisation sans changement fonctionnel
- `test:` — Ajout ou modification de tests
- `chore:` — Tâches de maintenance

---

## 📝 Licence

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

---

## 👤 Auteur

Créé par [arpap-byte](https://github.com/arpap-byte).

---

*« Chaque photo a une histoire. Nous lui redonnons une voix. »*
