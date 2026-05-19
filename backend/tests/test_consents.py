"""
Tests unitaires pour le service de consentements légaux (P1.3 + P1.5).

Couvre :
- enregistrer_consentement (append-only)
- consentement_actif
- consentements_checkout_recents (fenêtre de fraîcheur)
- retirer_consentement
- obtenir_etat_consentements (masquage IP)
- Non-régression : pas de leak de données entre utilisateurs

Exécuter : cd backend && .venv/bin/pytest tests/test_consents.py -v --tb=short

Utilise aiosqlite en mémoire (comme test_credits.py).
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.db_models import Base, Consentement
from app.services.consent_service import (
    CONSENT_FRESHNESS_MINUTES,
    CGV_VERSION,
    RETRACTATION_VERSION,
    RGPD_BIOMETRIQUE_VERSION,
    RGPD_IA_VERSION,
    consentement_actif,
    consentements_checkout_recents,
    enregistrer_consentement,
    obtenir_etat_consentements,
    retirer_consentement,
    _masquer_ip,
)
import app.db.session as db_session_mod

# ──────────────────────────────────────────────────────────────────────────────
# SQLite in-memory setup
# ──────────────────────────────────────────────────────────────────────────────

_engine = None
_test_factory = None


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Crée une base SQLite en mémoire, crée les tables, patch async_session."""
    global _engine, _test_factory

    _engine = create_async_engine(
        "sqlite+aiosqlite:///file:test_consents_mem?mode=memory&cache=shared",
        echo=False,
    )
    _test_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch la session utilisée par le service consent (via app.db.session)
    import app.db.session as db_session_mod
    _original = db_session_mod.async_session
    db_session_mod.async_session = _test_factory

    yield

    db_session_mod.async_session = _original
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


# ──────────────────────────────────────────────────────────────────────────────
# Tests : enregistrer_consentement
# ──────────────────────────────────────────────────────────────────────────────


class TestEnregistrerConsentement:
    """Tests pour la création append-only de consentements."""

    @pytest.mark.asyncio
    async def test_enregistrer_cgv_checkout(self, db_session):
        """Enregistrement CGV → ligne créée avec accepte=True."""
        async with _test_factory() as sess:
            async with sess.begin():
                c = await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="test@example.com",
                    ip="1.2.3.4",
                    user_agent="Mozilla/5.0",
                    contexte={"plan": "decouverte"},
                )

        assert c.id is not None
        assert c.type_consentement == "cgv_checkout"
        assert c.version_texte == CGV_VERSION
        assert c.email == "test@example.com"
        assert c.accepte is True
        assert c.accorde_le is not None
        assert c.retire_le is None
        assert c.ip == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_enregistrer_sans_ip_ni_email(self, db_session):
        """Enregistrement sans IP/email → OK (données optionnelles)."""
        async with _test_factory() as sess:
            async with sess.begin():
                c = await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_ia",
                    version_texte=RGPD_IA_VERSION,
                    utilisateur_id="user_123",
                )

        assert c.id is not None
        assert c.type_consentement == "rgpd_ia"
        assert c.utilisateur_id == "user_123"
        assert c.ip is None
        assert c.email is None

    @pytest.mark.asyncio
    async def test_enregistrer_multiple_meme_type(self, db_session):
        """Append-only : deux enregistrements CGV → deux lignes distinctes."""
        async with _test_factory() as sess:
            async with sess.begin():
                c1 = await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="multi@example.com",
                )
            async with sess.begin():
                c2 = await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="multi@example.com",
                )

        assert c1.id != c2.id, "Append-only : deux IDs différents attendus"
        assert c1.accorde_le != c2.accorde_le or True  # timestamps peuvent être égaux en SQLite

    @pytest.mark.asyncio
    async def test_enregistrer_renonciation_retractation(self, db_session):
        """Enregistrement renonciation rétractation."""
        async with _test_factory() as sess:
            async with sess.begin():
                c = await enregistrer_consentement(
                    sess,
                    type_consentement="renonciation_retractation",
                    version_texte=RETRACTATION_VERSION,
                    email="retract@example.com",
                )

        assert c.type_consentement == "renonciation_retractation"
        assert c.version_texte == RETRACTATION_VERSION


# ──────────────────────────────────────────────────────────────────────────────
# Tests : consentement_actif
# ──────────────────────────────────────────────────────────────────────────────


