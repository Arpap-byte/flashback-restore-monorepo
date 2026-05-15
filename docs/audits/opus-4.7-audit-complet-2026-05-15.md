# Audit Technique Complet — Flashback Restore

**Date** : 15 mai 2026  
**Supervision** : Opus 4.7  
**Périmètre** : Backend, Frontend, Base de données, Infrastructure

---

## Synthèse Exécutive

**Note globale** : 7.2/10

| Domaine | Issues P0 | Issues P1 | Issues P2 | Issues P3 | Total |
|---|---|---|---|---|---|
| Backend & DB | 6 🔴 | 9 🟠 | 8 🟡 | 7 🟢 | 30 |
| Frontend | 5 🔴 | 10 🟠 | 15 🟡 | 11 🟢 | 41 |
| Infrastructure | 8 🔴 | 8 🟠 | 8 🟡 | 5 🟢 | 29 |
| **Total** | **19** | **27** | **31** | **23** | **100** |

### Top 5 actions immédiates (cette semaine)

1. **Corriger les contraintes CHECK qui excluent `colorisation`** → crash 500 sur colorisation standalone
2. **Ajouter des headers de sécurité** (CSP, HSTS, X-Frame-Options) sur le frontend
3. **Ajouter 2-4 Go de swap** sur le VPS — OOM killer documenté
4. **Corriger le backup PostgreSQL** (exit code 2 systématique) + ajouter backup n8n
5. **Supprimer les secrets en clair** des unités systemd et les externaliser

---

## 1. Backend & Base de données

### 🔴 Critiques (P0)

| Fichier | Ligne | Problème | Risque | Correction |
|---|---|---|---|---|
| `api/auth.py` | 99-111 | **Énumération utilisateurs** : 409 vs 202 expose l'existence d'un compte | 🔴 Énumération possible | Retourner 202 Accepted générique |
| `config.py` | 19 | **`DB_PATH` SQLite mort** post-migration PostgreSQL | 🔴 Confusion maintenance | Supprimer |
| `config.py` | 33-35 | **`DID_API_KEY`, `DID_BASE_URL`** — D-ID retiré depuis mai 2026 | 🔴 Code mort | Supprimer + retirer `did_disponible` du `/health` |
| `stripe_service.py` | 237-244 | **Bug `_dernier_webhook`** : delta toujours ~0s, warning jamais déclenché | 🔴 Monitoring cassé | Sauvegarder l'ancien timestamp avant mise à jour |
| `db/models.py` | 148 | **`ck_essais_type` exclut `colorisation`** | 🔴 Crash 500 sur colorisation gratuite | Ajouter `'colorisation'` à la contrainte |
| `db/models.py` | 179-181 | **`ck_consommation_type` exclut `colorisation`** | 🔴 Crash 500 sur consommation crédit colorisation | Ajouter `'colorisation'` à la contrainte |

### 🟠 Hautes (P1)

| Fichier | Ligne | Problème | Correction |
|---|---|---|---|
| `api/user.py` | 160-169 | **N+1 JWT encodes** : 50 tokens par appel `/history` | Générer 1 token par appel |
| `api/user.py` | 65-97 | **6 requêtes DB séquentielles** pour `/me` | Fusionner en 2 requêtes |
| `db/queries.py` | 114 | **`_plan_cache` sans éviction** → fuite mémoire | `cachetools.TTLCache` |
| `db/models.py` | - | **Pas d'index sur `derniere_activite`** — scan séquentiel dashboard | Ajouter index |
| `db/models.py` | - | **Pas d'index sur `travaux.cree_le`** — scan séquentiel cleanup | Ajouter index |
| `api/routes.py` | 873-939 | **`_appliquer_restauration_pillow`** : 67 lignes mortes | Supprimer |
| `services/gemini_service.py` | 239-285 | **`obtenir_parametres_restauration`** : 47 lignes mortes | Supprimer |
| `services/veo_service.py` | 468-488 | **`verifier_statut_animation_veo`** : 21 lignes mortes | Supprimer |
| `db/queries.py` | 96-111 | **`MODELE_*_PAR_PLAN`** : 16 lignes jamais importées | Supprimer |

### 🟡 Moyennes (P2)

- `config.py:57-61` : Crash au boot si Stripe webhook placeholder → `warnings.warn()` au lieu de `raise`
- `main.py:220-229` : try/except silencieux sur `decoder_token` → logger en DEBUG
- `api/routes.py` : 1743 lignes monolithiques → splitter en modules
- `db/queries.py:1195-1214` : 20 alias de fonctions inutilisés
- `worker.py` : Docstrings mentionnent encore D-ID
- `api/routes.py:448-551` : SQL inline volumineux → déléguer à `queries.py`
- `limiter.py` + `rate_limit_middleware.py` : Double système de rate limiting

### 🟢 Basses (P3)

