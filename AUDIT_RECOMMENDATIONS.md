# Audit Flashback Restore — Rapport de Recommandations
Date: 11/05/2026
Auditeur: Claude Opus 4.7

## Résumé exécutif

Flashback Restore est un SaaS de restauration photo par IA techniquement fonctionnel, avec une architecture monorepo cohérente (FastAPI + Next.js 15) et une UI soignée (Framer Motion, design system bien pensé). Le périmètre métier est clair, les schémas Pydantic sont rigoureux et la couche d'audit/logs de sécurité a été mise en place. Le projet montre une maturité réelle sur les aspects produit.

**Cependant, plusieurs problèmes critiques compromettent la mise en production réelle** : (1) la base de données est **SQLite** alors que `docker-compose.yml` déclare PostgreSQL — incohérence majeure ; (2) une **URL IP en dur** (`http://148.230.116.52:8000`) est codée dans le service d'animation, exposant l'infrastructure et bloquant le HTTPS ; (3) **CORS autorise `localhost`** en production ; (4) absence totale de **migrations versionnées** (Alembic) — schéma géré par `ALTER TABLE` conditionnels ; (5) la **route `/api/auth/oauth` est exposée** mais le frontend n'utilise plus que NextAuth direct (code mort dangereux) ; (6) le **frontend bypass NextAuth via formulaire HTML natif** dans `auth/page.tsx` — pratique non standard et risquée.

Les axes prioritaires : migrer vers PostgreSQL (déjà prévu mais non implémenté), introduire Alembic, durcir CORS et headers de sécurité, externaliser l'URL publique du backend, unifier la stratégie d'auth, et ajouter une couche de tests E2E sur les parcours payants Stripe. Le code est globalement propre mais souffre de **duplication entre `auth.py` et `user.py`** (route `/me` dupliquée), de **prompts Gemini non robustes** au format JSON et d'une **absence de retry/backoff** sur les appels externes (Gemini, D-ID).

---

## 1. Architecture

### 1.1 Structure du projet

**✅ Forces**
- Monorepo clair avec séparation backend / landing (Next.js).
- Backend FastAPI bien découpé : `api/`, `services/`, `db/`, `models/`.
- Routeur intelligent de modèles IA (`services/model_router.py`) anticipant les COGS par plan — excellente initiative pour un SaaS.
- Schémas Pydantic complets et documentés (`models/schemas.py`).

**⚠️ Problèmes**
- **Incohérence SQLite vs PostgreSQL** : `db/database.py` utilise `sqlite3` natif (ligne 1) alors que `docker-compose.yml` déclare un service `db: postgres:16-alpine`. Le backend ne se connectera **jamais** à Postgres en l'état.
- Pas de couche ORM (SQLAlchemy / SQLModel) — tout est en SQL brut, difficile à maintenir et migrer.
- `landing/src/auth.ts` est physiquement hors de `landing/src/app/` mais importé via `@/auth` — convention acceptable mais à documenter.
- Le dossier `services/model_router.py` est défini mais **n'est jamais utilisé** dans `routes.py` (code mort).

**💡 Recommandations**
1. **Migrer vers PostgreSQL via SQLAlchemy + Alembic** (priorité 🔴). Garder SQLite uniquement pour les tests locaux.
2. Supprimer `model_router.py` ou l'intégrer réellement dans `restaurer()` et `animer()`.
3. Ajouter un fichier `ARCHITECTURE.md` documentant les flux et choix techniques.

### 1.2 Séparation des responsabilités

**✅ Forces**
- Services externalisés (`gemini_service.py`, `did_service.py`, `stripe_service.py`).
- Audit logs isolés dans `services/audit.py`.

**⚠️ Problèmes**
- `api/routes.py` (≈700 lignes) est **trop gros** et mélange : santé, stats admin, audit logs, analyse, restauration, animation, Stripe webhooks. Devrait être splitté en `routes_admin.py`, `routes_restore.py`, `routes_stripe.py`, `routes_animate.py`.
- La logique métier (consommation crédits, plan, refund) est **dans la route HTTP** (`routes.py`, lignes 280-340) — devrait être dans `services/credits_service.py`.
- Route `/api/auth/me` définie **deux fois** : `api/auth.py` ligne 191 ET `api/user.py` ligne 36. Risque de drift.

