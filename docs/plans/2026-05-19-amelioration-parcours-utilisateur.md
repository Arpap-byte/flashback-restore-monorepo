# Plan d'implémentation — Amélioration du parcours utilisateur

Date : 2026-05-19
Auteur : Architecture (Claude Opus 4.7)
Exécutant cible : DeepSeek Pro
Périmètre : Galerie "Images importées", choix de source pour restauration, redesign toggle Avant/Après, vérification bouton colorisation, packs de crédits S/M/L avec tarif abonné.

Référence : `docs/plans/2026-05-19-conformite-ux-billing-seo.md` (ce plan le complète, ne le remplace pas).

---

## 0. Vue d'ensemble

5 chantiers indépendants, exécutables dans cet ordre recommandé :

1. **G1** — Redesign toggle Avant / Après (UI seulement, sans dépendance) → 15 min
2. **G2** — Vérification bouton colorisation (debug, pas de gros code) → 10 min
3. **G3** — Galerie "Images importées" (DB + endpoints + page Next.js) → 2-3 h
4. **G4** — Choix de source dans /restore (réutilise G3) → 45 min
5. **G5** — Packs de crédits S/M/L avec tarif abonné (DB + Stripe + Pricing) → 2-3 h

Total estimé : ~6 h de dev avec tests.

---

## 1. Analyse de l'existant

### 1.1 Écran de comparaison (`landing/src/app/restore/RestoreClient.tsx` L583-619)

État actuel :
- 3 boutons rendus avec `rounded-full` + couleurs accent (lignes 588-618), visuellement identiques aux CTAs "Télécharger" et "Animer cette photo" plus bas (L701-746).
- Logique correcte : `setShowAfter()` + `setCompareMode()`.
- Confusion utilisateur : les 3 pills se confondent avec des CTAs primaires.

### 1.2 Bouton colorisation (L713-726, handler L272-302)

Fonctionnement :
- Récupère l'URL restaurée (`restoredUrl`) → `fetch(restoredUrl)`.
- Si 401/403 → rafraîchit le token via `getPhotoUrlAsync(restoreResult.url_image)` (F8, déjà patché).
- Crée un `File` → appelle `colorizePhoto(f)`.

Backend (`routes.py` L978-1063) : endpoint `POST /colorize` opérationnel, consomme `TARIF_COLORISATION[resolution]` crédits.

Points de vigilance possibles :
- Si `restoreResult.url_image` ne contient PAS `/uploads/`, `getPhotoUrlAsync` ne réinjecte pas de token → 401 silencieux.
- Le `resolution` n'est PAS transmis à `/colorize` côté front → backend force `720p` par défaut (à vérifier).
- Coût caché : la colorisation re-consomme un travail complet alors que le crédit a déjà été pris à la restauration.

### 1.3 Galerie / images importées

Aucune notion de "galerie personnelle" indépendante des travaux dans la DB. Table `Travail` ne stocke que des résultats de pipeline. Il faut une nouvelle table `images_importees` (alias possible : `bibliotheque_images`).

### 1.4 Packs de crédits

Existant :
- Endpoints `POST /stripe/create-credit-checkout` (routes.py L1399), service `creer_session_paiement_credits` (stripe_service.py L123).
- Price IDs Stripe `STRIPE_PRICE_CREDITS_30/50/110` dans `config.py`. Les noms (30/50/110) ne correspondent plus aux montants demandés par Seb (30/100/300).
- `Pricing.tsx` n'affiche AUCUN pack de crédits actuellement (que les abonnements).
- Table `achats_credits` existe (db_models.py L154) — peut être réutilisée.

À créer :
- Nouvelle table `credit_packs` (catalogue + tarif abonné) OU constantes Python figées (plus simple, recommandé).
- Endpoint qui retourne le catalogue avec le prix appliqué (abonné vs non-abonné).
- Section "Packs de crédits" dans `Pricing.tsx`.
- Marquage des crédits achetés comme non-expirants (nouvelle colonne `credits_perpetuels` sur `utilisateurs`, ou table de lots).

### 1.5 Modèles & queries pertinents

- `Utilisateur.credits` (int) : balance unique. Pour distinguer crédits abonnement (mensuels, expirants) vs crédits pack (perpétuels), il faut soit splitter en deux colonnes, soit traquer par lots.
- `AchatCredits` : trace d'historique seulement, pas de notion d'expiration.

---

## 2. Chantier G1 — Redesign toggle Avant / Après (15 min)

### Objectif
Les utilisateurs ne doivent plus confondre le toggle Avant / Après avec des CTAs d'action. Adopter un pattern segmented-control (style iOS / Apple Photos).

### Tâche G1.1 — Remplacer les 3 boutons par un segmented control (5 min)

Fichier : `landing/src/app/restore/RestoreClient.tsx`
Localisation : L587-619 (le bloc `{/* Toggle buttons */}`).

Remplacer par un conteneur unique pill avec 3 segments, fond plus discret, label "Aperçu :" devant.

```tsx
{/* Comparaison view-mode toggle (segmented control) */}
<div className="flex flex-col items-center gap-2">
  <span className="text-xs uppercase tracking-wider text-muted/70">
    Mode d'aperçu
  </span>
  <div
    role="tablist"
    aria-label="Mode d'affichage de la comparaison"
    className="inline-flex p-1 rounded-full bg-surface border border-card-border"
  >
    <button
      role="tab"
      aria-selected={!showAfter && !compareMode}
      onClick={() => { setShowAfter(false); setCompareMode(false); }}
      className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
        !showAfter && !compareMode
          ? "bg-card text-foreground shadow-sm"
          : "text-muted hover:text-foreground"
      }`}
    >
      Original
    </button>
    <button
      role="tab"
      aria-selected={showAfter && !compareMode}
      onClick={() => { setShowAfter(true); setCompareMode(false); }}
      className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
        showAfter && !compareMode
          ? "bg-card text-foreground shadow-sm"
          : "text-muted hover:text-foreground"
      }`}
    >
      Restauré
    </button>
    <button
      role="tab"
      aria-selected={compareMode}
      onClick={() => { setShowAfter(true); setCompareMode(true); }}
      className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 ${
        compareMode
          ? "bg-card text-foreground shadow-sm"
          : "text-muted hover:text-foreground"
      }`}
    >
      <ArrowLeftRight className="w-3.5 h-3.5" />
      Côte à côte
    </button>
  </div>