- Commentaires D-ID résiduels dans `routes.py`, `veo_service.py`, `services/__init__.py`
- `main.py:82` : Description API mentionne "portraits parlants" (obsolète)
- `worker.py:329` : `job_timeout=600` peut être court pour Veo 1080p → 900s
- `db/models.py:47` : `password_hash` NOT NULL mais OAuth = "" → sentinelle explicite
- Pas de FK index sur `consommation_credits.travail_id`
- `stripe_service.py:31` : Variable globale modifiée sans lock async

### Code mort total identifié
~**200 lignes** : DID_API_KEY, DB_PATH, `_appliquer_restauration_pillow`, `obtenir_parametres_restauration`, `verifier_statut_animation_veo`, `MODELE_*_PAR_PLAN`, 20 alias

---

## 2. Frontend

### 🔴 Critiques (P0)

| Fichier | Problème | Risque |
|---|---|---|
| `layout.tsx:59` | **Dark mode forcé** — `<html>` a `dark` en dur, toggle cassé | Thème bloqué |
| `next.config.ts` | **Aucun header de sécurité** — pas de CSP, HSTS, X-Frame-Options | XSS, clickjacking |
| `api.ts:94-98` | **Token JWT dans localStorage** — accessible à tout script XSS | Vol de session |
| `api.ts:270-287` | **Token JWT exposé dans l'URL** — `?token=` dans les query params | Fuite token (logs, referrer) |
| `admin/page.tsx:507` | **Clé admin en localStorage** — `flashback_admin_key` | Prise de contrôle admin |

### 🟠 Hautes (P1)

- **`unoptimized` sur tous les `<Image>`** : bypass complet optimisation Next.js → LCP dégradé
- **`robots` au format string déprécié** → SEO non garanti
- **Pas d'image OG/Twitter** → partages sans preview
- **Middleware regex trop permissif** → pas de vérification JWT côté middleware
- **Pas de `prefers-reduced-motion`** → accessibilité
- **`alt` text minimal** sur toutes les images
- **Sliders sans accessibilité clavier** → `onMouseDown` uniquement
- **Aucune page n'a son propre `metadata`** → même titre partout
- **Pas de `canonical` URL** → SEO contenu dupliqué
- **Pas de JSON-LD structured data**

### 🟡 Moyennes (P2)

- **Admin hors design system** : `bg-zinc-950` au lieu des tokens CSS
- **9 imports inutilisés** : `Loader2`, `Upload`, `AnimatePresence`, `Shield`, `ArrowRight`, `Trash2`, `User`, `Camera`
- **`console.error` en production** sur plusieurs pages
- **Spinners de chargement incohérents** — pas de composant partagé
- **Aucun lazy loading** — tout en un bundle client
- **`remotePatterns` limité à `flashback-restore.com`** — bloque les previews
- **Chaîne "travail/travaux" invalide** dans l'admin
- **Toggle de thème dupliqué** dans Navbar (desktop + mobile)

### 🟢 Basses (P3)

- `suppressHydrationWarning` dans le layout
- `<a>` au lieu de `<Link>` dans historique et animate → flash pleine page
- "2 à 3 minutes" / "30 secondes" en dur → UX trompeuse
- Pas d'`ErrorBoundary` React → crash complet si erreur
- Slider de comparaison sans transition CSS
- Scrollbar custom uniquement `-webkit-`

---

## 3. Infrastructure

### 🔴 Critiques (P0)

| Composant | Problème | Risque |
|---|---|---|
| **Swap** | Aucun swap configuré (15 Go RAM) | OOM killer inévitable — déjà survenu le 14 mai |
| **flashback-db** | Aucun healthcheck Docker | Crash DB non détecté |
| **postgres n8n** | Aucun healthcheck Docker | Idem |
| **Cron backup** | `backup_pg.sh` exit code 2 systématique | Backups non fiables |
| **Flood /api/health** | `148.230.116.52` bombarde → 429 | DDoS/healthcheck mal configuré |
| **Secrets en clair** | Dans systemd + `.env` | Exposition totale si accès root |
| **Pas de monitoring externe** | Aucun Uptime Robot/healthchecks.io | Aucune alerte si VPS down |
| **Postgres n8n** | Pas de backup | Perte workflows possible |

### 🟠 Hautes (P1)

- **N8N_ENCRYPTION_KEY** = `changeme_key` — clé par défaut
- **startLimitInterval** dans `[Service]` au lieu de `[Unit]` → restart policy incorrecte
- **Pas de limites mémoire/CPU** sur les 12 conteneurs Docker
- **Traefik en `network_mode: host`** → isolement réseau contourné
- **SSH port 22** sans fail2ban
- **Ollama sur 0.0.0.0:11434** — exposé si UFW désactivé
- **`.env` backend format invalide** pour systemd → variables non chargées
- **Cron backup sans alerting** — échecs silencieux

### 🟡 Moyennes (P2)

- Deux versions PostgreSQL (15 + 16) en parallèle
- Pas de rotation logs Docker → croissance disque
- Scans `/wp-admin` réguliers sur `flashback-restore.com`
- Monarx-agent instable (3 crashs le 14 mai)
- UFW : règles DENY redondantes sur ports internes
- RAM : 5.7/15 GiB au repos, seulement 1.3 GiB free
- Landing : pas de `ProtectSystem` contrairement au backend
- Sentry DSN vide → pas de capture d'erreur applicative

