# Audit Frontend Flashback Restore — Claude Fable 5

## Résumé exécutif

Le frontend est globalement soigné visuellement (design system cohérent, animations Framer Motion, dark theme), mais souffre de **trois problèmes structurels majeurs** : (1) un middleware Clerk qui déclare publiques toutes les routes censées être protégées (`/restore`, `/animate`, `/bibliotheque`, `/dashboard`), rendant la protection purement cosmétique côté client ; (2) une **incohérence de contrat API** avérée (`coloriser` vs `colorize`, `status` vs `statut`, `credits_utilises` vs `credits_consommes`) ; (3) un **conflit SEO frontal** entre `robots.ts` (qui interdit `/restore`, `/dashboard`, `/abonnement`) et `sitemap.ts` (qui les référence). S'y ajoutent : le bug Clerk d'icônes OAuth invisibles (le thème `dark` de `@clerk/themes` est installé mais jamais utilisé), des tokens JWT passés en query string, un dashboard admin avec clé en `localStorage`, et des dépendances mortes (`next-auth`, `@auth/core`). Le code est fonctionnel mais nécessite un sprint de durcissement avant montée en charge.

**Note : 5,5/10**

---

## 1. Architecture & Routing

### Middleware et routes "protégées" : protection illusoire ⚠️

`landing/src/middleware.ts` :

```ts
const isPublicRoute = createRouteMatcher([
  '/', '/sign-in(.*)', '/sign-up(.*)', ...
  '/bibliotheque',
  '/dashboard',
  '/restore',
  '/animate',
  ...
])
```

Les pages annoncées comme protégées (`/restore`, `/animate`, `/bibliotheque`, `/dashboard`) sont **explicitement publiques** dans le middleware. La "protection" repose uniquement sur des checks client (`if (!isAuthenticated) return <NotConnected />` dans `RestoreClient.tsx`, `AnimateClient.tsx`, `BibliothequeClient.tsx`, `DashboardClient.tsx`). Conséquences :
- Pas de redirection serveur vers `/sign-in` (contredit le cahier des charges).
- Flash de contenu non authentifié possible, et logique de protection dupliquée 4 fois avec des comportements divergents (`/auth?callbackUrl=` dans Animate/Restore, `/sign-in` dans Bibliothèque, `/auth` dans Dashboard).

### `/admin` : double système d'authentification incohérent

`/admin` n'est **pas** dans `isPublicRoute`, donc Clerk exige une session… puis la page (`admin/page.tsx`) ré-authentifie via `X-Admin-Key` stocké en `localStorage`. N'importe quel utilisateur Clerk connecté voit l'écran de login admin. Voir aussi §5.

### Suspense boundaries manquantes

- `app/auth/page.tsx` : `useSearchParams()` dans une page client **sans** `<Suspense>` → erreur de build / bailout CSR sous Next 14+.
- `app/restore/page.tsx` rend `<RestoreClient />` (qui utilise `useSearchParams`) sans Suspense — même problème.
- `BibliothequeClient.tsx` et `auth/reset-password/page.tsx` le font correctement (à généraliser).

### Divers

- **Métadonnées dupliquées** : `animate/layout.tsx` + `animate/page.tsx` définissent chacun `metadata` (le `page` écrase le `layout`). Idem pour `restore` et `dashboard`. À dédupliquer.
- `terms/page.tsx` fait un `permanentRedirect()` en composant : à déplacer dans `next.config.ts > redirects()` comme les autres.
- `next.config.ts` redirige `/contact` vers `/#footer` mais **aucun élément n'a `id="footer"`**.
- `Footer.tsx` et `about/page.tsx` linkent `/upload` (redirection 301 vers `/restore`) — autant lier directement `/restore`.
- `abonnement/succes` pointe vers `/dashboard` : OK, mais incohérent avec le wording "tableau de bord" alors que le plan ne donne pas forcément accès aux features.
- **`package.json` incohérent avec le contexte** : `next: 16.2.4`, `react: 19.2.4`, `lucide-react: ^1.14.0` — versions qui ne correspondent ni au Next 14/15 annoncé ni aux versions publiées. `next-auth` + `@auth/core` sont présents mais **plus utilisés nulle part** (migration Clerk terminée) → à supprimer.

---

## 2. Composants & UI/UX

### Bug Clerk #1 — Icônes OAuth invisibles

