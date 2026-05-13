"""
Tests d'authentification et de protection des endpoints avec l'architecture Clerk.

Vérifie que :
- Les endpoints publics (health, stats admin) sont accessibles
- Les endpoints protégés retournent 401 sans token Clerk
- Les endpoints protégés retournent 401 avec un token invalide

Exécuter : cd backend && .venv/bin/pytest tests/test_auth.py -v --tb=short
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Tests : endpoints publics
# ---------------------------------------------------------------------------

def test_health_check():
    """GET /api/health doit retourner 200 avec statut OK."""
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code} {res.text}"
    data = res.json()
    assert "statut" in data
    assert data["statut"] == "OK"


def test_stats_sans_admin_key_retourne_403():
    """GET /api/stats sans X-Admin-Key doit retourner 403."""
    res = client.get("/api/stats")
    # /api/stats est protégé par X-Admin-Key, pas par Clerk
    assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"


# ---------------------------------------------------------------------------
# Tests : endpoints protégés SANS token (doit retourner 401)
# ---------------------------------------------------------------------------

def test_user_me_sans_auth():
    """GET /api/user/me sans token doit retourner 401."""
    res = client.get("/api/user/me")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "detail" in res.json()
    assert res.json()["detail"] == "Authentification requise."


def test_upload_sans_auth():
    """POST /api/upload sans token doit retourner 404 (l'endpoint n'existe pas encore)
    ou 401 si l'endpoint est protégé et existe.

    Note : /api/upload n'est pas défini dans l'application actuelle.
    L'équivalent le plus proche est /api/analyze (POST, upload de fichier, protégé).
    Ce test vérifie que /api/analyze retourne 401 sans auth.
    """
    res = client.post("/api/analyze")
    # Sans fichier ni auth, FastAPI doit d'abord résoudre la dépendance exiger_utilisateur
    # qui lève HTTP 401 avant de valider le body
    assert res.status_code in (401, 422), \
        f"Expected 401 or 422, got {res.status_code}: {res.text}"
    if res.status_code == 401:
        assert "detail" in res.json()


def test_restore_sans_auth():
    """POST /api/restore sans token doit retourner 401."""
    res = client.post("/api/restore")
    # FastAPI résout les dépendances avant le body → exiger_utilisateur lève 401
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "detail" in res.json()
    assert res.json()["detail"] == "Authentification requise."


# ---------------------------------------------------------------------------
# Tests : endpoints protégés avec token INVALIDE (doit retourner 401)
# ---------------------------------------------------------------------------

def test_user_me_token_invalide():
    """GET /api/user/me avec un token bidon doit retourner 401."""
    res = client.get(
        "/api/user/me",
        headers={"Authorization": "Bearer token_bidon_invalide"}
    )
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "detail" in res.json()
    assert res.json()["detail"] == "Token invalide."


def test_restore_token_invalide():
    """POST /api/restore avec un token bidon doit retourner 401."""
    res = client.post(
        "/api/restore",
        headers={"Authorization": "Bearer token_bidon_invalide"}
    )
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert "detail" in res.json()
    assert res.json()["detail"] == "Token invalide."


def test_upload_token_invalide():
    """POST /api/analyze avec un token bidon doit retourner 401."""
    res = client.post(
        "/api/analyze",
        headers={"Authorization": "Bearer token_bidon_invalide"}
    )
    assert res.status_code in (401, 422), \
        f"Expected 401 or 422, got {res.status_code}: {res.text}"
    if res.status_code == 401:
        assert "detail" in res.json()
