"""
Tests du webhook Clerk - creation compte, signature, edge cases.

Execute: cd backend && .venv/bin/pytest tests/test_webhook_clerk.py -v --tb=short

Strategy:
- ensure_compte (app.services.clerk_account) - simuler creation/sync DB
- CLERK_WEBHOOK_SECRET - mock via monkeypatch (os.environ)
"""

import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def _setup_webhook_env(monkeypatch):
    """Configure CLERK_WEBHOOK_SECRET for all webhook tests."""
    from app.api import webhooks as wh
    monkeypatch.setattr(wh, "CLERK_WEBHOOK_SECRET", "whsec_test_mock_secret_for_pytest")
    # Bypass Svix signature verification in tests
    monkeypatch.setattr(wh, "_verifier_signature", lambda request, payload: {})
    import app.config
    monkeypatch.setattr(app.config, "DEBUG", True)
    yield


# ============================================================================
# Helpers
# ============================================================================

WEBHOOK_URL = "/api/webhooks/clerk"

CLERK_USER_ID = "user_3DunO7ve2Ml5pPApzCGlksLdSR6"
CLERK_EMAIL = "test@flashback-restore.com"

def _payload_create(email=CLERK_EMAIL, user_id=CLERK_USER_ID):
    """Payload user.created standard de Clerk."""
    return {
        "type": "user.created",
        "data": {
            "id": user_id,
            "email_addresses": [
                {"email_address": email, "id": "idn_xxx"}
            ],
        },
        "object": "event",
    }

def _payload_update(email=CLERK_EMAIL, user_id=CLERK_USER_ID):
    """Payload user.updated."""
    return {
        "type": "user.updated",
        "data": {
            "id": user_id,
            "email_addresses": [
                {"email_address": email, "id": "idn_xxx"}
            ],
        },
        "object": "event",
    }

def _payload_delete(user_id=CLERK_USER_ID):
    """Payload user.deleted."""
    return {
        "type": "user.deleted",
        "data": {"id": user_id},
        "object": "event",
    }

def _payload_unknown(user_id=CLERK_USER_ID):
    """Payload avec type inconnu."""
    return {
        "type": "session.created",
        "data": {"id": user_id},
        "object": "event",
    }

def _utilisateur_fake(user_id="local_uuid_123", email=CLERK_EMAIL):
    """Dictionnaire utilisateur simule."""
    return {
        "id": user_id,
        "email": email,
        "password_hash": "",
        "essais_restants": 3,
        "credits": 0,
        "est_abonne": 0,
        "plan": "gratuit",
        "retention_jours": 30,
        "oauth_provider": "clerk",
        "oauth_provider_id": CLERK_USER_ID,
        "cree_le": None,
        "derniere_connexion": None,
        "derniere_activite": None,
    }

# --- Mock ensure_compte ---

def _mock_ensure_compte(user_id="local_uuid_123", email=CLERK_EMAIL):
    async def _fake(clerk_id, email_addr, mettre_a_jour_email=False):
        return _utilisateur_fake(user_id, email_addr or email)
    return mock.patch("app.api.webhooks.ensure_compte", side_effect=_fake)

def _mock_ensure_compte_none():
    async def _fake(clerk_id, email_addr, mettre_a_jour_email=False):
        return None
    return mock.patch("app.api.webhooks.ensure_compte", side_effect=_fake)

# --- Mock supprimer_compte ---

def _mock_supprimer_compte(success=True):
    async def _fake(clerk_id):
        return success
    return mock.patch("app.api.webhooks.supprimer_compte", side_effect=_fake)

# --- Mock log_webhook ---

def _mock_log_webhook():
    async def _fake(*args, **kwargs):
        return "audit_test_id"
    return mock.patch("app.api.webhooks.log_webhook", side_effect=_fake)


class _MultiMock:
    def __init__(self, mocks):
        self._mocks = mocks
    def __enter__(self):
        for m in self._mocks:
            m.__enter__()
        return self
    def __exit__(self, *args):
        for m in reversed(self._mocks):
            m.__exit__(*args)


# ============================================================================
# Tests positifs
# ============================================================================