`@clerk/themes` est dans les dépendances mais **jamais importé**. Le `ClerkProvider` (`layout.tsx`) n'a aucune `appearance`, donc :
- Le **modal** `<SignInButton mode="modal">` du `Navbar.tsx` s'ouvre avec le thème Clerk **clair par défaut** sur fond dark → boutons sociaux blancs sur blanc.
- Les pages `sign-in`/`sign-up` définissent des `variables` custom mais pas de `baseTheme: dark`, ce qui laisse les SVG des social buttons en rendu light.

→ Correctif global dans §8 (Quick Win n°1). Vérifier aussi que la CSP autorise bien `img.clerk.com` (c'est le cas dans `next.config.ts`, OK).

### Bug Clerk #2 — "My Application"

Ce libellé provient du **nom de l'application dans le Clerk Dashboard** (Settings → General), pas du code. Aucun `appearance` ni `localization` ne le surcharge. Action : renommer dans le dashboard Clerk en "Flashback Restore". Côté code, on peut masquer le footer Clerk (`elements: { footer: "hidden" }`) déjà partiellement fait dans `Navbar.tsx` (`userButtonPopoverFooter: "hidden"`).

### Qualité des composants

- **Admin (`admin/page.tsx`) : rendu triple de `TravauxList`** dans la modale :
  ```tsx
  {modal.type === "travaux" && <TravauxList adminKey={adminKey} />}
  ...
  {modal.type === "travaux" && modal.extra && <TravauxList ... type statut />}
  {modal.type === "travaux" && !modal.extra && <TravauxList adminKey={adminKey} />}
  ```
  Ouvrir "Tous les travaux" monte le composant **deux fois** (2 appels API, tableau dupliqué) ; un drill-down type/statut monte la liste filtrée **et** la liste complète. Bug visuel et réseau.
- **Duplication massive** entre `RetoucheesTab.tsx` et `AnimationsTab.tsx` (`formatSize`, `formatExpiration`, `formatDate`, `STATUT_*` copiés-collés, aussi présents dans `DashboardClient`). À extraire dans `lib/format.ts`.
- `Pricing.tsx > CreditPacksSection` réimplémente `getCreditPacks`/`checkoutCreditPack` en `fetch` brut avec `any`, alors que `lib/api.ts` les expose déjà typés — et la page `/credits` les utilise correctement. Double source de vérité.
- `ImporteesTab.tsx` et `RetoucheesTab.tsx` naviguent avec `window.location.href = "/animate"` → full reload au lieu de `router.push()`.
- Navigation dans `DashboardClient` : `window.location.href = "/#pricing"` au lieu de `<Link>`.

### États de chargement et d'erreur

- Bons skeletons (`DashboardSkeleton`, grilles pulse en bibliothèque). ✅
- **Erreurs avalées silencieusement** : `fetchLibrary` / `fetchHistory` dans `BibliothequeClient.tsx` (`catch { /* Silencieux */ }`) → l'utilisateur voit "Aucune image importée" alors que l'API est en panne. Faux état vide = perte de confiance.
- `DashboardClient` : si `getUserMe` échoue, il **fabrique un faux utilisateur** plan gratuit / 0 crédits — un abonné Premium verrait "Gratuit, 0 crédits" pendant une panne API. Afficher une erreur réessayable plutôt qu'un fallback mensonger.
- Admin : `r.json()` sans check `res.ok` partout (`UtilisateursList`, `TravauxList`, `UserDetailView`) → `d.utilisateurs` undefined → crash `.map`.

### Accessibilité

- **Slider de comparaison (`RestoreClient`) : `onMouseDown` uniquement** — inutilisable au clavier ET au **tactile** (pas de `onTouchStart`/Pointer Events). Le mode "Côte à côte" est cassé sur mobile, cœur de la proposition de valeur.
- Modales (`admin Modal`, `OutOfCreditsModal`, galerie Restore, `RgpdConsentModal`) : pas de `role="dialog"`, `aria-modal`, focus trap ni fermeture `Escape`.
- `RetentionBar` : dropdown sans fermeture au clic extérieur ni gestion clavier.
- Bouton de fermeture d'erreur en bibliothèque : `✕` texte brut sans `aria-label`.
- Bon point : toggle 1080p en `role="switch"` + `aria-checked` ✅, segmented control en `role="tablist"` ✅.

### Responsive / thème

- Contradiction : le contexte annonce "dark uniquement" mais `ThemeProvider` + toggle Sun/Moon existent, avec des classes `dark:text-gray-950` partout. Les pages sign-in/sign-up imposent `background: #0a0a0a` en dur → en light mode, mélange incohérent. **Décider** : soit supprimer le toggle, soit assumer le light mode (et corriger Clerk en conséquence).
- `abonnement/succes` et `abonnement/annulation` : `group-hover:translate-x-1` sur l'icône `ArrowRight` mais le `<Link>` parent n'a pas la classe `group` → effet mort.
- Incohérence de contenu : Hero "50K+ photos restaurées", About "100 000+" — crédibilité.

---

## 3. Intégration API & État

### Incohérences de contrat backend↔frontend (bug #3 confirmé)

| Endroit | Champ envoyé/attendu | Problème |
|---|---|---|
| `lib/api.ts > restorePhoto` | `formData.append("coloriser", "true")` | vs `restoreFromLibrary` qui envoie `formData.append("colorize", ...)` — **un des deux est forcément ignoré par le backend** |
| `AnimationStatus` | clé `status` à valeurs françaises (`"termine"`) | vs `/api/job/{id}` qui renvoie `statut` — convention mixte FR/EN fragile |
| Admin `UtilisateurDetail.credits_utilises` | vs `UserDetailResponse.utilisateur.credits_consommes` | deux noms pour la même donnée |
| `AuditLogsSection` | `GET /api/audit-logs` | tous les autres endpoints admin sont sous `/api/admin/...` — préfixe incohérent |
| `restoreFromLibrary` retourne `{ jobId, travailId }` via `apiFetch<any>` | `any` masque le contrat | typer la réponse |

→ Recommandation forte : générer les types depuis le backend (OpenAPI + `openapi-typescript`) pour éliminer cette classe de bugs.

### Gestion des tokens Clerk

- `getAuthHeader()` appelle `clerk.session.getToken({ skipCache: true })` **à chaque requête** → un round-trip Clerk par appel API, alors que les tokens sont valides 60 s et que Clerk gère le cache/refresh lui-même. Pénalité de latence systématique (voir Quick Win n°4).
- `Pricing.tsx` : `localStorage.getItem("__clerk_db_jwt")` — **API interne Clerk non documentée**, c'est le dev browser JWT, pas un token de session. Cassera en prod et selon les versions. Remplacer par `checkoutCreditPack()` de `lib/api.ts`.
- `getPhotoUrl` ajoute le JWT en **query string** (`?token=...`) pour `<img>`/`<video>` — voir §5.
- `apiFetch` : retry sur 401 avec refresh ✅, `ApiError` typée avec status ✅, mais :
  - `clearTimeout(timeoutId)` n'est exécuté que si `attempt === 1` → si la requête réussit au 1er essai, l'`AbortController` peut se déclencher inutilement après coup ;
  - `delete options.headers` **mute l'objet du caller** ;
  - timeout par défaut 10 s un peu court pour `/api/user/history` sur connexion lente.

### Polling et asynchrone

- `AnimateClient` : backoff progressif (`POLL_DELAYS`), timeout 10 min, arrêt sur 401/403 via `ApiError`, cleanup `cancelled` — **bien fait** ✅. Petit bug d'affichage : `Math.round(status.progress || ...)` affiche `progress` du backend mais la barre l'ignore (largeur hardcodée 20/60/100 %).
- `RestoreClient` : `AbortController` + cleanup au démontage ✅. Mais `hasAutoRestored` déclenche `handleRestore()` depuis un `useEffect` dont la closure peut capturer un état périmé (`colorize` setté juste avant, non garanti au moment de l'appel).
- Double système d'auth en parallèle : `useAuth()` (AuthContext maison, lui-même wrapper de Clerk) **et** `useUser()` Clerk dans les mêmes composants (`isAuthenticated = !!user || !!clerkUser`). Redondant — l'AuthContext n'apporte que le cleanup `sessionStorage` ; tout fusionner sur Clerk.

---

## 4. Performance

- **`unoptimized` sur quasi toutes les `<Image>`** (Animate, Bibliothèque, Restore, tabs) : compréhensible pour les URLs tokenisées (`/uploads/...?token=`), mais perte totale de l'optimisation Next (WebP/AVIF, resize). Envisager un endpoint de thumbnails côté backend.
- **Bug inverse dans `DashboardClient`** : les miniatures d'historique utilisent `getPhotoUrl(t.url_resultat)` **sans token et sans `unoptimized`** → l'optimiseur Next fetch côté serveur une URL protégée → images cassées probables. À aligner (token + `unoptimized`).
- `skipCache: true` à chaque appel (cf. §3) : sur la bibliothèque, `RestoreClient.openGallery` fait un `getPhotoUrlAsync` **par image** (50 images = 50 `getToken` réseau). Récupérer le token une fois et le passer à `getPhotoUrl(url, token)`.
- Pages légales (`privacy`, `cookies`, `conditions-utilisation`, `mentions-legales`, `about`) en `"use client"` + framer-motion pour de simples fade-in : poids JS inutile sur des pages statiques. Les convertir en Server Components (+ CSS animations) réduirait le bundle et permettrait `export const metadata` (cf. §6).
- `getCreditPacks` fetché à la fois sur la home (`Pricing > CreditPacksSection`) et `/credits` — acceptable, mais sans cache (`fetch` brut sans revalidate).
- Dépendances mortes : `next-auth`, `@auth/core`, `@clerk/ui` (import `{ ui }` douteux dans `layout.tsx`, prop `ui` non standard de `ClerkProvider`), `react-icons` (lucide est utilisé partout). À purger.

---

## 5. Sécurité

1. **Token JWT en query string** (`getPhotoUrl` → `?token=...`) : le token de session Clerk complet finit dans l'historique navigateur, les logs Traefik/access logs, les en-têtes `Referer`, et `window.open(videoUrl)` l'expose dans un nouvel onglet. Préférer des **URLs signées courtes à usage unique** générées par le backend, ou des cookies pour `/uploads`.
2. **Clé admin en `localStorage`** (`flashback_admin_key`) : exfiltrable par toute XSS. Le CSP autorisant `'unsafe-inline'` pour les scripts, le risque est réel. Préférer un cookie httpOnly côté backend ou au minimum `sessionStorage` + protéger `/admin` par rôle Clerk (`publicMetadata.role === "admin"`) dans le middleware.
3. **CSP** (`next.config.ts`) : bonne base (HSTS, X-Frame-Options DENY ✅) mais `script-src 'unsafe-inline'` affaiblit tout. Migrer le JSON-LD vers des nonces ou accepter le hash. Noter aussi : `media-src` absent — les `<video src>` vers `/uploads` passent par `default-src 'self'` (OK tant que même domaine).
4. **IP du VPS exposée** dans `images.remotePatterns` (`http://148.230.116.52:8000`) : révèle l'origin derrière Traefik/Cloudflare et autorise du contenu en HTTP clair. À retirer en prod.
5. **Validation côté client** : type/taille de fichier vérifiés (JPEG/PNG/WebP, 20 Mo) ✅ — mais FAQ et page restore annoncent des limites contradictoires (FAQ : "TIFF, HEIC, 50 Mo" vs code : 20 Mo, pas de TIFF/HEIC).
6. Page `/cookies` documente un cookie `theme` (1 an) — en réalité le thème est en `localStorage`, et `auth_session` n'existe pas (cookies Clerk `__session`/`__client`). Le tableau cookies est **inexact**, risque RGPD documentaire.

---

## 6. SEO & Métadonnées

- **Conflit robots/sitemap (critique)** : `robots.ts` disallow `/dashboard/`, `/restore/`, `/animate/`, `/abonnement/` mais `sitemap.ts` les inclut tous. Google signalera "Indexed though blocked" / sitemap errors. Pire : `/restore` et `/animate` sont des **landing pages produit** vers lesquelles le blog fait des liens internes — les bloquer en robots sabote la stratégie SEO. Décision à prendre : indexer `/restore` et `/animate` (pages avec metadata complètes) et retirer `/dashboard`, `/bibliotheque`, `/abonnement/succes` du sitemap.
- **Pages sans métadonnées** : `about`, `privacy`, `cookies`, `conditions-utilisation`, `mentions-legales`, `credits` sont des client components sans `metadata` ni layout dédié → elles héritent du title générique du root layout. Ajouter un `layout.tsx` avec metadata par section, ou les convertir en Server Components.
- **JSON-LD dupliqué et contradictoire** : `layout.tsx` déclare `aggregateRating: 4.8/120` et `page.tsx` (home) `4.8/124` + deux blocs `SoftwareApplication` → risque de pénalité "self-serving reviews" et données structurées incohérentes. Garder un seul bloc, ou supprimer l'aggregateRating si non vérifiable.
- **OG images incohérentes** : root = `/og-image.png`, layouts animate/restore/dashboard = `/og-default.jpg`. Vérifier que les deux fichiers existent ; uniformiser.
- `canonical` présent uniquement sur le blog — l'ajouter au moins sur la home, `/restore`, `/about`.
- Blog : `generateStaticParams` + metadata article + canonical ✅ — la meilleure partie SEO du site. Manque un JSON-LD `Article`/`BlogPosting` par billet et `BreadcrumbList`.

---

## 7. Plan d'action priorisé

| Priorité | Problème | Fichier(s) | Impact | Effort |
|---|---|---|---|---|
| P0 | Routes protégées déclarées publiques dans le middleware | `src/middleware.ts` | Sécurité/UX : pas de redirection serveur, protection client only | 1h |
| P0 | Incohérence `coloriser` vs `colorize` (contrat API) | `lib/api.ts` | Fonctionnel : colorisation depuis la galerie probablement ignorée | 15 min |
| P0 | robots.ts ⟷ sitemap.ts contradictoires + `/restore` désindexé | `app/robots.ts`, `app/sitemap.ts` | SEO : pages produit invisibles, erreurs Search Console | 30 min |
| P0 | Icônes OAuth Clerk invisibles (pas de baseTheme dark) | `app/layout.tsx`, `sign-in/`, `sign-up/`, `Navbar.tsx` | Conversion : inscription quasi impossible | 30 min |
| P1 | Token JWT en query string sur `/uploads` | `lib/api.ts > getPhotoUrl` (+ backend) | Sécurité : fuite de session dans logs/referrer | 1-2 j (backend) |
| P1 | `useSearchParams` sans Suspense | `app/auth/page.tsx`, `app/restore/page.tsx` | Build/CSR bailout | 20 min |
| P1 | Slider comparaison souris uniquement | `restore/RestoreClient.tsx` | Mobile : feature clé cassée au tactile | 1h |
| P1 | `skipCache: true` à chaque getToken + token par image | `lib/api.ts`, `RestoreClient.tsx` | Perf : latence sur chaque appel API | 30 min |
| P1 | Miniatures dashboard sans token ni `unoptimized` | `dashboard/DashboardClient.tsx` | Images cassées sur le dashboard | 20 min |
| P1 | "My Application" dans l'UI Clerk | Clerk Dashboard (config) | Branding | 5 min |
| P2 | Rendu triple de `TravauxList` dans la modale admin | `admin/page.tsx` | Requêtes dupliquées, UI dupliquée | 20 min |
| P2 | `localStorage.__clerk_db_jwt` dans Pricing | `components/Pricing.tsx` | Achat de packs cassé en prod | 30 min |
| P2 | Erreurs avalées (bibliothèque) + faux fallback user (dashboard) | `BibliothequeClient.tsx`, `DashboardClient.tsx` | UX trompeuse en cas de panne | 2h |
| P2 | Pages légales client components sans metadata | `privacy/`, `cookies/`, `conditions-utilisation/`, `mentions-legales/`, `about/` | SEO + bundle | 3h |
| P2 | Clé admin en localStorage + admin non protégé par rôle | `admin/page.tsx`, `middleware.ts` | Sécurité | 2h |
| P3 | Dépendances mortes (`next-auth`, `@auth/core`, `react-icons`, `@clerk/ui`) | `package.json`, `layout.tsx` | Bundle, surface d'attaque | 1h |
| P3 | Fusion AuthContext / Clerk (double système) | `context/AuthContext.tsx` + tous les clients | Dette technique | 0,5 j |
| P3 | A11y modales (focus trap, Escape, aria) | `admin`, `OutOfCreditsModal`, `RgpdConsent`, galerie | Accessibilité | 0,5 j |
| P3 | JSON-LD dupliqué (ratings 120 vs 124), mentions légales `[À compléter]` | `layout.tsx`, `page.tsx`, `mentions-legales/page.tsx` | SEO + conformité légale | 1h |

---

## 8. Quick Wins (< 30 min chacun)

### 1. Thème dark Clerk global (bug icônes OAuth) — `app/layout.tsx`

```diff
 import { ClerkProvider } from "@clerk/nextjs";
-import { ui } from "@clerk/ui";
+import { dark } from "@clerk/themes";
 import { frFR } from "@clerk/localizations";
 ...
-        <ClerkProvider localization={frFR} ui={ui} domain="clerk.flashback-restore.com">
+        <ClerkProvider
+          localization={frFR}
+          domain="clerk.flashback-restore.com"
+          appearance={{
+            baseTheme: dark,
+            variables: { colorPrimary: "#f59e0b", colorBackground: "#1c1917" },
+            elements: {
+              socialButtonsBlockButton:
+                "border border-[#3a3a3a] bg-[#292524] text-white hover:bg-[#33302c]",
+            },
+          }}
+        >
```
(Le modal `SignInButton` du Navbar héritera automatiquement du thème — c'est lui le principal responsable du "blanc sur blanc".)

### 2. Aligner le champ colorisation — `lib/api.ts`

```diff
 export async function restoreFromLibrary(
   imageId: string, colorize: boolean, resolution: string
 ): Promise<{ jobId: string;