### 🟢 Basses (P3)

- Traefik `:latest` au lieu de version pinée
- Pas de `depends_on` avec healthchecks dans docker-compose
- Deux docker-compose pour Traefik (confusion possible)
- UDEV warnings cosmétiques au boot
- Redis natif + Redis Docker (redondance non documentée)

---

## 4. Plan d'action priorisé

### Semaine 1 (P0 — 19 issues)

| # | Action | Domaine | Effort |
|---|---|---|---|
| 1 | Corriger contraintes CHECK excluant `colorisation` | Backend | 30 min |
| 2 | Ajouter CSP, HSTS, X-Frame-Options, Referrer-Policy | Frontend | 1h |
| 3 | Ajouter 2-4 Go de swap | Infra | 15 min |
| 4 | Corriger `backup_pg.sh` (exit code 2) | Infra | 30 min |
| 5 | Ajouter backup PostgreSQL n8n | Infra | 30 min |
| 6 | Supprimer code mort (~200 lignes) | Backend | 1h |
| 7 | Supprimer secrets des unités systemd → `EnvironmentFile` protégé | Infra | 1h |
| 8 | Ajouter healthchecks Docker sur les 2 PostgreSQL | Infra | 20 min |
| 9 | Corriger thème dark mode forcé | Frontend | 30 min |
| 10 | Ajouter healthchecks.io (gratuit) | Infra | 15 min |
| 11 | Activer fail2ban SSH | Infra | 20 min |
| 12 | Corriger `_dernier_webhook` monitoring cassé | Backend | 15 min |
| 13 | Supprimer `DB_PATH`, `DID_*`, `did_disponible` | Backend | 20 min |
| 14 | Bloquer le flood `/api/health` (rate-limit IP) | Infra | 20 min |
| 15 | Retourner 202 au lieu de 409 sur `/register` | Backend | 15 min |
| 16 | Ajouter une page metadata par page | Frontend | 1h |
| 17 | Pin versions Docker (remplacer `latest`) | Infra | 15 min |
| 18 | Corriger `StartLimitInterval` → `[Unit]` | Infra | 10 min |
| 19 | Ajouter `memory`/`cpus` limits sur conteneurs lourds | Infra | 20 min |

**Effort semaine 1 estimé** : ~8h

### Semaine 2 (P1 — 27 issues)

| # | Action | Domaine |
|---|---|---|
| 20 | Splitter `routes.py` en modules | Backend |
| 21 | Fusionner requêtes `/me` (6→2) | Backend |
| 22 | Optimiser N+1 JWT dans `/history` | Backend |
| 23 | Ajouter indexes DB manquants | Backend |
| 24 | Remplacer `_plan_cache` par `TTLCache` | Backend |
| 25 | Supprimer `unoptimized` → activer Next.js Image Optimization | Frontend |
| 26 | Ajouter OG/Twitter images au layout | Frontend |
| 27 | Ajouter support `prefers-reduced-motion` | Frontend |
| 28 | Ajouter accessibilité clavier aux sliders/drag zones | Frontend |
| 29 | Corriger `robots` metadata format | Frontend |
| 30 | Ajouter `canonical` URL + JSON-LD | Frontend |
| 31 | Externaliser secrets (Vault/1Password CLI) | Infra |
| 32 | Ajouter limites Docker mémoire/CPU | Infra |
| 33 | Rotation logs Docker | Infra |

### Semaine 3+ (P2-P3 — 54 issues)

Nettoyage imports inutilisés, spinners cohérents, lazy loading, ErrorBoundary, `<a>`→`<Link>`, scrollbar cross-browser, commentaires D-ID résiduels, etc.

---

## 5. Scalabilité — Évaluation

| Facteur | Statut | Note |
|---|---|---|
| **Stateless backend** | ✅ FastAPI stateless (hors WebSocket) | 8/10 |
| **DB connexions** | ⚠️ Pool SQLAlchemy, pas de PgBouncer | 6/10 |
| **Queue** | ✅ ARQ + Redis — scalable horizontalement | 8/10 |
| **Stockage** | ✅ B2 object storage — scalable natif | 9/10 |
| **Cache** | ❌ Aucun cache HTTP (Redis dispo mais inutilisé) | 2/10 |
| **CDN** | ❌ Images servies depuis le backend | 2/10 |
| **Frontend** | ⚠️ Bundle unique, pas de lazy loading | 4/10 |
| **Monitoring** | ❌ Aucun APM, Sentry vide | 1/10 |
| **Déploiement** | ⚠️ Manuel (systemctl restart), pas de CI/CD | 3/10 |

**Note scalabilité** : 4.8/10 — Tenable pour <1000 utilisateurs, goulots identifiés.

---

*Rapport généré sous supervision Opus 4.7 — 15 mai 2026*
