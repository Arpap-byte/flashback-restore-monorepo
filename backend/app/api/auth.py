"""
Routes d'authentification (JWT).

Endpoints :
- POST /api/auth/register         : Créer un compte utilisateur
- POST /api/auth/login            : Se connecter et obtenir un token JWT
- POST /api/auth/forgot-password  : Demander un lien de réinitialisation
- POST /api/auth/reset-password   : Réinitialiser le mot de passe
- GET  /api/auth/me               : Récupérer les informations de l'utilisateur courant
"""

import logging
import secrets
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from app.auth import creer_token, exiger_utilisateur
from app.config import SITE_URL
from app.services.audit import log_auth
from app.db.queries import (
    ANIMATIONS_PAR_PLAN,
    changer_mot_de_passe,
    creer_token_reinitialisation,
    creer_utilisateur,
    creer_utilisateur_oauth,
    marquer_token_utilise,
    mettre_a_jour_derniere_connexion,
    obtenir_essais_restants,
    obtenir_plan_utilisateur,
    obtenir_utilisateur_par_email,
    obtenir_utilisateur_par_id,
    obtenir_utilisateur_par_oauth,
    verifier_token_reinitialisation,
)
from app.limiter import limiter
from app.mail import envoyer_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Schémas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Adresse email de l'utilisateur")
    password: str = Field(
        ..., min_length=8, description="Mot de passe (minimum 8 caractères)"
    )


class LoginRequest(BaseModel):
    email: str = Field(..., description="Adresse email de l'utilisateur")
    password: str = Field(..., description="Mot de passe")


class AuthResponse(BaseModel):
    token: str = Field(..., description="Token JWT")
    utilisateur: dict = Field(..., description="Informations utilisateur")


class OAuthRequest(BaseModel):
    provider: str = Field(..., description="Fournisseur OAuth (google, facebook, etc.)")
    provider_id: str = Field(..., description="Identifiant utilisateur chez le fournisseur")
    email: str = Field(..., description="Email de l'utilisateur")
    name: Optional[str] = Field(None, description="Nom affiché")


