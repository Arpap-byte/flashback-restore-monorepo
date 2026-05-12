# Plan : 15 corrections post-audit — Flashback Restore

**Date :** 2026-05-12
**Objectif :** Corriger les 15 problèmes restants de l'audit (quick wins + P1 résiduels)
**Contexte :** 10 P0 majeurs déjà corrigés (ports, secrets, isolation systemd, headers Traefik, dépendances manquantes, DB URL). Restent des corrections de sécurité, code quality, et frontend.

---

## Phase 1 — P0 sécurité restants (3 corrections)

### 1. Retirer la clé Gemini du query string URL
- **Fichier :** `backend/app/services/gemini_service.py:230-231,263`
- **Problème :** L'appel colorisation passe `key=GEMINI_API_KEY` en query param → fuite dans les logs HTTP
- **Action :** Remplacer par le header `x-goog-api-key` avec `httpx`

### 2. Wrapper les appels Gemini sync dans `asyncio.to_thread`
- **Fichier :** `backend/app/services/gemini_service.py:74,180`
- **Problème :** `client.models.generate_content()` bloque l'event loop FastAPI
- **Action :** `await asyncio.to_thread(client.models.generate_content, ...)` sur tous les appels

### 3. Exiger STRIPE_WEBHOOK_SECRET au boot (pas de fallback)
- **Fichier :** `backend/app/config.py:57`
- **Problème :** `STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")` — un déploiement sans .env accepterait n'importe quel webhook
- **Action :** Supprimer le fallback, lever une exception si absent

---

## Phase 2 — P1 sécurité + robustesse (5 corrections)

### 4. Rate limiting sur les routes coûteuses
- **Fichier :** `backend/app/api/routes.py`
- **Problème :** `/restore`, `/analyze`, `/animate` n'ont pas de `@limiter.limit()` → explosion COGS Gemini
- **Action :** Ajouter `@limiter.limit("10/minute")` sur ces 3 routes

### 5. Sanitiser les noms de fichiers uploadés
- **Fichier :** `backend/app/api/routes.py` (upload dans analyser, restaurer, animer)
- **Problème :** `fichier.filename` utilisé tel quel → path traversal possible (`../../etc/passwd`)
- **Action :** `re.sub(r'[^\w.-]', '_', fichier.filename)[:80]` + magic bytes avec `python-magic`

### 6. Remplacer l'IP codée en dur par PUBLIC_BACKEND_URL
- **Fichiers :** `backend/app/api/routes.py:419`, `backend/app/config.py`
- **Problème :** `f"http://148.230.116.52:8000/uploads/{nom_fichier}"` bloque HTTPS et casse en dev
- **Action :** Ajouter `PUBLIC_BACKEND_URL` dans `.env` / `config.py`, utiliser partout

### 7. Retirer `localhost` des CORS en production
- **Fichier :** `backend/app/main.py:78-90`
- **Problème :** CORS autorise `http://localhost:3000` en prod → vol de session possible
- **Action :** Variable d'env `ALLOWED_ORIGINS`, n'inclure localhost que si `ENVIRONMENT=development`

### 8. Réponse générique sur l'inscription (anti-énumération)
- **Fichier :** `backend/app/api/auth.py:78`
- **Problème :** `409 "email déjà utilisé"` permet de découvrir les utilisateurs inscrits
- **Action :** Retourner 202 Accepted systématiquement avec message "Si l'email n'existe pas, un lien sera envoyé"

---

## Phase 3 — Code quality + refactoring (4 corrections)

### 9. Supprimer la route `/api/auth/me` dupliquée
- **Fichiers :** `backend/app/api/auth.py:191`, `backend/app/api/user.py:36`
- **Problème :** Deux routes `/me` quasi-identiques → risque de drift
- **Action :** Supprimer la version dans `auth.py`, garder uniquement `user.py`

### 10. Factoriser le parsing JSON Gemini dupliqué
- **Fichier :** `backend/app/services/gemini_service.py:86-115,200-228`
- **Problème :** Logique de nettoyage markdown + fallback regex dupliquée entre `analyser_photo()` et `obtenir_parametres_restauration()`
- **Action :** Extraire une fonction `_parse_json_gemini(texte: str) -> dict`

### 11. Cache simple pour `obtenir_plan_utilisateur`
- **Fichier :** `backend/app/db/queries.py` (ou `database.py`)
- **Problème :** Chaque requête frontend hit la DB pour le plan utilisateur
- **Action :** `functools.lru_cache(maxsize=128)` avec TTL 60 secondes via timestamp

