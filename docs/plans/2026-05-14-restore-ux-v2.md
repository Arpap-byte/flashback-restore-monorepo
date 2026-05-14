# Restore UX + Pricing V2 — Plan d'Implémentation

> **Pour Hermes :** Utiliser `delegate_task` pour implémenter chaque tâche, avec Sonnet en orchestration et DeepSeek en implémentation.

**Objectif :** Ajouter le choix de résolution (720p/1080p/4K) et la colorisation avant validation de la restauration, mettre à jour la grille tarifaire, augmenter le coût des animations, et corriger le bug des images fraîchement générées.

**Architecture :** 
- Frontend : page `/restore` — nouveau panneau d'options (résolution + colorisation) avant le bouton "Restaurer"
- Backend : endpoint `/api/restore` accepte `resolution` + `coloriser`, endpoint `/api/animate` accepte `resolution`
- Pricing : constantes centralisées dans `routes.py` + `credits.py`

**Tech Stack :** Next.js 15 (app router), FastAPI, SQLite, ARQ, Tailwind CSS

---

## Phase 1 — Restore page UX (frontend)

### Tâche 1.1 : Ajouter le state `resolution` au composant RestorePage

**Fichiers :**
- Modifier : `landing/src/app/restore/page.tsx`

**Code :** Ajouter après `const [colorize, setColorize] = useState(false);`

```typescript
type Resolution = "720p" | "1080p" | "4k";
const [resolution, setResolution] = useState<Resolution>("720p");
```

### Tâche 1.2 : Remplacer le checkbox "Coloriser" par un panneau d'options complet

**Fichiers :**
- Modifier : `landing/src/app/restore/page.tsx` (lignes ~405-421)

**Code :** Remplacer le bloc `{!restoreResult && !restoring && (...)}` (la checkbox actuelle) par :