</div>
```

Différences clés vs version actuelle :
- Conteneur unique pill (pas 3 boutons séparés) → signal "choix" pas "action".
- Pas de couleur `accent` (réservée aux CTAs). Sélection = fond `bg-card` + shadow.
- Vocabulaire : "Original / Restauré / Côte à côte" plutôt que "Avant / Après / Comparer".
- Label "Mode d'aperçu" en majuscules au-dessus, lève toute ambiguïté.
- `role="tablist"` + `aria-selected` pour l'accessibilité.

### Tâche G1.2 — Supprimer les pastilles redondantes (2 min)

Lignes 691-698 du même fichier : le bloc `{/* Labels */}` (Avant / Après en pastille) devient redondant après G1.1 → supprimer entièrement.

### Tâche G1.3 — Test visuel (5 min)

```bash
cd /opt/flashback-restore-monorepo/landing
pnpm dev   # ou npm run dev
```
Ouvrir `/restore`, restaurer une photo de test, vérifier visuellement que :
- Le toggle est clairement identifiable comme un choix (pas un CTA).
- Les 3 segments fonctionnent (préserver `compareMode` slider).
- Les boutons "Télécharger / Coloriser / Animer / Nouvelle photo" en dessous restent les seuls CTAs proéminents.

---

## 3. Chantier G2 — Vérification bouton colorisation (10 min)

### Tâche G2.1 — Reproduire le bug si présent (3 min)

```bash
cd /opt/flashback-restore-monorepo
docker compose up -d
# Front
curl -I https://flashback-restore.com/restore   # vérif 200
```

Workflow manuel :
1. Login.
2. Upload une photo, restaurer en 720p (sans colorisation cochée).
3. Sur l'écran résultat, cliquer "Coloriser".
4. Observer la console réseau et la console JS.

### Tâche G2.2 — Audit du flux d'erreurs probables (5 min)

À vérifier dans cet ordre :

1. **Token JWT expiré** (token TTL = ?). Fichier `landing/src/lib/api.ts` → vérifier que `getPhotoUrlAsync` redemande bien un token frais à chaque appel et ne cache pas un token expiré.

2. **URL résultat sans token** : si `restoreResult.url_image` est une URL absolue (`https://...`) ou ne contient pas `/uploads/`, le code L113 et L281 ne réinjecte pas de token. Patch :
   ```ts
   // L'URL peut être absolue ; on regénère TOUJOURS via getPhotoUrlAsync
   const freshUrl = await getPhotoUrlAsync(restoreResult.url_image);
   const res = await fetch(freshUrl);
   ```

3. **Endpoint backend** : `POST /colorize` consomme des crédits — vérifier que l'utilisateur en a (sinon HTTP 402/403). À tester avec un user qui n'a plus de crédits → message d'erreur doit être clair.

4. **Cohérence du `resolution`** : envoyer le même `resolution` qu'à la restauration. Fichier `landing/src/lib/api.ts`, fonction `colorizePhoto(file: File, resolution?: string)` à étendre si nécessaire ; côté front passer `colorizePhoto(f, resolution)` L290 du RestoreClient.

5. **Backend route `/colorize` L978-1063 routes.py** : vérifier que la signature accepte bien le paramètre `resolution` (form field). Si absent, ajouter :
   ```python
   resolution: str = Form("720p")
   ```

### Tâche G2.3 — Ajout de logs et tests (2 min)

Dans `handleColorize` (L272-302), enrichir le `setError` :
```ts
} catch (err) {
  const msg = err instanceof Error ? err.message : String(err);
  console.error("[colorize] failed", err);
  setError(`Colorisation échouée : ${msg}`);
}
```

Test backend manuel :
```bash
TOKEN=$(...)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -F "fichier=@/tmp/test.jpg" -F "resolution=720p" \
  https://api.flashback-restore.com/colorize -i
```

---

## 4. Chantier G3 — Galerie "Images importées" (2-3 h)

### Architecture cible

- Table DB `images_importees`.
- Endpoints :
  - `POST /api/library/upload` — upload pur, sans pipeline IA, déduit 0 crédit.
  - `GET /api/library` — liste paginée.
  - `DELETE /api/library/{id}` — suppression.
- Stockage : `UPLOAD_DIR/library/{user_id}/{uuid}.{ext}` (séparation claire des résultats IA).
- Page Next.js : `/bibliotheque` (ou `/galerie`).
- Composant réutilisable : `<LibraryPicker />` pour le chantier G4.

### Tâche G3.1 — Modèle SQLAlchemy + migration (15 min)

Fichier : `backend/app/models/db_models.py`. Ajouter à la fin :

```python
class ImageImportee(Base):
    """Galerie personnelle d'images importées par l'utilisateur (sans traitement IA)."""

    __tablename__ = "images_importees"

    id = Column(String, primary_key=True, default=_new_uuid)
    utilisateur_id = Column(String, ForeignKey("utilisateurs.id"), nullable=False, index=True)
    chemin_fichier = Column(String, nullable=False)     # ex: library/{uid}/abc.jpg
    nom_origine = Column(String, nullable=True)         # nom de fichier d'origine
    mime_type = Column(String, nullable=False)
    taille_octets = Column(Integer, nullable=False)
    largeur = Column(Integer, nullable=True)
    hauteur = Column(Integer, nullable=True)
    cree_le = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    derniere_utilisation = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_lib_user_date", "utilisateur_id", text("cree_le DESC")),
        CheckConstraint(
            "mime_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_lib_mime",
        ),
    )
```