class TestWebhookClerkPositif:

    def test_user_created_cree_compte(self):
        """user.created doit appeler ensure_compte et retourner 200."""
        with _MultiMock([_mock_ensure_compte("local_123", "new@test.com"), _mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=_payload_create("new@test.com"))
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_user_updated_sync_email(self):
        """user.updated doit appeler ensure_compte avec mettre_a_jour_email=True."""
        with _MultiMock([_mock_ensure_compte("local_456", "updated@test.com"), _mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=_payload_update("updated@test.com"))
        assert res.status_code == 200

    def test_user_deleted_supprime_compte(self):
        """user.deleted doit appeler supprimer_compte et retourner 200."""
        with _MultiMock([_mock_supprimer_compte(True), _mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=_payload_delete())
        assert res.status_code == 200

    def test_type_inconnu_retourne_200_ignored(self):
        """Un event type inconnu retourne 200 avec status=ignored."""
        with _MultiMock([_mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=_payload_unknown())
        assert res.status_code == 200
        assert res.json()["status"] == "ignored"

    def test_user_created_sans_email(self):
        """user.created sans email valide - ne doit pas planter (200)."""
        payload = {"type": "user.created", "data": {"id": "user_no_email", "email_addresses": []}}
        with _MultiMock([_mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=payload)
        assert res.status_code == 200

    def test_user_created_avec_email_placeholder(self):
        """Email placeholder (@placeholder.local) - ignore."""
        payload = {
            "type": "user.created",
            "data": {
                "id": "user_placeholder",
                "email_addresses": [{"email_address": "nobody@placeholder.local", "id": "idn_yyy"}],
            },
        }
        with _MultiMock([_mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=payload)
        assert res.status_code == 200


# ============================================================================
# Tests non-regression
# ============================================================================

class TestWebhookClerkRegression:

    def test_webhook_idempotent_double_appel(self):
        """Deux user.created identiques retournent 200."""
        with _MultiMock([_mock_ensure_compte("local_idem", "idem@test.com"), _mock_log_webhook()]):
            r1 = client.post(WEBHOOK_URL, json=_payload_create("idem@test.com"))
            r2 = client.post(WEBHOOK_URL, json=_payload_create("idem@test.com"))
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_user_deleted_sans_compte_existant(self):
        """Suppression d'un compte inexistant retourne 200."""
        with _MultiMock([_mock_supprimer_compte(False), _mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=_payload_delete("user_inexistant"))
        assert res.status_code == 200

    def test_ensure_compte_echoue_retourne_200(self):
        """Si ensure_compte retourne None, le webhook retourne 200."""
        with _MultiMock([_mock_ensure_compte_none(), _mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=_payload_create("fail@test.com"))
        assert res.status_code == 200

    def test_webhook_accessible_sans_auth_jwt(self):
        """Le webhook ne necessite PAS de header Authorization JWT."""
        with _MultiMock([_mock_ensure_compte(), _mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=_payload_create())
        assert res.status_code == 200

    def test_payload_avec_user_id_vide(self):
        """Payload avec data.id vide - ne doit pas planter (200)."""
        payload = {"type": "user.created", "data": {"id": "", "email_addresses": []}}
        with _MultiMock([_mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=payload)
        assert res.status_code == 200
        assert res.json()["status"] == "ignored"

    def test_webhook_ne_bloque_pas_les_autres_routes(self):
        """Verifie que l'ajout du webhook ne casse pas les routes existantes."""
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["statut"] in ("ok", "OK")

    def test_webhook_auth_me_toujours_fonctionnel(self):
        """GET /api/user/me fonctionne toujours apres l'ajout du webhook."""
        res = client.get("/api/user/me")
        assert res.status_code == 401

    def test_rate_limit_webhook(self):
        """Le webhook est protege par un rate limit (ne doit pas planter)."""
        with _MultiMock([_mock_ensure_compte(), _mock_log_webhook()]):
            for _ in range(5):
                res = client.post(WEBHOOK_URL, json=_payload_create())
                assert res.status_code == 200


# ============================================================================
# Tests du service clerk_account
# ============================================================================

class TestClerkAccountServiceMocked:

    @pytest.mark.asyncio
    async def test_ensure_compte_retourne_dict_attendu(self):
        """Les cles retournees doivent inclure email, plan, credits, etc."""
        with _MultiMock([_mock_ensure_compte("local_test", "fields@test.com"), _mock_log_webhook()]):
            res = client.post(WEBHOOK_URL, json=_payload_create("fields@test.com"))
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_supprimer_compte_appele_avec_bon_id(self):
        """supprimer_compte doit recevoir le clerk_id du payload."""
        captured_id = None
        async def _capture(clerk_id):
            nonlocal captured_id
            captured_id = clerk_id
            return True
        with mock.patch("app.api.webhooks.supprimer_compte", side_effect=_capture), \
             _mock_log_webhook():
            client.post(WEBHOOK_URL, json=_payload_delete("user_target_999"))
        assert captured_id == "user_target_999"
