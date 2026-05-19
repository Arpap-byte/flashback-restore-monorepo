"""
Authentification JWT — utilitaires.

Fournit des fonctions pour créer et vérifier des tokens JWT,
ainsi qu'une dépendance FastAPI pour protéger les routes.

Compatible avec les tokens NextAuth.js (Auth.js), les tokens Clerk et les tokens internes.
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
DUREE_TOKEN_TELECHARGEMENT = timedelta(minutes=30)  # Pour URLs d'images/vidéos (balises <img>/<video>)

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


def creer_token_telechargement(utilisateur_id: str) -> str:
    """Crée un token JWT pour le téléchargement d'images/vidéos."""
    maintenant = datetime.now(timezone.utc)
    expiration = maintenant + DUREE_TOKEN_TELECHARGEMENT
    payload = {
        "sub": utilisateur_id,
        "scope": "download",
        "iat": maintenant,
        "exp": expiration,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHME)


def decoder_token(token: str) -> dict:
    """
    Décode et vérifie un token JWT.

    Essaie avec le secret interne HS256, puis avec le secret NextAuth,
    puis avec la vérification Clerk RS256 (JWKS).
    Lève une exception si le token est invalide.
    """
    # Étape 1 : tokens internes et NextAuth (HS256)
    for secret in _SECRETS:
        try:
            return jwt.decode(token, secret, algorithms=[ALGORITHME])
        except jwt.InvalidTokenError:
            continue

    # Étape 2 : tokens Clerk (RS256 via JWKS)
    from app.clerk_auth import verify_clerk_token
    try:
        return verify_clerk_token(token)
    except jwt.InvalidTokenError:
        pass

    raise jwt.InvalidTokenError("Token invalide")


async def _trouver_ou_creer_utilisateur(payload: dict) -> Optional[dict]:
    """
    Trouve un utilisateur à partir du payload JWT (NextAuth, interne ou Clerk).

    - Si sub est un UUID existant → retourne l'utilisateur
    - Si email présent → cherche par email
    - Si le token vient de Clerk (contient "sid") → crée l'utilisateur si nécessaire
    - Sinon (NextAuth) → rejette les emails inconnus
    """
    from app.db.queries import (
        creer_utilisateur_oauth,
        mettre_a_jour_derniere_connexion,
        obtenir_utilisateur_par_email,
        obtenir_utilisateur_par_id,
        obtenir_utilisateur_par_oauth,
    )

    utilisateur_id = payload.get("sub", "")
    email = payload.get("email", "")
    est_clerk = "sid" in payload  # Les tokens Clerk contiennent un session ID

    # Essayer par ID d'abord (seulement si ce n'est pas un sub Clerk "user_xxx")
    if utilisateur_id and not utilisateur_id.startswith("user_"):
        u = await obtenir_utilisateur_par_id(utilisateur_id)
        if u:
            await mettre_a_jour_derniere_connexion(u["id"])
            return u

    # Token Clerk : chercher par oauth_provider_id (sub Clerk)
    if est_clerk and utilisateur_id:
        u = await obtenir_utilisateur_par_oauth("clerk", utilisateur_id)
        if u:
            await mettre_a_jour_derniere_connexion(u["id"])
            # Mettre à jour l'email si le token Clerk contient un email différent
            if email and email.lower() != (u.get("email", "") or "").lower():
                from app.db.queries import mettre_a_jour_email
                try:
                    await mettre_a_jour_email(u["id"], email.lower())
                    logger.info(
                        "Email utilisateur Clerk mis à jour: id=%s ancien=%s → nouvel_email=%s",
                        u["id"], u.get("email"), email,
                    )
                    u["email"] = email
                except Exception:
                    # Email déjà pris par un autre compte — logguer sans bloquer
                    logger.warning(
                        "Email Clerk non mis à jour (déjà existant): id=%s email=%s → tentative=%s",
                        u["id"], u.get("email"), email,
                    )
            return u

    # Puis par email
    if email:
        u = await obtenir_utilisateur_par_email(email)
        if u:
            await mettre_a_jour_derniere_connexion(u["id"])
            return u

    # Token Clerk : créer l'utilisateur automatiquement
    # Mais JAMAIS avec un email placeholder — résoudre via l'API Clerk d'abord
    if est_clerk:
        provider_id = utilisateur_id

        # Si pas d'email dans le JWT, tenter la résolution via l'API Clerk
        if not email:
            from app.clerk_auth import resoudre_email_clerck
            email_resolu = await resoudre_email_clerck(provider_id)
            if email_resolu:
                email = email_resolu
            else:
                logger.error(
                    "REFUS: compte Clerk sans email identifiable — "
                    "sub=%s, impossible de résoudre via l'API Clerk",
                    provider_id,
                )
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Impossible d'identifier votre adresse email via Clerk. "
                        "Veuillez vérifier que votre compte Clerk possède une "
                        "adresse email primaire vérifiée."
                    ),
                )

        # Vérifier que l'email n'est pas un placeholder
        if email.endswith("@placeholder.local"):
            logger.error(
                "REFUS: email placeholder détecté pour Clerk user_id=%s email=%s",
                provider_id, email,
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "Votre compte ne possède pas d'adresse email vérifiée. "
                    "Veuillez ajouter une adresse email dans vos paramètres Clerk."
                ),
            )

        logger.info(
            "Création automatique utilisateur Clerk: email=%s provider_id=%s",
            email, provider_id,
        )
        from app.services.clerk_account import ensure_compte
        result = await ensure_compte(provider_id, email.lower())
        if result:
            return await obtenir_utilisateur_par_id(result["id"])

    # Token NextAuth ou autre : ne pas créer automatiquement
    if email:
        logger.warning("Tentative de connexion avec email inconnu: %s", email)

    return None


async def obtenir_utilisateur_courant(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(securite),
) -> Optional[dict]:
    """
    Dépendance FastAPI : extrait l'utilisateur courant du token JWT.

    Accepte les tokens internes, les tokens NextAuth.js ET les tokens Clerk.
    Si l'utilisateur Clerk n'existe pas encore, il est créé automatiquement.
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
