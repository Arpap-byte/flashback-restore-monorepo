# Finalisation NextAuth.js — Plan d'implémentation

> **Pour Hermes:** Utilise `subagent-driven-development` pour exécuter ce plan tâche par tâche.

**Goal:** Rendre le flux d'authentification Google/Facebook fonctionnel de bout en bout (frontend NextAuth → backend FastAPI).

**Architecture:** NextAuth.js v5 gère l'OAuth (Google, Facebook). Dans le callback `session()`, il encode un JWT avec `jose` (secret partagé `AUTH_SECRET`). Le frontend envoie ce JWT dans `Authorization: Bearer`. Le backend le décode avec le même secret et crée/reconnaît l'utilisateur.

**Tech Stack:** NextAuth v5 beta, jose, FastAPI, PyJWT, HS256

---

### Contexte

Le code est déjà écrit mais les variables d'environnement et la config OAuth sont manquantes. Fichiers concernés :

- `landing/src/auth.ts` — config NextAuth ✅
- `landing/src/middleware.ts` — protection routes ✅
- `landing/src/app/api/auth/[...nextauth]/route.ts` — handler ✅
- `backend/app/auth.py` — support double secret + création auto ✅
- `landing/src/lib/api.ts` — getAuthHeader() async ✅

---

### Task 1: Configurer les variables d'environnement NextAuth

**Objective:** Ajouter les variables requises pour NextAuth dans `.env.local` et `.env`

**Files:**
- Create: `landing/.env.local`
- Modify: `/root/flashback-restore-monorepo/.env` (ajouter placeholders)

**Step 1: Créer `.env.local` pour Next.js**

```bash
# landing/.env.local
NEXTAUTH_URL=http://localhost:8001
NEXTAUTH_SECRET=change-me-32-chars-minimum

# Google OAuth (à remplacer par les vraies clés)
AUTH_GOOGLE_ID=your-google-client-id.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=your-google-client-secret

# Facebook OAuth (à remplacer par les vraies clés)
AUTH_FACEBOOK_ID=your-facebook-app-id
AUTH_FACEBOOK_SECRET=your-facebook-app-secret

# Secret partagé avec le backend
AUTH_SECRET=same-as-in-root-env
```

**Step 2: Ajouter les placeholders dans `.env` racine**

Ajouter dans `/root/flashback-restore-monorepo/.env` :
```
# NextAuth
AUTH_GOOGLE_ID=your-google-client-id
AUTH_GOOGLE_SECRET=your-google-client-secret
AUTH_FACEBOOK_ID=your-facebook-app-id
AUTH_FACEBOOK_SECRET=your-facebook-app-secret
```

**Vérification:** `grep AUTH_ /root/flashback-restore-monorepo/.env` montre les 5 variables

---

### Task 2: Vérifier le path alias TypeScript

**Objective:** S'assurer que `@/auth` résout vers `src/auth.ts`

**Files:**
- Read: `landing/tsconfig.json`

**Step 1: Vérifier tsconfig.json**

```bash
grep -A5 '"@/' landing/tsconfig.json
```

Attendu : `"@/*": ["./src/*"]` dans `compilerOptions.paths`

**Step 2: Si absent, ajouter**

```json
"paths": {
  "@/*": ["./src/*"]
}
```

**Vérification:** Le middleware et le route handler utilisent `import { auth } from "@/auth"` et `import { handlers } from "@/auth"` — si le build passe, le path est correct.

---

### Task 3: Ajouter NEXTAUTH_URL dans l'environnement de prod

**Objective:** Configurer l'URL canonique pour que NextAuth génère les bons callbacks

**Files:**
- Modify: `landing/.env.local`

**Step 1: En local/dev**

```bash
NEXTAUTH_URL=http://localhost:8001
```

**Step 2: En production** (à ajuster selon le domaine)

```bash
NEXTAUTH_URL=https://flashback-restore.com
```

**Vérification:** La page `/auth` charge sans erreur. Le bouton Google redirige vers `https://accounts.google.com/o/oauth2/...` avec le bon `redirect_uri`.

---

### Task 4: Synchroniser AUTH_SECRET entre .env et .env.local

**Objective:** Le même secret doit être utilisé par NextAuth (pour signer le JWT) et par le backend (pour le vérifier)

**Files:**
- Read: `/root/flashback-restore-monorepo/.env`
- Write: `landing/.env.local`

**Step 1: Récupérer la valeur de AUTH_SECRET**

```bash
grep AUTH_SECRET /root/flashback-restore-monorepo/.env
```

**Step 2: La copier dans `.env.local`**

```
AUTH_SECRET=<même valeur que dans .env racine>
```

**Vérification:** Les deux fichiers ont la même valeur pour `AUTH_SECRET`.

---

### Task 5: Vérifier le build et corriger les erreurs

**Objective:** S'assurer que le frontend compile sans erreur avec NextAuth

**Files:**
- Terminal: `cd landing && npm run build 2>&1`

**Step 1: Lancer le build**

```bash
cd /root/flashback-restore-monorepo/landing
npm run build 2>&1 | tail -30
```

**Step 2: Corriger les erreurs si nécessaire**

Erreurs possibles :
- `Module not found: @/auth` → vérifier tsconfig paths (Task 2)
- `AUTH_GOOGLE_ID is required` → vérifier .env.local (Task 1)
- `jose not found` → `npm install jose`

**Vérification:** `npm run build` termine avec succès (exit 0).

---

### Task 6: Redémarrer les services et tester

**Objective:** Redémarrer le landing et tester que la page /auth s'affiche correctement

**Files:**
- Terminal: restart services

**Step 1: Redémarrer le landing**

```bash
systemctl restart flashback-landing
sleep 3
curl -s --connect-timeout 3 http://localhost:8001/auth | head -20
```

**Vérification:** La page `/auth` retourne du HTML contenant "Continuer avec Google".

---

### Task 7: Guide de création des apps OAuth (pour l'utilisateur)

**Objective:** Fournir à Seb les instructions pour créer les apps Google et Facebook

**Step 1: Google Cloud Console**

```
1. Aller sur https://console.cloud.google.com/apis/credentials
2. Créer un projet "Flashback Restore"
3. Configurer l'écran de consentement OAuth (externe, email utilisateur + profil)
4. Créer un ID client OAuth 2.0 (type: Application Web)
5. URI de redirection autorisés:
   - http://localhost:8001/api/auth/callback/google
   - https://flashback-restore.com/api/auth/callback/google
6. Copier Client ID et Client Secret dans .env.local:
   AUTH_GOOGLE_ID=<client-id>
   AUTH_GOOGLE_SECRET=<client-secret>
```

**Step 2: Facebook Developers**

```
1. Aller sur https://developers.facebook.com/apps
2. Créer une app "Flashback Restore" (type: Consommateur)
3. Ajouter le produit "Facebook Login" (Web)
4. URI de redirection OAuth valides:
   - http://localhost:8001/api/auth/callback/facebook
   - https://flashback-restore.com/api/auth/callback/facebook
5. Copier App ID et App Secret dans .env.local:
   AUTH_FACEBOOK_ID=<app-id>
   AUTH_FACEBOOK_SECRET=<app-secret>
```

**Step 3: Une fois les clés obtenues**

```bash
# Redémarrer le landing
systemctl restart flashback-landing
# Tester la connexion sur /auth
```

---

### Task 8: Commit final

```bash
git add landing/.env.local landing/src/auth.ts landing/src/middleware.ts landing/src/app/api/auth/
git add .env
git commit -m "feat: finalisation config NextAuth — Google/Facebook OAuth prêt"
```
