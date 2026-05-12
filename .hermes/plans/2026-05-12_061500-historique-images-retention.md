# Plan : Historique des images et politique de rétention

> **Pour Hermes :** Utiliser la compétence `subagent-driven-development` pour implémenter ce plan tâche par tâche.

**Objectif :** Permettre aux utilisateurs de consulter l'historique de leurs photos (original, restauré, animé), choisir une durée de conservation (7j, 30j, 90j), et supprimer leurs données. Le nettoyage automatique respecte le choix de chaque utilisateur.

**Architecture :** 
- Colonnes **utilisateurs** : `retention_jours` (7/30/90), `derniere_activite` (pour dashboard admin)
- Colonnes **travaux** : `chemin_animation`, `taille_original`, `taille_resultat` (pour dashboard admin — espace disque)
- Une seule migration Alembic qui ajoute les 5 colonnes en une fois
- Un endpoint `PUT /api/user/preferences` pour modifier la rétention
- Le service de nettoyage lit la rétention par utilisateur et supprime les 3 fichiers
- L'endpoint d'historique enrichi retourne les dates d'expiration et URLs de tous les médias
- L'utilisateur peut supprimer un travail individuel ou tout son historique
- Le dashboard admin pourra interroger : inscrits, photos traitées/stockées, espace disque, crédits — sans migration future

**Stack technique :** FastAPI + SQLAlchemy async + PostgreSQL + Pillow (inchangé)

---

## Vue d'ensemble des tâches

| # | Tâche | Fichiers | 
|---|-------|----------|
| 1 | Migration DB unique : 5 colonnes (utilisateurs + travaux) | `db_models.py`, migration Alembic |
| 2 | Enregistrer les tailles de fichiers à l'upload (dashboard admin) | `routes.py` (endpoints upload) |
| 3 | Queries : CRUD pour les préférences de rétention | `queries.py`, `database.py` |
| 4 | Queries : enregistrer le chemin d'animation + suppression travaux | `queries.py`, `database.py` |
| 5 | Endpoint `PUT` + `GET /api/user/preferences` | `user.py`, `schemas.py` |
| 6 | Endpoint `DELETE /api/user/history/{travail_id}` | `user.py` |
| 7 | Endpoint `DELETE /api/user/history` (tout supprimer) | `user.py` |
| 8 | Enrichir `GET /api/user/history` (expiration, URLs, tailles) | `user.py` |
| 9 | Sauvegarder `chemin_animation` quand l'animation termine | `routes.py` (statut_animation) |
| 10 | Refonte du service de nettoyage (rétention par utilisateur) | `cleanup.py` |
| 11 | Endpoint dashboard admin `GET /api/admin/dashboard` | `routes.py`, `schemas.py` |
| 12 | Cronjob de nettoyage quotidien | Cron Hermes |
| 13 | Tests : endpoints, rétention, nettoyage | `tests/` |

---

## Détail des tâches

### Tâche 1 : Migration DB unique — 5 colonnes en une fois

**Objectif :** Ajouter en une seule migration Alembic toutes les colonnes nécessaires pour l'historique + dashboard admin.

**Colonnes ajoutées :**

| Table | Colonne | Type | Défaut | Contrainte |
|-------|---------|------|--------|------------|
| `utilisateurs` | `retention_jours` | INTEGER | 30 | CHECK IN (7, 30, 90) |
| `utilisateurs` | `derniere_activite` | TIMESTAMPTZ | NULL | — |
| `travaux` | `chemin_animation` | VARCHAR | NULL | — |
| `travaux` | `taille_original` | INTEGER | NULL | — (octets) |
| `travaux` | `taille_resultat` | INTEGER | NULL | — (octets) |

**Fichiers :**
- Modifier : `backend/app/models/db_models.py` (classes `Utilisateur` et `Travail`)
- Créer : `backend/alembic/versions/<timestamp>_historique_retention_dashboard.py`

**Étape 1 : Mettre à jour `db_models.py`**

Classe `Utilisateur` — ajouter après `animations_utilisees` :

```python
retention_jours = Column(Integer, nullable=False, default=30)
derniere_activite = Column(DateTime(timezone=True), nullable=True)

# Ajouter la contrainte dans __table_args__ :
__table_args__ = (
    Index("idx_oauth_provider", "oauth_provider", "oauth_provider_id"),
    CheckConstraint(
        "retention_jours IN (7, 30, 90)",
        name="ck_utilisateurs_retention",
    ),
)
```

Classe `Travail` — ajouter après `chemin_resultat` :

