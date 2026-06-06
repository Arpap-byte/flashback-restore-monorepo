# Audit Sécurité API Flashback Restore

**Date** : 6 juin 2026
**Auditeur** : DeepSeek Pro (analyse directe du codebase)
**Périmètre** : `backend/app/` — auth, CORS, rate limiting, injection SQL, headers sécurité
**Fichiers analysés** : 12 fichiers clés (~3500 lignes)

---

## Résumé exécutif

L'API Flashback Restore présente un **bon niveau de sécurité général** (7.5/10). La vérification JWT est robuste (HS256 interne + RS256 Clerk via JWKS), le rate limiting Redis est correctement distribué, et **aucune vulnérabilité d'injection SQL n'a été trouvée** — toutes les requêtes SQL utilisent des paramètres bindés (`:param`). Les headers de sécurité sont présents (CSP, HSTS, X-Frame-Options). 

Points d'amélioration : le CSP référence encore `*.clerk.accounts.dev` au lieu du domaine primaire `clerk.flashback-restore.com`, l'endpoint `/api/sentry-test` est exposé en production, et plusieurs endpoints API manquent de rate limiting.

---

## 1. JWT — Authentification

### ✅ Forces

| Point | Détail |
|---|---|
| Double algorithme | HS256 (tokens internes) + RS256 (tokens Clerk via JWKS) |
| Vérification Clerk | `clerk_auth.py` — PyJWKClient avec cache LRU 1h, vérifie issuer + audience + expiration |
| Tokens téléchargement | `creer_token_telechargement()` — TTL 30 min, scope `"download"`, HS256 |
| Anti-énumération | Register → 202 même si email existe. Forgot-password → toujours "succès" |
| Rejet placeholders | `@placeholder.local` refusé avec HTTP 400, résolution API Clerk en fallback |
| Multiple secrets | Supporte `SECRET_KEY` + `AUTH_SECRET` (NextAuth) dans `decoder_token()` |

### ⚠️ Problèmes

| # | Priorité | Problème | Fichier |
|---|---|---|---|
| J1 | 🟡 | **TTL token auth = 24h** — long pour un token d'accès. Pas de refresh token. Un token volé donne 24h d'accès. | `auth.py:24` |
| J2 | 🟡 | **Pas de `type` claim** dans `creer_token()` — impossible de distinguer un token auth d'un token download côté vérification. Actuellement non exploitable car les routes utilisent des dépendances différentes, mais fragilité future. | `auth.py:36-46` |
| J3 | 🟢 | **`securite = HTTPBearer(auto_error=False)`** — le paramètre est nommé `securite` (français) ce qui est incohérent avec le reste de l'API. Pas de bug mais confusing pour les contributeurs. | `auth.py:28` |

### 💡 Recommandations

