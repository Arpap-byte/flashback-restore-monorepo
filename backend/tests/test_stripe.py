"""
Tests unitaires pour l'idempotence Stripe (stripe_events) et le webhook Stripe.

Exécuter : cd backend && .venv/bin/pytest tests/test_stripe.py -v --tb=short
"""

import time
import hmac
import hashlib
import json
import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.db.queries import (
    creer_utilisateur,
    obtenir_credits_restants,
    stripe_event_deja_traite,
    marquer_stripe_event_traite,
)
from app.config import STRIPE_WEBHOOK_SECRET


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _reset_test_db():
    """Drop + recreate toutes les tables pour une base propre."""
    from app.models.db_models import Base
    from app.db.session import _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    """Initialise la base de données une fois pour toute la session de test
    (drop_all + create_all pour garantir un schéma à jour)."""
    asyncio.run(_reset_test_db())


client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event_id(prefix: str = "evt_test") -> str:
    """Génère un ID d'événement unique pour les tests."""
    return f"{prefix}_{uuid4().hex[:16]}"


def _generer_signature_stripe(payload: bytes, secret: str = None) -> str:
    """Génère un en-tête Stripe-Signature valide pour un payload donné."""
    if secret is None:
        secret = STRIPE_WEBHOOK_SECRET
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def _payload_stripe_event(event_type: str, event_id: str) -> dict:
    """Construit un payload d'événement Stripe minimal mais valide."""
    return {
        "id": event_id,
        "object": "event",
        "api_version": "2023-10-16",
        "type": event_type,
        "data": {
            "object": {
                "id": "ch_test_123",
                "object": "charge",
                "amount": 2000,
                "currency": "eur",
            }
        },
    }


# ---------------------------------------------------------------------------
# Tests d'idempotence (DB directe)
# ---------------------------------------------------------------------------


class TestStripeEventIdempotence:
    """Tests pour stripe_event_deja_traite() et marquer_stripe_event_traite()"""

    @pytest.mark.asyncio
    async def test_stripe_event_deja_traite_non_existant(self):
        """Un événement jamais traité doit retourner False."""
        eid = _event_id("evt_nonexistant")
        deja = await stripe_event_deja_traite(eid)
        assert deja is False, (
            f"Événement {eid} ne devrait pas être marqué comme traité"
        )

    @pytest.mark.asyncio
    async def test_stripe_event_marquer_puis_verifier(self):
        """Marquer un event puis vérifier qu'il est traité → True."""
        eid = _event_id("evt_marquer")
        await marquer_stripe_event_traite(eid, "checkout.session.completed")

        deja = await stripe_event_deja_traite(eid)
        assert deja is True, (
            f"Événement {eid} devrait être marqué comme traité après marquage"
        )

    @pytest.mark.asyncio
    async def test_stripe_event_double_marquage(self):
        """
        Marquer deux fois le même event — la DB lève IntegrityError
        car la contrainte UNIQUE sur event_id est volontaire.
        L'idempotence est assurée au niveau du webhook (routes.py) qui
        appelle stripe_event_deja_traite() AVANT marquer_stripe_event_traite().
        Ce test documente le comportement attendu de la couche DB.
        """
        import sqlalchemy as sa

        eid = _event_id("evt_double")
        await marquer_stripe_event_traite(eid, "checkout.session.completed")

        # Le double marquage direct doit lever IntegrityError — c'est normal.
        # La protection est dans le webhook, pas dans la fonction DB.
        with pytest.raises(sa.exc.IntegrityError):
            await marquer_stripe_event_traite(
                eid, "checkout.session.completed"
            )

        # Vérification finale : l'event est toujours bien traité
        deja = await stripe_event_deja_traite(eid)
        assert deja is True


# ---------------------------------------------------------------------------
# Tests du webhook Stripe
# ---------------------------------------------------------------------------