```tsx
{/* Panneau d'options de traitement */}
{!restoreResult && !restoring && (
  <div className="max-w-xl mx-auto mb-6">
    {/* Photo preview */}
    <div className="relative w-full rounded-2xl overflow-hidden bg-surface border border-card-border mb-4">
      <Image
        src={preview}
        alt="Photo à restaurer"
        width={800}
        height={600}
        className="w-full h-auto object-contain"
        unoptimized
      />
    </div>

    {/* Options */}
    <div className="bg-card border border-card-border rounded-2xl p-5 space-y-5">
      {/* Résolution */}
      <div>
        <Label icon={Zap} label="Résolution" />
        <div className="grid grid-cols-3 gap-2 mt-2">
          {([
            { key: "720p", label: "720p", credits: 1, desc: "Standard" },
            { key: "1080p", label: "1080p", credits: 2, desc: "Haute déf." },
            { key: "4k", label: "4K", credits: 4, desc: "Ultra HD" },
          ] as const).map(({ key, label, credits, desc }) => (
            <button
              key={key}
              onClick={() => setResolution(key)}
              className={`p-3 rounded-xl border text-center transition-all ${
                resolution === key
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-card-border text-muted hover:border-accent/30"
              }`}
            >
              <div className="text-sm font-semibold">{label}</div>
              <div className="text-xs text-muted">{desc}</div>
              <div className="text-xs mt-1 font-medium">
                {credits} crédit{credits > 1 ? "s" : ""}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Colorisation */}
      <div>
        <Label icon={Palette} label="Colorisation" />
        <button
          onClick={() => setColorize(!colorize)}
          className={`w-full mt-2 p-3 rounded-xl border text-left transition-all flex items-center justify-between ${
            colorize
              ? "border-orange-400 bg-orange-400/10 text-orange-400"
              : "border-card-border text-muted hover:border-orange-400/30"
          }`}
        >
          <div>
            <div className="text-sm font-semibold">
              {colorize ? "Colorisation activée" : "Ajouter la colorisation"}
            </div>
            <div className="text-xs text-muted">
              +{resolution === "4k" ? "4" : resolution === "1080p" ? "2" : "1"} crédit{resolution === "4k" || resolution === "1080p" ? "s" : ""}
            </div>
          </div>
          <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
            colorize ? "border-orange-400 bg-orange-400" : "border-card-border"
          }`}>
            {colorize && <Check className="w-3 h-3 text-white" />}
          </div>
        </button>
      </div>

      {/* Récapitulatif */}
      <div className="bg-surface rounded-xl p-3 flex items-center justify-between">
        <span className="text-sm text-muted">Total</span>
        <span className="text-sm font-semibold text-foreground">
          {getCreditTotal(resolution, colorize)} crédit{getCreditTotal(resolution, colorize) > 1 ? "s" : ""}
        </span>
      </div>
    </div>

    {/* Boutons */}
    <div className="flex gap-3 mt-4 justify-center">
      <button onClick={handleClear} className="px-5 py-2.5 rounded-full border border-card-border text-muted hover:text-foreground text-sm transition-all">
        <X className="w-4 h-4 inline mr-1.5" />
        Annuler
      </button>
      <button onClick={handleRestore} className="px-6 py-2.5 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-sm hover:brightness-110 transition-all flex items-center gap-2">
        <Sparkles className="w-4 h-4" />
        Restaurer ({getCreditTotal(resolution, colorize)} crédit{getCreditTotal(resolution, colorize) > 1 ? "s" : ""})
      </button>
    </div>
  </div>
)}
```

### Tâche 1.3 : Ajouter la fonction `getCreditTotal` et les imports manquants

**Fichiers :**
- Modifier : `landing/src/app/restore/page.tsx`

**Imports à ajouter :**
```typescript
import { Check } from "lucide-react"; // ajouter à l'import existant
```

**Fonction :** Ajouter avant `export default function RestorePage()` :

```typescript
function getCreditTotal(resolution: string, colorize: boolean): number {
  const base = resolution === "4k" ? 4 : resolution === "1080p" ? 2 : 1;
  const colorExtra = resolution === "4k" ? 4 : resolution === "1080p" ? 2 : 1;
  return base + (colorize ? colorExtra : 0);
}
```

### Tâche 1.4 : Ajouter le composant `Label`

**Fichiers :**
- Modifier : `landing/src/app/restore/page.tsx`

**Code :** Ajouter AVANT `export default function RestorePage()` :

```typescript
function Label({ icon: Icon, label }: { icon: React.ComponentType<{ className?: string }>, label: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="w-4 h-4 text-accent" />
      <span className="text-sm font-medium text-foreground">{label}</span>
    </div>
  );
}
```

### Tâche 1.5 : Mettre à jour `handleRestore` pour passer `resolution`

**Fichiers :**
- Modifier : `landing/src/app/restore/page.tsx`

**Changement :** Dans `handleRestore`, remplacer `restorePhoto(file, colorize)` par :

```typescript
const { jobId, travailId } = await restorePhoto(file, colorize, resolution);
```

### Tâche 1.6 : Mettre à jour le type `restorePhoto` dans l'API client

**Fichiers :**
- Modifier : `landing/src/lib/api.ts`

**Code :** Remplacer la signature de `restorePhoto` :

```typescript
export async function restorePhoto(file: File, colorize?: boolean, resolution?: string): Promise<RestoreJobResponse> {
  const formData = new FormData();
  formData.append("fichier", file);
  if (colorize) formData.append("coloriser", "true");
  if (resolution) formData.append("resolution", resolution);
  return apiFetch<RestoreJobResponse>("/api/restore", {
    method: "POST",
    body: formData,
  }, 30000);
}
```

---

## Phase 2 — Backend pricing + resolution

### Tâche 2.1 : Ajouter la constante de pricing

**Fichiers :**
- Modifier : `backend/app/api/routes.py`

**Code :** Ajouter en haut du fichier, après les imports :

```python
# Grille tarifaire — résolutions et crédits
TARIF_RESTAURATION: dict[str, int] = {
    "720p": 1,
    "1080p": 2,
    "4k": 4,
}
TARIF_COLORISATION: dict[str, int] = {
    "720p": 1,
    "1080p": 2,
    "4k": 4,
}
TARIF_ANIMATION: dict[str, int] = {
    "720p": 10,
    "1080p": 20,
}
```

### Tâche 2.2 : Mettre à jour l'endpoint `/restore` pour accepter `resolution`

**Fichiers :**
- Modifier : `backend/app/api/routes.py` (~ligne 860-945)

**Changements :**
1. Ajouter `resolution: str = Form("720p")` aux paramètres
2. Remplacer le calcul de `nb_credits_total` :

```python
    # Valider la résolution
    if resolution not in TARIF_RESTAURATION:
        raise HTTPException(status_code=400, detail=f"Résolution invalide : {resolution}. Options : 720p, 1080p, 4k")
    
    nb_credits_total = TARIF_RESTAURATION[resolution]
    if coloriser:
        nb_credits_total += TARIF_COLORISATION[resolution]
