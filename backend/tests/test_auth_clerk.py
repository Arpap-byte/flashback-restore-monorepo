"""
Tests d'authentification Clerk — cas positifs et edge cases.
L'audit Sonnet a révélé que test_auth.py ne teste que les rejections.
Ce fichier couvre les cas où l'auth DOIT fonctionner.

Exécuter : cd backend && .venv/bin/pytest tests/test_auth_clerk.py -v --tb=short

Stratégie de mock :
- verify_clerk_token (app.clerk_auth) → simuler token Clerk valide/expiré/invalide
- _trouver_ou_creer_utilisateur (app.auth) → éviter la dépendance DB dans l'auth
- Les fonctions DB (dans app.api.user) → éviter la dépendance DB dans les handlers
  NOTE: on patch dans app.api.user (pas app.db.queries) car user.py fait
        "from app.db.queries import ..." → référence locale.
- ADMIN_API_KEY (app.api.routes) → pour les tests admin key
"""

import sys
import time
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

# Nécessaire pour que 'app' soit importable quand on lance depuis tests/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

client = TestClient(app)


# ============================================================================
# Helpers : mocks de vérification Clerk
# ============================================================================

def _payload_clerk_valide(user_id: str = "user_test_123", email: str = "test@example.com"):
    """Payload Clerk simulé avec sub, sid, email et expiration future."""
    return {
        "sub": user_id,
        "sid": "sess_test_clerk",
        "email": email,
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()) - 60,
        "iss": "https://clerk.flashback-restore.com",
    }


def _utilisateur_fake(user_id: str = "user_test_123", email: str = "test@example.com"):
    """Dictionnaire utilisateur simulé (format retourné par la DB)."""
    return {
        "id": user_id,
        "email": email,
        "credits": 0,
        "plan": "gratuit",
        "animations_utilisees": 0,
        "derniere_activite": None,
        "essais_restants": 3,
        "est_abonne": False,
        "retention_jours": 30,
    }


# --- Mocks Clerk ---

def _mock_verify_clerk_token_success(user_id: str = "user_test_123", email: str = "test@example.com"):
    return mock.patch(
        "app.clerk_auth.verify_clerk_token",
        return_value=_payload_clerk_valide(user_id, email),
    )


def _mock_verify_clerk_token_expired():
    import jwt as _jwt
    return mock.patch(
        "app.clerk_auth.verify_clerk_token",
        side_effect=_jwt.ExpiredSignatureError("Token expired"),
    )


def _mock_verify_clerk_token_invalide():
    import jwt as _jwt
    return mock.patch(
        "app.clerk_auth.verify_clerk_token",
        side_effect=_jwt.InvalidTokenError("Invalid token"),
    )


# --- Mock du lookup utilisateur (dans l'auth middleware) ---

def _mock_trouver_utilisateur(user_id: str = "user_test_123", email: str = "test@example.com"):
    async def _fake_trouver(payload: dict):
        return _utilisateur_fake(user_id, email)

    return mock.patch(
        "app.auth._trouver_ou_creer_utilisateur",
        side_effect=_fake_trouver,
    )


# --- Mocks DB pour les handlers d'endpoint ---
# IMPORTANT: user.py fait "from app.db.queries import obtenir_..."
# donc la référence est locale à app.api.user. On doit patcher
# app.api.user.<fonction>, PAS app.db.queries.<fonction>.

def _mock_db_user_detail(user_id: str = "user_test_123", email: str = "test@example.com"):
    """Mock obtenir_utilisateur_par_id → retourne un dict utilisateur complet."""
    async def _fake(id_):
        return _utilisateur_fake(user_id, email)
    return mock.patch("app.api.user.obtenir_utilisateur_par_id", side_effect=_fake)


def _mock_db_essais(user_id: str = "user_test_123"):
    async def _fake(id_):
        return {"essais_restants": 3, "est_abonne": False}
    return mock.patch("app.api.user.obtenir_essais_restants", side_effect=_fake)


def _mock_db_plan():
    async def _fake(id_):
        return "gratuit"
    return mock.patch("app.api.user.obtenir_plan_utilisateur", side_effect=_fake)


def _mock_db_retention():
    async def _fake(id_):
        return 30
    return mock.patch("app.api.user.obtenir_retention", side_effect=_fake)


