# Référence API — Flashback Restore

> Documentation complète de l'API REST du backend Flashback Restore.
>
> Base URL : `http://localhost:8000/api` (dev) ou `https://api.flashback-restore.com/api` (prod)

---

## 📋 Sommaire

- [POST /api/analyze](#post-apianalyze) — Analyser une photo
- [POST /api/restore](#post-apirestore) — Restaurer une photo
- [POST /api/animate](#post-apianimate) — Créer une animation
- [GET /api/animate/{job_id}](#get-apianimatejob_id) — Statut d'un job
- [GET /api/health](#get-apihealth) — Santé du service

---

## 🔐 Authentification

*À implémenter — L'API utilise actuellement des clés API en variable d'environnement.*

En production, les endpoints seront protégés par JWT ou clé API dans le header :

```
Authorization: Bearer <token>
```

Ou :

```
X-API-Key: <votre-clé-api>
```

---

## 📦 Modèles de données

### ImageUpload

Objet représentant une image envoyée à l'API.

Tous les endpoints d'upload utilisent `multipart/form-data`.

| Champ   | Type   | Requis | Description                        |
|---------|--------|--------|------------------------------------|
| `file`  | binary | Oui    | Fichier image (JPEG, PNG, WebP)    |

**Contraintes :**
- Taille max : 20 Mo
- Formats acceptés : `image/jpeg`, `image/png`, `image/webp`
- Résolution min : 100×100 px
- Résolution max : 4096×4096 px

---

## 🔬 Endpoints

---

### `POST /api/analyze`

Analyse une photo pour détecter les défauts (rayures, taches, décoloration, pliures).

#### Requête

```http
POST /api/analyze
Content-Type: multipart/form-data
```

| Champ  | Type   | Requis | Description     |
|--------|--------|--------|-----------------|
| `file` | binary | Oui    | Photo à analyser |

#### Réponse

**`200 OK`** — Analyse réussie

```json
{
  "id": "analy_abc123",
  "status": "completed",
  "defects": [
    {
      "type": "scratch",
      "confidence": 0.94,
      "location": "top_left",
      "description": "Rayure visible en haut à gauche, ~15px de long"
    },
    {
      "type": "discoloration",
      "confidence": 0.87,
      "location": "center",
      "description": "Zone décolorée au centre de l'image"
    }
  ],
  "quality_score": 0.62,
  "original_filename": "grand-mere-1950.jpg",
  "created_at": "2026-05-05T12:00:00Z"
}
```

| Champ              | Type     | Description                                    |
|--------------------|----------|------------------------------------------------|
| `id`               | string   | Identifiant unique de l'analyse                |
| `status`           | string   | `completed` ou `failed`                        |
| `defects`          | array    | Liste des défauts détectés                     |
| `defects[].type`   | string   | Type : `scratch`, `stain`, `discoloration`, `fold`, `tear` |
| `defects[].confidence` | float | Score de confiance (0.0 à 1.0)              |
| `defects[].location` | string | Zone : `top_left`, `top_right`, `center`, `bottom_left`, etc. |
| `defects[].description` | string | Description textuelle du défaut          |
| `quality_score`    | float    | Score de qualité général de la photo (0.0 = très abîmée, 1.0 = parfaite) |
| `original_filename` | string  | Nom du fichier original                        |
| `created_at`       | datetime | Horodatage ISO 8601                            |

**Erreurs**

| Code  | Description                               |
|-------|-------------------------------------------|
| `400` | Fichier invalide (format, taille)         |
| `413` | Fichier trop volumineux (>20 Mo)          |
| `422` | Impossible d'analyser l'image             |
| `500` | Erreur interne (Gemini indisponible, etc.) |

#### Exemple cURL

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@photo-ancienne.jpg"
```

---

### `POST /api/restore`

Restaure une photo en corrigeant les défauts détectés.

#### Requête

```http
POST /api/restore
Content-Type: multipart/form-data
```

| Champ            | Type    | Requis | Description                                      |
|------------------|---------|--------|--------------------------------------------------|
| `file`           | binary  | Oui    | Photo à restaurer                                |
| `analysis_id`    | string  | Non    | ID d'une analyse préalable (optimise le traitement) |
| `restoration_level` | string | Non | Niveau de restauration : `light`, `medium`, `deep` (défaut : `medium`) |
| `colorize`       | boolean | Non    | Coloriser une photo N&B (défaut : `false`)        |
| `enhance_faces`  | boolean | Non    | Améliorer spécifiquement les visages (défaut : `true`) |

#### Réponse

**`200 OK`** — Restauration réussie

```json
{
  "id": "rest_abc456",
  "status": "completed",
  "original_url": "/uploads/originals/photo-ancienne.jpg",
  "restored_url": "/uploads/restored/rest_abc456.jpg",
  "thumbnail_url": "/uploads/thumbnails/rest_abc456_thumb.jpg",
  "improvements": {
    "scratches_fixed": 3,
    "stains_removed": 1,
    "discoloration_fixed": true,
    "quality_gain": 0.28
  },
  "processing_time_ms": 3200,
  "original_filename": "photo-ancienne.jpg",
  "created_at": "2026-05-05T12:00:05Z"
}
```

| Champ                       | Type     | Description                                    |
|-----------------------------|----------|------------------------------------------------|
| `id`                        | string   | Identifiant unique de la restauration          |
| `status`                    | string   | `completed` ou `failed`                        |
| `original_url`              | string   | URL de la photo originale                      |
| `restored_url`              | string   | URL de la photo restaurée                      |
| `thumbnail_url`             | string   | URL de la miniature                            |
| `improvements.scratches_fixed` | int   | Nombre de rayures corrigées                    |
| `improvements.stains_removed` | int    | Nombre de taches supprimées                    |
| `improvements.discoloration_fixed` | bool | Décoloration corrigée                         |
| `improvements.quality_gain`  | float   | Gain de qualité (différence de score)          |
| `processing_time_ms`        | int      | Temps de traitement en millisecondes           |
| `original_filename`         | string   | Nom du fichier original                        |
| `created_at`                | datetime | Horodatage ISO 8601                            |

**Erreurs**

| Code  | Description                                     |
|-------|-------------------------------------------------|
| `400` | Fichier invalide ou paramètres incorrects       |
| `413` | Fichier trop volumineux                         |
| `422` | Échec de la restauration (photo trop abîmée)    |
| `500` | Erreur interne                                  |

#### Exemple cURL

```bash
curl -X POST http://localhost:8000/api/restore \
  -F "file=@photo-ancienne.jpg" \
  -F "restoration_level=deep" \
  -F "colorize=true"
```

---

### `POST /api/animate`

Crée une animation faciale à partir d'une photo restaurée. Cet endpoint est **asynchrone** : il retourne immédiatement un `job_id` à utiliser pour suivre la progression.

#### Requête

```http
POST /api/animate
Content-Type: application/json
```

```json
{
  "restoration_id": "rest_abc456",
  "expression": "smile",
  "duration": 5,
  "intensity": 0.7
}
```

| Champ             | Type    | Requis | Description                                           |
|-------------------|---------|--------|-------------------------------------------------------|
| `restoration_id`  | string  | Oui*   | ID de la restauration à animer                        |
| `image_url`       | string  | Oui*   | URL directe de l'image (alternative à restoration_id) |
| `expression`      | string  | Non    | Expression : `smile`, `surprise`, `neutral`, `blink` (défaut : `smile`) |
| `duration`        | int     | Non    | Durée en secondes (2–15, défaut : 5)                  |
| `intensity`       | float   | Non    | Intensité de l'expression (0.1–1.0, défaut : 0.7)     |

> *`restoration_id` ou `image_url` requis.

#### Réponse

**`202 Accepted`** — Job créé avec succès

```json
{
  "job_id": "anim_job789",
  "status": "processing",
  "estimated_duration_seconds": 45,
  "created_at": "2026-05-05T12:00:15Z"
}
```

| Champ                        | Type     | Description                               |
|------------------------------|----------|-------------------------------------------|
| `job_id`                     | string   | Identifiant unique du job d'animation     |
| `status`                     | string   | `processing`                              |
| `estimated_duration_seconds` | int      | Durée estimée avant complétion            |
| `created_at`                 | datetime | Horodatage ISO 8601                       |

**Erreurs**

| Code  | Description                                     |
|-------|-------------------------------------------------|
| `400` | Paramètres invalides (restoration_id inconnu, expression non supportée) |
| `402` | Crédit D-ID épuisé                              |
| `429` | Trop de requêtes (rate limit)                   |
| `500` | Erreur interne (D-ID indisponible)              |

#### Exemple cURL

```bash
curl -X POST http://localhost:8000/api/animate \
  -H "Content-Type: application/json" \
  -d '{
    "restoration_id": "rest_abc456",
    "expression": "smile",
    "duration": 5
  }'
```

---

### `GET /api/animate/{job_id}`

Récupère le statut d'un job d'animation. À appeler régulièrement (polling) jusqu'à ce que le statut soit `completed` ou `failed`.

#### Requête

```http
GET /api/animate/{job_id}
```

| Paramètre | Type   | Emplacement | Description              |
|-----------|--------|-------------|--------------------------|
| `job_id`  | string | Path        | ID du job d'animation    |

#### Réponse

**`200 OK`** — Job en cours

```json
{
  "job_id": "anim_job789",
  "status": "processing",
  "progress": 65,
  "estimated_remaining_seconds": 15,
  "created_at": "2026-05-05T12:00:15Z"
}
```

**`200 OK`** — Job terminé

```json
{
  "job_id": "anim_job789",
  "status": "completed",
  "progress": 100,
  "result": {
    "video_url": "/uploads/animations/anim_job789.mp4",
    "thumbnail_url": "/uploads/animations/anim_job789_thumb.jpg",
    "duration_seconds": 5,
    "format": "mp4",
    "resolution": "1080x1080",
    "size_bytes": 2450000
  },
  "processing_time_ms": 42000,
  "created_at": "2026-05-05T12:00:15Z",
  "completed_at": "2026-05-05T12:00:57Z"
}
```

| Champ                                  | Type     | Description                               |
|----------------------------------------|----------|-------------------------------------------|
| `job_id`                               | string   | Identifiant unique du job                 |
| `status`                               | string   | `processing`, `completed` ou `failed`     |
| `progress`                             | int      | Pourcentage (0–100)                       |
| `estimated_remaining_seconds`          | int/null | Temps restant estimé (null si terminé)   |
| `result.video_url`                     | string   | URL de la vidéo animée (si completed)     |
| `result.thumbnail_url`                 | string   | URL de la vignette                        |
| `result.duration_seconds`              | int      | Durée de la vidéo                         |
| `result.format`                        | string   | Format (`mp4`)                            |
| `result.resolution`                    | string   | Résolution (ex: `1080x1080`)              |
| `result.size_bytes`                    | int      | Taille du fichier en octets               |
| `processing_time_ms`                   | int/null | Temps de traitement total (null si en cours) |
| `created_at`                           | datetime | Horodatage de création                    |
| `completed_at`                         | datetime/null | Horodatage de complétion              |

**`200 OK`** — Job échoué

```json
{
  "job_id": "anim_job789",
  "status": "failed",
  "error": "D-ID processing failed: face not detected",
  "error_code": "FACE_NOT_DETECTED",
  "created_at": "2026-05-05T12:00:15Z",
  "completed_at": "2026-05-05T12:00:30Z"
}
```

**Erreurs**

| Code  | Description              |
|-------|--------------------------|
| `404` | Job non trouvé           |
| `500` | Erreur interne           |

#### Exemple cURL

```bash
curl http://localhost:8000/api/animate/anim_job789
```

#### Stratégie de polling recommandée

```javascript
async function pollAnimation(jobId, intervalMs = 3000, maxAttempts = 40) {
  for (let i = 0; i < maxAttempts; i++) {
    const res = await fetch(`/api/animate/${jobId}`);
    const data = await res.json();

    if (data.status === 'completed') return data.result;
    if (data.status === 'failed') throw new Error(data.error);

    await new Promise(r => setTimeout(r, intervalMs));
  }
  throw new Error('Timeout: animation took too long');
}
```

---

### `GET /api/health`

Vérifie la santé du service et de ses dépendances.

#### Requête

```http
GET /api/health
```

#### Réponse

**`200 OK`**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "gemini_api": "ok",
    "did_api": "ok",
    "disk_space": "85% free"
  },
  "uptime_seconds": 123456
}
```

| Champ                      | Type   | Description                                  |
|----------------------------|--------|----------------------------------------------|
| `status`                   | string | `healthy` ou `degraded`                      |
| `version`                  | string | Version de l'API                             |
| `environment`              | string | `development`, `staging` ou `production`     |
| `checks.database`          | string | `ok`, `error` ou `degraded`                  |
| `checks.redis`             | string | `ok`, `error` ou `degraded`                  |
| `checks.gemini_api`        | string | `ok`, `error` ou `degraded`                  |
| `checks.did_api`           | string | `ok`, `error` ou `degraded`                  |
| `checks.disk_space`        | string | Espace disque disponible                     |
| `uptime_seconds`           | int    | Temps depuis le dernier redémarrage          |

**`503 Service Unavailable`** — Service dégradé

```json
{
  "status": "degraded",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "redis": "error",
    "gemini_api": "ok",
    "did_api": "ok"
  }
}
```

---

## ⚠️ Codes d'erreur génériques

| Code HTTP | Signification                                          |
|-----------|--------------------------------------------------------|
| `400`     | Requête invalide (paramètres manquants, format incorrect) |
| `401`     | Non authentifié (à implémenter)                        |
| `402`     | Paiement requis / crédit épuisé                        |
| `403`     | Non autorisé                                           |
| `404`     | Ressource non trouvée                                  |
| `413`     | Fichier trop volumineux                                |
| `422`     | Entité non traitable (échec métier)                    |
| `429`     | Trop de requêtes (rate limiting)                       |
| `500`     | Erreur interne du serveur                              |
| `503`     | Service indisponible                                   |

Toutes les erreurs suivent le format :

```json
{
  "error": true,
  "code": "INVALID_IMAGE_FORMAT",
  "message": "Format d'image non supporté. Utilisez JPEG, PNG ou WebP.",
  "detail": "Le fichier reçu est de type image/gif"
}
```

---

## 📊 Rate Limiting

*À implémenter.*

| Endpoint            | Limite (par IP)      | Fenêtre   |
|---------------------|----------------------|-----------|
| `POST /api/analyze` | 20 requêtes          | 1 minute  |
| `POST /api/restore` | 10 requêtes          | 1 minute  |
| `POST /api/animate` | 5 requêtes           | 1 minute  |
| `GET /api/*`        | 60 requêtes          | 1 minute  |

---

## 🔄 Versionnement

L'API utilise un versionnement dans l'URL :

```
/api/v1/analyze
/api/v1/restore
```

La version actuelle (`/api/`) pointe vers la dernière version stable (`v1`).

---

*Documentation générée automatiquement à partir du code — Mise à jour : Mai 2026*