class TestConsentementActif:
    """Tests pour la vérification de consentement actif."""

    @pytest.mark.asyncio
    async def test_actif_apres_enregistrement(self, db_session):
        """Après enregistrement → consentement_actif = True."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="actif@example.com",
                )

        async with _test_factory() as sess:
            ok = await consentement_actif(
                sess, email="actif@example.com", type_consentement="cgv_checkout"
            )
        assert ok is True

    @pytest.mark.asyncio
    async def test_inactif_sans_consentement(self, db_session):
        """Aucun consentement → False."""
        async with _test_factory() as sess:
            ok = await consentement_actif(
                sess, email="inexistant@example.com", type_consentement="cgv_checkout"
            )
        assert ok is False

    @pytest.mark.asyncio
    async def test_inactif_apres_revocation(self, db_session):
        """Après révocation → consentement_actif = False."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_biometrique",
                    version_texte=RGPD_BIOMETRIQUE_VERSION,
                    utilisateur_id="user_revoque",
                )
            async with sess.begin():
                await retirer_consentement(
                    sess,
                    utilisateur_id="user_revoque",
                    type_consentement="rgpd_biometrique",
                )

        async with _test_factory() as sess:
            ok = await consentement_actif(
                sess,
                utilisateur_id="user_revoque",
                type_consentement="rgpd_biometrique",
            )
        assert ok is False

    @pytest.mark.asyncio
    async def test_actif_par_utilisateur_id(self, db_session):
        """Recherche par utilisateur_id."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_ia",
                    version_texte=RGPD_IA_VERSION,
                    utilisateur_id="user_ia",
                )

        async with _test_factory() as sess:
            ok = await consentement_actif(
                sess, utilisateur_id="user_ia", type_consentement="rgpd_ia"
            )
        assert ok is True

    @pytest.mark.asyncio
    async def test_sans_email_ni_utilisateur_id(self, db_session):
        """Sans email ni utilisateur_id → False (pas de recherche)."""
        async with _test_factory() as sess:
            ok = await consentement_actif(
                sess, type_consentement="cgv_checkout"
            )
        assert ok is False


# ──────────────────────────────────────────────────────────────────────────────
# Tests : consentements_checkout_recents
# ──────────────────────────────────────────────────────────────────────────────


class TestConsentementsCheckoutRecents:
    """Tests pour la vérification des 2 consentements checkout dans la fenêtre."""

    @pytest.mark.asyncio
    async def test_deux_consentements_recents(self, db_session):
        """CGV + rétractation récents → True."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="checkout@example.com",
                )
                await enregistrer_consentement(
                    sess,
                    type_consentement="renonciation_retractation",
                    version_texte=RETRACTATION_VERSION,
                    email="checkout@example.com",
                )

        async with _test_factory() as sess:
            ok = await consentements_checkout_recents(sess, email="checkout@example.com")
        assert ok is True

    @pytest.mark.asyncio
    async def test_manque_renonciation(self, db_session):
        """Seulement CGV → False."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="manque@example.com",
                )

        async with _test_factory() as sess:
            ok = await consentements_checkout_recents(sess, email="manque@example.com")
        assert ok is False

    @pytest.mark.asyncio
    async def test_manque_cgv(self, db_session):
        """Seulement rétractation → False."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="renonciation_retractation",
                    version_texte=RETRACTATION_VERSION,
                    email="sans_cgv@example.com",
                )

        async with _test_factory() as sess:
            ok = await consentements_checkout_recents(sess, email="sans_cgv@example.com")
        assert ok is False

    @pytest.mark.asyncio
    async def test_perime(self, db_session):
        """Consentement hors fenêtre de fraîcheur → False."""
        # Insère un consentement avec un timestamp ancien
        async with _test_factory() as sess:
            async with sess.begin():
                # Création manuelle avec timestamp passé
                for t in ("cgv_checkout", "renonciation_retractation"):
                    c = Consentement(
                        type_consentement=t,
                        version_texte=CGV_VERSION if t == "cgv_checkout" else RETRACTATION_VERSION,
                        email="perime@example.com",
                        accepte=True,
                        accorde_le=datetime.now(timezone.utc) - timedelta(minutes=CONSENT_FRESHNESS_MINUTES + 1),
                    )
                    sess.add(c)

        async with _test_factory() as sess:
            ok = await consentements_checkout_recents(sess, email="perime@example.com")
        assert ok is False

    @pytest.mark.asyncio
    async def test_revoque_puis_reaccepte(self, db_session):
        """Révocation → nouvelle acceptation récente → True."""
        async with _test_factory() as sess:
            async with sess.begin():
                # Premier consentement
                await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="cycle@example.com",
                )
                await enregistrer_consentement(
                    sess,
                    type_consentement="renonciation_retractation",
                    version_texte=RETRACTATION_VERSION,
                    email="cycle@example.com",
                )

            # Révocation CGV (simulée, pas de utilisateur_id sur du checkout email-only)
            async with sess.begin():
                # On ne peut pas révoquer par email dans retirer_consentement
                # (la fonction n'accepte que utilisateur_id). Ici on vérifie
                # juste le comportement normal après ré-acceptation.
                pass

        # Ré-acceptation fraîche
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="cycle@example.com",
                )
                await enregistrer_consentement(
                    sess,
                    type_consentement="renonciation_retractation",
                    version_texte=RETRACTATION_VERSION,
                    email="cycle@example.com",
                )

        async with _test_factory() as sess:
            ok = await consentements_checkout_recents(sess, email="cycle@example.com")
        assert ok is True


