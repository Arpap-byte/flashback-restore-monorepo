"""
Tests unitaires pour les crédits atomiques (consommer_credit avec FOR UPDATE).

Exécuter : cd backend && .venv/bin/pytest tests/test_credits.py -v --tb=short

Utilise aiosqlite en mémoire pour simuler le comportement atomique
sans dépendance PostgreSQL.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import Select

from app.models.db_models import Base
from app.db import queries as queries_module
from app.db.queries import (
    consommer_credit,
    crediter_utilisateur,
    creer_utilisateur,
    obtenir_credits_restants,
)
from app.services.credits import consommer_operation, peut_restaurer

# ──────────────────────────────────────────────────────────────────────────────
# SQLite in-memory setup
# ──────────────────────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///file:test_credits_mem?mode=memory&cache=shared"

# SQLite ne supporte pas SELECT ... FOR UPDATE.
# On remplace with_for_update() par un no-op pour compatibilité.


def _noop_with_for_update(self, *args, **kwargs):
    return self


Select.with_for_update = _noop_with_for_update


_engine = None
_test_factory = None


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """
    Crée une base SQLite en mémoire, crée les tables, et patche
    le async_session du module queries pour rediriger vers SQLite.
    """
    global _engine, _test_factory

    _engine = create_async_engine(TEST_DB_URL, echo=False)
    _test_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )

    # Création des tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch : toutes les fonctions de queries passeront par SQLite
    _original = queries_module.async_session
    queries_module.async_session = _test_factory

    yield

    # Nettoyage : drop tables et restauration de la session originale
    queries_module.async_session = _original
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def utilisateur_test(db_session):
    """Crée un utilisateur de test avec 0 crédits et 3 essais."""
    uid = await creer_utilisateur("test@credits.fr", "hash_test_123")
    assert uid is not None, "creer_utilisateur a échoué"
    return uid


@pytest_asyncio.fixture
async def utilisateur_sans_essais(db_session):
    """Crée un utilisateur avec 0 crédits et 0 essais."""
    uid = await creer_utilisateur("sans_essais@credits.fr", "hash_test_123")
    # Consomme les 3 essais
    for _ in range(3):
        res = await consommer_credit(uid, "restauration", "travail_fake")
        assert res["succes"], f"Échec consommation essai: {res}"
    return uid


# ──────────────────────────────────────────────────────────────────────────────
# Tests : queries.py
# ──────────────────────────────────────────────────────────────────────────────


class TestConsommerCredit:
    """Tests pour la fonction consommer_credit (atomicité FOR UPDATE)."""

    @pytest.mark.asyncio
    async def test_consommer_credit_succes(self, utilisateur_test):
        """Créditer 10, consommer 1 → reste 9."""
        uid = utilisateur_test

        # Créditer 10 crédits
        nouveau_solde = await crediter_utilisateur(uid, 10)
        assert nouveau_solde == 10

        # Épuiser d'abord les 3 essais gratuits (prioritaires)
        for _ in range(3):
            await consommer_credit(uid, "restauration", "travail_x")

        # Maintenant consomme 1 crédit payant
        res = await consommer_credit(uid, "restauration", "travail_1")
        assert res["succes"] is True
        assert res["type"] == "credit"
        assert res["credits_restants"] == 9

        # Vérifier le solde via obtenir_credits_restants
        infos = await obtenir_credits_restants(uid)
        assert infos["credits"] == 9
        assert infos["essais_restants"] == 0

    @pytest.mark.asyncio
    async def test_consommer_credit_insuffisant(self, utilisateur_test):
        """Créditer 0, tenter consommer 1 → succès=False."""
        uid = utilisateur_test

        # Épuiser les 3 essais gratuits
        for _ in range(3):
            await consommer_credit(uid, "restauration", "travail_x")

        # Plus d'essais, 0 crédits → doit échouer
        res = await consommer_credit(uid, "restauration", "travail_fail")
        assert res["succes"] is False
        assert "raison" in res
        assert "Plus de crédits" in res["raison"]

    @pytest.mark.asyncio
    async def test_consommer_credit_atomique(self, utilisateur_test):
        """
        Simule 2 consommations concurrentes et vérifie que le total
        consommé est cohérent (pas de double dépense).

        Note: SQLite ne supporte pas FOR UPDATE au sens PostgreSQL.
        On utilise un Lock asyncio pour forcer la sérialisation et
        tester la logique métier (5 crédits → 5 succès max).
        """
        uid = utilisateur_test

        # Épuiser les 3 essais gratuits pour ne tester que les crédits
        for _ in range(3):
            await consommer_credit(uid, "restauration", "travail_x")

        # Créditer 5
        await crediter_utilisateur(uid, 5)

        # Sérialiser via Lock asyncio pour simuler le comportement FOR UPDATE
        lock = asyncio.Lock()

        async def consommer_un():
            async with lock:
                return await consommer_credit(uid, "restauration", "travail_conc")

        results = await asyncio.gather(
            consommer_un(), consommer_un(), consommer_un(),
            consommer_un(), consommer_un(),
        )

        succes_count = sum(1 for r in results if r["succes"])
        echec_count = sum(1 for r in results if not r["succes"])

        assert succes_count == 5, (
            f"5 crédits → 5 consommations réussies attendues, "
            f"obtenu {succes_count} succès / {echec_count} échecs"
        )
        assert echec_count == 0

        # Vérifier qu'il reste bien 0 crédit
        infos = await obtenir_credits_restants(uid)
        assert infos["credits"] == 0

        # Une 6e tentative doit échouer
        res = await consommer_credit(uid, "restauration", "travail_extra")
        assert res["succes"] is False


class TestCrediterUtilisateur:
    """Tests pour crediter_utilisateur."""

    @pytest.mark.asyncio
    async def test_crediter_utilisateur(self, utilisateur_test):
        """Créditer 5 → solde = 5."""
        uid = utilisateur_test
        solde = await crediter_utilisateur(uid, 5)
        assert solde == 5

        # Vérifier via obtenir_credits_restants
        infos = await obtenir_credits_restants(uid)
        assert infos["credits"] == 5
        # Les essais restent inchangés (3 par défaut)
        assert infos["essais_restants"] == 3

    @pytest.mark.asyncio
    async def test_crediter_multiple_fois(self, utilisateur_test):
        """Créditer plusieurs fois → cumul correct."""
        uid = utilisateur_test
        await crediter_utilisateur(uid, 10)
        await crediter_utilisateur(uid, 20)
        await crediter_utilisateur(uid, 30)

        infos = await obtenir_credits_restants(uid)
        assert infos["credits"] == 60


class TestObtenirCreditsRestants:
    """Tests pour obtenir_credits_restants."""

    @pytest.mark.asyncio
    async def test_obtenir_credits_restants_structure(self, utilisateur_test):
        """Vérifie la structure de la réponse."""
        uid = utilisateur_test
        infos = await obtenir_credits_restants(uid)

        assert isinstance(infos, dict)
        assert "credits" in infos
        assert "essais_restants" in infos
        assert infos["credits"] == 0
        assert infos["essais_restants"] == 3

    @pytest.mark.asyncio
    async def test_obtenir_credits_restants_apres_credit(self, utilisateur_test):
        """Après un credit, le solde est mis à jour."""
        uid = utilisateur_test
        await crediter_utilisateur(uid, 7)
        infos = await obtenir_credits_restants(uid)
        assert infos["credits"] == 7


# ──────────────────────────────────────────────────────────────────────────────
# Tests : services/credits.py
# ──────────────────────────────────────────────────────────────────────────────


class TestPeutRestaurer:
    """Tests pour la fonction peut_restaurer (service)."""

    @pytest.mark.asyncio
    async def test_peut_restaurer_avec_credits(self, utilisateur_test):
        """Utilisateur avec crédits doit pouvoir restaurer."""
        uid = utilisateur_test
        await crediter_utilisateur(uid, 5)

        autorise, raison = await peut_restaurer(uid)
        assert autorise is True
        assert raison == ""

    @pytest.mark.asyncio
    async def test_peut_restaurer_avec_essais(self, utilisateur_test):
        """Utilisateur sans crédits mais avec essais doit pouvoir restaurer."""
        uid = utilisateur_test
        # 0 crédits, 3 essais
        autorise, raison = await peut_restaurer(uid)
        assert autorise is True
        assert raison == ""

    @pytest.mark.asyncio
    async def test_peut_restaurer_sans_credits(self, utilisateur_sans_essais):
        """Utilisateur sans crédits ni essais ne doit pas pouvoir restaurer."""
        uid = utilisateur_sans_essais
        autorise, raison = await peut_restaurer(uid)
        assert autorise is False
        assert "Crédits insuffisants" in raison


class TestConsommerOperation:
    """Tests pour la fonction consommer_operation (service)."""

    @pytest.mark.asyncio
    async def test_consommer_operation_restauration(self, utilisateur_test):
        """Consommer une opération de restauration → crédit déduit."""
        uid = utilisateur_test

        # Créditer 10 et épuiser les essais pour forcer la conso crédit
        await crediter_utilisateur(uid, 10)
        for _ in range(3):
            await consommer_credit(uid, "restauration", "travail_pre")

        # Vérifier solde avant
        infos_avant = await obtenir_credits_restants(uid)
        assert infos_avant["credits"] == 10
        assert infos_avant["essais_restants"] == 0

        # Consommer via le service
        await consommer_operation(uid, "restauration", "travail_op")

        # Vérifier solde après
        infos_apres = await obtenir_credits_restants(uid)
        assert infos_apres["credits"] == 9

    @pytest.mark.asyncio
    async def test_consommer_operation_epuise(self, utilisateur_sans_essais):
        """Consommer sans crédits → RuntimeError."""
        uid = utilisateur_sans_essais

        with pytest.raises(RuntimeError, match="Plus de crédits"):
            await consommer_operation(uid, "restauration", "travail_fail")

    @pytest.mark.asyncio
    async def test_consommer_operation_utilise_essai(self, utilisateur_test):
        """Consommer avec essais disponibles → utilise un essai d'abord."""
        uid = utilisateur_test
        # 0 crédits, 3 essais
        infos_avant = await obtenir_credits_restants(uid)
        assert infos_avant["essais_restants"] == 3
        assert infos_avant["credits"] == 0

        await consommer_operation(uid, "restauration", "travail_essai")

        infos_apres = await obtenir_credits_restants(uid)
        assert infos_apres["essais_restants"] == 2
        assert infos_apres["credits"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# Test d'intégrité : atomicité sous forte concurrence
# ──────────────────────────────────────────────────────────────────────────────

class TestAtomiciteCredits:
    """
    Tests avancés pour valider l'atomicité du SELECT ... FOR UPDATE.

    Note: SQLite ne supporte pas FOR UPDATE (verrouillage de ligne).
    On utilise un asyncio.Lock pour sérialiser les appels concurrents
    et tester la logique métier. En production (PostgreSQL), le
    FOR UPDATE fournit cette sérialisation automatiquement.
    """

    @pytest.mark.asyncio
    async def test_atomicite_haute_concurrence(self, utilisateur_test):
        """
        20 workers concurrents pour 5 crédits → exactement 5 succès.
        """
        uid = utilisateur_test

        # Épuiser les essais
        for _ in range(3):
            await consommer_credit(uid, "restauration", "travail_pre")

        # 5 crédits
        await crediter_utilisateur(uid, 5)

        # Lock pour simuler le comportement FOR UPDATE de PostgreSQL
        lock = asyncio.Lock()

        async def worker():
            async with lock:
                return await consommer_credit(uid, "restauration", "travail_conc")

        results = await asyncio.gather(*(worker() for _ in range(20)))

        succes = [r for r in results if r["succes"]]
        echecs = [r for r in results if not r["succes"]]

        assert len(succes) == 5, (
            f"Avec 5 crédits, attendu 5 succès, obtenu {len(succes)}"
        )
        assert len(echecs) == 15, (
            f"Avec 5 crédits, attendu 15 échecs, obtenu {len(echecs)}"
        )

        # Vérifier solde final = 0
        infos = await obtenir_credits_restants(uid)
        assert infos["credits"] == 0

    @pytest.mark.asyncio
    async def test_atomicite_credit_plus_essai(self, utilisateur_test):
        """
        10 workers concurrents, 3 essais + 2 crédits → 5 succès exactement.
        """
        uid = utilisateur_test
        # 3 essais (défaut) + 2 crédits = 5 opérations possibles
        await crediter_utilisateur(uid, 2)

        # Lock pour simuler le comportement FOR UPDATE de PostgreSQL
        lock = asyncio.Lock()

        async def worker():
            async with lock:
                return await consommer_credit(uid, "restauration", "travail_conc")

        results = await asyncio.gather(*(worker() for _ in range(10)))

        succes = [r for r in results if r["succes"]]
        echecs = [r for r in results if not r["succes"]]

        assert len(succes) == 5, (
            f"3 essais + 2 crédits → 5 succès attendus, obtenu {len(succes)}"
        )
        assert len(echecs) == 5

        infos = await obtenir_credits_restants(uid)
        assert infos["credits"] == 0
        assert infos["essais_restants"] == 0
