"""
Authentification JWT — utilitaires.

Fournit des fonctions pour créer et vérifier des tokens JWT,
ainsi qu'une dépendance FastAPI pour protéger les routes.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import SECRET_KEY

logger = logging.getLogger(__name__)

# Configuration JWT
ALGORITHME = "HS256"
DUREE_TOKEN = timedelta(hours=24)

# Schéma de sécurité Bearer
securite = HTTPBearer(auto_error=False)


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
    """Décode et vérifie un token JWT. Lève une exception si invalide."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHME])


async def obtenir_utilisateur_courant(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(securite),
) -> Optional[dict]:
    """
    Dépendance FastAPI : extrait l'utilisateur courant du token JWT.

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

    return {
        "id": payload["sub"],
        "email": payload["email"],
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