Migration Alembic :
```bash
cd /opt/flashback-restore-monorepo/backend
alembic revision -m "add_images_importees" --autogenerate
# Vérifier la migration générée
alembic upgrade head
```

### Tâche G3.2 — Queries (20 min)

Fichier : `backend/app/db/queries.py`. Ajouter section :

```python
# ---------------------------------------------------------------------------
# Galerie "Images importées" (bibliothèque personnelle)
# ---------------------------------------------------------------------------

async def creer_image_importee(
    utilisateur_id: str,
    chemin_fichier: str,
    nom_origine: str,
    mime_type: str,
    taille_octets: int,
    largeur: int | None = None,
    hauteur: int | None = None,
    *,
    session: AsyncSession,
) -> dict:
    img = ImageImportee(
        utilisateur_id=utilisateur_id,
        chemin_fichier=chemin_fichier,
        nom_origine=nom_origine,
        mime_type=mime_type,
        taille_octets=taille_octets,
        largeur=largeur,
        hauteur=hauteur,
    )
    session.add(img)
    await session.flush()
    return {"id": img.id, "chemin_fichier": img.chemin_fichier, "cree_le": img.cree_le}


async def lister_images_importees(
    utilisateur_id: str, limite: int = 50, offset: int = 0, *, session: AsyncSession
) -> list[dict]:
    res = await session.execute(
        sa_select(ImageImportee)
        .where(ImageImportee.utilisateur_id == utilisateur_id)
        .order_by(ImageImportee.cree_le.desc())
        .limit(limite)
        .offset(offset)
    )
    return [
        {
            "id": i.id,
            "chemin_fichier": i.chemin_fichier,
            "nom_origine": i.nom_origine,
            "mime_type": i.mime_type,
            "taille_octets": i.taille_octets,
            "largeur": i.largeur,
            "hauteur": i.hauteur,
            "cree_le": i.cree_le.isoformat(),
        }
        for i in res.scalars().all()
    ]


async def obtenir_image_importee(
    image_id: str, utilisateur_id: str, *, session: AsyncSession
) -> dict | None:
    res = await session.execute(
        sa_select(ImageImportee).where(
            ImageImportee.id == image_id,
            ImageImportee.utilisateur_id == utilisateur_id,
        )
    )
    img = res.scalars().first()
    if not img:
        return None
    return {"id": img.id, "chemin_fichier": img.chemin_fichier, "mime_type": img.mime_type}


async def supprimer_image_importee(
    image_id: str, utilisateur_id: str, *, session: AsyncSession
) -> bool:
    res = await session.execute(
        sa_select(ImageImportee).where(
            ImageImportee.id == image_id,
            ImageImportee.utilisateur_id == utilisateur_id,
        )
    )
    img = res.scalars().first()
    if not img:
        return False
    await session.delete(img)
    return True
```

N'oublier d'importer `ImageImportee` en tête de fichier.

### Tâche G3.3 — Endpoints API (30 min)

Fichier : `backend/app/api/routes.py`. Ajouter après le bloc `/restore` :

```python
# ===========================================================================
# Galerie "Images importées" (bibliothèque utilisateur)
# ===========================================================================

LIBRARY_DIR = UPLOAD_DIR / "library"
LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/library/upload", response_model=dict)
async def upload_bibliotheque(
    fichier: UploadFile = File(...),
    utilisateur: dict = Depends(authentifier_utilisateur),
):
    """Importe une image dans la galerie personnelle de l'utilisateur (sans traitement IA)."""
    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 20 Mo).")
    if fichier.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Format non supporté.")

    user_dir = LIBRARY_DIR / utilisateur["id"]
    user_dir.mkdir(parents=True, exist_ok=True)
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[fichier.content_type]
    nom = f"{uuid.uuid4().hex}.{ext}"
    chemin = user_dir / nom
    chemin.write_bytes(contenu)

    # Optionnel : lire dimensions via PIL
    try:
        from PIL import Image as PILImage
        with PILImage.open(chemin) as im:
            largeur, hauteur = im.size
    except Exception:
        largeur, hauteur = None, None

    rel = f"library/{utilisateur['id']}/{nom}"
    async with session_scope() as session:
        img = await creer_image_importee(
            utilisateur_id=utilisateur["id"],
            chemin_fichier=rel,
            nom_origine=fichier.filename or "image",
            mime_type=fichier.content_type,
            taille_octets=len(contenu),
            largeur=largeur,
            hauteur=hauteur,
            session=session,
        )
    return {"id": img["id"], "url": f"/uploads/{rel}"}


@router.get("/library", response_model=dict)
async def lister_bibliotheque(
    limite: int = 50,
    offset: int = 0,
    utilisateur: dict = Depends(authentifier_utilisateur),
):
    async with session_scope() as session:
        items = await lister_images_importees(
            utilisateur["id"], limite=limite, offset=offset, session=session
        )
    # Ajouter une URL signée pour chaque
    for it in items:
        it["url"] = f"/uploads/{it['chemin_fichier']}"
    return {"items": items, "limite": limite, "offset": offset}


@router.delete("/library/{image_id}", response_model=dict)
async def supprimer_bibliotheque(
    image_id: str,
    utilisateur: dict = Depends(authentifier_utilisateur),
):
    async with session_scope() as session:
        img = await obtenir_image_importee(image_id, utilisateur["id"], session=session)
        if not img:
            raise HTTPException(status_code=404, detail="Image introuvable.")
        # Suppression du fichier physique
        chemin_abs = UPLOAD_DIR / img["chemin_fichier"]
        if chemin_abs.exists():
            chemin_abs.unlink()
        await supprimer_image_importee(image_id, utilisateur["id"], session=session)
    return {"deleted": True}
```

⚠️ Importer `creer_image_importee`, `lister_images_importees`, `obtenir_image_importee`, `supprimer_image_importee` depuis `app.db.queries`.