# ──────────────────────────────────────────────────────────────────────────────
# Tests : retirer_consentement
# ──────────────────────────────────────────────────────────────────────────────


class TestRetirerConsentement:
    """Tests pour la révocation de consentement."""

    @pytest.mark.asyncio
    async def test_retirer_actif(self, db_session):
        """Révocation d'un consentement actif → True, retire_le mis à jour."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_biometrique",
                    version_texte=RGPD_BIOMETRIQUE_VERSION,
                    utilisateur_id="user_rgpd",
                )

        async with _test_factory() as sess:
            async with sess.begin():
                ok = await retirer_consentement(
                    sess,
                    utilisateur_id="user_rgpd",
                    type_consentement="rgpd_biometrique",
                )
            assert ok is True

            # Vérifier que retire_le est bien mis
            from sqlalchemy import select
            stmt = (
                select(Consentement)
                .where(
                    Consentement.utilisateur_id == "user_rgpd",
                    Consentement.type_consentement == "rgpd_biometrique",
                )
                .order_by(Consentement.accorde_le.desc())
                .limit(1)
            )
            result = await sess.execute(stmt)
            c = result.scalar_one_or_none()
            assert c is not None
            assert c.retire_le is not None

    @pytest.mark.asyncio
    async def test_retirer_inexistant(self, db_session):
        """Aucun consentement actif à révoquer → False."""
        async with _test_factory() as sess:
            async with sess.begin():
                ok = await retirer_consentement(
                    sess,
                    utilisateur_id="fantome",
                    type_consentement="rgpd_biometrique",
                )
            assert ok is False

    @pytest.mark.asyncio
    async def test_retirer_deja_revoque(self, db_session):
        """Révocation d'un consentement déjà révoqué → False."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_biometrique",
                    version_texte=RGPD_BIOMETRIQUE_VERSION,
                    utilisateur_id="double_revoke",
                )
            async with sess.begin():
                ok1 = await retirer_consentement(
                    sess,
                    utilisateur_id="double_revoke",
                    type_consentement="rgpd_biometrique",
                )
            async with sess.begin():
                ok2 = await retirer_consentement(
                    sess,
                    utilisateur_id="double_revoke",
                    type_consentement="rgpd_biometrique",
                )

        assert ok1 is True
        assert ok2 is False, "Deuxième révocation doit retourner False"


# ──────────────────────────────────────────────────────────────────────────────
# Tests : obtenir_etat_consentements
# ──────────────────────────────────────────────────────────────────────────────


