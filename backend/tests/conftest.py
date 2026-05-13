"""
Infrastructure de test partagée pour Flashback Restore.

Fournit :
- Moteur SQLAlchemy session-scoped (SQLite en mémoire via aiosqlite)
- Session DB function-scoped avec isolation par rollback de transaction
- Client HTTP FastAPI (TestClient)
- Headers admin préconfigurés
- Compatibilité SQLite : désactive FOR UPDATE (non supporté)

Utilisation :
    def test_exemple(client, admin_headers):
        res = client.get("/api/stats", headers=admin_headers)
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_db(db_session):
        uid = await creer_utilisateur("test@test.com", "hash")
        ...

Règles :
- Pas de variables globales mutables dans les fixtures (Sonnet P1-B)
- Pas de asyncio.run() au niveau module
- Chaque fixture est documentée avec docstring
- Les fixtures sont auto-nettoyantes (rollback de transaction)
"""

import os

os.environ["TESTING"] = "true"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.sql import Select

from app.models.db_models import Base

# ---------------------------------------------------------------------------
# Constantes magiques externalisées (recommandation Sonnet P1-C)
# ---------------------------------------------------------------------------
ESSAIS_GRATUITS_DEFAUT = 3
CREDITS_PACK_BASE = 10

TEST_DB_URL = "sqlite+aiosqlite:///file:flashback_test_mem?mode=memory&cache=shared"

# ---------------------------------------------------------------------------
# Compatibilité SQLite : désactiver FOR UPDATE (non supporté par SQLite)
# ---------------------------------------------------------------------------


def _noop_with_for_update(self, *args, **kwargs):
    """Remplace with_for_update() par un no-op pour compatibilité SQLite."""
    return self


Select.with_for_update = _noop_with_for_update

# ---------------------------------------------------------------------------
# Fixtures session-scoped (créées une fois pour toute la session de test)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Moteur SQLAlchemy partagé pour toute la session de test.

    Crée un moteur SQLite en mémoire et initialise les tables une seule fois.
    Le moteur vit toute la durée de la session pytest (pas de dispose prématuré).
    """
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    # Pas de drop — le moteur vit le temps de la session.
    # SQLite in-memory est automatiquement nettoyé à la fin du processus.
    await engine.dispose()


# ---------------------------------------------------------------------------
# Fixtures function-scoped (créées et nettoyées pour chaque test)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Session SQLAlchemy isolée par test, avec rollback automatique.

    Stratégie d'isolation :
    1. Ouvre une connexion et une transaction sur le moteur partagé
    2. Crée une session liée à cette connexion
    3. Monkey-patch queries.async_session pour rediriger vers notre session
    4. Remplace session.commit() par session.flush() pour garder toutes
       les modifications dans la transaction de test
    5. Après le test : rollback de la transaction → isolation parfaite

    Le monkey-patch est restauré après chaque test.
    """
    from contextlib import asynccontextmanager

    import app.db.queries as queries

    async with db_engine.connect() as conn:
        async with conn.begin() as transaction:

            @asynccontextmanager
            async def _test_session():
                """Context manager qui crée une session liée à la transaction de test.

                Remplace commit par flush pour que toutes les écritures restent
                dans la transaction — le rollback final du fixture nettoie tout.
                """
                session = AsyncSession(bind=conn, expire_on_commit=False)
                # Intercepter commit → flush pour rester dans la transaction
                _original_commit = session.commit
                session.commit = session.flush  # type: ignore[method-assign]
                try:
                    yield session
                finally:
                    session.commit = _original_commit  # type: ignore[method-assign]
                    await session.close()

            # Sauvegarder et remplacer la session factory du module queries
            _original_session = queries.async_session
            queries.async_session = _test_session

            yield conn

            # Rollback : toutes les modifications sont annulées
            await transaction.rollback()
            # Restaurer la session factory originale
            queries.async_session = _original_session


# ---------------------------------------------------------------------------
# Fixtures HTTP (client FastAPI + headers)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def client():
    """Client HTTP FastAPI (TestClient) pour les tests d'intégration.

    Utilise TestClient de Starlette/FastAPI qui permet de tester les endpoints
    sans démarrer de serveur HTTP réel.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture(scope="function")
def admin_headers():
    """Headers HTTP avec X-Admin-Key valide (depuis la configuration).

    Utilise ADMIN_API_KEY défini dans app.config (chargé depuis .env).
    """
    from app.config import ADMIN_API_KEY

    return {"X-Admin-Key": ADMIN_API_KEY}