### Tâche G3.4 — Modifier `/restore` pour accepter une `image_importee_id` (10 min)

Routes.py L870 — `POST /restore`. Ajouter un paramètre optionnel :

```python
@router.post("/restore")
async def restaurer_photo(
    fichier: UploadFile | None = File(None),
    image_importee_id: str | None = Form(None),
    resolution: str = Form("720p"),
    colorize: bool = Form(False),
    utilisateur: dict = Depends(authentifier_utilisateur),
):
    if not fichier and not image_importee_id:
        raise HTTPException(400, "Fournir un fichier ou un image_importee_id.")
    if image_importee_id:
        async with session_scope() as session:
            img = await obtenir_image_importee(
                image_importee_id, utilisateur["id"], session=session
            )
        if not img:
            raise HTTPException(404, "Image de la bibliothèque introuvable.")
        chemin_source = UPLOAD_DIR / img["chemin_fichier"]
        contenu = chemin_source.read_bytes()
        mime_type = img["mime_type"]
        nom_original = chemin_source.name
    else:
        contenu = await fichier.read()
        # ... logique existante
```

Refactor : isoler la lecture de `contenu` dans un bloc en amont, puis le reste du pipeline existant continue inchangé.

### Tâche G3.5 — Client API frontend (10 min)

Fichier : `landing/src/lib/api.ts`. Ajouter :

```ts
export interface LibraryImage {
  id: string;
  url: string;
  nom_origine: string;
  mime_type: string;
  taille_octets: number;
  largeur: number | null;
  hauteur: number | null;
  cree_le: string;
}

export async function uploadToLibrary(file: File): Promise<LibraryImage> {
  const fd = new FormData();
  fd.append("fichier", file);
  const res = await apiFetch("/library/upload", { method: "POST", body: fd });
  if (!res.ok) throw new Error(`Upload galerie échoué (${res.status})`);
  return res.json();
}

export async function listLibrary(limit = 50, offset = 0): Promise<{ items: LibraryImage[] }> {
  const res = await apiFetch(`/library?limite=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(`Chargement galerie échoué (${res.status})`);
  return res.json();
}

export async function deleteLibraryImage(id: string): Promise<void> {
  const res = await apiFetch(`/library/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Suppression échouée (${res.status})`);
}

export async function restoreFromLibrary(
  imageId: string, colorize: boolean, resolution: string
): Promise<{ jobId: string; travailId: string }> {
  const fd = new FormData();
  fd.append("image_importee_id", imageId);
  fd.append("colorize", String(colorize));
  fd.append("resolution", resolution);
  const res = await apiFetch("/restore", { method: "POST", body: fd });
  if (!res.ok) throw new Error(`Restauration échouée (${res.status})`);
  const data = await res.json();
  return { jobId: data.job_id, travailId: data.travail_id };
}
```

### Tâche G3.6 — Page Next.js `/bibliotheque` (30 min)

Créer :
- `landing/src/app/bibliotheque/page.tsx` (server component minimal qui rend le client)
- `landing/src/app/bibliotheque/BibliothequeClient.tsx` (UI complète)
- `landing/src/app/bibliotheque/layout.tsx` (metadata SEO : noindex car privée)

Squelette `BibliothequeClient.tsx` :

```tsx
"use client";
import { useEffect, useState } from "react";
import Image from "next/image";
import { Upload, Trash2, Sparkles } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useAuth } from "@/context/AuthContext";
import { uploadToLibrary, listLibrary, deleteLibraryImage, LibraryImage } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function BibliothequeClient() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [items, setItems] = useState<LibraryImage[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (!user) return;
    listLibrary().then(r => setItems(r.items)).catch(console.error);
  }, [user]);

  const handleUpload = async (files: FileList | null) => {
    if (!files) return;
    setUploading(true);
    try {
      for (const f of Array.from(files)) {
        const img = await uploadToLibrary(f);
        setItems(prev => [img, ...prev]);
      }
    } finally { setUploading(false); }
  };

  const handleDelete = async (id: string) => {
    await deleteLibraryImage(id);
    setItems(prev => prev.filter(i => i.id !== id));
  };

  const handleRestoreFrom = (img: LibraryImage) => {
    sessionStorage.setItem("flashback_library_image_id", img.id);
    sessionStorage.setItem("flashback_photo", img.url);
    router.push("/restore?source=library");
  };

  // ... rendu : zone d'upload + grille de cartes, chaque carte ayant
  // "Restaurer" (bleu, primary) et "Supprimer" (rouge ghost).
}
```

Pas de couleur d'accent sur "Supprimer" — utiliser `text-red-500 hover:bg-red-500/10`.

### Tâche G3.7 — Navbar (5 min)

Fichier : `landing/src/components/Navbar.tsx` — ajouter un lien "Ma galerie" (entre "Historique" et "Restaurer") visible aux utilisateurs connectés.

### Tâche G3.8 — Tests (15 min)

```bash
cd /opt/flashback-restore-monorepo/backend
pytest tests/test_library_api.py -v   # à créer
```

Test minimal :
- POST `/library/upload` → 200, retourne `id` + `url`.
- GET `/library` → liste contient l'item.
- POST `/restore` avec `image_importee_id` → 200, génère un travail.
- DELETE `/library/{id}` → 200, fichier physique supprimé.
- Anti-IDOR : un user A ne peut pas DELETE l'image d'un user B → 404.

---

## 5. Chantier G4 — Choix de source dans /restore (45 min)

### Tâche G4.1 — Composant `<SourcePicker />` (20 min)

Fichier : `landing/src/app/restore/SourcePicker.tsx` (nouveau).

Affiche 2 onglets : "Téléverser" / "Ma galerie". 
- Onglet 1 : la dropzone existante (extraite de `RestoreClient.tsx` L421-462).
- Onglet 2 : grille des images de la galerie, sélection en cliquant.

```tsx
"use client";
import { useEffect, useState } from "react";
import Image from "next/image";
import { Upload, Library } from "lucide-react";
import { listLibrary, LibraryImage } from "@/lib/api";