- **J1** : Réduire `DUREE_TOKEN` à 1h et implémenter un refresh token (ou s'appuyer sur Clerk pour le refresh côté frontend, ce qui est déjà le cas)
- **J2** : Ajouter `"type": "access"` dans `creer_token()` et vérifier dans `obtenir_utilisateur_courant()` que le type est bien `"access"` ou absent (rétrocompatibilité)

---

## 2. CORS

### ✅ Forces

- `ALLOWED_ORIGINS` chargé depuis `.env` — configurable sans rebuild
- Fallback dev propre (localhost:3000, localhost:8001, domaines prod)
- Filtre `"localhost" not in origin` en production

### ⚠️ Problèmes

| # | Priorité | Problème | Fichier |
|---|---|---|---|
| C1 | 🟢 | **`allow_methods=["*"]` et `allow_headers=["*"]`** — permissif mais acceptable avec `allow_origins` restreint et `allow_credentials=True`. Pas exploitable en l'état. | `main.py:131-132` |
| C2 | 🟢 | **Fallback hardcodé** — les origines locales et `flashback-restore.com` sont en dur si `ALLOWED_ORIGINS` est vide. Pas grave mais mériterait un warning. | `main.py:116-121` |

---

## 3. Rate Limiting

### ✅ Forces

- **Double couche** : middleware HTTP (`rate_limit_middleware.py`) + décorateur (`limiter.py`)
- **Redis distribué** — survit aux redémarrages, cohérent multi-workers
- **Graceful degradation** — si Redis down, les requêtes passent (log warning)
- **X-Forwarded-For** correctement géré (Traefik)
- **Endpoints critiques protégés** : register (5/min), login (5/min), forgot-password (3/min), restore/animate (10/min), stripe checkout (5/min)

### ⚠️ Problèmes

| # | Priorité | Problème | Fichier |
|---|---|---|---|
| R1 | 🟠 | **Endpoints sans rate limiting** : `/api/user/me`, `/api/user/history`, `/api/library/*`, `/api/job/{job_id}`, `/api/webhooks/clerk`, `/api/stripe/webhook`. Un attaquant peut saturer ces endpoints. | `rate_limit_middleware.py:16-26` |
| R2 | 🟡 | **Webhook Stripe non limité** — acceptable car Stripe a son propre rate limiting, mais une couche supplémentaire ne ferait pas de mal. | N/A |
| R3 | 🟢 | **Pas de rate limit par utilisateur authentifié** — le rate limiting est uniquement par IP. Un utilisateur Premium et un attaquant sur la même IP partagent le même quota. | `rate_limit_middleware.py:67` |

### 💡 Recommandations

- **R1** : Ajouter des limites sur `/api/user/me` (30/min), `/api/user/history` (20/min), `/api/library/*` (20/min), `/api/job/{job_id}` (30/min)
- **R3** : Pour les routes authentifiées, utiliser `f"rate:user:{user_id}:{path}"` en fallback quand l'utilisateur est identifié

---

## 4. Injection SQL

### ✅ Forces — **AUCUNE VULNÉRABILITÉ TROUVÉE**

Toutes les requêtes SQL brutes (`_sa_text()`) utilisent **exclusivement** des paramètres bindés `:param`. Aucune concaténation de chaîne avec des entrées utilisateur.

| Pattern | Fichier | Status |
|---|---|---|
| `_sa_text("SELECT ... WHERE id = :uid"), {"uid": user_id}` | `routes.py`, `user.py`, `main.py` | ✅ Safe |
| ORM SQLAlchemy (`select()`, `update()`) | `queries.py`, `clerk_account.py` | ✅ Safe |
| Conditions dynamiques par binding | `routes.py:676-685` (admin/travaux) | ✅ Safe |
| Filtres audit logs par ORM | `queries.py:1145-1193` | ✅ Safe — utilise `AuditLog.email == email`, pas de raw SQL |

**Vérification exhaustive** : 50 occurrences de `_sa_text` / `text(` / `.execute(` passées en revue — toutes bindées.

---

## 5. Headers de sécurité

### ✅ Forces

| Header | Valeur | Status |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | ✅ |
| `X-Frame-Options` | `DENY` | ✅ |
| `Strict-Transport-Security` | `max-age=63072000` (2 ans) | ✅ |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | ✅ |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | ✅ |
| `Cache-Control` (uploads) | `no-store, private` | ✅ |

### ⚠️ Problèmes

| # | Priorité | Problème | Fichier |
|---|---|---|---|
| H1 | 🔴 | **CSP utilise `*.clerk.accounts.dev`** — le domaine primaire Clerk est `clerk.flashback-restore.com`. Les requêtes vers `*.clerk.accounts.dev` sont bloquées en production. Corriger en `clerk.flashback-restore.com`. | `main.py:146-153` |
| H2 | 🟡 | **`style-src 'unsafe-inline'`** — nécessaire pour certaines UI mais idéalement à remplacer par des nonces ou hashes. | `main.py:149` |
| H3 | 🟡 | **Pas de `X-XSS-Protection`** — obsolète mais certains scanners le flaggent. `0` ou `1; mode=block`. | `main.py:140-155` |

### 💡 Recommandations

- **H1 (CRITIQUE)** : Remplacer `https://*.clerk.accounts.dev` par `https://clerk.flashback-restore.com` dans `connect-src` et `frame-src`

---

## 6. Input Validation

### ✅ Forces

- **Double validation upload** : Content-Type + magic bytes + signature binaire (fallback)
- **Taille max upload** : 20 Mo
- **Anti directory traversal** : `chemin.resolve()` doit commencer par `UPLOAD_DIR.resolve()`
- **Résolution** : whitelist `("720p", "1080p", "4k")` via TARIF_RESTAURATION dict
- **Rétention** : whitelist `(7, 30, 90)` jours
- **Pydantic validation** : `EmailStr`, `min_length=8` sur register/login

---

## 7. Autres vecteurs

### ⚠️ Problèmes

| # | Priorité | Problème | Fichier |
|---|---|---|---|
| A1 | 🔴 | **`/api/sentry-test` exposé en production** — endpoint qui lève une exception volontaire. N'importe qui peut déclencher des erreurs Sentry, polluer les logs, et potentiellement causer un déni de service si Sentry a un rate limit. | `main.py:315-318` |
| A2 | 🟠 | **Error leaking dans `/api/restore`** — `message_erreur=str(e)` stocke l'erreur brute en base, et `detail=f"Erreur lors de l'analyse : {str(e)}"` l'expose dans la réponse HTTP. Si l'erreur vient de Gemini, elle peut contenir la clé API dans l'URL. Le skill documente ce risque mais il persiste dans le code. | `routes.py:870-879` |
| A3 | 🟠 | **`/api/health` exposé en dev** — en mode non-production, retourne tous les détails d'infrastructure. Pas critique car `ENVIRONMENT=production` masque ces détails, mais si `ENVIRONMENT` est mal configuré, fuite d'info. | `routes.py:314-330` |
| A4 | 🟡 | **Pas de vérification `state` OAuth** — les routes OAuth (`google`, `facebook`) dans `api/auth.py` n'ont pas de paramètre `state` pour prévenir le CSRF OAuth. Acceptable si Clerk gère l'OAuth (ce qui est le cas), mais les routes sont toujours exposées. | `api/auth.py` |
| A5 | 🟢 | **`ADMIN_API_KEY` vide** — si non configurée, les endpoints admin sont inaccessibles (bon), mais aucun log/warning au démarrage pour avertir l'opérateur. | `config.py:43` |

### 💡 Recommandations

- **A1 (CRITIQUE)** : Supprimer ou protéger `/api/sentry-test` par `X-Admin-Key` + `ENVIRONMENT != "production"` + supprimer complètement en production
- **A2** : Sanitizer `str(e)` avant de le stocker/exposer. Utiliser `_nettoyer_message_erreur()` comme pour Veo
- **A3** : Logguer un warning si `ENVIRONMENT != "production"` et que le health endpoint est exposé

---

## 8. Webhooks — Sécurité

### ✅ Forces

- **Signature Svix HMAC** sur `POST /api/webhooks/clerk` — vérification du corps brut (bytes)
- **Idempotence** : `ON CONFLICT DO NOTHING` sur création compte
- **Rate limiting** : `@limiter.limit("60/minute")` sur le webhook Clerk
- **Pas d'authentification JWT** sur les webhooks (correct — Clerk n'envoie pas de token)
- **Soft-delete** pour `user.deleted` — anonymisation sans perte de données

