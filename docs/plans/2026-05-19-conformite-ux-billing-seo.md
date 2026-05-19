# Plan d'Amélioration Flashback Restore — Conformité, UX, Billing, SEO

> **Source :** Email de Seb du 19/05/2026
> **Plan créé :** 19/05/2026

**Goal:** Mettre Flashback Restore en conformité légale, améliorer l'UX, implémenter le billing hybride, et optimiser le SEO.

**Architecture:** Modifications full-stack (Next.js frontend + FastAPI backend + PostgreSQL). Chaque priorité est indépendante et peut être déployée séparément.

---

## Priorité 1 : Conformité Légale & Corrections Critiques

### Tâche 1.1 : Créer la page /conditions-utilisation (redirection depuis /terms)
**Files:** `landing/src/app/conditions-utilisation/page.tsx` (nouveau), `landing/src/app/terms/page.tsx` (garder comme fallback)
**Action:** Créer une page dédiée /conditions-utilisation avec le contenu existant des CGU, rediriger /terms vers /conditions-utilisation

### Tâche 1.2 : Créer la page "Mentions Légales"
**Files:** `landing/src/app/mentions-legales/page.tsx` (nouveau), `landing/src/components/Footer.tsx` (modifier)
**Contenu:** SIRET, adresse siège social, capital social, hébergeur (Hostinger), contact DPO
**Footer:** Mettre à jour le lien "Mentions légales" → /mentions-legales

### Tâche 1.3 : Ajouter case à cocher CGV + renonciation rétractation dans le checkout
**Files:** `backend/app/services/stripe_service.py` (modifier), `landing/src/components/Pricing.tsx` (modifier)
**Backend:** Ajouter `metadata` dans la session Stripe pour tracer l'acceptation
**Frontend:** Créer une page de checkout intermédiaire avec checkbox CGV + renonciation

### Tâche 1.4 : Bouton de résiliation "en 3 clics"
**Files:** `landing/src/app/dashboard/` (modifier), `backend/app/api/user.py` (nouvel endpoint)
**Implémentation:** 
- Bouton "Résilier mon abonnement" dans le dashboard
- Confirmation modale
- Appel API → backend appelle Stripe `cancel_subscription`
- Route: `POST /api/user/cancel-subscription`

### Tâche 1.5 : Consentement RGPD avant upload
**Files:** `landing/src/app/restore/RestoreClient.tsx`, `landing/src/app/animate/AnimateClient.tsx`
**Implémentation:** Modale de consentement granulaire (traitement biométrique) avant premier upload

---

## Priorité 2 : UX & Frontend

### Tâche 2.1 : Slider Avant/Après sur la homepage
**Files:** `landing/src/components/Hero.tsx` (modifier), nouveau composant `BeforeAfterSlider.tsx`
**Implémentation:** Image de démo avec slider drag pour montrer l'effet

### Tâche 2.2 : Drag & Drop immédiat depuis la homepage
**Files:** `landing/src/app/page.tsx`, `landing/src/components/Hero.tsx`
**Implémentation:** Zone drag-drop dans le Hero → redirige vers /restore avec l'image en session

### Tâche 2.3 : Système de filigrane (watermark)
**Files:** `backend/app/services/gemini_service.py` (modifier)
**Implémentation:** Pour les utilisateurs gratuits, appliquer watermark semi-transparent sur l'image restaurée

### Tâche 2.4 : Badges éthiques IA
**Files:** `landing/src/app/historique/`, `landing/src/app/dashboard/`
**Implémentation:** Icônes discrètes "✨ restauré par IA", "🎬 animé par IA"

### Tâche 2.5 : Métadonnées personnalisées dans la galerie
**Files:** `backend/app/models/db_models.py` (modifier), `backend/app/db/queries.py`, `backend/app/api/user.py`, frontend galerie
**Implémentation:** Champs titre, date_prise, lieu sur les travaux

---

## Priorité 3 : Billing Hybride & Buckets

### Tâche 3.1 : Modèle de crédits par buckets
**Files:** `backend/app/models/db_models.py` (nouvelle table), `backend/app/db/queries.py` (refonte)
**Tables:**
- `credits_buckets`: id, utilisateur_id, type (subscription/one_time/bonus), quantite, expire_le, priorite
- `consommation_credits` modifié: + bucket_id

### Tâche 3.2 : Logique de consommation par priorité
**Files:** `backend/app/db/queries.py` (consommer_credit réécrit)
**Ordre:** Seau 1 (abonnement, expire) → Seau 2 (packs, n'expire pas) → Seau 3 (bonus)

### Tâche 3.3 : Stripe Checkout pour packs de crédits
**Files:** `backend/app/services/stripe_service.py`, `backend/app/api/routes.py`
**Implémentation:** Nouveau endpoint `POST /api/stripe/create-credit-pack-session`, prix variables

### Tâche 3.4 : Tarification abonnés (réduction sur packs)
**Files:** `backend/app/services/stripe_service.py`
**Implémentation:** Détection plan actif → coupon 10-20% via Stripe

### Tâche 3.5 : Renouvellement mensuel des crédits abonnement
**Files:** `backend/app/services/stripe_service.py` (webhook)
**Implémentation:** Webhook `invoice.paid` → créditer le bucket subscription, expirer l'ancien

---

## Priorité 4 : SEO & Désambiguïsation

### Tâche 4.1 : Mise à jour des métadonnées SEO
**Files:** `landing/src/app/layout.tsx`, `landing/src/app/page.tsx`, `landing/src/components/Hero.tsx`
**Keywords à ajouter:** "photo", "image", "colorisation", "retouche photo", "restauration image"
**Title:** "Flashback Restore — Restauration et colorisation de photos par IA"

### Tâche 4.2 : Balises alt et contenu sémantique
**Files:** Toutes les pages avec images
**Action:** Ajouter alt="Photo restaurée par IA" etc.

---

## Ordre d'exécution recommandé

1. **Priorité 1** (bloquant lancement) → aujourd'hui
2. **Priorité 2** (UX critique) → cette semaine
3. **Priorité 3** (billing refonte) → cette semaine (backend lourd)
4. **Priorité 4** (SEO) → en parallèle