type Props = {
  onFileSelected: (file: File) => void;
  onLibrarySelected: (image: LibraryImage) => void;
};

export default function SourcePicker({ onFileSelected, onLibrarySelected }: Props) {
  const [tab, setTab] = useState<"upload" | "library">("upload");
  const [libItems, setLibItems] = useState<LibraryImage[]>([]);

  useEffect(() => {
    if (tab === "library" && libItems.length === 0) {
      listLibrary().then(r => setLibItems(r.items)).catch(() => {});
    }
  }, [tab]);

  return (
    <div className="max-w-2xl mx-auto">
      {/* Onglets */}
      <div className="inline-flex p-1 rounded-full bg-surface border border-card-border mb-6">
        <button onClick={() => setTab("upload")} className={tabCls(tab === "upload")}>
          <Upload className="w-4 h-4 mr-1.5 inline" /> Téléverser
        </button>
        <button onClick={() => setTab("library")} className={tabCls(tab === "library")}>
          <Library className="w-4 h-4 mr-1.5 inline" /> Ma galerie
        </button>
      </div>
      {tab === "upload" ? <UploadZone onFile={onFileSelected} /> : (
        <LibraryGrid items={libItems} onPick={onLibrarySelected} />
      )}
    </div>
  );
}
```

### Tâche G4.2 — Intégration dans RestoreClient (15 min)

Dans `RestoreClient.tsx` :
1. Remplacer la dropzone L421-462 par `<SourcePicker ... />`.
2. Ajouter un nouvel état `libraryImageId: string | null` pour traquer si la source est une image de la galerie.
3. Modifier `handleRestore` :
   ```ts
   if (libraryImageId) {
     const { jobId } = await restoreFromLibrary(libraryImageId, colorize, resolution);
     // ... poll comme d'habitude
   } else {
     // chemin upload existant
   }
   ```
4. Au montage, lire `sessionStorage.getItem("flashback_library_image_id")` pour pré-sélectionner si on vient de `/bibliotheque`.

### Tâche G4.3 — Tests visuels (10 min)

- Sans galerie : onglet "Ma galerie" affiche un état vide + CTA "Importer dans la galerie".
- Avec galerie : grille, clic = sélection, badge visuel.
- Restauration depuis sélection → travail créé.

---

## 6. Chantier G5 — Packs de crédits S/M/L avec tarif abonné (2-3 h)

### Tarification (email Seb 2026-05-19)

| Pack | Crédits | Prix non-abonné | Prix abonné (≈ -20%) |
|------|---------|-----------------|----------------------|
| S    | 30      | 4,99 €          | 3,99 €               |
| M    | 100     | 9,99 €          | 7,99 €               |
| L    | 300     | 19,99 €         | 15,99 €              |

Règle "crédits perpétuels" : les crédits achetés via packs n'expirent jamais. Les crédits attribués via abonnement mensuel expirent (logique existante à conserver).

### Tâche G5.1 — Décision modèle : 2 colonnes vs table de lots (5 min)

**Recommandation : 2 colonnes sur `utilisateurs`** (plus simple, suffisant) :
- `credits` (existant) → crédits abonnement, RESET à chaque cycle mensuel.
- `credits_perpetuels` (nouveau) → crédits packs, jamais reset.

Logique de consommation : on draine d'abord les `credits` (abonnement), puis les `credits_perpetuels`. Évite de "gaspiller" des crédits pack quand l'utilisateur est encore abonné.

### Tâche G5.2 — Migration DB (10 min)

`backend/app/models/db_models.py` L42 — ajouter :

```python
credits_perpetuels = Column(Integer, nullable=False, default=0)
```

Migration Alembic :
```bash
cd /opt/flashback-restore-monorepo/backend
alembic revision -m "add_credits_perpetuels"
# éditer la migration : op.add_column("utilisateurs", Column("credits_perpetuels", Integer, server_default="0", nullable=False))
alembic upgrade head
```

### Tâche G5.3 — Catalogue packs côté backend (15 min)

Fichier : `backend/app/services/credits.py` (ou nouveau `backend/app/services/packs_credits.py`).

```python
# Catalogue immuable des packs de crédits
PACKS_CREDITS = {
    "S": {"credits": 30,  "prix_eur": 4.99,  "prix_abonne_eur": 3.99,  "stripe_price": "STRIPE_PRICE_PACK_S",     "stripe_price_abonne": "STRIPE_PRICE_PACK_S_ABO"},
    "M": {"credits": 100, "prix_eur": 9.99,  "prix_abonne_eur": 7.99,  "stripe_price": "STRIPE_PRICE_PACK_M",     "stripe_price_abonne": "STRIPE_PRICE_PACK_M_ABO"},
    "L": {"credits": 300, "prix_eur": 19.99, "prix_abonne_eur": 15.99, "stripe_price": "STRIPE_PRICE_PACK_L",     "stripe_price_abonne": "STRIPE_PRICE_PACK_L_ABO"},
}

def get_pack_price_id(pack: str, est_abonne: bool) -> str:
    """Retourne le Stripe price_id selon le statut d'abonnement."""
    config = PACKS_CREDITS[pack]
    key = "stripe_price_abonne" if est_abonne else "stripe_price"
    env_var = config[key]
    from os import getenv
    price_id = getenv(env_var)
    if not price_id:
        raise ValueError(f"{env_var} non configuré")
    return price_id