---

## 9. Plan d'action priorisé

| # | Priorité | Problème | Fichier(s) | Effort | Impact |
|---|---|---|---|---|---|
| H1 | 🔴 P0 | CSP référence `*.clerk.accounts.dev` au lieu du domaine primaire | `main.py:146-153` | 2 min | 🔴 Bloque les requêtes Clerk en prod |
| A1 | 🔴 P0 | `/api/sentry-test` exposé en production | `main.py:315-318` | 5 min | 🔴 Pollution Sentry, DoS potentiel |
| A2 | 🟠 P1 | Error leaking — clé API Gemini dans messages d'erreur | `routes.py:870-879`, `gemini_service.py` | 20 min | 🟠 Fuite de clé API |
| R1 | 🟠 P1 | Rate limiting manquant sur `/api/user/*`, `/api/library/*`, `/api/job/*` | `rate_limit_middleware.py:16-26` | 15 min | 🟠 Saturation possible |
| J1 | 🟡 P2 | TTL token auth de 24h — trop long | `auth.py:24` | 5 min | 🟡 Fenêtre de vol importante |
| J2 | 🟡 P2 | Pas de `type` claim dans les tokens auth | `auth.py:36-46` | 10 min | 🟡 Confusion future possible |
| H2 | 🟡 P2 | `style-src 'unsafe-inline'` dans CSP | `main.py:149` | 1-2h | 🟡 Faiblesse CSP |
| R3 | 🟢 P3 | Rate limit par IP au lieu de user_id sur routes auth | `rate_limit_middleware.py:67` | 30 min | 🟢 IP partagée = quota partagé |
| C1 | 🟢 P3 | `allow_methods=["*"]` et `allow_headers=["*"]` | `main.py:131-132` | 2 min | 🟢 Acceptable avec origines restreintes |
| A5 | 🟢 P3 | Warning si `ADMIN_API_KEY` non configurée | `config.py:43` | 2 min | 🟢 Qualité de vie ops |

