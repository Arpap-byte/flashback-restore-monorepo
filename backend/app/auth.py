"""
Authentification JWT — utilitaires.

Fournit des fonctions pour créer et vérifier des tokens JWT,
ainsi qu'une dépendance FastAPI pour protéger les routes.

Compatible avec les tokens NextAuth.js (Auth.js) et les tokens internes.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import AUTH_SECRET, SECRET_KEY

logger = logging.getLogger(__name__)

# Configuration JWT
ALGORITHME = "HS256"
DUREE_TOKEN = timedelta(hours=24)

# Schéma de sécurité Bearer
securite = HTTPBearer(auto_error=False)

# Liste des secrets acceptés (interne + NextAuth)
_SECRETS = [SECRET_KEY]
if AUTH_SECRET and AUTH_SECRET != SECRET_KEY:
    _SECRETS.append(AUTH_SECRET)


def creer_token(utilisateur_id: str, email: str) -> str:
    """Crée un token JWT pour un utilisateur."""
    maintenant = datetime.now(timezone.utc)
    expiration = maintenant + DUREE_TOKEN
    payload = {
        "sub": utilisateur_id,
        "email": email,
        "iat": maintenant,
        "exp": expiration,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHME)


def decoder_token(token: str) -> dict:
    """
    Décode et vérifie un token JWT.

    Essaie avec le secret interne, puis avec le secret NextAuth.
    Lève une exception si le token est invalide.
    """
    for secret in _SECRETS:
        try:
            return jwt.decode(token, secret, algorithms=[ALGORITHME])
        except jwt.InvalidTokenError:
            continue
    raise jwt.InvalidTokenError("Token invalide")


async def _trouver_ou_creer_utilisateur(payload: dict) -> Optional[dict]:
    """
    Trouve un utilisateur à partir du payload JWT (NextAuth ou interne).

    - Si sub est un UUID existant → retourne l'utilisateur
    - Si email présent → cherche par email, crée si nécessaire
    """
    from app.db.database import (
        creer_utilisateur_oauth,
        mettre_a_jour_derniere_connexion,
        obtenir_utilisateur_par_email,
        obtenir_utilisateur_par_id,
    )

    utilisateur_id = payload.get("sub", "")
    email = payload.get("email", "")

    # Essayer par ID d'abord
    if utilisateur_id:
        u = obtenir_utilisateur_par_id(utilisateur_id)
        if u:
            mettre_a_jour_derniere_connexion(u["id"])
            return u

    # Puis par email (token NextAuth)
    if email:
        u = obtenir_utilisateur_par_email(email)
        if u:
            mettre_a_jour_derniere_connexion(u["id"])
            return u

        # Créer automatiquement l'utilisateur OAuth
        provider = payload.get("provider", "nextauth")
        provider_id = payload.get("providerAccountId", email)
        nouvel_id = creer_utilisateur_oauth(email, provider, provider_id)
        if nouvel_id:
            u = obtenir_utilisateur_par_id(nouvel_id)
            if u:
                return u
        else:
            # L'email existe déjà (compte email/password) — retourner celui-ci
            u = obtenir_utilisateur_par_email(email)
            if u:
                mettre_a_jour_derniere_connexion(u["id"])
                return u

    return None


async def obtenir_utilisateur_courant(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(securite),
) -> Optional[dict]:
    """
    Dépendance FastAPI : extrait l'utilisateur courant du token JWT.

    Accepte les tokens internes ET les tokens NextAuth.js.
    Si l'utilisateur NextAuth n'existe pas encore, il est créé automatiquement.
    Si aucun token n'est fourni, retourne None.
    Si le token est invalide ou expiré, lève HTTP 401.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    try:
        payload = decoder_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide.")

    utilisateur = await _trouver_ou_creer_utilisateur(payload)
    if utilisateur is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable.")

    return {
        "id": utilisateur["id"],
        "email": utilisateur["email"],
    }


async def exiger_utilisateur(
    utilisateur: Optional[dict] = Depends(obtenir_utilisateur_courant),
) -> dict:
    """
    Dépendance FastAPI : exige un utilisateur authentifié.

    Lève HTTP 401 si aucun token valide n'est présent.
    """
    if utilisateur is None:
        raise HTTPException(status_code=401, detail="Authentification requise.")
    return utilisateur