```

Ajouter dans `backend/app/config.py` :
```python
STRIPE_PRICE_PACK_S: str = os.getenv("STRIPE_PRICE_PACK_S", "")
STRIPE_PRICE_PACK_S_ABO: str = os.getenv("STRIPE_PRICE_PACK_S_ABO", "")
STRIPE_PRICE_PACK_M: str = os.getenv("STRIPE_PRICE_PACK_M", "")
STRIPE_PRICE_PACK_M_ABO: str = os.getenv("STRIPE_PRICE_PACK_M_ABO", "")
STRIPE_PRICE_PACK_L: str = os.getenv("STRIPE_PRICE_PACK_L", "")
STRIPE_PRICE_PACK_L_ABO: str = os.getenv("STRIPE_PRICE_PACK_L_ABO", "")
```

### Tâche G5.4 — Créer les Prices Stripe (15 min)

Via dashboard Stripe OU script :

```bash
cd /opt/flashback-restore-monorepo/scripts
cat > create_stripe_packs.py <<'PY'
import os, stripe
stripe.api_key = os.environ["STRIPE_API_KEY"]

PACKS = [
    ("Pack S — 30 crédits",         499,  "pack_s"),
    ("Pack S abonné — 30 crédits",  399,  "pack_s_abo"),
    ("Pack M — 100 crédits",        999,  "pack_m"),
    ("Pack M abonné — 100 crédits", 799,  "pack_m_abo"),
    ("Pack L — 300 crédits",       1999,  "pack_l"),
    ("Pack L abonné — 300 crédits",1599,  "pack_l_abo"),
]
for name, cents, lookup in PACKS:
    prod = stripe.Product.create(name=name, metadata={"type": "credit_pack", "lookup": lookup})
    price = stripe.Price.create(unit_amount=cents, currency="eur", product=prod.id,
                                lookup_key=lookup, metadata={"type": "credit_pack"})
    print(f"{lookup}: {price.id}")
PY
python create_stripe_packs.py
```

Reporter les `price_id` dans `.env` / secret manager.

### Tâche G5.5 — Service Stripe : étendre `creer_session_paiement_credits` (15 min)

Fichier : `backend/app/services/stripe_service.py`. Refondre la fonction (remplace L123-189) :

```python
from app.services.packs_credits import PACKS_CREDITS, get_pack_price_id

async def creer_session_paiement_pack(
    pack: str,       # "S", "M", "L"
    email: str,
    est_abonne: bool,
    url_succes: str,
    url_annulation: str,
) -> dict:
    if pack not in PACKS_CREDITS:
        raise ValueError(f"Pack inconnu : {pack}")
    config = PACKS_CREDITS[pack]
    prix_id = get_pack_price_id(pack, est_abonne)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        customer_email=email,
        line_items=[{"price": prix_id, "quantity": 1}],
        success_url=url_succes + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=url_annulation,
        locale="fr",
        metadata={
            "type": "credit_pack",
            "pack": pack,
            "credits": str(config["credits"]),
            "email": email,
            "est_abonne_au_paiement": "1" if est_abonne else "0",
            "perpetuel": "1",
        },
    )
    return {"checkout_url": session.url, "session_id": session.id}
```

Garder l'ancienne `creer_session_paiement_credits` en deprecated pour compatibilité, ou la supprimer si non utilisée ailleurs (vérifier d'abord).

### Tâche G5.6 — Endpoint API & catalogue (15 min)

Fichier : `backend/app/api/routes.py`. Ajouter :

```python
@router.get("/credit-packs", response_model=dict)
async def lister_packs_credits(
    utilisateur: dict | None = Depends(authentifier_utilisateur_optionnel),
):
    """Retourne le catalogue des packs avec le bon prix (abonné ou pas)."""
    est_abonne = bool(utilisateur and utilisateur.get("est_abonne"))
    packs = []
    for code, cfg in PACKS_CREDITS.items():
        packs.append({
            "code": code,
            "credits": cfg["credits"],
            "prix_eur": cfg["prix_abonne_eur"] if est_abonne else cfg["prix_eur"],
            "prix_normal_eur": cfg["prix_eur"],
            "remise_abonne": est_abonne,
            "perpetuel": True,
        })
    return {"packs": packs, "est_abonne": est_abonne}


@router.post("/stripe/create-pack-checkout", response_model=CheckoutReponse)
async def creer_checkout_pack(
    requete: PackCheckoutRequete,
    utilisateur: dict = Depends(authentifier_utilisateur),
):
    pack = requete.pack.upper()
    if pack not in PACKS_CREDITS:
        raise HTTPException(400, "Pack inconnu")
    est_abonne = bool(utilisateur.get("est_abonne"))
    resultat = await creer_session_paiement_pack(
        pack=pack,
        email=utilisateur["email"],
        est_abonne=est_abonne,
        url_succes=f"{SITE_URL}/dashboard?paiement=success",
        url_annulation=f"{SITE_URL}/pricing?paiement=cancel",
    )
    return resultat
```

`PackCheckoutRequete` (dans `app/api/schemas.py`) :
```python
class PackCheckoutRequete(BaseModel):
    pack: Literal["S", "M", "L"]
```

### Tâche G5.7 — Webhook Stripe : créditer en perpétuels (15 min)

Fichier : `backend/app/api/routes.py` autour de L1490 (`if metadata.get("type") == "credits"`). Ajouter une branche pour `credit_pack` :

```python
if metadata.get("type") == "credit_pack":
    email = metadata.get("email")
    nb_credits = int(metadata.get("credits", 0))
    perpetuel = metadata.get("perpetuel") == "1"
    pack = metadata.get("pack", "?")
    montant = session_obj["amount_total"] / 100  # cents → euros
    if nb_credits > 0 and email:
        async with session_scope() as session:
            utilisateur = await obtenir_utilisateur_par_email(email, session=session)
            if utilisateur:
                if perpetuel:
                    await crediter_utilisateur_perpetuel(
                        utilisateur["id"], nb_credits, session=session
                    )
                else:
                    await crediter_utilisateur(utilisateur["id"], nb_credits, session=session)
                await enregistrer_achat_credits(
                    utilisateur["id"], session_id, nb_credits, montant, session=session
                )
        logger.info(f"Pack {pack} crédité (perpétuel) : email={email}, credits={nb_credits}")
    return WebhookReponse(recu=True)
