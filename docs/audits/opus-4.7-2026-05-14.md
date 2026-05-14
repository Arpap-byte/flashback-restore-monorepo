# Rapport d'audit — Flashback Restore
**Date :** 14 Mai 2026
**Auditeur :** Claude Opus 4.7
**Version stack :** PostgreSQL 16 + FastAPI + Next.js 15 + Clerk
**Périmètre :** Codebase complet (backend + landing + infra)

---

## Résumé exécutif

Flashback Restore présente une architecture saine post-migration PostgreSQL, avec une bonne séparation backend/frontend, une couverture de tests honnête (45/49) et une infrastructure cohérente (systemd, Traefik, B2, ARQ). Cependant, l'audit révèle **plusieurs problèmes critiques** : (1) le rate limiter est un middleware en mémoire non distribué — KO en multi-worker uvicorn ; (2) le système d'auth supporte simultanément Clerk + JWT interne + NextAuth, ce qui crée une surface d'attaque large et de la dette ; (3) `session.py` contient encore du code mort SQLite (WAL checkpoint) ; (4) plusieurs routes utilisent `_sa_text` brut au lieu de l'ORM (risque d'injection si paramètres mal passés ailleurs) ; (5) la cohérence frontend↔backend est globalement bonne mais le footer pointe vers `/upload` au lieu de `/restore` (lien cassé). La sécurité Clerk est correctement implémentée (JWKS + cache), Stripe est idempotent, et la consommation de crédits est atomique. **Priorité immédiate** : corriger le rate limiter, supprimer le code mort SQLite, et fixer les liens de navigation cassés.

**Note globale :** 7.3/10 — Production viable mais avec corrections P0/P1 à appliquer sous 7 jours.

---

## 1. Architecture

### Forces
- ✅ Séparation claire : `backend/` (FastAPI), `landing/` (Next.js), `infra/` (systemd, Traefik, backups)
- ✅ ORM SQLAlchemy 2.0 async + Pydantic v2 — stack moderne et typée
- ✅ Worker ARQ découplé pour les tâches longues (restauration, animation) — bonne pratique
- ✅ Stockage objet B2 (S3-compatible) pour scaler horizontalement
- ✅ Cache JWKS Clerk via `lru_cache` + `lifespan=3600` — propre
- ✅ Reverse proxy Traefik avec Let's Encrypt automatique
- ✅ Migration PostgreSQL terminée avec backups automatisés vers B2

### Problèmes
- 🔴 **`backend/app/db/session.py`** : contient encore tout le bloc legacy SQLite (`PRAGMA journal_mode`, `WAL checkpoint`, `integrity_check`) alors que SQLite est officiellement abandonné. Code mort confus.
- 🟠 **Double système d'authentification** : `auth.py` accepte Clerk + JWT interne + NextAuth. Mais `api/auth.py` expose toujours `/api/auth/register`, `/api/auth/login`, `/api/auth/forgot-password` (legacy). Frontend utilise Clerk exclusivement → ces routes sont des **vecteurs d'attaque inutiles**.
- 🟠 **`backend/src/auth.ts` (NextAuth)** existe encore alors que `ClerkProvider` est utilisé dans `layout.tsx`. Code mort frontend.
- 🟠 **Pas de migrations Alembic** : `init_db()` fait `Base.metadata.create_all`. Toute modification de schéma en prod nécessitera des SQL manuels.
- 🟡 **`config.py`** mélange validation au moment de l'import (raise au boot) et avertissements (`warnings.warn`). Comportement incohérent.
- 🟡 Le `DATABASE_URL` par défaut dans `config.py` est `postgresql+asyncpg://flashback:flashback@localhost:5432/flashback` — credentials par défaut dangereux si quelqu'un démarre sans `.env`.

### Recommandations
1. **Supprimer le bloc SQLite** dans `session.py` (tests utilisent leur propre engine via `conftest.py`)
2. **Introduire Alembic** : `alembic init`, `alembic revision --autogenerate` après chaque modification de modèle
3. **Désactiver les routes legacy** `/api/auth/register`, `/login`, `/forgot-password`, `/reset-password` ou les protéger par un feature flag
4. **Supprimer `landing/src/auth.ts`** et la route `/api/auth/[...nextauth]/route.ts` si NextAuth n'est plus utilisé
5. Retirer le default `DATABASE_URL` et lever une `RuntimeError` si absent

---

## 2. Sécurité

### Forces
- ✅ Clerk JWT vérifié via JWKS RS256 avec validation issuer (`clerk_auth.py`)
- ✅ Audit logs avec masquage email RGPD (`services/audit.py`)
- ✅ Stripe webhook idempotent (table `stripe_events`)
- ✅ Bcrypt pour les mots de passe (legacy)
- ✅ Extraction IP propre derrière proxy (X-Forwarded-For)
- ✅ Sentry intégré pour observabilité
- ✅ `STRIPE_WEBHOOK_SECRET` placeholder bloque le boot — bonne pratique

### Problèmes

#### 🔴 P0 — Rate limiter non distribué
**Fichier :** `backend/app/rate_limit_middleware.py`
Le rate limiter est un dict Python en mémoire (`_requests`). Si vous lancez uvicorn avec `--workers 4`, chaque worker a son propre compteur → la limite réelle = limite × 4. En cas de scaling horizontal, c'est totalement contourné.

#### 🔴 P0 — Surface d'attaque auth dédoublée
**Fichier :** `backend/app/api/auth.py`
Les routes `/api/auth/login`, `/register`, `/forgot-password`, `/reset-password` sont exposées alors que le frontend utilise uniquement Clerk. Un attaquant peut bruteforcer/spammer ces endpoints. Le rate limit local + middleware non distribué n'offre pas de protection sérieuse.

#### 🟠 P1 — CSP absente
Aucune Content-Security-Policy n'est définie dans `main.py` ni dans `next.config`. Risque XSS amplifié.

#### 🟠 P1 — CORS trop permissif (à vérifier)
`ALLOWED_ORIGINS` chargé depuis env mais non visible dans le snippet — vérifier qu'il n'est pas `["*"]` en prod.

#### 🟠 P1 — Endpoint admin protégé par header simple
**Fichier :** `backend/app/api/routes.py` — `GET /api/stats`
`X-Admin-Key` comparé probablement sans `secrets.compare_digest` → vulnérable au timing attack.

#### 🟠 P1 — Token JWT dans l'URL pour les uploads
**Fichier :** `landing/src/lib/api.ts` — `getPhotoUrlAsync`
Les tokens JWT sont passés en query string `?token=...`. Ils apparaissent dans les logs Traefik, l'historique navigateur, et le Referer. **Critique** : un token JWT Clerk volé donne accès complet au compte.

#### 🟠 P1 — `AUTH_SECRET` accepté dans la liste des secrets JWT
**Fichier :** `backend/app/auth.py`
`_SECRETS = [SECRET_KEY, AUTH_SECRET]` : si `AUTH_SECRET` (utilisé par NextAuth côté front) fuite, on peut forger des tokens internes.

#### 🟡 P2 — Pas de protection CSRF sur les routes mutation
Stripe checkout, suppression d'historique, mise à jour préférences — pas de double-token CSRF.

#### 🟡 P2 — `magic` (libmagic) utilisé pour validation MIME mais pas vu de limite stricte de taille
À vérifier dans `/api/analyze`, `/api/restore`, `/api/animate` (truncated dans `routes.py`).

#### 🟡 P2 — `forgot-password` génère des tokens via `secrets.token_urlsafe` (OK) mais pas vu de rate limit applicatif distinct → le DoS sur l'envoi d'emails est possible.

### Recommandations
1. **Migrer le rate limiter sur Redis** (atomique via `INCR` + `EXPIRE`) — fichier `rate_limit_middleware.py`
2. **Supprimer ou désactiver `api/auth.py`** legacy si Clerk est seule source de vérité
3. **Ajouter CSP** via middleware Starlette + meta tag Next.js
4. **`secrets.compare_digest`** pour la comparaison `X-Admin-Key`
5. **Servir les uploads protégés via cookie httpOnly** ou via URLs présignées B2 (déjà possible avec boto3)
6. **Audit Sentry de toutes les routes** sensibles + alerte sur 5xx > 1%
7. Ajouter validation explicite de la taille fichier dans toutes les routes upload

### Vérification middlewares et guards
- ✅ `exiger_utilisateur` est bien appliqué partout où nécessaire (auth.py, routes.py, user.py)
- ✅ `_trouver_ou_creer_utilisateur` gère bien la création JIT d'utilisateurs Clerk
- ⚠️ Pas de middleware global qui force HTTPS (compté sur Traefik — OK)
- ⚠️ Pas de middleware qui force `Strict-Transport-Security` à reconfirmer

---

## 3. UX / Frontend

### Cohérence backend ↔ frontend

| Élément frontend | Endpoint backend | Statut |
|---|---|---|
| `/restore` — bouton restaurer | `POST /api/restore` | ✅ |
| `/restore` — bouton coloriser | `POST /api/restore` avec param ou `/colorize` (truncated) | ⚠️ À vérifier dans routes.py |
| `/animate` — comportements | `COMPORTEMENT_VERS_EXPRESSION` (did_service.py) ET `PROMPTS_PAR_COMPORTEMENT` (veo_service.py) | ✅ Cohérents (naturel, sourire, rire, respirer, clin_oeil, salut) |
| `/animate` — résolutions 720p/1080p | `TARIF_ANIMATION` (720p, 1080p) | ✅ |
| `/restore` — résolutions 720p/1080p/4K | `TARIF_RESTAURATION` | ✅ |
| `/dashboard` | `GET /api/user/me`, `/api/user/history` | ✅ |
| `/historique` — préférences rétention | `PUT /api/user/preferences` (7/30/90) | ✅ Cohérent avec `CheckConstraint` DB |
| `/admin` | `GET /api/stats` + endpoints utilisateurs détaillés | ⚠️ `routes.py` truncated — vérifier que tous les endpoints admin (`/api/admin/users`, `/api/admin/travaux`) existent réellement |
| `Pricing` — plans | `STRIPE_PRICE_*` | ✅ |
| `Pricing` — plan "pro" affiché ? | Backend connaît "pro" (illimité) | ⚠️ Pas de Stripe price ID pour "pro" |

### Problèmes

#### 🔴 P0 — Liens cassés dans le footer
**Fichier :** `landing/src/components/Footer.tsx`
- `"Restaurer une photo"` → `/upload` ❌ (la route est `/restore`)
- `"Restaurer"` (section Entreprise) → `/upload` ❌
- Plusieurs liens "Mentions légales" → `/terms` (devrait être une page distincte)

#### 🟠 P1 — Plan "pro" affiché mais pas commercialisable
Le backend gère `CREDITS_PAR_PLAN["pro"] = -1` et `MODELE_RESTAURATION_PAR_PLAN["pro"] = "imagen-4-batch"`, mais aucun `STRIPE_PRICE_PRO` n'existe. → soit supprimer "pro" partout, soit ajouter le price ID.

#### 🟠 P1 — Console admin : sécurité de l'`ADMIN_API_KEY`
**Fichier :** `landing/src/app/admin/page.tsx`
La clé est stockée en `localStorage` (`STORAGE_KEY = "flashback_admin_key"`). Une XSS = compromission totale de l'admin. Solutions : (a) protéger l'admin par Clerk avec un rôle, (b) déplacer la clé en cookie httpOnly + endpoint de login admin.

#### 🟠 P1 — Toast/feedback manquant après actions critiques
- Suppression d'un travail → pas vu de toast de confirmation explicite
- Achat de crédits → redirige vers Stripe mais aucun retour visuel si l'utilisateur revient
- Erreurs API → certaines pages affichent `error` mais sans format unifié

#### 🟠 P1 — Page `/auth` redirige toujours vers `/sign-in` ou `/sign-up`
C'est OK mais aucun fallback si Clerk est down → l'utilisateur reste bloqué sur "Redirection vers l'authentification..." indéfiniment.

#### 🟠 P1 — `/animate` : `getPhotoUrlAsync` peut échouer silencieusement
Si le token est expiré, le `<video>` peut afficher un placeholder cassé sans message clair pour l'utilisateur.

#### 🟡 P2 — Polling animation : intervalles longs
**Fichier :** `landing/src/app/animate/page.tsx`
`POLL_DELAYS = [5000, 8000, 12000, 20000, 30000]` — premier feedback à 5s, c'est long sans loader animé. La progress bar n'est pas synchronisée avec un `progress` réel (Veo ne le fournit pas).

#### 🟡 P2 — Sessions cross-comptes
**Fichier :** `landing/src/context/AuthContext.tsx`
Le nettoyage `sessionStorage` quand `user.id` change est bien fait, mais si l'utilisateur change de compte rapidement, il peut voir brièvement la photo de l'ancien utilisateur (race condition).

#### 🟡 P2 — Pages d'erreur génériques
`error.tsx` et `not-found.tsx` sont jolis mais aucun lien vers le support ou un email de contact.

#### 🟢 P3 — Apostrophe HTML mal encodée
Plusieurs `&apos;` dans `FAQ.tsx` rendus comme texte brut dans les `answer` strings → `&apos;` apparaîtra littéralement à l'utilisateur. Voir ligne `"l&apos;application"`, `"l&apos;IA"`.

### Navigation : tous les liens fonctionnent-ils ?
- ✅ `/`, `/restore`, `/animate`, `/dashboard`, `/historique`, `/admin`
- ✅ `/about`, `/privacy`, `/terms`, `/cookies`, `/business`
- ✅ `/abonnement/succes`, `/abonnement/annulation`
- ✅ `/sign-in`, `/sign-up`, `/auth`, `/auth/forgot-password`, `/auth/reset-password`
- ❌ `/upload` (référencé dans Footer mais inexistant)
- ⚠️ `/dashboard` redirige bien les non-authentifiés ? (truncated)

### Logs et monitoring
- ✅ Sentry configuré (avec sample 10%)
- ✅ Audit logs en DB (`audit_logs` table)
- ⚠️ Pas de log structuré JSON pour parsing facile en prod (Loki/ELK)
- ⚠️ `logger.info` partout mais pas de `correlation_id` pour tracer une requête de bout en bout
- ❌ Pas de métriques Prometheus exposées (`/metrics`)
- ❌ Pas d'alerting défini (Sentry envoie des erreurs mais pas de SLO)

### Parcours utilisateur complet
1. Inscription via Clerk Google → ✅
2. Première visite `/restore` → ✅ (essais gratuits affichés)
3. Upload photo → token JWT dans URL ⚠️
4. Restauration → polling job ARQ → ✅
5. Téléchargement résultat → ✅
6. Achat crédits Stripe → ✅ webhook idempotent
7. Animation → polling Veo → ⚠️ délai long sans feedback
8. Suppression historique → ⚠️ pas de confirmation visuelle forte

---

## 4. Qualité du code

### Problèmes

#### Duplication / Dead code
- 🔴 `backend/app/db/session.py` — 50+ lignes de code SQLite mort (WAL checkpoint, integrity check)
- 🟠 `backend/app/services/did_service.py` — D-ID est abandonné au profit de Veo, mais le service reste actif
- 🟠 `landing/src/auth.ts` + `/api/auth/[...nextauth]/route.ts` — NextAuth mort
- 🟠 `backend/app/api/auth.py` — endpoints legacy login/register/forgot/reset

#### Imports inutilisés / TODO
- 🟡 `routes.py` importe `creer_session_paiement_credits` mais le truncated empêche de voir l'usage
- 🟡 Plusieurs `from PIL import Image; Image.MAX_IMAGE_PIXELS = 50_000_000` — pratique fragile (mutation globale au load module)
- 🟡 `backend/app/limiter.py` est un no-op (commenté comme tel) — code pollutif, devrait être supprimé

#### Gestion d'erreurs
- 🟠 `gemini_service.py::_parser_json_gemini` : fallback regex hyper-complexe avec triple-tentative → fragile, devrait utiliser `json.JSONDecoder` ou un schéma strict
- 🟠 `mail.py::envoyer_email` retourne `False` silencieusement → l'appelant ne sait pas si l'utilisateur a reçu son lien de reset
- 🟠 `storage.py::uploader_fichier` raise `ClientError` mais aucun retry custom sur 5xx B2 (boto3 retries gère les 5xx mais pas les network timeouts custom)
- 🟡 `worker.py::restauration_job` truncated mais doit avoir un try/except global avec mise à jour `statut="erreur"` + rollback crédits — à vérifier

#### Typage
- ✅ Pydantic v2 généreusement utilisé
- ✅ TypeScript strict probable côté frontend
- 🟡 `_row_to_dict` retourne `Optional[dict]` mais perd toute info de type — préférer retourner les modèles ORM tels quels
- 🟡 `decoder_token` retourne `dict` (any) → devrait être typé `ClerkPayload | InternalPayload`

#### Tests
- ✅ 45/49 tests passent
- ✅ Tests d'idempotence Stripe (`test_stripe.py`) très bien faits
- ✅ Tests de concurrence crédits (`test_credits.py`) avec lock SQLite no-op
- 🟠 **4 tests Clerk/Stripe échouent** (mentionnés) — pas de précision sur lesquels → bloqueur pour CI
- 🟠 Tests d'intégration HTTP avec auth réelle absents (Clerk mocké uniquement)
- 🟠 Aucun test E2E (Playwright/Cypress) — pourtant le frontend est complexe
- 🟡 `test_tarification.py` ne teste pas les rejets de résolutions invalides en HTTP (skippés)

### Recommandations
1. Supprimer `did_service.py` si Veo est exclusif
2. Supprimer `limiter.py` (no-op) et appeler directement `check_rate_limit` du middleware
3. Activer mypy strict sur backend
4. Ajouter Playwright pour parcours critique : signup → upload → restauration → download
5. Investiguer et fixer les 4 tests échoués

---

## 5. Performance backend

### Problèmes

#### 🟠 P1 — Requêtes N+1 potentielles
- `services/cleanup.py` : la jointure `Travail + Utilisateur.retention_jours` est OK mais le `await session.delete(travail)` dans une boucle déclenche un SELECT + DELETE par ligne. Utiliser un `DELETE` bulk avec `WHERE id IN (...)`.
- `api/user.py::me` exécute 2 sous-requêtes `text("SELECT COUNT(*) FROM travaux ...")` séquentiellement → grouper avec `GROUP BY type` en une seule requête.

#### 🟠 P1 — Indexes manquants probables
**Fichier :** `models/db_models.py`
- `Travail.statut` — utilisé dans `WHERE statut IN ('termine','erreur')` (cleanup) → pas d'index
- `Travail.cree_le` — utilisé dans `WHERE cree_le >= debut_mois` (user.me) → pas d'index
- `Travail.utilisateur_id` — ✅ indexé
- `StripeEvent.event_id` — devrait être PK ou unique index pour idempotence rapide
- `AuditLog.evenement` + `AuditLog.cree_le` — utilisés dans dashboard admin → composite index manquant

#### 🟠 P1 — Pas de timeout HTTPX uniforme
- `did_service.py` : `timeout=30.0`
- `veo_service.py` : truncated mais à vérifier
- `storage.py` : connect=10, read=30 ✅
- `gemini_service.py` : pas vu de timeout explicite

#### 🟡 P2 — `pool_size=10, max_overflow=20`
**Fichier :** `db/session.py`
Pour un VPS avec 2-4 workers uvicorn, c'est correct, mais à monitorer avec PostgreSQL `max_connections`.

#### 🟡 P2 — Pas de cache Redis pour les lectures fréquentes
`obtenir_utilisateur_par_id`, `obtenir_plan_utilisateur` sont appelés à chaque requête authentifiée → idéal pour un cache court (30s).

### Recommandations
1. Ajouter les indexes manquants via Alembic
2. Cache Redis 30s pour `utilisateur` (invalider au changement de plan/crédits)
3. Timeouts httpx uniformes via `httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))`
4. Refactor cleanup en bulk DELETE

---

## 6. Modèle de données

### Forces
- ✅ UUIDs en clé primaire (sécurité, scaling)
- ✅ Foreign keys explicites
- ✅ CheckConstraint sur `retention_jours IN (7, 30, 90)`
- ✅ Timestamps timezone-aware (`DateTime(timezone=True)`)
- ✅ Index sur `utilisateur_id` (travaux), `oauth_provider`, `email` (unique)

### Problèmes

#### 🟠 P1 — Colonnes `nullable=True` à corriger
- `Travail.utilisateur_id` est nullable → pourquoi ? Tout travail doit appartenir à un utilisateur (sinon orphelin).
- `Utilisateur.plan` est nullable avec default `"gratuit"` → mettre `nullable=False, server_default="gratuit"`
- `Utilisateur.password_hash` est `nullable=False` mais les utilisateurs Clerk n'ont pas de password → soit nullable, soit mettre un sentinel `"clerk_oauth"`

#### 🟠 P1 — `est_abonne` est un `Integer` (0/1 flag)
Devrait être `Boolean`. Source de bugs.

#### 🟠 P1 — Données orphelines possibles
- Si un `Utilisateur` est supprimé, les `Travail` restent (pas de `ON DELETE CASCADE` vu dans le snippet) → comportement à valider
- `AuditLog.utilisateur_id` peut référencer un utilisateur supprimé → OK si FK = `SET NULL`, KO sinon
- `ConsommationCredits` doit garder l'historique même après suppression utilisateur (compliance) → vérifier

#### 🟠 P1 — Pas de contrainte d'unicité sur `StripeEvent.event_id`
Si pas unique, deux webhooks identiques peuvent être insérés simultanément → race condition.

#### 🟡 P2 — `Travail.type` est un `String` libre
Devrait être un `Enum` PostgreSQL (`restauration`, `animation`, `analyse`, `colorisation`). Risque de typo silencieuse.

#### 🟡 P2 — `Utilisateur.mois_animation_courant` est `String` (format YYYY-MM)
Devrait être une colonne `Date` ou un `(year, month)` calculé.

### Recommandations
1. Migration Alembic :
   - `ALTER TABLE travaux ALTER COLUMN utilisateur_id SET NOT NULL`
   - `est_abonne` → Boolean
   - FK cascade : `ON DELETE CASCADE` pour `travaux`, `ON DELETE SET NULL` pour `audit_logs`
   - Unique constraint sur `stripe_events.event_id`
2. Enum PostgreSQL pour `Travail.type` et `Travail.statut`

---

## 7. Plan d'action priorisé

| ID | Problème | Priorité | Fichier(s) | Effort | Impact |
|----|----------|----------|-----------|--------|--------|
| 1 | Rate limiter en mémoire — KO multi-worker | 🔴 P0 | `rate_limit_middleware.py` | 2h | Sécurité critique |
| 2 | Liens footer cassés (`/upload`) | 🔴 P0 | `Footer.tsx` | 5min | UX cassée publique |
| 3 | Code mort SQLite dans session.py | 🔴 P0 | `db/session.py` | 15min | Confusion + maintien dur |
| 4 | Endpoints auth legacy exposés inutilement | 🔴 P0 | `api/auth.py`, `main.py` | 30min | Surface d'attaque |
| 5 | Token JWT en query string `?token=` | 🟠 P1 | `lib/api.ts`, `storage.py` | 4h | Fuite token via logs |
| 6 | Admin key en localStorage | 🟠 P1 | `admin/page.tsx` | 3h | Compromission admin via XSS |
| 7 | Pas d'index sur `Travail.statut`, `cree_le` | 🟠 P1 | `db_models.py` + Alembic | 1h | Perf cleanup + dashboard |
| 8 | Plan "pro" affiché sans Stripe price | 🟠 P1 | `Pricing.tsx`, queries.py | 1h | Cohérence offre |
| 9 | `utilisateur_id` nullable sur Travail | 🟠 P1 | `db_models.py` | 1h | Intégrité données |
| 10 | NextAuth code mort | 🟠 P1 | `auth.ts`, route.ts | 30min | Dette technique |
| 11 | D-ID code mort si Veo exclusif | 🟠 P1 | `did_service.py` | 30min | Dette technique |
| 12 | CSP absente | 🟠 P1 | `main.py` middleware | 2h | XSS hardening |
| 13 | `secrets.compare_digest` pour `X-Admin-Key` | 🟠 P1 | `routes.py` | 10min | Timing attack |
| 14 | Pas de migrations Alembic | 🟠 P1 | Nouveau dossier `alembic/` | 4h | Risque corruption schéma |
| 15 | `est_abonne` Integer au lieu de Boolean | 🟡 P2 | `db_models.py` + migration | 1h | Lisibilité |
| 16 | Cache Redis utilisateur | 🟡 P2 | nouvelle classe service | 3h | Perf |
| 17 | Bulk DELETE dans cleanup | 🟡 P2 | `services/cleanup.py` | 1h | Perf |
| 18 | Tests E2E Playwright | 🟡 P2 | nouveau dossier | 8h | Régression |
| 19 | Apostrophes `&apos;` dans FAQ | 🟢 P3 | `FAQ.tsx` | 10min | Cosmétique |
| 20 | Métriques Prometheus | 🟢 P3 | `main.py` | 2h | Observabilité |

---

## 8. Quick wins (< 30 min chacun)

### Quick Win 1 — Fixer les liens footer cassés
**Fichier :** `landing/src/components/Footer.tsx`

```diff
- { label: "Restaurer une photo", href: "/upload" },
+ { label: "Restaurer une photo", href: "/restore" },
```

```diff
Entreprise: [
    { label: "À propos", href: "/about" },
-   { label: "Restaurer", href: "/upload" },
+   { label: "Restaurer", href: "/restore" },
    { label: "Animer", href: "/animate" },
```

---

### Quick Win 2 — Supprimer le code mort SQLite dans session.py
**Fichier :** `backend/app/db/session.py`

```diff
 async def init_db() -> None:
     """Crée les tables si elles n'existent pas."""
     from app.models.db_models import Base
-
-    # Vérification WAL au démarrage — uniquement pour SQLite
-    if "sqlite" in DATABASE_URL:
-        db_path = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "flashback.db"))
-        try:
-            import sqlite3
-            conn = sqlite3.connect(db_path)
-            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
-            if journal_mode.lower() != "wal":
-                logger.warning(f"journal_mode={journal_mode}, passage en WAL...")
-                conn.execute("PRAGMA journal_mode=WAL")
-            wal_info = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
-            if wal_info:
-                logger.info(f"WAL checkpoint démarrage : {wal_info}")
-            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
-            if integrity != "ok":
-                logger.error(f"INTÉGRITÉ DB ÉCHEC : {integrity}")
-            else:
-                logger.info("DB integrity_check OK au démarrage")
-            conn.close()
-        except Exception as e:
-            logger.warning(f"Vérification WAL démarrage échouée (non-bloquant) : {e}")
-    else:
-        logger.info("PostgreSQL détecté — skip vérification WAL.")
-
+    logger.info("Initialisation des tables PostgreSQL...")
     async with _engine.begin() as conn:
         await conn.run_sync(Base.metadata.create_all)


 async def close_db() -> None:
-    """Ferme proprement le moteur de base de données.
-
-    Force un WAL checkpoint (TRUNCATE) avant de fermer si SQLite,
-    pour garantir qu'aucune donnée n'est perdue en cas de crash ultérieur.
-    """
-    if "sqlite" in DATABASE_URL:
-        db_path = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "flashback.db"))
-        try:
-            import sqlite3
-            conn = sqlite3.connect(db_path)
-            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
-            conn.close()
-            logger.info("WAL checkpoint forcé (TRUNCATE) avant fermeture DB.")
-        except Exception as e:
-            logger.warning(f"WAL checkpoint échoué (non-bloquant) : {e}")
-
+    """Ferme proprement le moteur de base de données."""
     await _engine.dispose()
```

---

### Quick Win 3 — `secrets.compare_digest` pour la clé admin
**Fichier :** `backend/app/api/routes.py` (header check à localiser)

Recherche : `if x_admin_key != ADMIN_API_KEY` ou similaire.

```diff
- if x_admin_key != ADMIN_API_KEY:
+ import secrets
+ if not ADMIN_API_KEY or not secrets.compare_digest(x_admin_key or "", ADMIN_API_KEY):
     raise HTTPException(status_code=403, detail="Accès refusé.")
```

---

### Quick Win 4 — Supprimer le `DATABASE_URL` par défaut dangereux
**Fichier :** `backend/app/config.py`

```diff
-DATABASE_URL: str = os.getenv(
-    "DATABASE_URL",
-    "postgresql+asyncpg://flashback:flashback@localhost:5432/flashback",
-)
+DATABASE_URL: str = os.getenv("DATABASE_URL", "")
+if not DATABASE_URL:
+    raise RuntimeError("DATABASE_URL must be set in environment or .env file")
```

---

### Quick Win 5 — Supprimer `limiter.py` no-op et son import
**Fichier :** `backend/app/limiter.py` → DELETE

**Fichier :** `backend/app/api/routes.py` et `auth.py`
```diff
- from app.limiter import limiter
```
Et retirer tous les `@limiter.limit(...)` (no-op de toute façon).

---

### Quick Win 6 — Fixer les `&apos;` HTML mal échappés dans FAQ
**Fichier :** `landing/src/components/FAQ.tsx`

```diff
-    answer:
-      "Notre IA de restauration analyse votre photo pour détecter automatiquement les défauts : rayures, taches, déchirures, décoloration. Elle reconstruit ensuite les zones endommagées en s&apos;appuyant sur le contexte de l&apos;image. Le processus prend moins de 10 secondes.",
+    answer:
+      "Notre IA de restauration analyse votre photo pour détecter automatiquement les défauts : rayures, taches, déchirures, décoloration. Elle reconstruit ensuite les zones endommagées en s'appuyant sur le contexte de l'image. Le processus prend moins de 10 secondes.",
```

Appliquer à toutes les occurrences de `&apos;` dans les `answer` strings (JSX text content rend littéralement les entités HTML quand elles sont dans une chaîne JS, pas dans du JSX direct).

---

### Quick Win 7 — Désactiver les routes auth legacy (si Clerk exclusif)
**Fichier :** `backend/app/main.py`

```diff
- from app.api.auth import router as auth_router
- ...
- app.include_router(auth_router)
+ # Routes auth legacy désactivées — Clerk est la seule source d'authentification
+ # from app.api.auth import router as auth_router
+ # app.include_router(auth_router)
```

Ou commenter individuellement les endpoints `/login`, `/register`, `/forgot-password`, `/reset-password` et garder uniquement `/me`.

---

### Quick Win 8 — Ajouter `ondelete="CASCADE"` aux FK travaux
**Fichier :** `backend/app/models/db_models.py`

```diff
-    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=True, index=True)
+    utilisateur_id = Column(String, ForeignKey("utilisateurs.id", ondelete="CASCADE"), nullable=False, index=True)
```

⚠️ Nécessite une migration Alembic + nettoyer d'éventuels travaux orphelins avant.

---

### Quick Win 9 — Index sur Travail.cree_le et statut
**Fichier :** `backend/app/models/db_models.py`

```diff
 class Travail(Base):
     __tablename__ = "travaux"
     ...
+    __table_args__ = (
+        Index("idx_travaux_statut_cree", "statut", "cree_le"),
+        Index("idx_travaux_user_type_cree", "utilisateur_id", "type", "cree_le"),
+    )
```

---

### Quick Win 10 — Constraint unique sur stripe_events.event_id
**Fichier :** `backend/app/models/db_models.py`

Localiser `class StripeEvent` et ajouter `unique=True` :
```diff
-    event_id = Column(String, nullable=False, index=True)
+    event_id = Column(String, nullable=False, unique=True, index=True)
```

---

**Fin du rapport.**

**Action recommandée :** committer ce rapport dans `docs/audits/opus-4.7-2026-05-14.md`, créer une issue GitHub par item P0/P1, et appliquer les 10 Quick Wins dans la journée. Une revue de sécurité externe (pentest) est conseillée avant de passer le cap des 100 utilisateurs payants.