```python
chemin_animation = Column(String, nullable=True)
taille_original = Column(Integer, nullable=True)
taille_resultat = Column(Integer, nullable=True)
```

**Étape 2 : Générer la migration**

```bash
cd /root/flashback-restore-monorepo/backend
alembic revision --autogenerate -m "historique_retention_dashboard"
alembic upgrade head
```

**Étape 3 : Vérifier**

```bash
psql -h localhost -U flashback -d flashback -c "\d utilisateurs" | grep -E "retention|derniere_activite"
psql -h localhost -U flashback -d flashback -c "\d travaux" | grep -E "animation|taille"
```

---

### Tâche 2 : Enregistrer les tailles de fichiers à l'upload

**Objectif :** Remplir `taille_original` et `taille_resultat` pour que le dashboard admin puisse afficher l'espace disque utilisé.

**Fichiers :**
- Modifier : `backend/app/api/routes.py` (endpoints `analyze`, `restore`, `colorize`, `animate`)
- Modifier : `backend/app/db/database.py` et `queries.py` (ajouter les tailles à `mettre_a_jour_travail`)

**Étape 1 : Étendre `mettre_a_jour_travail`**

Dans `queries.py`, ajouter les paramètres `taille_original` et `taille_resultat` :

```python
async def mettre_a_jour_travail(
    travail_id: str,
    statut: Optional[str] = None,
    chemin_resultat: Optional[str] = None,
    resultat_json: Optional[str] = None,
    message_erreur: Optional[str] = None,
    taille_original: Optional[int] = None,
    taille_resultat: Optional[int] = None,
) -> bool:
    valeurs = {"modifie_le": _utcnow()}
    if statut is not None:
        valeurs["statut"] = statut
    if chemin_resultat is not None:
        valeurs["chemin_resultat"] = chemin_resultat
    if resultat_json is not None:
        valeurs["resultat_json"] = resultat_json
    if message_erreur is not None:
        valeurs["message_erreur"] = message_erreur
    if taille_original is not None:
        valeurs["taille_original"] = taille_original
    if taille_resultat is not None:
        valeurs["taille_resultat"] = taille_resultat
    # ... reste inchangé
```

**Étape 2 : Enregistrer la taille à l'upload dans chaque endpoint**

Dans `analyser()`, après `creer_travail()` :

```python
taille = len(contenu)
mettre_a_jour_travail(travail_id, taille_original=taille)
```

Dans `restaurer()`, après avoir écrit le fichier restauré :

```python
taille_resultat_val = chemin_restaure.stat().st_size
mettre_a_jour_travail(travail_id, taille_resultat=taille_resultat_val)
```

Dans `coloriser_standalone()`, idem.

Dans `animer()`, à la sauvegarde.

**Étape 3 : Mettre à jour `derniere_activite` utilisateur**

Créer une fonction utilitaire :

```python
# Dans queries.py
async def mettre_a_jour_activite(utilisateur_id: str) -> bool:
    async with async_session() as session:
        stmt = (
            update(Utilisateur)
            .where(Utilisateur.id == utilisateur_id)
            .values(derniere_activite=_utcnow())
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0
```

Appeler cette fonction au début de chaque endpoint d'upload (analyze, restore, colorize, animate) :

```python
from app.db.database import mettre_a_jour_activite
mettre_a_jour_activite(utilisateur["id"])
```

---

### Tâche 3 : Queries — préférences de rétention

**Objectif :** Ajouter les fonctions `mettre_a_jour_retention()` et `obtenir_retention()`.

**Fichiers :**
- Modifier : `backend/app/db/queries.py`
- Modifier : `backend/app/db/database.py` (wrappers sync)

**Étape 1 : Ajouter les fonctions async dans `queries.py`**

```python
async def mettre_a_jour_retention(utilisateur_id: str, retention_jours: int) -> bool:
    """Met à jour la durée de rétention des fichiers d'un utilisateur."""
    async with async_session() as session:
        stmt = (
            update(Utilisateur)
            .where(Utilisateur.id == utilisateur_id)
            .values(retention_jours=retention_jours)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0


async def obtenir_retention(utilisateur_id: str) -> Optional[int]:
    """Récupère la durée de rétention d'un utilisateur (7, 30, ou 90 jours)."""
    async with async_session() as session:
        stmt = select(Utilisateur.retention_jours).where(Utilisateur.id == utilisateur_id)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        return row if row is not None else 30  # défaut
```

**Étape 2 : Ajouter les wrappers sync dans `database.py`**