### 12. Supprimer `react-icons`, utiliser exclusivement `lucide-react`
- **Fichier :** `landing/src/components/Footer.tsx` + `package.json`
- **Problème :** `react-icons` importé en entier pour 3 icônes → ~50 Ko inutiles
- **Action :** Remplacer par `lucide-react` (déjà installé), désinstaller `react-icons`

---

## Phase 4 — Frontend UX + performance (3 corrections)

### 13. Timeout et backoff sur le polling D-ID
- **Fichier :** `landing/src/app/animate/page.tsx:50-78`
- **Problème :** Polling 5s sans timeout max ni backoff → UX bloquée si panne externe
- **Action :** Timeout 2 minutes max, backoff exponentiel (5→8→12→20s), bouton "Reprendre" après timeout

### 14. Auto-dismiss des toasts d'erreur
- **Fichiers :** `landing/src/app/restore/page.tsx`, `landing/src/app/animate/page.tsx`
- **Problème :** Le toast d'erreur reste affiché jusqu'à clic manuel
- **Action :** `setTimeout(() => setError(null), 6000)` après affichage

### 15. `next.config.ts` : ajouter le domaine de production + remplacer `<img>` par `<Image>`
- **Fichiers :** `landing/next.config.ts`, `Hero.tsx`, `restore/page.tsx`, `animate/page.tsx`, `dashboard/page.tsx`
- **Problème :** `remotePatterns` sans `flashback-restore.com` → images cassées + pas de lazy loading natif
- **Action :** Ajouter `{ protocol: "https", hostname: "flashback-restore.com" }` dans remotePatterns + remplacer `<img>` par `<Image>` avec `loading="lazy"`

---

## Ordre d'exécution recommandé

| Ordre | # | Correction | Temps estimé | Impact |
|-------|---|-----------|-------------|--------|
| 1 | 3 | STRIPE_WEBHOOK_SECRET mandatory | 5 min | Sécurité |
| 2 | 1 | Clé Gemini dans query string | 10 min | Sécurité |
| 3 | 2 | Gemini sync → asyncio.to_thread | 10 min | Perf/Sécurité |
| 4 | 6 | PUBLIC_BACKEND_URL | 10 min | Config |
| 5 | 5 | Sanitiser filename + magic bytes | 15 min | Sécurité |
| 6 | 4 | Rate limiting /restore /animate | 10 min | Sécurité/COGS |
| 7 | 7 | CORS localhost en prod | 10 min | Sécurité |
| 8 | 8 | Anti-énumération /register | 5 min | Privacy |
| 9 | 9 | Supprimer /me dupliqué | 5 min | Code quality |
| 10 | 10 | Factoriser parsing Gemini | 15 min | Code quality |
| 11 | 11 | Cache plan utilisateur | 10 min | Performance |
| 12 | 12 | Supprimer react-icons | 10 min | Performance |
| 13 | 13 | Timeout polling D-ID | 15 min | UX |
| 14 | 14 | Auto-dismiss toast | 5 min | UX |
| 15 | 15 | next.config.ts + <Image> | 20 min | Perf/SEO |

**Total estimé :** ~2h30

---

## Fichiers modifiés par phase

| Fichier | Corrections |
|---------|------------|
| `backend/app/config.py` | #3, #6 |
| `backend/app/services/gemini_service.py` | #1, #2, #10 |
| `backend/app/api/routes.py` | #4, #5, #6 |
| `backend/app/main.py` | #7 |
| `backend/app/api/auth.py` | #8, #9 |
| `backend/app/api/user.py` | #9 (garde /me) |
| `backend/app/db/queries.py` | #11 |
| `backend/.env` | #6 (ajout PUBLIC_BACKEND_URL) |
| `landing/package.json` | #12 |
| `landing/src/components/Footer.tsx` | #12 |
| `landing/src/app/animate/page.tsx` | #13, #14 |
| `landing/src/app/restore/page.tsx` | #14 |
| `landing/next.config.ts` | #15 |
| `landing/src/components/Hero.tsx` | #15 |
| `landing/src/app/dashboard/page.tsx` | #15 |

## Validation

- Après chaque phase : `systemctl restart flashback-backend` + `curl https://flashback-restore.com/api/health`
- Après corrections frontend : rebuild `landing` + `systemctl restart flashback-landing`
- Vérifier qu'aucun 500/502 n'apparaît
- Tester un upload (sanitization filename)
- Tester le polling D-ID avec timeout simulé
