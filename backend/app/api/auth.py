"""
Routes d'authentification (JWT).

Endpoints :
- POST /api/auth/register  : Créer un compte utilisateur
- POST /api/auth/login     : Se connecter et obtenir un token JWT
- GET  /api/auth/me        : Récupérer les informations de l'utilisateur courant
"""

import logging

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.auth import creer_token, exiger_utilisateur
from app.db.database import (
    creer_utilisateur,
    mettre_a_jour_derniere_connexion,
    obtenir_essais_restants,
    obtenir_utilisateur_par_email,
    obtenir_utilisateur_par_id,
)
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str = Field(..., description="Adresse email de l'utilisateur")
    password: str = Field(
        ..., min_length=8, description="Mot de passe (minimum 8 caractères)"
    )


class LoginRequest(BaseModel):
    email: str = Field(..., description="Adresse email de l'utilisateur")
    password: str = Field(..., description="Mot de passe")


class AuthResponse(BaseModel):
    token: str = Field(..., description="Token JWT")
    utilisateur: dict = Field(..., description="Informations utilisateur")


class UserResponse(BaseModel):
    id: str
    email: str
    essais_restants: int
    est_abonne: bool
    credits: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", response_model=AuthResponse)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    """
    Crée un nouveau compte utilisateur.

    Le mot de passe est haché avec bcrypt avant stockage.
    Retourne un token JWT permettant d'accéder aux routes protégées.
    """
    # Vérifier si l'utilisateur existe déjà
    existing = obtenir_utilisateur_par_email(body.email)
    if existing:
        raise HTTPException(
            status_code=409, detail="Un compte avec cet email existe déjà."
        )

    # Hacher le mot de passe
    password_hash = bcrypt.hashpw(
        body.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # Créer l'utilisateur
    utilisateur_id = creer_utilisateur(body.email, password_hash)
    if utilisateur_id is None:
        raise HTTPException(
            status_code=500, detail="Erreur lors de la création du compte."
        )

    # Créer le token
    token = creer_token(utilisateur_id, body.email)
    logger.info(f"Nouvel utilisateur créé : {body.email}")

    return AuthResponse(
        token=token,
        utilisateur={
            "id": utilisateur_id,
            "email": body.email,
            "essais_restants": 3,
            "est_abonne": False,
            "credits": 0,
        },
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest):
    """
    Connecte un utilisateur existant.

    Vérifie l'email et le mot de passe, puis retourne un token JWT.
    """
    utilisateur = obtenir_utilisateur_par_email(body.email)
    if utilisateur is None:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    # Vérifier le mot de passe
    if not bcrypt.checkpw(
        body.password.encode("utf-8"),
        utilisateur["password_hash"].encode("utf-8"),
    ):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    # Mettre à jour la dernière connexion
    mettre_a_jour_derniere_connexion(utilisateur["id"])

    # Créer le token
    token = creer_token(utilisateur["id"], utilisateur["email"])
    logger.info(f"Connexion réussie : {utilisateur['email']}")

    # Récupérer les essais
    essais = obtenir_essais_restants(utilisateur["id"]) or {
        "essais_restants": 0,
        "est_abonne": False,
    }

    return AuthResponse(
        token=token,
        utilisateur={
            "id": utilisateur["id"],
            "email": utilisateur["email"],
            "essais_restants": essais["essais_restants"],
            "est_abonne": essais["est_abonne"],
            "credits": utilisateur.get("credits", 0),
        },
    )


@router.get("/me", response_model=UserResponse)
async def me(utilisateur: dict = Depends(exiger_utilisateur)):
    """
    Retourne les informations de l'utilisateur courant.
    Nécessite un token JWT valide.
    """
    detail = obtenir_utilisateur_par_id(utilisateur["id"])
    if detail is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    essais = obtenir_essais_restants(utilisateur["id"]) or {
        "essais_restants": 0,
        "est_abonne": False,
    }

    return UserResponse(
        id=detail["id"],
        email=detail["email"],
        essais_restants=essais["essais_restants"],
        est_abonne=essais["est_abonne"],
        credits=detail.get("credits", 0),
    )