```

Nouvelle query `crediter_utilisateur_perpetuel` dans `backend/app/db/queries.py` :
```python
async def crediter_utilisateur_perpetuel(
    utilisateur_id: str, montant: int, *, session: AsyncSession
) -> None:
    await session.execute(
        sa_text("UPDATE utilisateurs SET credits_perpetuels = credits_perpetuels + :m WHERE id = :id"),
        {"m": montant, "id": utilisateur_id},
    )
```

### Tâche G5.8 — Logique de consommation : draine credits puis credits_perpetuels (10 min)

Fichier : `backend/app/services/credits.py` — fonction `consommer_operation`. Modifier la SQL de décrément pour faire :

```sql
UPDATE utilisateurs
SET credits = GREATEST(0, credits - LEAST(:n, credits)),
    credits_perpetuels = credits_perpetuels - GREATEST(0, :n - credits)
WHERE id = :id
```

Et `peut_restaurer` / `peut_animer` : vérifier `credits + credits_perpetuels >= n` au lieu de `credits >= n`.

⚠️ Adapter aussi le getter `/me` (routes.py) pour renvoyer `credits_total = credits + credits_perpetuels` ainsi que les 2 valeurs séparément.

### Tâche G5.9 — Reset mensuel ne touche QUE `credits` (5 min)

Fichier `routes.py` L1543 et L1586 (gestion `customer.subscription.updated` / `invoice.paid`).

La logique `mettre_a_jour_attribution_credits` doit faire un UPDATE sur la colonne `credits` UNIQUEMENT, jamais sur `credits_perpetuels`. Vérifier que c'est bien le cas (probablement déjà OK, juste à confirmer).

### Tâche G5.10 — Affichage Pricing.tsx (30 min)

Fichier : `landing/src/components/Pricing.tsx`. Sous la grille des plans (après L333), ajouter une section "Packs de crédits".

```tsx
import { useEffect, useState } from "react";

interface CreditPack {
  code: "S" | "M" | "L";
  credits: number;
  prix_eur: number;
  prix_normal_eur: number;
  remise_abonne: boolean;
  perpetuel: boolean;
}

