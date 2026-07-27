# Plan d'action Flashback Restore — Audit complet 27/07/2026

> **Pour Hermes :** Exécuter ce plan tâche par tâche. Chaque tâche = 1 commit.

**Objectif :** Corriger les bugs identifiés lors de l'audit complet du site Flashback Restore, priorité #1 aux icônes Clerk cassées.

**Architecture :** Monorepo Next.js + FastAPI. Auth Clerk production (domaine primaire `clerk.flashback-restore.com`). Déploiement via systemd sur VPS Hostinger.

---

## 🔍 Résumé de l'audit

| Vérification | Statut |
|---|---|
| Services systemd (backend, landing, arq-worker) | ✅ Tous actifs |
| API health (gemini, db, stripe, b2) | ✅ Tout disponible |
| Pages publiques (/, /sign-in, /sign-up, /credits) | ✅ HTTP 200 |
| Pages protégées (/restore, /dashboard, /bibliotheque) | ✅ 307 → /sign-in |
| Middleware Clerk | ✅ NextResponse.redirect OK |
| CSP headers | ✅ img.clerk.com inclus |
| CLERK_ISSUER / CLERK_JWKS_URL | ✅ Configurés, JWKS accessible |
| API credit-packs | ✅ Fonctionnel |
| DB utilisateurs | ✅ 11 utilisateurs, 3 premium |

---

## 🔴 P0 — Icônes Clerk invisibles (boîtes vides)

**Cause racine :** Le `<ClerkProvider>` dans `layout.tsx` a un bloc `elements` incomplet. Les pages `/sign-in` et `/sign-up` définissent `socialButtonsBlockButton`, `socialButtonsBlockButtonText`, `providerIcon__google`, `providerIcon__facebook`, `providerIcon__tiktok` — mais le `ClerkProvider` global **ne les a pas**. Résultat : le modal sign-in ouvert depuis la Navbar (qui utilise le ClerkProvider global) affiche les boutons sociaux sans style → icônes invisibles.

### Tâche 1 : Ajouter les éléments manquants au ClerkProvider dans layout.tsx

**Fichier :** `landing/src/app/layout.tsx`

**Action :** Dans le bloc `elements` du `ClerkProvider` (ligne 105-110), ajouter les 5 éléments manquants :

```tsx
elements: {
  card: "border border-[#292524] shadow-2xl",
  formButtonPrimary: "bg-[#f59e0b] hover:bg-[#d97706] text-black font-semibold",
  footerActionLink: "text-[#f59e0b] hover:text-[#d97706]",
  providerIcon: "w-5 h-5",
  // ✅ AJOUTER CES 5 LIGNES :
  socialButtonsBlockButton:
    "border border-[#3a3a3a] bg-[#292524] text-white hover:bg-[#33302c] rounded-lg",
  socialButtonsBlockButtonText: "text-white font-medium",
  providerIcon__google: "filter-none",
  providerIcon__facebook: "filter-none",
  providerIcon__tiktok: "brightness-0 invert",
},
```

**Vérification :** Rebuild + restart landing :
```bash
cd /opt/flashback-restore-monorepo/landing && npm run build && chown -R flashback:flashback .next && systemctl restart flashback-landing
```

Puis tester visuellement sur https://flashback-restore.com → cliquer "Connexion" dans la navbar → les icônes Google/Facebook/TikTok doivent être visibles.

---

## 🟡 P1 — ENFORCE_CONSENT désactivé en production

**Cause :** `ENFORCE_CONSENT` n'est pas défini dans `/etc/flashback/.env` → valeur par défaut `false` → les checkouts Stripe passent sans vérifier les consentements RGPD côté backend. Les checkboxes sont présentées côté frontend (UI) mais le backend les ignore.

### Tâche 2 : Activer ENFORCE_CONSENT en production

**Fichier :** `/etc/flashback/.env`

**Action :** Ajouter la ligne :
```bash
ENFORCE_CONSENT=true
```

**Vérification :**
```bash
systemctl restart flashback-backend
curl -s http://localhost:8000/api/health
```

---

## 🟡 P2 — Table `abonnements` vide en production

**Contexte :** Les 3 utilisateurs premium (seb, nicolas, rija) n'ont **aucune ligne** dans `abonnements`. La table est vide. Conséquences :
- Le portail client Stripe est cassé (pas de `stripe_customer_id`)
- Le job de relances plante (cherche `Utilisateur.stripe_customer_id`)
- Si les abonnements expirent, `subscription.deleted` ne rétrogradera personne

**Note :** Les 3 utilisateurs ont été promus manuellement (pas via Stripe). Leurs abonnements expirent le 15 juin 2026 → déjà passés. Aucune souscription Stripe active.

### Tâche 3 : Rétrograder les utilisateurs premium expirés en gratuit

**Fichier :** Base de données PostgreSQL (`flashback-db`)

**Action :**
```sql
UPDATE utilisateurs SET plan = 'gratuit', est_abonne = 0 WHERE plan = 'premium';
```

**Vérification :**
```bash
docker exec flashback-db psql -U flashback -d flashback -c "SELECT id, email, plan, est_abonne FROM utilisateurs WHERE email IN ('sebastien.archeny@gmail.com', 'nicolas.archeny@live.com', 'rija.rkt@gmail.com');"
```

---

## 🟢 P3 — Points vérifiés OK (pas d'action requise)

| Composant | Statut | Détail |
|---|---|---|
| Middleware redirect | ✅ | `NextResponse.redirect` OK, pas de 404 |
| isPublicRoute | ✅ | `/credits` inclus, `/restore`/`/dashboard`/`/bibliotheque` protégés |
| CLERK_ISSUER / JWKS | ✅ | `clerk.flashback-restore.com`, JWKS HTTP 405 (normal) |
| CSP | ✅ | `img.clerk.com` autorisé en `style-src` et `img-src` |
| NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL | ✅ | `/bibliotheque` dans `.env.local` |
| colorNeutral | ✅ | `#78716c` partout (pas blanc) |
| @clerk/ui | ✅ | Importé + passé au ClerkProvider |
| socialButtonsBlockButton | ✅ | Sur sign-in et sign-up (manquant dans layout.tsx → corrigé Tâche 1) |
| providerIcon__google/facebook/tiktok | ✅ | Sur sign-in et sign-up (manquant dans layout.tsx → corrigé Tâche 1) |
| robots.ts | ✅ | `/restore` et `/animate` autorisés (plus dans disallow) |
| API coloriser vs colorize | ✅ | Aligné sur `coloriser` |

---

## 📋 Ordre d'exécution

1. **Tâche 1** — Fix icônes Clerk (P0, critique utilisateur)
2. **Tâche 2** — Activer ENFORCE_CONSENT (P1, conformité RGPD)
3. **Tâche 3** — Rétrograder premium expirés (P2, intégrité données)

---

*Plan généré par audit automatisé le 27/07/2026.*