class UserResponse(BaseModel):
    id: str
    email: str
    essais_restants: int
    est_abonne: bool
    credits: int
    plan: str = Field(default="gratuit", description="Forfait actuel (gratuit, decouverte, premium, annuel, pro)")
    animations_utilisees: int = Field(default=0, description="Animations utilisées ce mois-ci")
    animations_limite: int = Field(default=0, description="Limite d'animations par mois (-1 = illimité)")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    """
    Crée un nouveau compte utilisateur.

    Le mot de passe est haché avec bcrypt avant stockage.
    Retourne un token JWT permettant d'accéder aux routes protégées.

    Pour éviter l'énumération d'utilisateurs, si l'email existe déjà,
    un 202 Accepted est retourné avec un message générique (l'info est logguée côté serveur).
    """
    # Vérifier si l'utilisateur existe déjà
    existing = await obtenir_utilisateur_par_email(body.email)
    if existing:
        await log_auth(request, "register", email=body.email, reussite=False, detail="Email déjà utilisé")
        logger.info(f"Tentative d'inscription avec un email déjà utilisé : {body.email}")
        return JSONResponse(
            status_code=202,
            content={"message": "Si cet email n'est pas déjà utilisé, un email de vérification a été envoyé."},
        )

    # Hacher le mot de passe
    password_hash = bcrypt.hashpw(
        body.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # Créer l'utilisateur
    utilisateur_id = await creer_utilisateur(body.email, password_hash)
    if utilisateur_id is None:
        raise HTTPException(
            status_code=500, detail="Erreur lors de la création du compte."
        )

    # Créer le token
    token = creer_token(utilisateur_id, body.email)
    logger.info(f"Nouvel utilisateur créé : {body.email}")

    # Audit log
    await log_auth(request, "register", email=body.email, utilisateur_id=utilisateur_id, reussite=True)

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
    utilisateur = await obtenir_utilisateur_par_email(body.email)
    if utilisateur is None:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    # Vérifier le mot de passe
    if not bcrypt.checkpw(
        body.password.encode("utf-8"),
        utilisateur["password_hash"].encode("utf-8"),
    ):
        await log_auth(request, "login", email=body.email, reussite=False, detail="Mot de passe incorrect")
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    # Mettre à jour la dernière connexion
    await mettre_a_jour_derniere_connexion(utilisateur["id"])

    # Créer le token
    token = creer_token(utilisateur["id"], utilisateur["email"])
    logger.info(f"Connexion réussie : {utilisateur['email']}")

    # Audit log
    await log_auth(request, "login", email=body.email, utilisateur_id=utilisateur["id"], reussite=True)

    # Récupérer les essais
    essais = await obtenir_essais_restants(utilisateur["id"]) or {
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




# ---------------------------------------------------------------------------
# Réinitialisation de mot de passe
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="Adresse email du compte")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Token de réinitialisation reçu par email")
    password: str = Field(
        ..., min_length=8, description="Nouveau mot de passe (minimum 8 caractères)"
    )


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    """
    Envoie un email de réinitialisation de mot de passe.

    Pour des raisons de sécurité, retourne toujours un succès,
    même si l'email n'existe pas (pour éviter l'énumération d'utilisateurs).
    """
    utilisateur = await obtenir_utilisateur_par_email(body.email)

    if utilisateur and utilisateur.get("password_hash"):
        await log_auth(request, "forgot_password", email=body.email, utilisateur_id=utilisateur["id"], reussite=True)
        # Générer un token sécurisé
        token = secrets.token_urlsafe(48)
        await creer_token_reinitialisation(utilisateur["id"], token)

        # Envoyer l'email
        lien = f"{SITE_URL}/auth/reset-password?token={token}"
        corps = f"""
        <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px">
            <h2 style="color:#f59e0b">Flashback Restore</h2>
            <p>Vous avez demandé la réinitialisation de votre mot de passe.</p>
            <p>Cliquez sur le bouton ci-dessous pour définir un nouveau mot de passe :</p>
            <a href="{lien}" style="display:inline-block;padding:12px 24px;background:#f59e0b;color:#111;text-decoration:none;border-radius:8px;font-weight:bold;margin:16px 0">
                Réinitialiser mon mot de passe
            </a>
            <p style="color:#888;font-size:12px">Ce lien expire dans 30 minutes.</p>
            <p style="color:#888;font-size:12px">Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</p>
        </div>
        """

        envoyer_email(body.email, "Réinitialisation de votre mot de passe", corps)
        logger.info(f"Email de réinitialisation envoyé à {body.email}")

    if not utilisateur or not utilisateur.get("password_hash"):
        await log_auth(request, "forgot_password", email=body.email, reussite=False, detail="Email inconnu ou compte OAuth")
    # Toujours retourner un succès
    return {"message": "Si un compte existe avec cet email, vous recevrez un lien de réinitialisation."}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, body: ResetPasswordRequest):
    """
    Réinitialise le mot de passe avec un token valide.
    """
    # Vérifier le token
    entry = await verifier_token_reinitialisation(body.token)
    if not entry:
        await log_auth(request, "reset_password", reussite=False, detail="Token invalide ou expiré")
        raise HTTPException(
            status_code=400,
            detail="Ce lien de réinitialisation est invalide ou a expiré.",
        )

    # Hacher le nouveau mot de passe
    password_hash = bcrypt.hashpw(
        body.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # Changer le mot de passe et marquer le token (atomique)
    from app.db.session import async_session
    async with async_session() as session:
        async with session.begin():
            ok = await changer_mot_de_passe(entry["utilisateur_id"], password_hash, session=session)
            if not ok:
                raise HTTPException(status_code=500, detail="Erreur lors du changement de mot de passe.")
            await marquer_token_utilise(body.token, session=session)

    logger.info(f"Mot de passe réinitialisé pour l'utilisateur {entry['utilisateur_id']}")

    await log_auth(request, "reset_password", utilisateur_id=entry["utilisateur_id"], reussite=True)

    return {"message": "Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter."}