```python
# Dans les imports async :
mettre_a_jour_retention as _async_mettre_a_jour_retention,
obtenir_retention as _async_obtenir_retention,

# Wrappers sync à la fin du fichier :
def mettre_a_jour_retention(utilisateur_id: str, retention_jours: int) -> bool:
    return _sync(_async_mettre_a_jour_retention(utilisateur_id, retention_jours))

def obtenir_retention(utilisateur_id: str) -> int:
    return _sync(_async_obtenir_retention(utilisateur_id))
```

**Étape 3 : Test rapide**

```python
# Vérifier que l'import fonctionne
python -c "from app.db.database import obtenir_retention, mettre_a_jour_retention; print('OK')"
```

---

### Tâche 4 : Queries — mise à jour du chemin d'animation

**Objectif :** Permettre de sauvegarder `chemin_animation` sur un travail (quand l'animation D-ID est terminée).

**Fichiers :**
- Modifier : `backend/app/db/queries.py`
- Modifier : `backend/app/db/database.py`

**Étape 1 : Fonction async**

```python
async def mettre_a_jour_chemin_animation(travail_id: str, chemin_animation: str) -> bool:
    """Enregistre le chemin/URL de l'animation terminée pour un travail."""
    async with async_session() as session:
        stmt = (
            update(Travail)
            .where(Travail.id == travail_id)
            .values(chemin_animation=chemin_animation, modifie_le=_utcnow())
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0
```

**Étape 2 : Wrapper sync dans `database.py`**

```python
def mettre_a_jour_chemin_animation(travail_id: str, chemin_animation: str) -> bool:
    return _sync(_async_mettre_a_jour_chemin_animation(travail_id, chemin_animation))
```

---

### Tâche 5 : Endpoint `PUT /api/user/preferences`

**Objectif :** Permettre à l'utilisateur de changer sa durée de rétention (7, 30, ou 90 jours).

**Fichiers :**
- Modifier : `backend/app/api/user.py`
- Modifier : `backend/app/models/schemas.py`

**Étape 1 : Ajouter le schéma Pydantic dans `schemas.py`**

```python
class PreferencesRequete(BaseModel):
    """Requête pour modifier les préférences utilisateur."""
    retention_jours: int = Field(
        ..., ge=7, le=90,
        description="Durée de conservation : 7, 30 ou 90 jours",
    )
```

**Étape 2 : Ajouter l'endpoint dans `user.py`**

```python
from app.models.schemas import PreferencesRequete
from app.db.database import mettre_a_jour_retention, obtenir_retention

@router.put("/preferences")
async def preferences(
    body: PreferencesRequete,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Modifie les préférences de l'utilisateur (durée de conservation des photos).
    Valeurs acceptées : 7, 30, 90 (jours).
    """
    if body.retention_jours not in (7, 30, 90):
        raise HTTPException(
            status_code=400,
            detail="La durée de conservation doit être 7, 30 ou 90 jours.",
        )

    ok = mettre_a_jour_retention(utilisateur["id"], body.retention_jours)
    if not ok:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    return {
        "message": "Préférences mises à jour.",
        "retention_jours": body.retention_jours,
    }


@router.get("/preferences")
async def lire_preferences(utilisateur: dict = Depends(exiger_utilisateur)):
    """Retourne les préférences de l'utilisateur (durée de conservation)."""
    retention = obtenir_retention(utilisateur["id"])
    return {
        "retention_jours": retention,
        "options_disponibles": [7, 30, 90],
    }
```

---

### Tâche 6 : Endpoint `DELETE /api/user/history/{travail_id}`

**Objectif :** Permettre à l'utilisateur de supprimer un travail spécifique et ses fichiers associés.

**Fichiers :**
- Modifier : `backend/app/api/user.py`

**Étape 1 : Ajouter l'endpoint**

```python
import os
from app.db.database import obtenir_travail

@router.delete("/history/{travail_id}")
async def supprimer_travail(
    travail_id: str,
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Supprime un travail spécifique et tous ses fichiers associés
    (photo originale, résultat, animation). L'utilisateur doit être
    propriétaire du travail.
    """
    travail = obtenir_travail(travail_id)
    if travail is None:
        raise HTTPException(status_code=404, detail="Travail introuvable.")
    if travail.get("utilisateur_id") != utilisateur["id"]:
        raise HTTPException(status_code=403, detail="Ce travail ne vous appartient pas.")

    # Supprimer les fichiers physiques
    fichiers_a_supprimer = []
    for champ in ["chemin_photo", "chemin_resultat", "chemin_animation"]:
        chemin = travail.get(champ)
        if chemin and os.path.isfile(chemin):
            try:
                os.remove(chemin)
                fichiers_a_supprimer.append(champ)
            except OSError as e:
                logger.warning(f"Impossible de supprimer {chemin}: {e}")

    # Supprimer l'enregistrement en base
    from app.db.database import supprimer_travail as _supprimer_travail
    _supprimer_travail(travail_id)

    return {
        "message": "Travail supprimé.",
        "fichiers_supprimes": fichiers_a_supprimer,
    }
```

---

### Tâche 7 : Query + Endpoint `DELETE /api/user/history` (tout supprimer)

**Objectif :** Permettre à l'utilisateur de supprimer TOUT son historique d'un coup.

**Fichiers :**
- Modifier : `backend/app/db/queries.py` (ajouter `supprimer_travail` et `supprimer_tous_travaux_utilisateur`)
- Modifier : `backend/app/db/database.py`
- Modifier : `backend/app/api/user.py`

**Étape 1 : Ajouter les queries async dans `queries.py`**

```python
async def supprimer_travail(travail_id: str) -> bool:
    """Supprime un travail de la base (sans toucher aux fichiers)."""
    async with async_session() as session:
        stmt = select(Travail).where(Travail.id == travail_id)
        result = await session.execute(stmt)
        travail = result.scalar_one_or_none()
        if travail is None:
            return False
        await session.delete(travail)
        await session.commit()
        return True


async def supprimer_tous_travaux_utilisateur(utilisateur_id: str) -> int:
    """Supprime tous les travaux d'un utilisateur. Retourne le nombre supprimé."""
    async with async_session() as session:
        stmt = select(Travail).where(Travail.utilisateur_id == utilisateur_id)
        result = await session.execute(stmt)
        travaux = result.scalars().all()
        count = len(travaux)
        for t in travaux:
            await session.delete(t)
        await session.commit()
        return count
```

**Étape 2 : Wrappers sync dans `database.py`**

```python
def supprimer_travail(travail_id: str) -> bool:
    return _sync(_async_supprimer_travail(travail_id))

def supprimer_tous_travaux_utilisateur(utilisateur_id: str) -> int:
    return _sync(_async_supprimer_tous_travaux_utilisateur(utilisateur_id))
```

**Étape 3 : Endpoint dans `user.py`**

```python
@router.delete("/history")
async def supprimer_tout_historique(
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Supprime TOUS les travaux de l'utilisateur et leurs fichiers associés.
    ⚠️ Action irréversible.
    """
    from app.db.database import (
        lister_travaux_par_utilisateur,
        supprimer_tous_travaux_utilisateur as _supprimer_tous,
    )

    # Récupérer tous les travaux pour supprimer les fichiers
    tous_les_travaux = lister_travaux_par_utilisateur(utilisateur["id"], limite=10000)

    fichiers_supprimes = 0
    for travail in tous_les_travaux:
        for champ in ["chemin_photo", "chemin_resultat", "chemin_animation"]:
            chemin = travail.get(champ)
            if chemin and os.path.isfile(chemin):
                try:
                    os.remove(chemin)
                    fichiers_supprimes += 1
                except OSError:
                    pass

    nb_supprimes = _supprimer_tous(utilisateur["id"])

    return {
        "message": f"{nb_supprimes} travaux supprimés.",
        "travaux_supprimes": nb_supprimes,
        "fichiers_supprimes": fichiers_supprimes,
    }
```

---

### Tâche 8 : Enrichir `GET /api/user/history`

**Objectif :** Ajouter les URLs des 3 médias, la date d'expiration calculée, et le statut de rétention.

**Fichiers :**
- Modifier : `backend/app/api/user.py`

**Étape 1 : Remplacer l'endpoint existant**

```python
from datetime import datetime, timedelta, timezone
from app.db.database import obtenir_retention

@router.get("/history")
async def history(
    utilisateur: dict = Depends(exiger_utilisateur),
    limite: int = 50,
):
    """Retourne l'historique enrichi des travaux de l'utilisateur."""
    travaux = lister_travaux_par_utilisateur(utilisateur["id"], limite)
    retention = obtenir_retention(utilisateur["id"])

    resultat = []
    for t in travaux:
        cree_le = t.get("cree_le")
        expire_le = None
        if cree_le:
            # Parser la date (peut être string ISO ou datetime)
            if isinstance(cree_le, str):
                cree_dt = datetime.fromisoformat(cree_le.replace("Z", "+00:00"))
            else:
                cree_dt = cree_le
            expire_dt = cree_dt + timedelta(days=retention)
            expire_le = expire_dt.isoformat()

        # Construire les URLs publiques
        def _vers_url(chemin):
            if not chemin:
                return None
            nom_fichier = os.path.basename(chemin)
            return f"/uploads/{nom_fichier}"

        resultat.append({
            "id": t["id"],
            "type": t["type"],
            "statut": t["statut"],
            "url_original": _vers_url(t.get("chemin_photo")),
            "url_resultat": _vers_url(t.get("chemin_resultat")),
            "url_animation": _vers_url(t.get("chemin_animation")),
            "message_erreur": t.get("message_erreur"),
            "cree_le": cree_le.isoformat() if hasattr(cree_le, 'isoformat') else str(cree_le),
            "expire_le": expire_le,
            "retention_jours": retention,
        })

    return {
        "travaux": resultat,
        "retention_jours": retention,
        "total": len(resultat),
    }
```

---

### Tâche 9 : Sauvegarder `chemin_animation` à la fin de l'animation

**Objectif :** Quand le statut d'animation passe à `termine`, enregistrer l'URL de la vidéo.

**Fichiers :**
- Modifier : `backend/app/api/routes.py` (endpoint `statut_animation`)

**Étape 1 : Modifier `statut_animation`**

Dans `routes.py`, après la correspondance des statuts vers ligne ~730. Quand `data["status"] == "done"` :

```python
# Sauvegarder le chemin d'animation quand c'est terminé
if data.get("status") == "done" and data.get("result_url"):
    # Trouver le travail associé à ce job_id
    travail = obtenir_travail_par_job_externe(job_id)
    if travail:
        # Télécharger la vidéo D-ID et la sauvegarder localement
        # (ou simplement stocker l'URL si on préfère)
        from app.db.database import mettre_a_jour_travail, mettre_a_jour_chemin_animation
        mettre_a_jour_travail(
            travail["id"],
            statut="termine",
            chemin_resultat=data["result_url"],
        )
        mettre_a_jour_chemin_animation(travail["id"], data["result_url"])
```

> **Note :** La vidéo D-ID est hébergée par D-ID avec une URL temporaire. Pour une conservation long-terme, il faudrait télécharger le MP4 et le stocker localement. Mais ça peut être fait dans une itération suivante — pour l'instant, on stocke l'URL.

---

### Tâche 10 : Refonte du service de nettoyage

**Objectif :** Remplacer le nettoyage 30j fixe par une logique qui lit `retention_jours` par utilisateur et supprime les 3 fichiers.

**Fichiers :**
- Modifier : `backend/app/services/cleanup.py`

**Étape 1 : Réécrire `nettoyer_uploads()`**

```python
"""
Service de nettoyage des uploads expirés.

Pour chaque travail terminé/en erreur, vérifie si sa date de création
dépasse la rétention configurée par son propriétaire. Supprime les 3
fichiers (original, résultat, animation) et l'enregistrement DB.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from app.db.database import _obtenir_connexion
from app.db.database import supprimer_travail as _supprimer_travail_db

logger = logging.getLogger(__name__)


def _supprimer_fichier_si_existe(chemin: str) -> bool:
    """Supprime un fichier s'il existe. Retourne True si supprimé."""
    if chemin and os.path.isfile(chemin):
        try:
            os.remove(chemin)
            return True
        except OSError:
            return False
    return False


def nettoyer_uploads() -> dict:
    """
    Scanne les travaux terminés/en erreur et supprime ceux dont la date
    dépasse la rétention configurée par leur propriétaire.

    Returns:
        dict avec : travaux_supprimes, fichiers_supprimes, espace_libere_octets, erreurs
    """
    conn = _obtenir_connexion()
    try:
        # Récupérer les travaux expirés avec leur rétention utilisateur
        maintenant = datetime.now(timezone.utc)
        rows = conn.execute("""
            SELECT t.id, t.chemin_photo, t.chemin_resultat, t.chemin_animation,
                   t.cree_le, u.retention_jours
            FROM travaux t
            JOIN utilisateurs u ON t.utilisateur_id = u.id
            WHERE t.statut IN ('termine', 'erreur')
        """).fetchall()

        travaux_supprimes = 0
        fichiers_supprimes = 0
        espace_libere = 0
        erreurs = 0

        for row in rows:
            travail_id, chemin_photo, chemin_resultat, chemin_animation, cree_le, retention = row

            # Vérifier l'expiration
            if isinstance(cree_le, str):
                cree_le = datetime.fromisoformat(cree_le.replace("Z", "+00:00"))

            retention = retention or 30
            date_expiration = cree_le + timedelta(days=retention)

            if maintenant <= date_expiration:
                continue  # Pas encore expiré

            # Supprimer les 3 fichiers
            for chemin in [chemin_photo, chemin_resultat, chemin_animation]:
                if chemin and os.path.isfile(chemin):
                    try:
                        taille = os.path.getsize(chemin)
                        os.remove(chemin)
                        fichiers_supprimes += 1
                        espace_libere += taille
                        logger.info(f"Supprimé : {os.path.basename(chemin)} ({taille} octets)")
                    except OSError as e:
                        erreurs += 1
                        logger.error(f"Erreur suppression {chemin}: {e}")

            # Supprimer l'enregistrement DB
            try:
                conn.execute("DELETE FROM travaux WHERE id = ?", (travail_id,))
                travaux_supprimes += 1
            except Exception as e:
                erreurs += 1
                logger.error(f"Erreur suppression DB travail {travail_id}: {e}")

        conn.commit()

        logger.info(
            f"Nettoyage terminé : {travaux_supprimes} travaux supprimés, "
            f"{fichiers_supprimes} fichiers ({espace_libere} octets), {erreurs} erreurs"
        )
        return {
            "travaux_supprimes": travaux_supprimes,
            "fichiers_supprimes": fichiers_supprimes,
            "espace_libere_octets": espace_libere,
            "erreurs": erreurs,
        }

    except Exception as e:
        logger.exception(f"Erreur globale du nettoyage : {e}")
        return {
            "travaux_supprimes": 0,
            "fichiers_supprimes": 0,
            "espace_libere_octets": 0,
            "erreurs": 1,
        }
    finally:
        conn.close()
```

> ⚠️ **Piège** : La requête SQL utilise `?` pour PostgreSQL. Si on est sur PostgreSQL, utiliser `%s`. À adapter selon le moteur — ou utiliser SQLAlchemy directement.

**Version PostgreSQL avec SQLAlchemy** (recommandée) :

```python
from app.db.session import async_session
from sqlalchemy import select, delete
from app.models.db_models import Travail, Utilisateur

async def _nettoyer_async() -> dict:
    maintenant = datetime.now(timezone.utc)
    fichiers_supprimes = 0
    espace_libere = 0
    travaux_supprimes = 0
    erreurs = 0

    async with async_session() as session:
        # Jointure travaux + utilisateurs pour obtenir la rétention
        stmt = (
            select(Travail, Utilisateur.retention_jours)
            .join(Utilisateur, Travail.utilisateur_id == Utilisateur.id)
            .where(Travail.statut.in_(['termine', 'erreur']))
        )
        result = await session.execute(stmt)
        rows = result.all()

        for travail, retention in rows:
            retention = retention or 30
            date_expiration = travail.cree_le + timedelta(days=retention)

            if maintenant <= date_expiration:
                continue

            for chemin in [travail.chemin_photo, travail.chemin_resultat, travail.chemin_animation]:
                if chemin and os.path.isfile(chemin):
                    try:
                        taille = os.path.getsize(chemin)
                        os.remove(chemin)
                        fichiers_supprimes += 1
                        espace_libere += taille
                    except OSError as e:
                        erreurs += 1
                        logger.error(f"Erreur suppression {chemin}: {e}")

            await session.delete(travail)
            travaux_supprimes += 1

        await session.commit()

    return {
        "travaux_supprimes": travaux_supprimes,
        "fichiers_supprimes": fichiers_supprimes,
        "espace_libere_octets": espace_libere,
        "erreurs": erreurs,
    }


def nettoyer_uploads() -> dict:
    """Wrapper sync pour le endpoint admin."""
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_nettoyer_async())
```

---

### Tâche 11 : Endpoint dashboard admin `GET /api/admin/dashboard`

**Objectif :** Fournir un endpoint admin qui agrège les métriques clés pour le dashboard.

**Fichiers :**
- Modifier : `backend/app/api/routes.py`
- Modifier : `backend/app/models/schemas.py`

**Étape 1 : Ajouter le schéma de réponse dans `schemas.py`**

```python
class DashboardAdminReponse(BaseModel):
    """Réponse du dashboard administrateur."""
    utilisateurs: dict = Field(..., description="Stats utilisateurs")
    travaux: dict = Field(..., description="Stats travaux")
    stockage: dict = Field(..., description="Stats stockage")
    credits: dict = Field(..., description="Stats crédits")

class DashboardUtilisateurs(BaseModel):
    total: int = 0
    actifs_7j: int = 0
    actifs_30j: int = 0
    par_plan: dict = Field(default_factory=dict)

class DashboardTravaux(BaseModel):
    total: int = 0
    photos_stockees: int = 0
    par_type: dict = Field(default_factory=dict)
    par_statut: dict = Field(default_factory=dict)

class DashboardStockage(BaseModel):
    espace_total_octets: int = 0
    espace_total_mb: float = 0.0
    par_utilisateur_top5: list = Field(default_factory=list)

class DashboardCredits(BaseModel):
    total_distribues: int = 0
    total_consommes: int = 0
    credits_actifs: int = 0
```

**Étape 2 : Ajouter l'endpoint dans `routes.py`**

```python
from datetime import datetime, timedelta, timezone
from app.models.schemas import DashboardAdminReponse

@router.get("/admin/dashboard")
async def dashboard_admin(request: Request):
    """
    Retourne les métriques agrégées pour le dashboard administrateur.
    
    **Protégé par token admin** : nécessite l'en-tête X-Admin-Key.
    """
    admin_key = request.headers.get("X-Admin-Key")
    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")
    
    from app.db.session import async_session
    from sqlalchemy import text as _sa_text
    
    maintenant = datetime.now(timezone.utc)
    il_y_a_7j = maintenant - timedelta(days=7)
    il_y_a_30j = maintenant - timedelta(days=30)
    
    async with async_session() as session:
        # --- Utilisateurs ---
        total_utilisateurs = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM utilisateurs")
        )).fetchone()[0]
        
        actifs_7j = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM utilisateurs WHERE derniere_activite >= :seuil"),
            {"seuil": il_y_a_7j}
        )).fetchone()[0]
        
        actifs_30j = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM utilisateurs WHERE derniere_activite >= :seuil"),
            {"seuil": il_y_a_30j}
        )).fetchone()[0]
        
        par_plan_rows = (await session.execute(
            _sa_text("SELECT plan, COUNT(*) as nb FROM utilisateurs GROUP BY plan ORDER BY nb DESC")
        )).fetchall()
        
        # --- Travaux ---
        total_travaux = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM travaux")
        )).fetchone()[0]
        
        photos_stockees = (await session.execute(
            _sa_text("SELECT COUNT(*) FROM travaux WHERE statut IN ('termine', 'erreur')")
        )).fetchone()[0]
        
        par_type_rows = (await session.execute(
            _sa_text("SELECT type, COUNT(*) as nb FROM travaux GROUP BY type ORDER BY nb DESC")
        )).fetchall()
        
        par_statut_rows = (await session.execute(
            _sa_text("SELECT statut, COUNT(*) as nb FROM travaux GROUP BY statut ORDER BY nb DESC")
        )).fetchall()
        
        # --- Stockage (espace disque estimé depuis la DB) ---
        espace_rows = (await session.execute(
            _sa_text("""
                SELECT COALESCE(SUM(COALESCE(taille_original, 0)), 0) 
                     + COALESCE(SUM(COALESCE(taille_resultat, 0)), 0) 
                     as total_octets
                FROM travaux 
                WHERE statut IN ('termine', 'erreur')
            """)
        )).fetchone()
        espace_total_octets = espace_rows[0] if espace_rows else 0
        
        # Top 5 utilisateurs par espace utilisé
        top5_rows = (await session.execute(
            _sa_text("""
                SELECT u.email, 
                       COALESCE(SUM(COALESCE(t.taille_original, 0)), 0) 
                     + COALESCE(SUM(COALESCE(t.taille_resultat, 0)), 0) as espace_octets
                FROM travaux t
                JOIN utilisateurs u ON t.utilisateur_id = u.id
                WHERE t.statut IN ('termine', 'erreur')
                GROUP BY u.email
                ORDER BY espace_octets DESC
                LIMIT 5
            """)
        )).fetchall()
        
        # --- Crédits ---
        credits_rows = (await session.execute(
            _sa_text("""
                SELECT 
                    COALESCE(SUM(credits), 0) as total_distribues,
                    COALESCE((SELECT SUM(credits_utilises) FROM consommation_credits), 0) as total_consommes
                FROM utilisateurs
            """)
        )).fetchone()
        
        credits_actifs = (await session.execute(
            _sa_text("SELECT COALESCE(SUM(credits), 0) FROM utilisateurs")
        )).fetchone()[0]
    
    return {
        "utilisateurs": {
            "total": total_utilisateurs,
            "actifs_7j": actifs_7j,
            "actifs_30j": actifs_30j,
            "par_plan": {row[0] or "inconnu": row[1] for row in par_plan_rows},
        },
        "travaux": {
            "total": total_travaux,
            "photos_stockees": photos_stockees,
            "par_type": {row[0]: row[1] for row in par_type_rows},
            "par_statut": {row[0]: row[1] for row in par_statut_rows},
        },
        "stockage": {
            "espace_total_octets": espace_total_octets,
            "espace_total_mb": round(espace_total_octets / (1024 * 1024), 2),
            "top5_utilisateurs": [
                {"email": row[0], "espace_mb": round(row[1] / (1024 * 1024), 2)}
                for row in top5_rows
            ],
        },
        "credits": {
            "total_distribues": credits_rows[0] if credits_rows else 0,
            "total_consommes": credits_rows[1] if credits_rows else 0,
            "credits_actifs": credits_actifs,
        },
    }
```

---

### Tâche 12 : Planification du nettoyage (cron quotidien)

**Objectif :** Exécuter le nettoyage automatiquement (quotidiennement).

**Fichiers :**
- Modifier : `backend/app/main.py` (optionnel — via le cron Hermes)

**Option A — Cron Hermes (recommandé, déjà en place) :**

```python
# Via cronjob dans Hermes :
# cronjob action='create' schedule='0 3 * * *' 
# prompt='Appelle POST /api/admin/cleanup avec le header X-Admin-Key sur le backend Flashback (PORT 8000).'
```

**Option B — FastAPI BackgroundTasks :**

Pas recommandé pour un service de nettoyage — un cron externe est plus fiable.

---

### Tâche 13 : Tests

**Objectif :** Couvrir les nouveaux endpoints et la logique de rétention.

**Fichiers :**
- Créer/modifier : `backend/tests/test_history.py`
- Modifier : `backend/tests/conftest.py` (fixtures)

**Étape 1 : Test de l'endpoint préférences**

```python
def test_preferences_put(client, auth_headers):
    resp = client.put("/api/user/preferences", json={"retention_jours": 7}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["retention_jours"] == 7

def test_preferences_get(client, auth_headers):
    resp = client.get("/api/user/preferences", headers=auth_headers)
    assert resp.status_code == 200
    assert "retention_jours" in resp.json()

def test_preferences_invalid(client, auth_headers):
    resp = client.put("/api/user/preferences", json={"retention_jours": 5}, headers=auth_headers)
    assert resp.status_code == 400
```

**Étape 2 : Test suppression travail**

```python
def test_supprimer_travail(client, auth_headers):
    # Créer un travail puis le supprimer
    ...

def test_supprimer_tout_historique(client, auth_headers):
    ...
```

---

## Ordre d'exécution recommandé

1. **Tâche 1** → Migration DB unique (5 colonnes)
2. **Tâche 2** → Tailles de fichiers + `derniere_activite` (fondation dashboard)
3. **Tâche 3 & 4** → Queries (rétention, animation, suppression)
4. **Tâche 5 & 8** → Endpoints préférences + historique enrichi
5. **Tâche 6 & 7** → Endpoints suppression
6. **Tâche 9** → Fix animation (sauvegarde `chemin_animation`)
7. **Tâche 10** → Refonte nettoyage
8. **Tâche 11** → Endpoint dashboard admin
9. **Tâche 12** → Cron quotidien
10. **Tâche 13** → Tests

---

## Résumé des endpoints créés/modifiés

| Méthode | Endpoint | Auth | Description |
|---------|----------|------|-------------|
| `PUT` | `/api/user/preferences` | JWT | Définir rétention (7/30/90) |
| `GET` | `/api/user/preferences` | JWT | Lire rétention actuelle |
| `GET` | `/api/user/history` | JWT | Historique enrichi (+ URLs, expiration, tailles) |
| `DELETE` | `/api/user/history/{travail_id}` | JWT | Supprimer un travail + fichiers |
| `DELETE` | `/api/user/history` | JWT | Supprimer tout l'historique |
| `GET` | `/api/admin/dashboard` | X-Admin-Key | Dashboard admin (utilisateurs, travaux, stockage, crédits) |
| `POST` | `/api/admin/cleanup` | X-Admin-Key | (existant, refondu) Nettoyage selon rétention |

---

## Risques et points d'attention

| Risque | Mitigation |
|--------|-----------|
| Vidéos D-ID stockées en URL externe temporaire | Idéalement télécharger le MP4 pour stockage local (itération suivante) |
| Nettoyage concurrent avec un accès utilisateur | Utiliser `statut IN ('termine', 'erreur')` — ne pas toucher aux travaux en cours |
| PostgreSQL vs SQLite dans la requête de nettoyage | Utiliser SQLAlchemy ORM plutôt que du SQL brut |
| RGPD : droit à l'oubli | Les endpoints DELETE `/history` et `/history/{id}` couvrent ce besoin |
| Espace disque avec beaucoup d'animations | La rétention configurable permet de limiter, mais monitorer l'espace disque |