def _mock_db_full(user_id: str = "user_test_123", email: str = "test@example.com"):
    """Mocks toutes les queries DB appelées par les handlers d'endpoint user."""
    return _MultiMock([
        _mock_db_user_detail(user_id, email),
        _mock_db_essais(user_id),
        _mock_db_plan(),
        _mock_db_retention(),
    ])


# --- Mock combiné auth + DB pour un test positif complet ---

def _mock_auth_and_db(user_id: str = "user_test_123", email: str = "test@example.com"):
    """Mock complet : verify_clerk_token + lookup utilisateur + queries DB."""
    return _MultiMock([
        _mock_verify_clerk_token_success(user_id, email),
        _mock_trouver_utilisateur(user_id, email),
        _mock_db_full(user_id, email),
    ])


# --- Helper pour composer plusieurs mocks ---

class _MultiMock:
    """Applique plusieurs mocks en même temps (context manager composé)."""
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
# Tests positifs — Token Clerk valide
# ============================================================================

class TestAuthClerkPositif:
    """Tests où l'authentification DOIT réussir."""

    def test_user_me_avec_token_valide(self):
        """Avec un token Clerk valide, GET /api/user/me doit retourner 200."""
        with _mock_auth_and_db("user_test_123", "test@example.com"):
            res = client.get("/api/user/me", headers={
                "Authorization": "Bearer valid_test_token"
            })
        assert res.status_code == 200, \
            f"Token valide rejeté : {res.status_code} {res.json()}"

    def test_user_me_retourne_donnees_utilisateur(self):
        """La réponse doit contenir les champs utilisateur attendus."""
        with _mock_auth_and_db("user_test_456", "user456@example.com"):
            res = client.get("/api/user/me", headers={
                "Authorization": "Bearer valid_test_token"
            })
        assert res.status_code == 200
        data = res.json()
        assert "email" in data, f"Réponse inattendue (pas d'email): {data}"
        assert data["email"] == "user456@example.com"

    def test_user_trials_avec_token_valide(self):
        """GET /api/user/trials avec token valide doit retourner 200."""
        with _MultiMock([
            _mock_verify_clerk_token_success("user_789"),
            _mock_trouver_utilisateur("user_789"),
            _mock_db_essais("user_789"),
        ]):
            res = client.get("/api/user/trials", headers={
                "Authorization": "Bearer valid_test_token"
            })
        assert res.status_code == 200, \
            f"Token valide rejeté sur /trials : {res.status_code}"

    def test_user_preferences_avec_token_valide(self):
        """GET /api/user/preferences avec token valide doit retourner 200."""
        with _MultiMock([
            _mock_verify_clerk_token_success("user_prefs"),
            _mock_trouver_utilisateur("user_prefs"),
            _mock_db_retention(),
        ]):
            res = client.get("/api/user/preferences", headers={
                "Authorization": "Bearer valid_test_token"
            })
        assert res.status_code == 200, \
            f"Token valide rejeté sur /preferences : {res.status_code}"

    def test_restore_avec_token_valide(self):
        """POST /api/restore avec token valide doit accepter le token
        (le body incomplet donnera 422, mais pas 401)."""
        with _MultiMock([
            _mock_verify_clerk_token_success("user_rest"),
            _mock_trouver_utilisateur("user_rest"),
        ]):
            res = client.post("/api/restore", json={"photo_id": "test_photo"}, headers={
                "Authorization": "Bearer valid_token"
            })
        # Peut être 404 (pas de photo) ou 422 (validation) — mais PAS 401
        assert res.status_code != 401, \
            f"Token valide rejeté sur restore: {res.status_code}"


# ============================================================================
# Tests Admin Key
# ============================================================================

class TestAuthAdminKey:
    """Tests de l'authentification par X-Admin-Key."""

    def test_stats_admin_key_valide_200(self):
        """GET /api/stats avec X-Admin-Key valide doit passer l'auth
        (retourne 200 ou 500 si DB absente, mais JAMAIS 403)."""
        with mock.patch("app.api.routes.ADMIN_API_KEY", "super-secret-admin-key"):
            res = client.get("/api/stats", headers={
                "X-Admin-Key": "super-secret-admin-key"
            })
        # Sans DB, le endpoint peut échouer avec 500, mais jamais 403
        assert res.status_code != 403, \
            f"Admin key valide rejetée (403): {res.json()}"

    def test_stats_sans_admin_key_retourne_403(self):
        """GET /api/stats sans X-Admin-Key doit retourner 403."""
        with mock.patch("app.api.routes.ADMIN_API_KEY", "some-admin-key"):
            res = client.get("/api/stats")
        assert res.status_code == 403, \
            f"Attendu 403 sans admin key, reçu: {res.status_code}"

    def test_stats_admin_key_invalide_403(self):
        """GET /api/stats avec X-Admin-Key invalide doit retourner 403."""
        with mock.patch("app.api.routes.ADMIN_API_KEY", "super-secret-admin-key"):
            res = client.get("/api/stats", headers={
                "X-Admin-Key": "wrong-admin-key"
            })
        assert res.status_code == 403, \
            f"Admin key invalide devrait être 403, reçu: {res.status_code}"


