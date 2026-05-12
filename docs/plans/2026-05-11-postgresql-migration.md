# Migration PostgreSQL — Plan d'implémentation

> **Pour Hermes :** Utiliser subagent-driven-development pour implémenter ce plan tâche par tâche.

**Objectif :** Migrer la base de données de SQLite (sqlite3 brut) vers PostgreSQL via SQLAlchemy + Alembic, sans interruption de service.

**Architecture :** Remplacer `database.py` (1124 lignes, SQL brut) par des modèles SQLAlchemy + sessions async/await. PostgreSQL déjà déclaré dans docker-compose mais jamais connecté. On utilisera PostgreSQL local (Docker) ou externe selon la config `DATABASE_URL`.

**Stack :** Python 3.11, SQLAlchemy 2.0 (async), Alembic, asyncpg, PostgreSQL 16

**Durée estimée :** 4-6h avec agents spécialisés

---

## Préparation — Analyse du schéma actuel

### Tables et relations :

| Table | Lignes | Relations |
|-------|--------|-----------|
| `utilisateurs` | 8 colonnes | parent de travaux, essais, achats, consommation, reset_mdp, audit |
| `travaux` | 11 colonnes | FK → utilisateurs, référencé par essais, consommation |
| `abonnements` | 9 colonnes | standalone (lié à Stripe) |
| `essais_gratuits` | 5 colonnes | FK → utilisateurs, travaux |
| `achats_credits` | 6 colonnes | FK → utilisateurs |
| `consommation_credits` | 6 colonnes | FK → utilisateurs, travaux |
| `reinitialisation_mdp` | 7 colonnes | FK → utilisateurs |
| `audit_logs` | 9 colonnes | FK → utilisateurs |

### Fonctions à migrer (database.py) :
- `initialiser_base()` → Alembic migrations
- `creer_utilisateur()`, `trouver_utilisateur_par_email()`, `obtenir_utilisateur()`, `maj_derniere_connexion()`
- `mettre_a_jour_mot_de_passe()`, `stocker_token_reinitialisation()`, `valider_token_reinitialisation()`
- `creer_travail()`, `mettre_a_jour_travail()`, `obtenir_travail()`, `obtenir_travaux_utilisateur()`
- `consommer_credit()`, `crediter_utilisateur()`, `decrementer_essais()`
- `obtenir_plan_utilisateur()`, `peut_animer()`, `enregistrer_animation()`
- `enregistrer_essai_gratuit()`
- `creer_ou_maj_abonnement()`, `maj_statut_abonnement()`, `attribuer_credits_abonnement()`
- `enregistrer_achat_credits()`
- `consulter_audit_logs()`

---

## Phase 0 — Infrastructure PostgreSQL (30 min)

### T0.1 : Installer PostgreSQL si pas déjà dispo
```bash
# Vérifier si PostgreSQL est déjà dans Docker
docker ps | grep postgres
# Si non : le docker-compose a déjà un service db (postgres:16-alpine)
# → le lancer : docker compose -f /root/flashback-restore-monorepo/docker-compose.yml up -d db
```
**Vérification :** `docker exec flashback-db pg_isready`

### T0.2 : Créer la base de données
```bash
docker exec flashback-db psql -U flashback -c "CREATE DATABASE flashback;" 2>/dev/null || echo "already exists"
```

### T0.3 : Installer les dépendances Python
```bash
cd /root/flashback-restore-monorepo/backend
.venv/bin/pip install sqlalchemy[asyncio] alembic asyncpg psycopg2-binary
```

### T0.4 : Initialiser Alembic
```bash
cd /root/flashback-restore-monorepo/backend
.venv/bin/alembic init alembic
```
Configurer `alembic.ini` → `sqlalchemy.url = postgresql+asyncpg://flashback:flashback@localhost:5432/flashback`

---

## Phase 1 — Modèles SQLAlchemy (45 min)

### T1.1 : Créer `backend/app/models/db_models.py`
- Déclarer les 8 tables en classes SQLAlchemy (Base = declarative_base())
- Types : TEXT → String, INTEGER → Integer, REAL → Float
- ForeignKey et relationships pour toutes les FK
- Colonnes avec server_default= pour les valeurs par défaut
- CHECK constraints via `__table_args__`

```python
# Exemple pour utilisateurs
class Utilisateur(Base):
    __tablename__ = "utilisateurs"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    essais_restants = Column(Integer, nullable=False, server_default="3")
    credits = Column(Integer, nullable=False, server_default="0")
    est_abonne = Column(Integer, nullable=False, server_default="0")
    cree_le = Column(String, nullable=False)
    derniere_connexion = Column(String, nullable=False)
```

**Vérification :** `python -c "from app.models.db_models import Base; print('OK')"`

### T1.2 : Créer la session async SQLAlchemy
Fichier : `backend/app/db/session.py`
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"), echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

### T1.3 : Générer la migration Alembic initiale
```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "initial_schema_from_sqlite"
.venv/bin/alembic upgrade head
```
**Vérification :** `docker exec flashback-db psql -U flashback -d flashback -c "\dt"` — doit lister les 8 tables