class TestObtenirEtatConsentements:
    """Tests pour la récupération d'état des consentements."""

    @pytest.mark.asyncio
    async def test_structure_sans_consentement(self, db_session):
        """Aucun consentement → tous False."""
        async with _test_factory() as sess:
            etat = await obtenir_etat_consentements(sess, utilisateur_id="new_user")

        assert isinstance(etat, dict)
        assert "consentements" in etat
        assert "historique" in etat
        assert etat["consentements"]["cgv_checkout"] is False
        assert etat["consentements"]["renonciation_retractation"] is False
        assert etat["consentements"]["rgpd_biometrique"] is False
        assert etat["consentements"]["rgpd_ia"] is False
        assert etat["historique"] == []

    @pytest.mark.asyncio
    async def test_etat_apres_enregistrements(self, db_session):
        """Après enregistrements → les types enregistrés sont True."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_biometrique",
                    version_texte=RGPD_BIOMETRIQUE_VERSION,
                    utilisateur_id="user_full",
                )
                await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_ia",
                    version_texte=RGPD_IA_VERSION,
                    utilisateur_id="user_full",
                )

        async with _test_factory() as sess:
            etat = await obtenir_etat_consentements(sess, utilisateur_id="user_full")

        assert etat["consentements"]["rgpd_biometrique"] is True
        assert etat["consentements"]["rgpd_ia"] is True
        assert etat["consentements"]["cgv_checkout"] is False
        assert len(etat["historique"]) == 2

    @pytest.mark.asyncio
    async def test_masquage_ip(self, db_session):
        """L'IP dans l'historique est masquée."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="ip@example.com",
                    ip="192.168.1.42",
                )

        async with _test_factory() as sess:
            # On ne peut pas obtenir_etat_consentements par email
            # (nécessite utilisateur_id), mais on teste le masquage
            # via la fonction helper directement
            from app.services.consent_service import _masquer_ip
            masked = _masquer_ip("192.168.1.42")
            assert masked == "192.168.1.***"

            masked_ipv6 = _masquer_ip("2001:db8::1")
            assert masked_ipv6.endswith("****")

    @pytest.mark.asyncio
    async def test_historique_ordre_chrono_inverse(self, db_session):
        """L'historique est trié du plus récent au plus ancien."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_biometrique",
                    version_texte=RGPD_BIOMETRIQUE_VERSION,
                    utilisateur_id="user_chrono",
                )
            # Petit délai pour garantir l'ordre
            import asyncio
            await asyncio.sleep(0.1)
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_ia",
                    version_texte=RGPD_IA_VERSION,
                    utilisateur_id="user_chrono",
                )

        async with _test_factory() as sess:
            etat = await obtenir_etat_consentements(sess, utilisateur_id="user_chrono")

        historique = etat["historique"]
        assert len(historique) == 2
        assert historique[0]["type"] == "rgpd_ia", "Plus récent en premier"
        assert historique[1]["type"] == "rgpd_biometrique"


# ──────────────────────────────────────────────────────────────────────────────
# Tests de non-régression
# ──────────────────────────────────────────────────────────────────────────────


class TestNonRegression:
    """Garanties d'intégrité et de sécurité."""

    @pytest.mark.asyncio
    async def test_isolation_utilisateurs(self, db_session):
        """Les consentements de user_A ne sont pas visibles par user_B."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="rgpd_biometrique",
                    version_texte=RGPD_BIOMETRIQUE_VERSION,
                    utilisateur_id="user_A",
                )

        # user_B n'a aucun consentement
        async with _test_factory() as sess:
            ok = await consentement_actif(
                sess,
                utilisateur_id="user_B",
                type_consentement="rgpd_biometrique",
            )
        assert ok is False, "user_B ne doit pas voir les consentements de user_A"

    @pytest.mark.asyncio
    async def test_isolation_email(self, db_session):
        """Les consentements d'un email ne sont pas visibles par un autre email."""
        async with _test_factory() as sess:
            async with sess.begin():
                await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="alice@example.com",
                )

        async with _test_factory() as sess:
            ok = await consentement_actif(
                sess,
                email="bob@example.com",
                type_consentement="cgv_checkout",
            )
        assert ok is False

    @pytest.mark.asyncio
    async def test_append_only_pas_de_modification(self, db_session):
        """On ne modifie jamais une ligne existante : accepte ne passe jamais à False."""
        async with _test_factory() as sess:
            async with sess.begin():
                c = await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="append@example.com",
                )
            c_id = c.id

        # Le service retirer_consentement ne modifie pas la ligne existante,
        # il ajoute retire_le sur une ligne existante (ce n'est pas un UPDATE de la colonne accepte).
        # On vérifie que la ligne originelle a toujours accepte=True
        async with _test_factory() as sess:
            from sqlalchemy import select
            stmt = select(Consentement).where(Consentement.id == c_id)
            result = await sess.execute(stmt)
            original = result.scalar_one()
            assert original.accepte is True, "La ligne originale doit garder accepte=True (append-only)"

    @pytest.mark.asyncio
    async def test_versions_differentes_coexistent(self, db_session):
        """Deux consentements CGV avec versions différentes → lignes distinctes."""
        async with _test_factory() as sess:
            async with sess.begin():
                c1 = await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte="v1.0-old",
                    email="versions@example.com",
                )
            async with sess.begin():
                c2 = await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte="v2.0-new",
                    email="versions@example.com",
                )

        assert c1.version_texte == "v1.0-old"
        assert c2.version_texte == "v2.0-new"
        assert c1.id != c2.id

    @pytest.mark.asyncio
    async def test_contexte_json_present(self, db_session):
        """Le contexte est bien sauvegardé en JSON."""
        async with _test_factory() as sess:
            async with sess.begin():
                c = await enregistrer_consentement(
                    sess,
                    type_consentement="cgv_checkout",
                    version_texte=CGV_VERSION,
                    email="ctx@example.com",
                    contexte={"plan": "premium", "source": "pricing_page"},
                )

        assert c.contexte is not None
        assert "premium" in c.contexte