**💡 Recommandations**
1. Splitter `routes.py` en 4-5 modules thématiques.
2. Créer une couche service (`services/credits.py`, `services/restoration.py`) pour extraire la logique de `routes.py`.
3. Supprimer la duplication `/api/auth/me` vs `/api/user/me`.

### 1.3 Gestion de la configuration

**✅ Forces**
- `config.py` centralisé avec `load_dotenv`.
- Échecs explicites si secrets critiques manquants (`GEMINI_API_KEY`, `SECRET_KEY`).

**⚠️ Problèmes**
- **URL absolue codée en dur** dans `api/routes.py` ligne 419 : `f"http://148.230.116.52:8000/uploads/{nom_fichier}"`. Bloque HTTPS, expose IP infra, casse en dev.
- URLs Stripe en dur : `URL_SUCCES_STRIPE = "http://localhost:3000/..."` (lignes 49-50) — utilisées en prod ! Stripe redirigera vers localhost.
- `STRIPE_WEBHOOK_SECRET` a un fallback `"whsec_placeholder"` (config.py ligne 57) : un déploiement sans `.env` accepterait des webhooks non signés.
- Pas de validation Pydantic Settings (`pydantic-settings`) pour le typage strict des variables d'env.

**💡 Recommandations**
1. Ajouter `PUBLIC_BACKEND_URL` dans `.env`, utiliser partout (`f"{PUBLIC_BACKEND_URL}/uploads/{nom_fichier}"`).
2. Remplacer `URL_SUCCES_STRIPE`/`URL_ANNULATION_STRIPE` par `SITE_URL + "/abonnement/succes"`.
3. Supprimer le fallback `whsec_placeholder` : faire planter au boot si manquant.
4. Migrer vers `BaseSettings` de `pydantic-settings`.

### 1.4 Cohérence backend/frontend

**⚠️ Problèmes**
- `landing/src/lib/api.ts` ligne 1 : `API_BASE = ""` côté client → utilise un chemin relatif → suppose un reverse proxy. Mais `next.config.ts` autorise `http://148.230.116.52:8000` pour les images : double source de vérité.
- Le frontend déclare `UserMe` avec `nom`, `credits_utilises`, `photos_restaurees_mois`, `date_renouvellement` — **aucun de ces champs n'est retourné par `/api/user/me`** (cf. `api/user.py`). Le dashboard affichera systématiquement des valeurs nulles.
- `next.config.ts` ne déclare pas `https://` ni le domaine de prod (`flashback-restore.com`) dans `remotePatterns` — les images cassées en prod.

**💡 Recommandations**
1. Aligner le contrat OpenAPI : générer les types TS depuis le backend (`openapi-typescript`).
2. Compléter `/api/user/me` côté backend pour retourner les champs attendus par le frontend (statistiques mensuelles, date de renouvellement Stripe).
3. Corriger `next.config.ts` pour autoriser le domaine HTTPS de production.

---

## 2. Sécurité

### 2.1 Authentification et autorisation

**✅ Forces**
- Bcrypt pour le hash des mots de passe (`api/auth.py` ligne 89).
- JWT signé avec HS256 et expiration 24h.
- Liste de secrets multiples acceptée (`auth.py` ligne 28) pour la transition NextAuth.
- Audit logs sur tous les événements critiques.

**🔴 Problèmes critiques**
- **`landing/src/app/auth/page.tsx` lignes 64-87** : la connexion utilise un **formulaire HTML natif injecté dans le DOM** pour bypasser `signIn()` de NextAuth. Pratique non standard, fragile, et casse la protection CSRF intégrée. À refactorer immédiatement avec `signIn("credentials", { ... })`.
- **Création automatique d'utilisateur via JWT** : `auth.py` ligne 84 (`_trouver_ou_creer_utilisateur`) crée silencieusement un compte si le payload JWT contient un email inconnu. **N'importe quel JWT signé avec `AUTH_SECRET` permet de créer un compte arbitraire** — vecteur d'usurpation si `AUTH_SECRET` est leaked.
- **Route `/api/auth/oauth`** (auth.py ligne 132) accepte un `provider_id` non vérifié auprès du provider OAuth. Protégée par `X-Internal-Key`, mais cette clé sert aussi à d'autres usages. Si elle fuite, un attaquant peut se connecter en tant que n'importe qui.