---

## Phase 2 — Réécriture de database.py en async SQLAlchemy (90 min)

### T2.1 : Créer `backend/app/db/queries.py` — fonctions CRUD utilisateurs
- `creer_utilisateur(email, password_hash)` → INSERT RETURNING
- `trouver_utilisateur_par_email(email)` → SELECT WHERE
- `obtenir_utilisateur(user_id)` → SELECT BY ID
- `maj_derniere_connexion(user_id)` → UPDATE
- `mettre_a_jour_mot_de_passe(user_id, hash)` → UPDATE
- Toutes les fonctions async avec `async_session`

**Vérification :** Test unitaire simple créant un utilisateur via la nouvelle fonction

### T2.2 : Fonctions travaux
- `creer_travail()` → INSERT
- `mettre_a_jour_travail()` → UPDATE
- `obtenir_travail()` → SELECT
- `obtenir_travaux_utilisateur()` → SELECT with JOIN

### T2.3 : Fonctions crédits/essais (CRITIQUE — race condition)
- `consommer_credit(user_id)` → UPDATE atomique avec `WHERE credits > 0 RETURNING credits`
- `decrementer_essais(user_id)` → UPDATE avec `WHERE essais_restants > 0`
- `crediter_utilisateur(user_id, nb)` → UPDATE
- `obtenir_plan_utilisateur(user_id)` → SELECT avec cache
- `peut_animer(user_id)` → SELECT + vérification
- `enregistrer_animation(user_id)` → UPDATE compteur
- `enregistrer_essai_gratuit(user_id, type, travail_id)` → INSERT

### T2.4 : Fonctions Stripe/abonnement
- `creer_ou_maj_abonnement()` → UPSERT
- `maj_statut_abonnement()` → UPDATE
- `attribuer_credits_abonnement()` → UPDATE avec transaction
- `enregistrer_achat_credits()` → INSERT

### T2.5 : Fonctions audit/reset
- `stocker_token_reinitialisation()` → INSERT
- `valider_token_reinitialisation()` → SELECT + UPDATE
- `consulter_audit_logs()` → SELECT with filters

---

## Phase 3 — Intégration (45 min)

### T3.1 : Mettre à jour `database.py`
- Garder le module comme point d'entrée
- Réexporter toutes les fonctions depuis `queries.py`
- Supprimer le code SQLite brut
- `initialiser_base()` → appeler Alembic ou juste loguer (les migrations sont gérées)

### T3.2 : Mettre à jour les imports dans routes/auth/services
- Remplacer `from app.db.database import ...` par les imports existants (ils pointent déjà vers database.py)
- Les signatures de fonctions doivent être IDENTIQUES (mêmes noms, mêmes params, mêmes retours)
- Si des fonctions sont sync → wrapper async_to_sync dans FastAPI (qui supporte nativement l'async)

### T3.3 : Mettre à jour la config
- `DATABASE_URL` doit pointer vers PostgreSQL
- Tester la connexion au démarrage

**Vérification :** `curl http://localhost:8000/api/health` → `db_disponible: true`

---

## Phase 4 — Tests et validation (30 min)

### T4.1 : Tests unitaires
- Test création utilisateur
- Test consommation crédit atomique
- Test transaction rollback

### T4.2 : Tests d'intégration
- Parcours complet : register → login → upload → restore → animate
- Vérification que les crédits sont correctement débités
- Vérification historique travaux

### T4.3 : Test de charge
- 50 requêtes concurrentes sur `/api/restore`
- Vérifier que les crédits ne sont pas consommés en double (race condition fixée)

---

## Phase 5 — Déploiement (15 min)

### T5.1 : Mettre à jour docker-compose ou utiliser le service existant
- Le service `db` (postgres:16-alpine) est déjà dans docker-compose.yml
- Le lancer si pas déjà fait

### T5.2 : Mettre à jour le fichier .env
- `DATABASE_URL=postgresql+asyncpg://flashback:flashback@localhost:5432/flashback`

### T5.3 : Appliquer les migrations
```bash
cd /root/flashback-restore-monorepo/backend
.venv/bin/alembic upgrade head
```

### T5.4 : Migrer les données existantes (SQLite → PostgreSQL)
- Script one-shot : lire SQLite, écrire PostgreSQL
- Conserver le fichier SQLite comme backup

### T5.5 : Redémarrer le backend
```bash
systemctl restart flashback-backend
curl http://localhost:8000/api/health
```

---

## Risques et mitigations

| Risque | Probabilité | Mitigation |
|--------|-------------|------------|
| Race condition crédits | Élevée | UPDATE atomique PostgreSQL (RETURNING) |
| Incompatibilité signatures | Moyenne | Garder les mêmes noms/params, wrapper si besoin |
| Perte de données migration | Faible | Backup SQLite, script de migration testé |
| Downtime | Faible | Migration sans interruption (nouvelle DB, puis switch) |
| Dépendances cassées | Faible | pip install dans le venv existant |