# ============================================================================
# Edge cases auth
# ============================================================================

class TestAuthClerkEdgeCases:
    """Edge cases que l'audit Sonnet a identifié comme manquants."""

    def test_token_expire_retourne_401(self):
        """Un token Clerk expiré doit retourner 401.

        Note: decoder_token() rattrape ExpiredSignatureError (sous-classe
        de InvalidTokenError) et lève un InvalidTokenError générique.
        Le endpoint reçoit donc un 401 'Token invalide.' — c'est le
        comportement observé. Ce test vérifie que le statut HTTP est
        bien 401 (pas 403 ni 500).
        """
        with _mock_verify_clerk_token_expired():
            res = client.get("/api/user/me", headers={
                "Authorization": "Bearer expired_token"
            })
        assert res.status_code == 401, \
            f"Token expiré devrait être 401, reçu: {res.status_code}"
        detail = res.json().get("detail", "")
        # Le message exact dépend du niveau de rattrapage,
        # mais le statut 401 est la seule garantie contractuelle
        assert "token" in detail.lower(), \
            f"Message attendu mentionnant token, reçu: {detail}"

    def test_token_invalide_retourne_401(self):
        """Un token Clerk invalide (non expiré) doit retourner 401."""
        with _mock_verify_clerk_token_invalide():
            res = client.get("/api/user/me", headers={
                "Authorization": "Bearer invalid_clerk_token"
            })
        assert res.status_code == 401, \
            f"Token invalide devrait être 401, reçu: {res.status_code}"

    def test_health_sans_auth(self):
        """GET /api/health doit être accessible sans auth (test de cohérence)."""
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert "statut" in data

    def test_token_valide_sans_header_bearer(self):
        """Sans header Authorization du tout, exiger_utilisateur doit lever 401."""
        with _mock_auth_and_db():
            res = client.get("/api/user/me")
        # Même si le mock rend verify_clerk_token valide,
        # sans header Authorization, obtenir_utilisateur_courant
        # reçoit credentials=None → retourne None → exiger_utilisateur lève 401
        assert res.status_code == 401, \
            f"Sans header Authorization, attendu 401, reçu: {res.status_code}"

    def test_route_protegee_avec_bearer_vide(self):
        """Header Authorization: Bearer (sans token) doit retourner 401."""
        with _mock_auth_and_db():
            res = client.get("/api/user/me", headers={
                "Authorization": "Bearer "
            })
        assert res.status_code == 401, \
            f"Bearer vide devrait être 401, reçu: {res.status_code}"

    def test_token_clerk_meme_email_nouveau_user_id(self):
        """Même email mais user_id Clerk différent : doit quand même réussir
        (l'utilisateur est trouvé par email)."""
        with _mock_auth_and_db("user_clerk_new_999", "existing@example.com"):
            res = client.get("/api/user/me", headers={
                "Authorization": "Bearer clerk_token_new_user"
            })
        assert res.status_code == 200, \
            f"Même email / nouveau sub rejeté : {res.status_code}"

    def test_verify_clerk_token_appele_avec_bon_token(self):
        """Vérifie que verify_clerk_token reçoit bien le token extrait
        du header Authorization (pas un token hardcodé)."""
        with mock.patch(
            "app.clerk_auth.verify_clerk_token",
            return_value=_payload_clerk_valide("user_x", "x@test.com"),
        ) as mock_verify, \
             _mock_trouver_utilisateur("user_x"), \
             _mock_db_full("user_x"):
            client.get("/api/user/me", headers={
                "Authorization": "Bearer mon_token_specifique"
            })
        mock_verify.assert_called_once_with("mon_token_specifique")
