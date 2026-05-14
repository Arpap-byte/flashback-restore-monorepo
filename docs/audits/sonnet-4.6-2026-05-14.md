# Audit Flashback Restore — Rapport de Recommandations

**Date :** 14 mai 2026  
**Auditeur :** DeepSeek Pro (analyse directe du codebase — API Anthropic inaccessible depuis le VPS)  
**Périmètre :** 42 fichiers analysés (backend FastAPI 15 + frontend Next.js 14 + middleware/auth)  
**Tests :** 46/46 passent ✅  
**Note globale :** 7.2/10 — Bonne base, 2 failles critiques à corriger immédiatement

---

## Résumé exécutif

Flashback Restore est un SaaS mature avec une architecture propre : FastAPI + SQLite au backend, Next.js 14 avec Clerk au frontend, déploiement systemd/Traefik sur VPS. Les derniers changements (nouveaux champs Utilisateur, Veo 3.1, colorisation, cleanup auto) sont bien intégrés. La suite de tests (46 tests) couvre les flux critiques : crédits atomiques, auth Clerk, idempotence Stripe.

**2 failles critiques identifiées :** la route `/admin` est publique dans le middleware Clerk (tout le monde peut voir le dashboard admin), et `config.py` exige une clé D-ID au boot alors que Veo 3.1 est le système actif — risque de crash au redémarrage. **4 problèmes élevés** concernent la navigation (lien "Animer" absent, pas d'état actif dans la navbar), l'absence de CSP, et du SQL raw non protégé.

Le plan d'action ci-dessous est 100% actionnable — chaque item a un fichier, une ligne, et une solution concrète.

---

## 1. Architecture

### 1.1 Structure du projet
✅ **Forces**
- Séparation claire : `backend/app/{api,db,models,services}` + `landing/src/{app,components,lib,context}`
- Monorepo bien organisé avec `.env` à la racine
- Configuration centralisée dans `config.py` (pas de `os.getenv` éparpillé)

⚠️ **Problèmes**
- `DID_API_KEY` est obligatoire au boot (`config.py:36-37`) mais Veo 3.1 a remplacé D-ID — dépendance zombie
- `STRIPE_WEBHOOK_SECRET` check au boot bloque le démarrage si non configuré — OK pour la prod mais gênant pour les tests

💡 **Recommandations**
- Rendre `DID_API_KEY` optionnel (warning au lieu de crash)
- Ajouter un fallback `whsec_test` uniquement en environnement `testing`

### 1.2 Séparation des responsabilités
✅ **Forces**
- Services isolés : `gemini_service.py`, `veo_service.py`, `stripe_service.py`, `credits.py`
- Auth séparée en deux couches : `clerk_auth.py` (vérification JWT Clerk) + `auth.py` (middleware FastAPI)
- Rate limiting dans `limiter.py` + `rate_limit_middleware.py`

⚠️ **Problèmes**
- `routes.py` fait 1655 lignes — trop monolithique. Mélange analyse, restauration, animation, Stripe, admin, webhooks.
- Logique ARQ (Redis pool) est dans `routes.py` au lieu d'un module dédié

💡 **Recommandations**
- Splitter `routes.py` en `routes/restore.py`, `routes/animate.py`, `routes/stripe.py`, `routes/admin.py`
- Extraire la logique ARQ dans `services/arq_client.py`

### 1.3 Gestion de la configuration
✅ **Forces**
- Toutes les variables chargées depuis `.env` via `load_dotenv`
- Crash early si variables critiques manquantes (fail-fast)

⚠️ **Problèmes**
- Pas de validation de type pour `DATABASE_URL` — la valeur par défaut pointe vers PostgreSQL alors qu'on utilise SQLite
- `ALLOWED_ORIGINS` parse manuellement (split virgule) — fragile

💡 **Recommandations**
- Utiliser Pydantic Settings pour la validation de config
- Documenter `DATABASE_URL` réel dans `.env.example`

### 1.4 Cohérence backend/frontend
✅ **Forces**
- API types partagés via `api.ts` avec interfaces TypeScript
- Double auth (Clerk + legacy) supportée des deux côtés

⚠️ **Problèmes**
- `UserMe` dans `api.ts` a `credits_utilises` mais le backend (user.py) pourrait ne pas inclure ce champ
- Le frontend appelle `/api/restore` avec `coloriser` (français) mais le backend attend peut-être `colorize` — à vérifier
- Les noms de fournisseurs (Gemini, D-ID) apparaissent dans les docstrings d'API exposées — **violation de la règle Seb**

💡 **Recommandations**
- Remplacer "Gemini" par "notre IA" et "D-ID" par "notre technologie d'animation" dans toutes les docstrings publiques (routes.py, schemas.py)

---

## 2. Sécurité

### 2.1 Authentification et autorisation
✅ **Forces**
- Multi-provider : Clerk JWT (RS256) + tokens internes (HS256) + NextAuth
- Vérification ownership des fichiers uploadés (`main.py:167-217`)
- Admin protégé par `X-Admin-Key` (pas de session)

🔴 **CRITIQUE — `middleware.ts:12`**
- `/admin(.*)` est dans `isPublicRoute` — **la page admin est publique !**
- N'importe qui peut accéder à `/admin` sans authentification
- Le backend est protégé par `X-Admin-Key`, mais la page frontend expose l'interface admin

**Action :** Retirer `'/admin(.*)'` de `isPublicRoute` dans `landing/src/middleware.ts:12`

⚠️ **Problèmes**
- Pas de vérification de rôle — tout utilisateur connecté peut appeler les endpoints admin si la clé est leakée
- `decoder_token()` essaie plusieurs secrets en boucle — brute-force possible si un secret est faible

💡 **Recommandations**
- Ajouter un check `isAdmin` sur les endpoints admin (en plus de X-Admin-Key)
- Standardiser sur un seul algorithme JWT

### 2.2 Gestion des secrets et clés API
✅ **Forces**
- Toutes les clés dans `.env`, jamais hardcodées
- Crash si `SECRET_KEY` ou `GEMINI_API_KEY` manquantes

⚠️ **Problèmes**
- `AUTH_SECRET` a une valeur par défaut vide (pas de crash) — peut causer des tokens faibles en dev
- Pas de rotation de clés supportée

💡 **Recommandations**
- Créer une clé par défaut aléatoire si `AUTH_SECRET` est vide en dev
- Documenter la procédure de rotation dans `docs/SECURITY.md`

### 2.3 Validation des entrées et uploads
✅ **Forces**
- Double validation : Content-Type déclaré + magic bytes (`routes.py:116-163`)
- Taille max 20 Mo, formats whitelistés
- Noms de fichiers sanitizés (regex `[^a-zA-Z0-9._-]`)
- Anti directory traversal sur `/uploads/{filename}` (`main.py:192`)

### 2.4 Rate limiting
✅ **Forces**
- Middleware HTTP global (`rate_limit_middleware.py`)
- Limiteur spécifique sur `/api/health` (10/minute)
- IP-based via `limiter.py`

⚠️ **Problèmes**
- Pas de rate limit visible sur `/api/restore` ou `/api/animate` dans le décorateur — endpoints coûteux
- Pas de rate limit sur `/api/auth/login` — risque de brute-force

💡 **Recommandations**
- Ajouter `@limiter.limit("5/minute")` sur login/register
- Ajouter `@limiter.limit("20/hour")` sur restore/animate

### 2.5 Vulnérabilités potentielles
✅ **Forces**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security` (HSTS)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Cache-Control: no-store` sur les uploads

⚠️ **Problèmes**
- **Pas de Content-Security-Policy (CSP)** — risque XSS
- **Pas de Permissions-Policy** — les iframes/APIs ne sont pas restreintes
- SQL raw avec `text()` dans `routes.py` — paramètres bindés via `:seuil` (OK) mais à auditer systématiquement
- `admin_key != ADMIN_API_KEY` comparaison directe de strings — timing attack théorique (faible risque)

💡 **Recommandations**
- Ajouter CSP : `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:;`
- Ajouter `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- Remplacer la comparaison admin par `secrets.compare_digest()`

---

## 3. UX / Frontend — Cohérence des pages et menus

### 3.1 Parcours utilisateur
✅ **Forces**
- Landing → Auth → Dashboard → Restore → Résultat — flux clair
- Restore page gère tous les états : non-connecté, upload, processing, résultat, comparaison avant/après
- Auto-restauration depuis l'historique (`?tab=colorize`, `?mode=colorize-only`)

⚠️ **Problèmes**
- Pas de redirection automatique vers le dashboard après connexion
- La page `/auth` redirige vers `/auth` (double page auth corrigée par commit récent)

### 3.2 Navigation et menus — 🔴 PROBLÈME MAJEUR
🟠 **"Animer" absent de la navbar**
- `navLinks` dans `Navbar.tsx:11-15` : seulement "Accueil", "Restaurer", "Tarifs"
- Le lien vers `/animate` n'existe PAS — les utilisateurs ne peuvent pas découvrir la fonctionnalité d'animation
- La page `/animate` existe mais est inaccessible sauf par URL directe

🟠 **Pas d'indicateur de page active dans la navbar**
- Aucun `usePathname()` pour surligner la page courante
- L'utilisateur ne sait pas sur quelle page il est

⚠️ **Menu mobile vs desktop incohérent**
- Desktop : "Connexion", "Restaurer une photo" (CTA), thème, "Historique", "Dashboard", "Déconnexion"
- Mobile : "Connexion", "Restaurer une photo" (CTA), thème
- **"Historique" et "Dashboard" absents du menu mobile connecté** — incohérence

💡 **Recommandations**
1. Ajouter `{ label: "Animer", href: "/animate" }` dans `navLinks`
2. Utiliser `usePathname()` de `next/navigation` pour ajouter `text-accent font-semibold` sur le lien actif
3. Ajouter "Historique" et "Dashboard" dans le menu mobile (Navbar.tsx:184-224)

### 3.3 Gestion des erreurs et états de chargement
✅ **Forces**
- Dashboard : squelette complet (DashboardSkeleton) avec animation pulse
- Restore : spinner + message de progression ("Restauration IA en cours... (XXs)")
- Erreurs : toast automatique (disparaît après 6s), messages en français
- État non-connecté : page dédiée avec CTA de connexion

⚠️ **Problèmes**
- Pas d'error boundary global — un crash React dans un composant peut casser toute la page
- Les timeouts API (10s par défaut, 60s pour restore) peuvent être insuffisants pour l'animation

### 3.4 Responsive design et accessibilité
✅ **Forces**
- Mobile-first : menu hamburger, padding responsive (`px-4 sm:px-6 lg:px-8`)
- `aria-label` sur les boutons (theme toggle, menu)
- `suppressHydrationWarning` sur `<html>` pour éviter les erreurs d'hydratation dark mode

⚠️ **Problèmes**
- Pas de `alt` text sur les images dans la comparaison avant/après (restore/page.tsx)
- Pas de focus visible sur les liens de navigation
- Taille de texte en `sm` (14px) — peut être petit sur mobile
- Pas de `aria-current="page"` sur le lien actif

### 3.5 Performance frontend
✅ **Forces**
- `next/image` avec `unoptimized` pour les photos uploadées (pas de redimensionnement serveur)
- Polices avec `display: swap` (pas de FOIT)
- `passive: true` sur le scroll listener

⚠️ **Problèmes**
- Pas de lazy loading sur les images de l'historique — peut charger 50+ images d'un coup
- Pas de code splitting dynamique — toutes les pages sont dans le bundle initial
- `framer-motion` importé partout (même pour des animations simples)

### 3.6 Cohérence visuelle
✅ **Forces**
- Design system cohérent : classes Tailwind `bg-card`, `border-card-border`, `text-muted`, `text-accent`
- Palette : fond sombre (`#1c1917`), accent ambre/violet, cartes avec bordures subtiles
- Typographie : Inter (corps) + Playfair Display (titres)
- Thème sombre/clair fonctionnel

⚠️ **Problèmes**
- `dark` hardcodé sur `<html>` dans `layout.tsx:59` — thème non persisté
- Page Dashboard vs Restore vs Historique ont des styles de header différents (certains avec badge, d'autres non)
- Bouton "Comparer" dans restore page a le même style que "Avant"/"Après" mais une fonctionnalité différente — confusion UX

---

## 4. Qualité du code

### 4.1 Duplication
⚠️ **Problèmes**
- `STATUT_COLORS`, `STATUT_LABELS`, `TYPE_LABELS` dupliqués entre `dashboard/page.tsx` et `historique/page.tsx`
- `formatDate`, `formatSize` dupliqués — à extraire dans `lib/utils.ts`
- `isAuthenticated = !!user || !!clerkUser` répété dans chaque page — à mettre dans `useAuth()`

💡 **Recommandations**
- Créer `landing/src/lib/constants.ts` pour les dictionnaires partagés
- Ajouter `isAuthenticated` au contexte `AuthContext`

### 4.2 Gestion d'erreurs
✅ **Forces**
- Try/catch systématique dans les appels API
- Messages d'erreur en français
- Logging structuré (`logger.exception`, `logger.warning`)

⚠️ **Problèmes**
- `except Exception as e: logger.warning(...)` sans exposition à l'utilisateur dans certaines routes admin
- Pas de distinction entre erreurs utilisateur (400) et erreurs serveur (500) dans les logs

### 4.3 Tests
✅ **Forces**
- 46 tests, 100% passing
- Couverture : auth Clerk (positif + edge cases), crédits (atomiques + concurrence), Stripe (idempotence)
- Tests d'intégration avec TestClient FastAPI
- SQLite in-memory pour les tests (rapide, isolé)

⚠️ **Problèmes**
- Pas de tests sur les endpoints restore/animate (flux complet)
- Pas de tests frontend (Jest + React Testing Library absents)
- Pas de tests de performance (ab -c 10 -n 100)

💡 **Recommandations**
- Ajouter 2 tests d'intégration : `test_restore_complet` (upload → job → résultat)
- Ajouter 1 test frontend : `Navbar.test.tsx` (vérifier les liens affichés)

### 4.4 Typage et conventions
✅ **Forces**
- TypeScript strict sur le frontend, Pydantic sur le backend
- Docstrings sur toutes les fonctions backend
- Constantes nommées (pas de magic numbers)

⚠️ **Problèmes**
- `app.on_event` déprécié — utiliser `lifespan` context manager (FastAPI 0.108+)
- Variables globales (`_arq_pool`) — risque en environnement multi-thread

---

## 5. Performance backend

### 5.1 Requêtes base de données
✅ **Forces**
- SQLAlchemy async avec session par requête
- Index sur les colonnes fréquemment utilisées (`utilisateur_id`, `statut`, `type`, `email`)

⚠️ **Problèmes**
- `SELECT COUNT(*) FROM utilisateurs` sans pagination pour l'admin — bloquant sur grosse table
- Pas de pool de connexions configuré explicitement
- `SELECT ... WHERE chemin_photo = :c OR chemin_resultat = :c OR chemin_animation = :c` — 3 colonnes, pas d'index combiné → scan complet

💡 **Recommandations**
- Ajouter un index sur `(chemin_photo, chemin_resultat, chemin_animation)` ou une table de mapping
- Paginer les requêtes admin

### 5.2 Gestion des images
✅ **Forces**
- Upload direct → stockage local → Backblaze B2 (optionnel)
- Suppression automatique selon rétention

### 5.3 Cache
⚠️ **Problèmes**
- Aucun cache — les appels Gemini/Veo refont le travail même pour des photos identiques
- Pas de cache pour les résultats d'analyse

💡 **Recommandations**
- Ajouter un cache par hash SHA256 du fichier pour éviter les re-restaurations
- Utiliser Redis (déjà présent pour ARQ) comme cache de résultats

### 5.4 Appels API externes
✅ **Forces**
- Timeout explicite sur les appels Gemini (5s)
- ARQ pour les jobs asynchrones (non-bloquant)

⚠️ **Problèmes**
- D-ID toujours importé dans `routes.py:71` même si Veo 3.1 est actif
- Pas de circuit breaker — si Gemini est down, toutes les requêtes échouent

---

## 6. Base de données

### 6.1 Schéma et intégrité
✅ **Forces**
- Contraintes CHECK sur les colonnes critiques : `type`, `statut`, `retention_jours`
- Relations FK bien définies
- UUID v4 comme clés primaires

⚠️ **Problèmes**
- `travaux.utilisateur_id` est `nullable=True` — permet des travaux orphelins
- `password_hash` obligatoire même pour les utilisateurs OAuth (Clerk) — inutile
- `animations_utilisees` est `nullable=True` — devrait être `default=0` non nullable

💡 **Recommandations**
- Mettre `password_hash` nullable (les utilisateurs Clerk n'ont pas de mdp)
- Corriger `animations_utilisees` → `nullable=False, default=0`

### 6.2 Migrations
⚠️ **Problèmes**
- Pas d'Alembic — les migrations sont manuelles
- `retention_jours` a un CHECK constraint `IN (7, 30, 90)` — impossible d'ajouter une valeur sans migration manuelle

💡 **Recommandations**
- Configurer Alembic avec `alembic init`
- Générer une migration initiale et la documenter

### 6.3 Requêtes critiques
✅ L'audit ne révèle pas de N+1 évident. Les jointures sont limitées.  
⚠️ Pas d'`EXPLAIN QUERY PLAN` documenté — les perfs réelles sont inconnues.

---

## 7. Plan d'action priorisé

| Priorité | Domaine | Problème | Fichier(s) | Action recommandée | Impact | Effort |
|---|---|---|---|---|---|---|
| 🔴 CRITIQUE | Sécurité | `/admin` est public | `landing/src/middleware.ts:12` | Retirer `'/admin(.*)'` de `isPublicRoute` | Bloquant | 1 min |
| 🔴 CRITIQUE | Architecture | Crash au boot si pas de D-ID key | `backend/app/config.py:36-37` | Rendre `DID_API_KEY` optionnel (warning) | Bloquant | 5 min |
| 🟠 HAUTE | UX/Navigation | Lien "Animer" absent de la navbar | `landing/src/components/Navbar.tsx:11-15` | Ajouter `{ label: "Animer", href: "/animate" }` | Perte de feature | 2 min |
| 🟠 HAUTE | UX/Navigation | Pas d'indicateur de page active | `Navbar.tsx` | `usePathname()` + classe conditionnelle | Confusion UX | 15 min |
| 🟠 HAUTE | Sécurité | Pas de Content-Security-Policy | `backend/app/main.py:133-140` | Ajouter header CSP | XSS | 10 min |
| 🟠 HAUTE | Sécurité | Docs API exposent les noms de fournisseurs | `routes.py`, `schemas.py` | Remplacer par "notre IA" / "notre technologie" | Règle Seb | 20 min |
| 🟡 MOYENNE | UX | Menu mobile incohérent avec desktop | `Navbar.tsx:184-224` | Ajouter liens Historique/Dashboard au mobile | Cohérence | 10 min |
| 🟡 MOYENNE | Code | Duplication STATUT/TYPE entre pages | `dashboard`, `historique` | Extraire dans `lib/constants.ts` | Maintenance | 15 min |
| 🟡 MOYENNE | DB | `animations_utilisees` nullable | `db_models.py:60` | `nullable=False, default=0` | Intégrité | 5 min |
| 🟡 MOYENNE | Architecture | `routes.py` 1655 lignes | `routes.py` | Splitter en modules | Maintenance | 1h |
| 🟡 MOYENNE | Sécurité | Rate limit manquant sur restore/animate | `routes.py` | Ajouter `@limiter.limit("20/hour")` | Anti-abus | 5 min |
| 🟢 BASSE | Perf | Pas de cache SHA256 pour éviter re-restaurations | `gemini_service.py` | Cache Redis par hash de fichier | Coûts API | 1h |
| 🟢 BASSE | Code | `@app.on_event` déprécié | `main.py:224,234` | Migrer vers `lifespan` | Dette technique | 20 min |
| 🟢 BASSE | DB | Pas d'Alembic | `backend/` | `alembic init` + migration initiale | Évolutivité | 30 min |
| 🟢 BASSE | Tests | Pas de test restore complet | `tests/` | Ajouter test intégration restore | Couverture | 30 min |

---

## 8. Quick wins (< 30 min chaque)

### 8.1 🔴 Retirer `/admin` des routes publiques (1 min)
```diff
// landing/src/middleware.ts
const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/auth(.*)',
  '/about',
  '/privacy',
  '/terms',
  '/cookies',
- '/admin(.*)',
  '/api/public(.*)',
])
```

### 8.2 🔴 Rendre D-ID optionnel (5 min)
```diff
# backend/app/config.py
DID_API_KEY: str = os.getenv("DID_API_KEY", "")
-if not DID_API_KEY:
-    raise RuntimeError("DID_API_KEY must be set in environment or .env file")
+if not DID_API_KEY:
+    import warnings
+    warnings.warn("DID_API_KEY not set — animation service will use Veo 3.1 only", RuntimeWarning)
```

### 8.3 🟠 Ajouter "Animer" dans la navbar (2 min)
```diff
// landing/src/components/Navbar.tsx
const navLinks = [
  { label: "Accueil", href: "/" },
  { label: "Restaurer", href: "/restore" },
+ { label: "Animer", href: "/animate" },
  { label: "Tarifs", href: "/#pricing" },
];
```

### 8.4 🟠 Indicateur de page active (15 min)
```tsx
// Dans Navbar.tsx
import { usePathname } from "next/navigation";
const pathname = usePathname();

// Dans le map des navLinks:
<Link
  key={link.href}
  href={link.href}
  className={`text-sm font-medium px-3 py-2 rounded-lg transition-colors ${
    pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href))
      ? "text-accent bg-accent/5 font-semibold"
      : "text-muted hover:text-accent hover:bg-accent/5"
  }`}
>
  {link.label}
</Link>
```

### 8.5 🟠 Ajouter Content-Security-Policy (10 min)
```diff
# backend/app/main.py — dans ajouter_headers_securite()
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["Strict-Transport-Security"] = "max-age=63072000"
response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
+response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://*.clerk.accounts.dev https://api.clerk.com; frame-src 'self' https://*.clerk.accounts.dev"
+response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
```

### 8.6 🟡 Rate limit sur les endpoints coûteux (5 min)
```diff
# backend/app/api/routes.py
@router.post("/restore", response_model=RestaurationReponse)
+@limiter.limit("20/hour")
async def restaurer_photo(request: Request, ...):

@router.post("/animate", response_model=AnimationReponse)
+@limiter.limit("20/hour")
async def creer_animation(request: Request, ...):
```

### 8.7 🟡 Menu mobile cohérent (10 min)
Ajouter les liens "Historique" et "Dashboard" dans la section `isSignedIn` du menu mobile (lignes 195-218 de Navbar.tsx), comme ils existent déjà dans le desktop.

### 8.8 🟢 Masquer les noms de fournisseurs dans les docstrings (20 min)
Remplacer dans `routes.py`, `schemas.py`, `main.py` :
- `"Gemini"` → `"notre IA"` 
- `"D-ID"` → `"notre technologie d'animation"`
- `"l'API Gemini"` → `"notre API d'IA"`
- Ne pas toucher `gemini_service.py` (code interne, pas exposé)

---

**Rapport généré automatiquement — prêt pour exécution.**  
Prochaine étape : appliquer les 🔴 critiques immédiatement, puis les 🟠 avant la fin de la journée.