**⚠️ Problèmes**
- Pas de vérification d'email (pas de double opt-in).
- Pas de mécanisme de rotation/revocation des JWT (pas de blocklist Redis).
- Limite `5/minute` sur `/login` mais aucune protection sur le brute-force distribué (par IP seulement).

**💡 Recommandations**
1. Refactorer `auth/page.tsx` pour utiliser `signIn("credentials", { redirect: false })` puis `router.push()`.
2. **Supprimer la création auto d'utilisateur** dans `_trouver_ou_creer_utilisateur` — exiger un endpoint explicite `/api/auth/sync-oauth`.
3. Ajouter un système de **verrouillage temporaire de compte** après N échecs (clé Redis `lockout:{email}`).
4. Implémenter une **blocklist JWT** dans Redis pour le logout effectif.
5. Ajouter une vérification d'email (envoi de token, table `verifications`).

### 2.2 Gestion des secrets et clés API

**🔴 Problèmes critiques**
- Le fichier `gemini_service.py` (ligne 230-231, 263) tente de coloriser via une **URL absolue avec la clé Gemini en query param** : `params={"key": GEMINI_API_KEY}` — la clé apparaîtra dans les logs HTTP, proxies, et fichiers de debug. Utiliser le SDK `genai.Client` ou un header `x-goog-api-key`.
- `config.py` ligne 57 : `STRIPE_WEBHOOK_SECRET` avec fallback `"whsec_placeholder"` permet à un déploiement mal configuré d'accepter n'importe quel webhook (même si la signature est invalide, le boot ne crashe pas).

**⚠️ Problèmes**
- Aucune indication de gestion des secrets via un vault (Hashicorp Vault, AWS Secrets Manager, Doppler). Les `.env` sur VPS sont un risque.
- Pas de rotation des `SECRET_KEY` / `AUTH_SECRET` documentée.

**💡 Recommandations**
1. Faire échouer le boot si `STRIPE_WEBHOOK_SECRET` manquant en prod.
2. Utiliser le SDK officiel pour la colorisation Gemini.
3. Documenter une procédure de rotation des secrets dans `docs/SECRETS.md`.

### 2.3 Validation des entrées et uploads

**✅ Forces**
- Validation MIME et taille (`routes.py` lignes 33, 209-220).
- Schémas Pydantic stricts sur tous les bodies.

**⚠️ Problèmes**
- **Pas de validation du contenu réel** du fichier (magic bytes). Un attaquant peut envoyer un fichier `.exe` renommé `.jpg` avec `Content-Type: image/jpeg`. Utiliser `python-magic`.
- Le nom de fichier original est inclus dans le nom stocké (`{uuid}_{fichier.filename}`) — risque de **path traversal** si `filename = "../../etc/passwd"`. À sanitiser avec `werkzeug.utils.secure_filename` ou regex stricte.
- Taille max 20 Mo mais lue **en mémoire** (`await fichier.read()`) — DoS facile en envoyant 100 uploads parallèles de 20 Mo.
- Aucune validation du contenu visuel : un attaquant peut uploader des images CSAM, contenu interdit, etc. — pas de modération.

**💡 Recommandations**
1. Sanitiser strictement `fichier.filename` : `re.sub(r'[^a-zA-Z0-9._-]', '_', filename)`.
2. Vérifier les magic bytes avec `python-magic`.
3. Lire en streaming et arrêter dès dépassement de quota.
4. Ajouter une vérification de modération (Google Vision SafeSearch, Sightengine) avant traitement.

### 2.4 Rate limiting

**✅ Forces**
- `slowapi` configuré avec `Limiter` par IP, défaut `60/minute`.
- Limites custom sur `/register` (5/min), `/login` (5/min), `/forgot-password` (3/min).

**⚠️ Problèmes**
- **Aucune limite sur les routes coûteuses** : `/api/restore`, `/api/analyze`, `/api/animate` — pas de `@limiter.limit()`. Un utilisateur authentifié peut spammer 1000 restaurations par minute, ce qui explose la facture Gemini avant même que la consommation de crédits ne bloque (puisque le crédit n'est consommé qu'**après** validation du fichier).
- Limite par IP seulement → derrière Cloudflare/Traefik avec un seul X-Forwarded-For, peut être bypassée. Configurer `Limiter(key_func=...)` pour utiliser l'IP réelle.
- Pas de rate limit sur `/api/stripe/webhook` — un attaquant peut spammer pour saturer.