class TestWebhookStripe:
    """Tests pour l'endpoint POST /api/stripe/webhook"""

    def test_webhook_stripe_sans_signature(self):
        """POST /api/stripe/webhook sans header Stripe-Signature → 400."""
        res = client.post("/api/stripe/webhook", content=b"{}")
        assert res.status_code == 400, (
            f"Attendu 400, reçu {res.status_code} : {res.json()}"
        )
        assert "manquant" in res.json()["detail"].lower()

    def test_webhook_stripe_signature_invalide(self):
        """POST avec signature bidon → 400."""
        res = client.post(
            "/api/stripe/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "t=9999999999,v1=abcdef123456"},
        )
        assert res.status_code == 400, (
            f"Attendu 400, reçu {res.status_code} : {res.json()}"
        )

    def test_webhook_stripe_evenement_valide(self):
        """
        POST avec signature valide (calculée avec le webhook secret)
        pour un événement non géré spécifiquement → 200.
        """
        eid = _event_id("evt_webhook")
        payload = _payload_stripe_event("charge.succeeded", eid)
        corps = json.dumps(payload).encode("utf-8")
        signature = _generer_signature_stripe(corps)

        res = client.post(
            "/api/stripe/webhook",
            content=corps,
            headers={"Stripe-Signature": signature},
        )
        assert res.status_code == 200, (
            f"Attendu 200, reçu {res.status_code} : {res.json()}"
        )

        data = res.json()
        assert data["type_evenement"] == "charge.succeeded"
        assert "traité avec succès" in data["message"]

        # Vérification idempotence : un second appel avec le même event_id
        # doit retourner 200 aussi, avec un message différent
        signature2 = _generer_signature_stripe(corps)
        res2 = client.post(
            "/api/stripe/webhook",
            content=corps,
            headers={"Stripe-Signature": signature2},
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert "déjà traité" in data2["message"].lower()


# ---------------------------------------------------------------------------
# Tests du webhook checkout.session.completed (P0-Critique)
# ---------------------------------------------------------------------------


class TestWebhookCheckoutCompleted:
    """Tests critiques pour l'event checkout.session.completed."""

    @pytest.mark.asyncio
    async def test_webhook_checkout_session_completed_credite_utilisateur(self, db_session):
        """
        P0-Critique : L'event checkout.session.completed doit créditer l'utilisateur.
        C'est le test financier le plus critique du système.

        Scénario : achat de crédits (mode payment, metadata.type=credits).
        Le webhook doit retrouver l'utilisateur par email, ajouter les crédits,
        et enregistrer l'achat.
        """
        email = f"test_{uuid4().hex[:8]}@test.fr"
        uid = await creer_utilisateur(email, "dummy")
        assert uid is not None, "Échec création utilisateur de test"

        eid = _event_id("evt_checkout_real")
        payload = json.dumps({
            "id": eid,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_abc123",
                    "mode": "payment",
                    "payment_status": "paid",
                    "amount_total": 999,
                    "metadata": {
                        "type": "credits",
                        "email": email,
                        "credits": "30",
                    },
                    "customer_email": email,
                }
            }
        }).encode()

        sign = _generer_signature_stripe(payload)

        res = client.post("/api/stripe/webhook",
                          content=payload,
                          headers={"Stripe-Signature": sign})
        assert res.status_code == 200

        # VÉRIFICATION CRITIQUE: les crédits ont-ils été attribués ?
        credits = await obtenir_credits_restants(uid)
        assert credits["credits"] > 0, (
            "Les crédits n'ont PAS été attribués après paiement !"
        )

    @pytest.mark.asyncio
    async def test_webhook_checkout_idempotence(self, db_session):
        """Double livraison checkout.session.completed → crédits attribués une seule fois."""
        email = f"test_{uuid4().hex[:8]}@test.fr"
        uid = await creer_utilisateur(email, "dummy")
        assert uid is not None, "Échec création utilisateur de test"

        eid = _event_id("evt_double_checkout")
        payload = json.dumps({
            "id": eid,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test",
                    "mode": "payment",
                    "payment_status": "paid",
                    "amount_total": 999,
                    "metadata": {
                        "type": "credits",
                        "email": email,
                        "credits": "30",
                    },
                }
            }
        }).encode()

        sign = _generer_signature_stripe(payload)

        # Premier envoi
        r1 = client.post("/api/stripe/webhook", content=payload,
                         headers={"Stripe-Signature": sign})
        assert r1.status_code == 200
        credits_apres_1 = await obtenir_credits_restants(uid)

        # Second envoi (même event) — doit être ignoré
        r2 = client.post("/api/stripe/webhook", content=payload,
                         headers={"Stripe-Signature": sign})
        assert r2.status_code == 200
        credits_apres_2 = await obtenir_credits_restants(uid)

        # Les crédits ne doivent PAS avoir doublé
        assert credits_apres_2["credits"] == credits_apres_1["credits"], (
            f"Idempotence cassée : {credits_apres_1['credits']} → {credits_apres_2['credits']}"
        )
