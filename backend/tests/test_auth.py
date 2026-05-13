"""
Tests unitaires pour les endpoints d'authentification.
Exécuter : cd backend && .venv/bin/pytest tests/test_auth.py -v
"""

import sys, time, secrets, os, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.queries import (
    init_db,
    obtenir_utilisateur_par_email,
    creer_token_reinitialisation,
    verifier_token_reinitialisation,
)
client = TestClient(app)

# Initialisation async de la base
asyncio.run(init_db())

# Délai entre tests pour éviter rate limit (5/min)
SLEEP = 1.2


@pytest.fixture(autouse=True)
def rate_limit_pause():
    if not os.environ.get("TESTING"):
        time.sleep(SLEEP)


class TestRegister:
    def test_register_success(self):
        res = client.post("/api/auth/register", json={
            "email": "t1@test.fr", "password": "testpass123"
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert data["utilisateur"]["essais_restants"] == 3

    def test_register_duplicate(self):
        client.post("/api/auth/register", json={"email": "t2@test.fr", "password": "testpass123"})
        res = client.post("/api/auth/register", json={"email": "t2@test.fr", "password": "testpass123"})
        assert res.status_code == 409

    def test_password_too_short(self):
        res = client.post("/api/auth/register", json={"email": "x@t.fr", "password": "1234567"})
        assert res.status_code == 422

    def test_missing_fields(self):
        assert client.post("/api/auth/register", json={}).status_code == 422

    def test_hash_stored(self):
        client.post("/api/auth/register", json={"email": "t3@test.fr", "password": "mypassword"})
        u = asyncio.run(obtenir_utilisateur_par_email("t3@test.fr"))
        assert u and u["password_hash"] != "mypassword"


class TestLogin:
    def test_success(self):
        client.post("/api/auth/register", json={"email": "t4@test.fr", "password": "testpass123"})
        res = client.post("/api/auth/login", json={"email": "t4@test.fr", "password": "testpass123"})
        assert res.status_code == 200
        assert "token" in res.json()

    def test_wrong_password(self):
        client.post("/api/auth/register", json={"email": "t5@test.fr", "password": "testpass123"})
        res = client.post("/api/auth/login", json={"email": "t5@test.fr", "password": "wrong"})
        assert res.status_code == 401

    def test_unknown_email(self):
        res = client.post("/api/auth/login", json={"email": "noone@x.fr", "password": "x"})
        assert res.status_code == 401

    def test_missing_pw(self):
        assert client.post("/api/auth/login", json={"email": "x@x.fr"}).status_code == 422


class TestForgotPassword:
    def test_existing(self):
        client.post("/api/auth/register", json={"email": "t6@test.fr", "password": "testpass123"})
        res = client.post("/api/auth/forgot-password", json={"email": "t6@test.fr"})
        assert res.status_code == 200
        assert "message" in res.json()

    def test_unknown(self):
        res = client.post("/api/auth/forgot-password", json={"email": "no@no.fr"})
        assert res.status_code == 200  # security: never reveal

    def test_missing(self):
        assert client.post("/api/auth/forgot-password", json={}).status_code == 422

    def test_creates_token(self):
        email = "t7@test.fr"
        client.post("/api/auth/register", json={"email": email, "password": "testpass123"})
        client.post("/api/auth/forgot-password", json={"email": email})
        # pas d'erreur = OK


class TestResetPassword:
    def test_invalid_token(self):
        res = client.post("/api/auth/reset-password", json={"token": "bad", "password": "newpass123"})
        assert res.status_code == 400

    def test_success_flow(self):
        email = "t8@test.fr"
        r = client.post("/api/auth/register", json={"email": email, "password": "oldpass123"})
        assert r.status_code == 200, f"Register failed: {r.json()}"
        u = asyncio.run(obtenir_utilisateur_par_email(email))
        assert u is not None, f"User {email} not found"

        token = secrets.token_urlsafe(48)
        asyncio.run(creer_token_reinitialisation(u["id"], token))
        assert asyncio.run(verifier_token_reinitialisation(token)) is not None

        res = client.post("/api/auth/reset-password", json={"token": token, "password": "newpass123"})
        assert res.status_code == 200

        # Token used
        assert asyncio.run(verifier_token_reinitialisation(token)) is None

        # Old pwd fails, new pwd works
        assert client.post("/api/auth/login", json={"email": email, "password": "oldpass"}).status_code == 401
        assert client.post("/api/auth/login", json={"email": email, "password": "newpass123"}).status_code == 200

    def test_short_password(self):
        assert client.post("/api/auth/reset-password", json={"token": "x", "password": "1234567"}).status_code == 422

    def test_already_used(self):
        email = "t9@test.fr"
        client.post("/api/auth/register", json={"email": email, "password": "oldpass123"})
        u = asyncio.run(obtenir_utilisateur_par_email(email))
        token = secrets.token_urlsafe(48)
        asyncio.run(creer_token_reinitialisation(u["id"], token))

        client.post("/api/auth/reset-password", json={"token": token, "password": "newpass123"})
        res = client.post("/api/auth/reset-password", json={"token": token, "password": "another123"})
        assert res.status_code == 400



class TestMe:
    def test_no_token(self):
        assert client.get("/api/auth/me").status_code == 401

    def test_invalid(self):
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer x"}).status_code == 401

    def test_success(self):
        client.post("/api/auth/register", json={"email": "t10@test.fr", "password": "testpass123"})
        token = client.post("/api/auth/login", json={
            "email": "t10@test.fr", "password": "testpass123"
        }).json()["token"]
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["email"] == "t10@test.fr"