function CreditPacksSection() {
  const [packs, setPacks] = useState<CreditPack[] | null>(null);
  const [estAbonne, setEstAbonne] = useState(false);

  useEffect(() => {
    fetch("/api/credit-packs", { credentials: "include" })
      .then(r => r.json())
      .then(d => { setPacks(d.packs); setEstAbonne(d.est_abonne); })
      .catch(() => setPacks([]));
  }, []);

  const handleBuy = async (code: string) => {
    const res = await fetch("/api/stripe/create-pack-checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ pack: code }),
    });
    if (!res.ok) { /* gérer erreur, p.ex. rediriger /auth si 401 */ return; }
    const data = await res.json();
    window.location.href = data.checkout_url;
  };

  if (!packs) return null;
  return (
    <div className="mt-20 max-w-5xl mx-auto">
      <h3 className="text-2xl font-bold text-center text-foreground mb-2 font-[family-name:var(--font-playfair)]">
        Packs de crédits supplémentaires
      </h3>
      <p className="text-center text-muted text-sm mb-2">
        Achat ponctuel, crédits sans expiration.
      </p>
      {estAbonne && (
        <p className="text-center text-emerald-500 text-sm mb-8 font-medium">
          ✓ En tant qu'abonné, vous bénéficiez d'un tarif réduit sur tous les packs.
        </p>
      )}
      <div className="grid md:grid-cols-3 gap-6">
        {packs.map(p => (
          <div key={p.code} className="bg-card border border-card-border rounded-2xl p-6 flex flex-col">
            <div className="text-lg font-semibold text-foreground">Pack {p.code}</div>
            <div className="text-3xl font-bold text-foreground mt-2">
              {p.prix_eur.toFixed(2).replace(".", ",")} €
              {p.remise_abonne && (
                <span className="ml-2 text-sm text-muted line-through font-normal">
                  {p.prix_normal_eur.toFixed(2).replace(".", ",")} €
                </span>
              )}
            </div>
            <div className="mt-1 inline-block px-3 py-1 rounded-full text-xs font-semibold bg-accent/15 text-accent self-start">
              {p.credits} crédits
            </div>
            <p className="text-muted text-sm mt-4 flex-1">
              {p.credits === 30 && "Pour quelques restaurations occasionnelles."}
              {p.credits === 100 && "Le meilleur rapport pour un projet familial."}
              {p.credits === 300 && "Idéal pour numériser un album complet."}
            </p>
            <p className="text-xs text-emerald-500 mt-2">✓ Crédits sans expiration</p>
            <button
              onClick={() => handleBuy(p.code)}
              className="mt-4 w-full py-3 rounded-full bg-accent text-white dark:text-gray-950 font-semibold text-sm hover:brightness-110 transition-all"
            >
              Acheter ce pack
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Brancher `<CreditPacksSection />` dans le composant `Pricing` exporté.

### Tâche G5.11 — Tests E2E (30 min)

1. **Backend pytest** :
   - `GET /credit-packs` sans auth → prix non-abonné, `est_abonne: false`.
   - `GET /credit-packs` avec user abonné → prix réduits, `est_abonne: true`.
   - `POST /stripe/create-pack-checkout` sans auth → 401.
   - Webhook `checkout.session.completed` avec metadata `type=credit_pack` → `credits_perpetuels` incrémenté.
   - Consommation : user avec credits=2 et credits_perpetuels=5, opération à 4 crédits → credits=0, credits_perpetuels=3.

2. **Stripe CLI** :
   ```bash
   stripe listen --forward-to https://api.flashback-restore.com/stripe/webhook
   stripe trigger checkout.session.completed --add payment_intent:metadata.type=credit_pack
   ```

3. **Frontend manuel** :
   - Visiteur non-connecté sur `/pricing` → voir les 3 packs au prix normal.
   - Cliquer "Acheter" → redirige vers `/auth` (à câbler dans `handleBuy`).
   - User abonné → voir les prix réduits + badge "✓ tarif abonné".
   - Achat Stripe test card `4242 4242 4242 4242` → retour `/dashboard?paiement=success`, balance crédits perpétuels +N.

---

## 7. Points d'attention transverses

### 7.1 Pas de noms de fournisseurs dans le contenu public
- ✗ "Backblaze", "Replicate", "Gemini" → ✓ "notre IA", "intelligence artificielle".
- Vérifier `Pricing.tsx`, `BibliothequeClient.tsx`, `SourcePicker.tsx`, copies marketing.

### 7.2 httpx, pas aiohttp
Aucun nouvel appel HTTP backend dans ce plan n'utilise aiohttp. Si refacto nécessaire (G2.2), migrer vers httpx au passage.

### 7.3 Sécurité
- IDOR : `obtenir_image_importee` filtre TOUJOURS par `utilisateur_id`.
- Anti-bypass crédits : `peut_restaurer` doit additionner `credits + credits_perpetuels`.
- Métadata Stripe : ne JAMAIS faire confiance aux montants côté webhook, toujours utiliser le mapping serveur (`PACKS_CREDITS[pack].credits`), pas `metadata.credits` (déjà géré ci-dessus mais à revalider).
- Token JWT galerie : appliquer le même mécanisme que `/uploads/` (token signé) sur `library/` (même middleware).

### 7.4 RGPD / rétention
La galerie "Images importées" est un stockage explicite par l'utilisateur → relève du consentement RGPD "stockage prolongé". Ajouter une mention dans `/privacy` + checkbox "J'accepte que mes images soient conservées dans ma galerie personnelle" au premier upload.

### 7.5 Performances
- Galerie : pagination obligatoire (limite par défaut 50, charger plus en lazy scroll).
- Thumbnail : si fichiers > 1 Mo, générer un .webp 400 px lors de l'upload (`PILImage.thumbnail`) pour la grille.

### 7.6 Migration data
- Tous les utilisateurs existants : `credits_perpetuels = 0` par défaut (server_default suffit).
- Les anciens achats via `STRIPE_PRICE_CREDITS_30/50/110` restent fonctionnels ; ces crédits ont été versés dans `credits` (non-perpétuels). C'est OK, on documente le changement de politique pour les NOUVEAUX achats uniquement.

### 7.7 SEO
- `/bibliotheque` → `metadata.robots = { index: false, follow: false }` (page privée).
- Sitemap : ne pas ajouter `/bibliotheque`.

### 7.8 Variables d'environnement à ajouter

`.env.production` (backend) :
```
STRIPE_PRICE_PACK_S=price_xxx
STRIPE_PRICE_PACK_S_ABO=price_xxx
STRIPE_PRICE_PACK_M=price_xxx
STRIPE_PRICE_PACK_M_ABO=price_xxx
STRIPE_PRICE_PACK_L=price_xxx
STRIPE_PRICE_PACK_L_ABO=price_xxx
```

Mettre à jour aussi `infra/` (compose, secrets) et la doc d'onboarding.

---

## 8. Ordre d'exécution recommandé

```
Jour 1 (3 h) :
  G1 — toggle Avant/Après          (15 min)
  G2 — vérif colorisation          (10 min)
  G5.1-G5.4 — DB + Stripe Prices   (50 min)
  G5.5-G5.7 — service + webhook    (45 min)
  G5.8-G5.9 — consommation         (15 min)
  G5.10 — UI Pricing               (30 min)
  G5.11 — tests packs              (30 min)

Jour 2 (3 h) :
  G3.1-G3.3 — DB + endpoints       (65 min)
  G3.4 — restore depuis lib        (10 min)
  G3.5-G3.7 — frontend galerie     (45 min)
  G3.8 — tests                     (15 min)
  G4.1-G4.3 — picker dans /restore (45 min)
  Tests E2E complets               (30 min)
```

---

## 9. Checklist de livraison

- [ ] Migration Alembic `add_images_importees` jouée en staging puis prod
- [ ] Migration Alembic `add_credits_perpetuels` jouée en staging puis prod
- [ ] 6 Prices Stripe créés (S, M, L × normal/abonné) et reportés en env
- [ ] Endpoints `/library/*` testés + couverts par pytest
- [ ] Endpoint `/credit-packs` retourne le bon prix selon `est_abonne`
- [ ] Webhook Stripe crédite bien dans `credits_perpetuels` pour les packs
- [ ] UI `/bibliotheque` accessible depuis Navbar
- [ ] UI `/restore` propose le picker upload / galerie
- [ ] Toggle Avant / Après redesigné, plus de confusion avec les CTAs
- [ ] Bouton "Coloriser" testé sur photo restaurée 720p / 1080p / 4K sans erreur
- [ ] Page Pricing affiche les 3 packs avec tarif abonné si connecté
- [ ] Mentions légales / privacy mises à jour pour la galerie
- [ ] Aucun nom de fournisseur tech ajouté dans le contenu public
- [ ] Aucune dépendance aiohttp ajoutée

---

## 10. Risques & mitigation

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Stripe Prices mal créés (mauvais montant) | M | Élevé | Script `create_stripe_packs.py` + double-check dashboard avant prod |
| Confusion entre `credits` et `credits_perpetuels` côté code | M | Moyen | Helper `credits_total()` centralisé, jamais lire les deux séparément ailleurs |
| Galerie qui sature le disque | M | Moyen | Quota par user (à terme), thumbnails, monitoring `df` |
| Token JWT galerie absent | F | Élevé (data leak) | Réutiliser middleware `/uploads/` existant pour `library/`, test IDOR |
| Webhook Stripe rejoué deux fois (idempotence) | F | Moyen | Table `stripe_events` existe déjà (db_models.py L215), vérifier qu'elle est lookup-up avant crédit |

---

Fin du plan.