```

3. Ajouter `resolution` dans le `resultat_json` :

```python
    await mettre_a_jour_travail(
        travail_id,
        resultat_json=json.dumps({"arq_job_id": job.job_id, "coloriser": coloriser, "resolution": resolution}),
    )
```

4. Passer `resolution` au worker :
```python
    job = await pool.enqueue_job(
        'restauration_job',
        utilisateur["id"],
        str(chemin_original),
        coloriser,
        travail_id,
        nb_credits_total,
        resolution,  # nouvel argument
    )
```

### Tâche 2.3 : Mettre à jour l'endpoint `/colorize` pour accepter `resolution`

**Fichiers :**
- Modifier : `backend/app/api/routes.py` (~ligne 964-1030)

**Changements :** Ajouter `resolution: str = Form("720p")` et utiliser `TARIF_COLORISATION[resolution]` pour `nb_credits_total`.

### Tâche 2.4 : Mettre à jour l'endpoint `/animate` pour la nouvelle tarification

**Fichiers :**
- Modifier : `backend/app/api/routes.py` (~ligne 1050-1100)

**Changements :**
1. Remplacer le crédit fixe par `TARIF_ANIMATION.get(resolution, 10)`
2. Accepter `resolution: str = Form("720p")`

### Tâche 2.5 : Mettre à jour le worker ARQ pour accepter `resolution`

**Fichiers :**
- Modifier : `backend/app/worker.py`

**Changements :** Ajouter `resolution: str = "720p"` à `restauration_job()` et `colorisation_job()`, et passer la résolution au service de traitement.

---

## Phase 3 — Bugfix : image fraîchement générée

### Tâche 3.1 : Diagnostiquer le bug

**Problème :** Quand on restaure une photo puis qu'on clique sur "Coloriser" ou "Animer", l'image restaurée est fetchée via l'URL avec token. Si le token expire ou si l'URL est mal formée, l'opération échoue.

**Vérification :** 
```bash
curl -I "https://flashback-restore.com/uploads/xxx_restaure.jpg?token=..."
```

### Tâche 3.2 : Améliorer la robustesse du fetch d'image restaurée

**Fichiers :**
- Modifier : `landing/src/app/restore/page.tsx` (handleColorize, ~ligne 220-245)
- Modifier : `landing/src/lib/api.ts` (getPhotoUrlAsync)

**Changement :** Dans `handleColorize`, si le fetch de `restoredUrl` échoue, réessayer avec `getPhotoUrlAsync` pour rafraîchir le token :

```typescript
const handleColorize = async () => {
    if (!file || !restoreResult || !restoredUrl) return;
    setColorizing(true);
    setError(null);
    try {
      let res = await fetch(restoredUrl);
      // F7 + F8: Si l'URL avec token a expiré, rafraîchir le token
      if (!res.ok && res.status === 401) {
        const freshUrl = await getPhotoUrlAsync(restoreResult.url_image);
        res = await fetch(freshUrl);
      }
      if (!res.ok) {
        throw new Error(`Impossible de récupérer l'image restaurée (${res.status}).`);
      }
      // ... suite inchangée
```

---

## Phase 4 — Animation page pricing

### Tâche 4.1 : Ajouter le sélecteur de résolution sur la page `/animate`

**Fichiers :**
- Modifier : `landing/src/app/animate/page.tsx`

**Code :** Ajouter un sélecteur de résolution (720p/1080p) avec affichage du coût :

```tsx
const ANIMATION_COST: Record<string, number> = { "720p": 10, "1080p": 20 };
const [animResolution, setAnimResolution] = useState<string>("720p");
```

Dans le panneau de comportement, ajouter :
```tsx
<div className="grid grid-cols-2 gap-2">
  <button onClick={() => setAnimResolution("720p")} className={...}>
    720p · 10 crédits
  </button>
  <button onClick={() => setAnimResolution("1080p")} className={...}>
    1080p · 20 crédits
  </button>
</div>
```

### Tâche 4.2 : Passer la résolution à l'API animate

**Fichiers :**
- Modifier : `landing/src/lib/api.ts`

```typescript
export async function animatePhoto(file: File, comportement: string = "naturel", resolution: string = "720p"): Promise<AnimateResult> {
  const formData = new FormData();
  formData.append("fichier", file);
  formData.append("comportement", comportement);
  formData.append("resolution", resolution);
  return apiFetch<AnimateResult>("/api/animate", { method: "POST", body: formData }, 30000);
}
```

---

## Phase 5 — Tests de non-régression

### Tâche 5.1 : Test backend — tarification restauration

**Fichiers :**
- Créer : `backend/tests/test_tarification.py`

```python
def test_tarif_restauration_720p():
    assert TARIF_RESTAURATION["720p"] == 1

def test_tarif_restauration_1080p():
    assert TARIF_RESTAURATION["1080p"] == 2

def test_tarif_restauration_4k():
    assert TARIF_RESTAURATION["4k"] == 4

def test_tarif_animation_720p():
    assert TARIF_ANIMATION["720p"] == 10

def test_tarif_animation_1080p():
    assert TARIF_ANIMATION["1080p"] == 20
```

### Tâche 5.2 : Test endpoint — validation résolution

```python
def test_restauration_resolution_invalide():
    """POST /api/restore avec resolution=480p → 400"""
    ...

def test_restauration_720p_colorize_cout():
    """Vérifie que 720p + colorisation = 2 crédits"""
    ...

def test_restauration_4k_sans_couleur_cout():
    """Vérifie que 4K sans colorisation = 4 crédits"""
    ...
```

### Tâche 5.3 : Lancer tous les tests

```bash
cd backend && python -m pytest tests/ -v
```

---

## Phase 6 — Documentation GitHub

### Tâche 6.1 : Mettre à jour `.env.example`

Ajouter les nouvelles constantes de tarification documentées.

### Tâche 6.2 : Mettre à jour `docs/ARCHITECTURE.md`

Ajouter section "Tarification" avec la grille complète.

### Tâche 6.3 : Commit + push

```bash
git add -A
git commit -m "feat: restore UX v2 — resolution selector + new pricing + bugfix"
git push
```

---

## Récapitulatif des fichiers modifiés

| Fichier | Changement |
|---|---|
| `landing/src/app/restore/page.tsx` | Panneau d'options, resolution state, getCreditTotal, Label |
| `landing/src/lib/api.ts` | restorePhoto(resolution), animatePhoto(resolution) |
| `landing/src/app/animate/page.tsx` | Sélecteur résolution + coût |
| `backend/app/api/routes.py` | Constantes TARIF_*, endpoints /restore + /colorize + /animate |
| `backend/app/worker.py` | Accepter `resolution` |
| `backend/tests/test_tarification.py` | Nouveaux tests |
| `docs/ARCHITECTURE.md` | Section tarification |
| `.env.example` | Documentation tarifs |