---

## 10. Quick Wins (< 30 min chacun)

### QW1 — Fix CSP Clerk domain (P0 — 2 min)

```diff
# main.py:146-153
- "connect-src 'self' https://*.clerk.accounts.dev https://api.clerk.com; "
+ "connect-src 'self' https://clerk.flashback-restore.com https://api.clerk.com; "
- "frame-src 'self' https://*.clerk.accounts.dev https://js.stripe.com"
+ "frame-src 'self' https://clerk.flashback-restore.com https://js.stripe.com"
```

### QW2 — Désactiver sentry-test en production (P0 — 5 min)

```diff
# main.py:315-318
 @app.get("/api/sentry-test")
 async def sentry_test():
-    """Endpoint de test : déclenche une exception pour vérifier Sentry."""
-    raise Exception("Test Sentry — si SENTRY_DSN est configuré, cette erreur remonte dans Sentry")
+    """Endpoint de test Sentry — développement uniquement."""
+    if ENVIRONMENT == "production":
+        raise HTTPException(status_code=404, detail="Not found")
+    raise Exception("Test Sentry — si SENTRY_DSN est configuré, cette erreur remonte dans Sentry")
```

### QW3 — Ajouter rate limits manquants (P1 — 15 min)

```diff
# rate_limit_middleware.py:16-26
 LIMITS = {
     "/api/auth/register": (5, 60),
     "/api/auth/login": (5, 60),
     "/api/auth/forgot-password": (3, 60),
     "/api/health": (30, 60),
     "/api/analyze": (10, 60),
     "/api/restore": (10, 60),
     "/api/animate": (10, 60),
     "/api/stripe/create-checkout": (5, 60),
     "/api/stripe/create-pack-checkout": (5, 60),
+    "/api/user/me": (30, 60),
+    "/api/user/history": (20, 60),
+    "/api/user/subscription": (20, 60),
+    "/api/job": (30, 60),  # attention: match exact, les job_id sont dans le path
 }
```

Note : `/api/job/{job_id}` nécessite un match par préfixe plutôt que exact. Modifier `check_rate_limit()` pour supporter `startswith`.

### QW4 — Sanitizer les erreurs Gemini (P1 — 20 min)

Créer une fonction `_sanitize_error()` dans `routes.py` :

```python
import re

def _sanitize_error(error: Exception) -> str:
    """Nettoie un message d'erreur pour éviter de fuiter des clés API."""
    msg = str(error)
    # Supprimer les clés API Gemini dans les URLs
    msg = re.sub(r'key=[A-Za-z0-9_-]+', 'key=REDACTED', msg)
    # Tronquer à 200 caractères
    if len(msg) > 200:
        msg = msg[:197] + "..."
    return msg
```

Puis remplacer `message_erreur=str(e)` par `message_erreur=_sanitize_error(e)` dans tous les handlers d'erreur.

---

## 11. Conclusion

**Note globale : 7.5/10**

L'API est **solide sur les fondamentaux** : JWT correct, pas d'injection SQL, rate limiting distribué, headers de sécurité présents. Les 2 problèmes P0 (CSP Clerk et sentry-test exposé) sont des corrections triviales de moins de 10 minutes. Les P1 (rate limits manquants et error leaking) demandent ~35 minutes.

Aucune faille critique permettant une compromission n'a été identifiée. Le principal risque est la fuite de clé API Gemini dans les messages d'erreur (A2), qui est déjà documenté dans le skill Flashback mais pas encore corrigé dans le code.

---

*Audit réalisé par analyse directe du codebase (DeepSeek Pro) — 12 fichiers, ~3500 lignes analysées.*