**💡 Recommandations**
1. Ajouter `@limiter.limit("10/minute")` sur `/restore`, `/animate`, `/analyze`.
2. Configurer la `key_func` pour utiliser `X-Forwarded-For` (premier IP) après vérification du proxy de confiance.
3. Implémenter une limite par utilisateur authentifié (en plus de l'IP).

### 2.5 Vulnérabilités potentielles

**🔴 Critique**
- **CORS** (`main.py` ligne 78) : `allow_origins=["http://localhost:3000", "http://localhost:8001", ...]` en **production** — un attaquant peut héberger un site malveillant sur `localhost:3000` et faire des requêtes authentifiées. **Retirer `localhost` en prod**.
- **`allow_credentials=True` + `allow_methods=["*"]` + `allow_headers=["*"]`** : config trop permissive.
- **Énumération d'utilisateurs** : `POST /api/auth/register` renvoie un 409 explicite "email déjà utilisé" — permet de découvrir qui est inscrit. Renvoyer un message générique ou un 202 systématique.
- **Pas de headers de sécurité** : pas de `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`. À ajouter via middleware.

**⚠️ Problèmes**
- `routes.py` ligne 419 : URL backend en HTTP (148.230...). D-ID télécharge la photo en clair → fuite potentielle.
- Pas de protection CSRF explicite côté API (acceptable si JWT en `Authorization` header uniquement, mais à documenter).

**💡 Recommandations**
1. Retirer `localhost` de `allow_origins` en production via variable d'env.
2. Ajouter `secure_middleware` (Starlette) ou un middleware custom pour les headers.
3. Renvoyer un 202 générique sur `/register`.

---

## 3. UX / Frontend

### 3.1 Parcours utilisateur

**✅ Forces**
- Parcours simple : `/restore` → upload → restaurer → animer.
- Slider avant/après fluide et responsive (drag souris + touch).
- Composant `StripeCheckoutButton` avec validation d'email en place.

**⚠️ Problèmes**
- **Redirection `/upload` → `/restore`** (`next.config.ts`) permanente : casse les liens externes et les anciennes URLs partagées.
- Le parcours d'animation utilise `sessionStorage` (`flashback_photo`) pour passer la photo entre pages — fragile, perdu au refresh, et ne marche pas si l'utilisateur ouvre `/animate` dans un nouvel onglet.
- Pas de feedback clair sur le nombre de crédits restants après restauration (le composant Hero ne se rafraîchit pas).
- Aucune page `/abonnement/succes` ou `/abonnement/annulation` n'existe alors que Stripe redirige vers ces URLs (`routes.py` ligne 48-49) → 404 après paiement.

**💡 Recommandations**
1. Créer les pages `/abonnement/succes` et `/abonnement/annulation` (priorité 🔴 — casse le funnel de paiement).
2. Remplacer `sessionStorage` par un query param ou un identifiant de travail backend.
3. Rafraîchir `useAuth()` après chaque opération consommant un crédit.

### 3.2 Gestion des erreurs et états de chargement

**✅ Forces**
- États de loading explicites partout (`restoring`, `animating`).
- `error.tsx`, `not-found.tsx`, `loading.tsx` au niveau du layout.
- Toast d'erreur dans `/restore` et `/animate`.

**⚠️ Problèmes**
- **Polling D-ID** dans `animate/page.tsx` (5s) sans backoff exponentiel ni timeout maximum → si D-ID est lent ou planté, l'utilisateur attendra indéfiniment.
- Erreurs réseau silencieuses : `try { ... } catch { /* Silently ignore polling errors */ }` (ligne 67). En cas de panne D-ID prolongée, aucun feedback.
- Pas de gestion du cas **403 quota dépassé** explicitement : message générique au lieu d'un CTA vers `/pricing`.
- Le toast d'erreur reste affiché jusqu'à clic manuel — pas d'auto-dismiss.

**💡 Recommandations**
1. Ajouter un timeout de 2 minutes max sur le polling D-ID + bouton "Reprendre".
2. Backoff : 5s → 8s → 12s → 20s.
3. Mapper les codes HTTP : 402 → "Crédits insuffisants" + CTA paiement, 403 → "Limite mensuelle" + CTA upgrade.

### 3.3 Responsive design

**✅ Forces**
- Tailwind avec breakpoints utilisés correctement (`sm:`, `lg:`).
- Hero adapté mobile/desktop, navbar avec menu burger.
- Slider Before/After avec un fallback en toggle pour mobile.

**⚠️ Problèmes**
- Le slider Before/After (`restore/page.tsx` ligne 408) utilise une astuce CSS de largeur dynamique qui peut **causer un layout shift** sur certains navigateurs mobiles.
- Le pricing à **5 colonnes en xl** (`Pricing.tsx`) est très dense — sur écran 13" cela devient illisible (boutons et badges qui débordent).

**💡 Recommandations**
1. Tester le slider sur Safari mobile (cas iOS Safari avec object-contain).
2. Passer le pricing à 3 colonnes max avec carrousel pour les plans extras.

### 3.4 Accessibilité

**🟠 Problèmes**
- **Aucun `<h1>` sur de nombreuses pages** vérifiables (Pricing, FAQ). Le SEO et les lecteurs d'écran en souffrent.
- Le slider Before/After n'a **aucune alternative clavier** — utilisateurs handicapés bloqués.
- Boutons icônes seules (close, theme toggle) sans `aria-label` systématique.
- Contraste : le `text-muted` sur fond `bg-card` peut tomber sous WCAG AA en mode clair (à vérifier).
- Pas d'attribut `lang="fr"` sur les inputs OAuth Google/Facebook (impact mineur).
- `auth/forgot-password/page.tsx` ligne 88 : `Pensez à vérifier vos spams.` avec un apostrophe non échappé ne devrait pas casser, mais convention.

**💡 Recommandations**
1. Audit Lighthouse Accessibilité ciblé (objectif > 90).
2. Ajouter navigation clavier sur le slider (touches flèches).
3. Compléter tous les `aria-label`.
4. Tester avec NVDA / VoiceOver.

### 3.5 Performance frontend

**✅ Forces**
- Next.js 15 avec App Router.
- Fonts auto-optimisées via `next/font/google`.
- Framer Motion utilisé avec `useInView` pour éviter les animations hors écran.

**⚠️ Problèmes**
- **`<img>` natifs au lieu de `<Image>` Next.js** dans Hero, restore, animate, dashboard → pas de lazy loading, pas de srcset optimisé. Charge ~3-5 Mo de plus.
- Bundle Framer Motion important (~80 Ko) — utilisable mais peut être code-splitté.
- `react-icons` importé en entier pour 3 icônes (`Footer.tsx`) — alors que `lucide-react` est déjà la base ; supprimer `react-icons`.
- Pas de `loading="lazy"` sur les images de demo.

**💡 Recommandations**
1. Remplacer `<img>` par `<Image>` partout (priorité 🟠).
2. Supprimer `react-icons` et utiliser exclusivement `lucide-react`.
3. Audit Lighthouse Performance (objectif LCP < 2.5s).

---

## 4. Qualité du code

### 4.1 Duplication

**⚠️ Problèmes identifiés**
- **`/api/auth/me` vs `/api/user/me`** : code quasi-identique entre `api/auth.py` ligne 191 et `api/user.py` ligne 36.
- **Parsing JSON Gemini** : la logique de nettoyage des blocs markdown et le fallback regex est dupliquée entre `analyser_photo()` et `obtenir_parametres_restauration()` dans `gemini_service.py` (lignes 86-115 et 200-228). Extraire une fonction `_parser_json_gemini(texte: str) -> dict`.
- **Validation upload** : le bloc de validation MIME + taille est dupliqué 3 fois dans `routes.py` (`analyser`, `restaurer`, `animer`). Créer une fonction `_valider_upload(fichier, contenu)`.
- **Gestion crédits + travail** : pattern `consommer_credit` + `mettre_a_jour_travail("erreur")` répété, à factoriser.

**💡 Recommandations**
1. Extraire un service `services/uploads.py` avec validation centralisée.
2. Factoriser le parsing Gemini.
3. Supprimer l'un des deux `/me`.

### 4.2 Gestion d'erreurs

**⚠️ Problèmes**
- `except Exception as e` partout dans `routes.py` — masque les bugs réels et logge tout au même niveau.
- Les exceptions Stripe (`stripe.error.StripeError`) sont attrapées génériquement → impossible de distinguer carte refusée / problème réseau / clé API invalide.
- `routes.py` ligne 491 : sur l'animation, après échec de `peut_animer`, on rembourse **1 crédit** sans vérifier si on l'avait vraiment consommé (et on a peut-être consommé un essai gratuit, pas un crédit).
- Le `crediter_utilisateur(user_id, 1)` de remboursement (routes.py ligne 290) ne distingue pas crédit payant vs essai gratuit → un utilisateur qui consomme un essai gratuit puis rate la colorisation se voit rembourser un crédit payant — **avantage indu**.

**💡 Recommandations**
1. Spécialiser les `except` : `httpx.HTTPError`, `stripe.error.CardError`, `ValueError`, etc.
2. Implémenter une **transaction atomique** pour la consommation de crédit + création de travail (rollback en cas d'échec).
3. Logger d'un côté la stack trace (logger.exception), de l'autre renvoyer un message utilisateur clair.

### 4.3 Tests

**⚠️ Problèmes**
- Couverture limitée à `test_auth.py` côté backend. **Aucun test** sur :
  - `routes.py` (analyse, restauration, animation)
  - Webhooks Stripe
  - Service Gemini (parsing robuste du JSON)
  - Service D-ID
  - Frontend (aucun test E2E Playwright/Cypress visible)
- Les tests dépendent du rate limiter via `TESTING=true` (`conftest.py`) — fragile, repose sur l'ordre d'import.
- Aucun test d'intégration des paiements (mode test Stripe non utilisé).

**💡 Recommandations**
1. Ajouter une suite minimale `test_routes.py` mockant Gemini/D-ID.
2. Tests E2E Playwright sur le parcours : signup → upload → restore → checkout (mode Stripe test).
3. Test de régression sur le parsing Gemini avec des réponses réelles capturées.

### 4.4 Typage et conventions

**✅ Forces**
- Pydantic strict côté backend.
- TypeScript strict côté frontend (probablement, à vérifier `tsconfig.json`).
- Conventions Python PEP8 respectées.

**⚠️ Problèmes**
- Utilisation extensive de `any` dans `AuthContext.tsx` (`(session?.user as any)?.id`, `(session as any)?.apiToken`) — perd l'intérêt de TS.
- Types frontend non synchronisés avec les schémas Pydantic (cf. `UserMe`).
- Côté Python : `Optional[X] = None` parfois manqué (`evenement: str = None` dans `consulter_audit_logs`).

**💡 Recommandations**
1. Déclarer un module `types/next-auth.d.ts` pour étendre `Session` proprement.
2. Générer les types TS depuis OpenAPI (`openapi-typescript`).

---

## 5. Performance backend

### 5.1 Requêtes base de données

**🔴 Problèmes critiques**
- **`_obtenir_connexion()` ouvre/ferme une connexion SQLite à chaque appel** (`database.py` ligne 17) → sous charge, c'est catastrophique. Pas de pool de connexions.
- **N+1 patterns** dans `consommer_credit` : 3 requêtes successives au lieu d'un UPDATE atomique avec condition.
- **Race condition** sur `decrementer_essais` et `consommer_credit` : SELECT puis UPDATE sans verrou → deux requêtes parallèles peuvent décrémenter en double.
- WAL activé (bien) mais SQLite reste limité en concurrence d'écriture (~100 TPS).

**💡 Recommandations**
1. **Migrer vers PostgreSQL + SQLAlchemy avec pool** (priorité 🔴).
2. Utiliser des `UPDATE ... WHERE credits > 0 RETURNING credits` pour la consommation atomique.
3. Ajouter `BEGIN IMMEDIATE` pour les sections critiques sur SQLite tant que la migration n'est pas faite.

### 5.2 Gestion des images

**⚠️ Problèmes**
- Les images sont **stockées sur disque local** (`UPLOAD_DIR`) — pas scalable horizontalement, pas de CDN. En cas de redéploiement, perte des fichiers si pas de volume persistant.
- Aucune compression / redimensionnement avant stockage : un JPEG 20 Mo reste 20 Mo.
- Pas de TTL ni de nettoyage automatique : le disque va se remplir.
- L'image originale + restaurée + colorisée = jusqu'à 3 fichiers par opération.

**💡 Recommandations**
1. Migrer vers **S3 / R2 / B2** avec URLs signées.
2. Compresser à max 2048px côté serveur avant traitement.
3. Cron de nettoyage des fichiers > 30 jours non liés à un travail terminé.
4. CDN devant les uploads (Cloudflare).

### 5.3 Cache

**⚠️ Problèmes**
- **Redis déclaré dans `docker-compose.yml`** mais **jamais utilisé** dans le code backend (`limiter.py` utilise le store en mémoire par défaut de slowapi).
- Pas de cache sur `/api/auth/me`, `/api/user/me`, `obtenir_plan_utilisateur()` — chaque requête frontend hit la DB.
- Pas de cache HTTP (`Cache-Control`) sur les routes statiques.

**💡 Recommandations**
1. Connecter `slowapi` à Redis pour un rate limiting distribué.
2. Cacher `obtenir_plan_utilisateur` (TTL 60s, invalidation sur webhook Stripe).
3. Headers `Cache-Control: public, max-age=86400` sur `/uploads/*`.

### 5.4 Appels API externes

**🔴 Problèmes critiques**
- **Pas de retry/backoff** sur Gemini et D-ID : un timeout réseau ponctuel fait échouer la restauration et **consomme le crédit utilisateur**.
- **Timeouts trop courts** : `httpx.AsyncClient(timeout=30.0)` pour D-ID (création) et `60.0` pour la colorisation Gemini — un seul échec et tout est perdu.
- L'appel Gemini est **synchrone** (`client.models.generate_content()`) dans une route async — bloque l'event loop FastAPI ! À wrapper dans `run_in_threadpool`.

**💡 Recommandations**
1. **Wrapper les appels Gemini synchrones avec `await asyncio.to_thread(...)`** (priorité 🔴).
2. Implémenter `tenacity` avec retry exponentiel (3 tentatives, 2s/4s/8s).
3. Pattern circuit breaker pour D-ID.
4. Décorrélation : pousser le job dans une queue (Celery/RQ), retourner un job_id, traiter en async.

---

## 6. Plan d'action priorisé

| Priorité | Domaine | Problème | Fichier(s) | Action recommandée | Impact |
|----------|---------|----------|------------|-------------------|--------|
| 🔴 | Infra | SQLite en code vs Postgres en compose | `db/database.py`, `docker-compose.yml` | Migrer vers SQLAlchemy + Alembic + Postgres | Bloquant prod multi-instances |
| 🔴 | Sécurité | CORS autorise localhost en prod | `main.py:78-90` | Variable d'env `ALLOWED_ORIGINS` | Vol de session via site malveillant |
| 🔴 | Config | URL `148.230.116.52:8000` en dur | `routes.py:419` | `PUBLIC_BACKEND_URL` dans `.env` | Bloque HTTPS et change de VPS |
| 🔴 | Funnel | Pages `/abonnement/succes` manquantes | `landing/src/app/` | Créer les pages | Casse le retour Stripe → perte de conversions |
| 🔴 | Perf | Gemini SDK synchrone dans route async | `gemini_service.py:74,180` | `await asyncio.to_thread(...)` | Event loop bloqué → throughput x10 |
| 🔴 | Sécurité | Création auto user via JWT | `auth.py:84` | Endpoint explicite + double opt-in | Usurpation si secret leaké |
| 🔴 | Sécurité | URL Gemini avec clé en query string | `gemini_service.py:230` | Utiliser SDK ou header | Fuite clé via logs |
| 🟠 | Sécurité | Pas de rate limit sur /restore /animate | `routes.py` | `@limiter.limit("10/minute")` | DoS et explosion COGS Gemini |
| 🟠 | Sécurité | filename non sanitisé | `routes.py:166,237` | Sanitiser via regex | Path traversal potentiel |
| 🟠 | Auth | Formulaire HTML bypass NextAuth | `auth/page.tsx:64-87` | `signIn("credentials")` | Casse CSRF, fragile |
| 🟠 | UX | Polling D-ID sans timeout max | `animate/page.tsx:50-78` | Timeout 2 min + backoff | UX bloquée si panne externe |
| 🟠 | Code | Logique crédits dans la route | `routes.py:280-340` | Extraire en `services/credits.py` | Maintenabilité, tests |
| 🟠 | Code | `routes.py` 700+ lignes | `api/routes.py` | Splitter en 4-5 fichiers | Maintenabilité |
| 🟠 | Perf | Pas de pool DB | `database.py:17` | SQLAlchemy + pool ou Postgres | Latence sous charge |
| 🟠 | Perf | `<img>` non optimisé | `Hero.tsx`, `restore/page.tsx`, etc. | `next/image` | LCP, bande passante |
| 🟠 | Sécurité | Pas de headers sécurité | `main.py` | Middleware CSP/HSTS/X-Frame-Options | Protection XSS/clickjacking |
| 🟡 | Sécurité | Énumération users sur /register | `auth.py:78` | Réponse générique 202 | Privacy users |
| 🟡 | Code | Duplication /me | `auth.py:191`, `user.py:36` | Supprimer un des deux | Drift de comportement |
| 🟡 | Code | Parsing JSON Gemini dupliqué | `gemini_service.py:86,200` | Factoriser | DRY |
| 🟡 | Tests | Couverture limitée à auth | `tests/` | Ajouter tests routes + E2E | Confiance déploiement |
| 🟡 | Stockage | Uploads sur disque local | `routes.py` | Migrer vers S3/R2 | Scalabilité, durabilité |
| 🟡 | Perf | Pas de cache plan/user | `database.py:obtenir_plan_utilisateur` | Cache Redis 60s | Latence frontend |
| 🟡 | Types | `any` partout dans AuthContext | `context/AuthContext.tsx` | `next-auth.d.ts` | Sécurité types |
| 🟢 | UX | Slider non accessible clavier | `restore/page.tsx:408` | `onKeyDown` flèches | A11y |
| 🟢 | Frontend | `react-icons` import lourd | `Footer.tsx` | Lucide uniquement | -50 Ko bundle |
| 🟢 | Code | `model_router.py` non utilisé | `services/model_router.py` | Intégrer ou supprimer | Code mort |
| 🟢 | Frontend | `next.config.ts` sans HTTPS prod | `landing/next.config.ts` | Ajouter `flashback-restore.com` | Images cassées prod |

---

## 7. Quick wins (< 30 min chaque)

1. **Externaliser `PUBLIC_BACKEND_URL`** dans `.env` et remplacer la ligne 419 de `routes.py`. Évite de hard-coder l'IP du VPS.
2. **Faire échouer le boot si `STRIPE_WEBHOOK_SECRET` manquant** : supprimer le fallback `whsec_placeholder` dans `config.py:57`.
3. **Retirer `localhost` de CORS en prod** via variable d'env `ALLOWED_ORIGINS` lue dans `main.py`.
4. **Ajouter `@limiter.limit("10/minute")` sur `/restore`, `/animate`, `/analyze`** dans `routes.py`.
5. **Créer les pages `/abonnement/succes` et `/abonnement/annulation`** (même contenu basique : "Merci, votre abonnement est actif" + redirection dashboard).
6. **Sanitiser `fichier.filename`** : remplacer `fichier.filename` par `re.sub(r'[^\w.-]', '_', fichier.filename)[:80]` dans les 3 routes.
7. **Supprimer `/api/auth/me` dupliqué** (garder celui de `user.py`).
8. **Wrapper les appels Gemini sync** : `await asyncio.to_thread(client.models.generate_content, ...)` dans `gemini_service.py`.
9. **Supprimer `react-icons`** dans `Footer.tsx`, utiliser `lucide-react`. Économie ~50 Ko bundle.
10. **Headers de sécurité** : ajouter un middleware Starlette ajoutant `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security: max-age=63072000`.
11. **Auto-dismiss du toast d'erreur** : `setTimeout(() => setError(null), 6000)` dans `restore/page.tsx` et `animate/page.tsx`.
12. **Réponse générique sur /register** : retourner 202 systématique ou message neutre pour éviter l'énumération.
13. **Cache `obtenir_plan_utilisateur`** avec `functools.lru_cache` + TTL maison (60s) — gain rapide en attendant Redis.
14. **Ajouter `loading="lazy"` sur `<img>`** dans Hero (`Hero.tsx`), Features, restore.
15. **Aligner `next.config.ts`** : ajouter `{ protocol: "https", hostname: "flashback-restore.com" }` dans `remotePatterns`.

---

**Conclusion** : le projet est à 70% de maturité production. Les corrections de la section 🔴 sont indispensables avant d'augmenter le trafic ou de communiquer publiquement. Une fois ces points traités, le SaaS aura une base saine pour scaler.