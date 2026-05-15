"""
Vérification des tokens JWT Clerk.

Utilise PyJWKClient pour récupérer les clés publiques RS256
depuis l'endpoint JWKS de Clerk, avec cache LRU (1h).
"""

import logging
from functools import lru_cache
from typing import Any, Dict, Optional

import jwt
from jwt import PyJWKClient, PyJWKClientError

from app.config import CLERK_ISSUER, CLERK_JWKS_URL, CLERK_AUDIENCE, CLERK_SECRET_KEY

logger = logging.getLogger(__name__)

# Cache du client JWKS — une seule instance, jamais expirée par le LRU
# Le cache interne de PyJWKClient (lifespan) gère le rafraîchissement des clés


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    """
    Retourne un client JWKS configuré pour Clerk.

    Le cache LRU (maxsize=1) garantit qu'une seule instance est créée.
    Le cache interne de PyJWKClient (lifespan=3600s) gère le
    rafraîchissement périodique des clés.
    """
    if not CLERK_JWKS_URL:
        raise ValueError("CLERK_JWKS_URL is not configured")
    return PyJWKClient(CLERK_JWKS_URL, cache_jwk_set=True, lifespan=3600)


def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    Vérifie un token JWT émis par Clerk.

    - Récupère la clé publique RS256 via JWKS
    - Décode et vérifie la signature, l'émetteur et l'expiration
    - Retourne le payload décodé

    Args:
        token: Le JWT encodé au format Bearer

    Returns:
        Le payload décodé du JWT

    Raises:
        jwt.InvalidTokenError: Si le token est invalide, expiré,
                               ou si l'émetteur ne correspond pas
    """
    if not CLERK_ISSUER:
        raise jwt.InvalidTokenError("CLERK_ISSUER is not configured")

    try:
        client = _get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
    except PyJWKClientError as e:
        logger.warning("Échec récupération clé JWKS : %s", e)
        raise jwt.InvalidTokenError("Impossible de récupérer la clé de signature Clerk")

    # Configuration de la vérification du token
    decode_options = {"verify_exp": True, "verify_aud": True} if CLERK_AUDIENCE else {"verify_exp": True, "verify_aud": False}
    decode_kwargs: dict = {
        "algorithms": ["RS256"],
        "issuer": CLERK_ISSUER,
        "options": decode_options,
    }
    if CLERK_AUDIENCE:
        decode_kwargs["audience"] = CLERK_AUDIENCE

    payload = jwt.decode(
        token,
        signing_key.key,
        **decode_kwargs,
    )

    logger.debug("Token Clerk vérifié pour sub=%s email=%s", payload.get("sub"), payload.get("email"))
    return payload


async def resoudre_email_clerck(user_id: str) -> Optional[str]:
    """
    Résout l'email d'un utilisateur Clerk via l'API Backend.

    Appelée quand le JWT Clerk ne contient pas d'email (utilisateurs
    créés via OAuth sans email primaire vérifié). Utilise la CLERK_SECRET_KEY
    pour interroger GET /v1/users/{user_id}.

    Args:
        user_id: L'ID Clerk de l'utilisateur (ex: "user_3Dgb1J1a929MIeMMZZcZt4Qe6Xx")

    Returns:
        L'email primaire de l'utilisateur, ou None si non trouvé/indisponible
    """
    if not CLERK_SECRET_KEY:
        logger.warning("CLERK_SECRET_KEY non configurée, impossible de résoudre l'email Clerk")
        return None

    # Extraire le domaine de l'ISSUER pour construire l'URL de l'API
    # Ex: https://thorough-satyr-83.clerk.accounts.dev → https://api.clerk.com
    # Pour les instances de développement Clerk, l'API est toujours sur api.clerk.com
    clerk_api_url = "https://api.clerk.com/v1"

    import httpx

    try:
        headers = {
            "Authorization": f"Bearer {CLERK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{clerk_api_url}/users/{user_id}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 404:
                logger.warning("Utilisateur Clerk introuvable via API: user_id=%s", user_id)
                return None
            if resp.status_code != 200:
                logger.warning(
                    "Erreur API Clerk users/%s: HTTP %s",
                    user_id, resp.status_code,
                )
                return None

            data = resp.json()
            # Récupérer l'email primaire depuis les adresses email
            email_addresses = data.get("email_addresses", [])
            for addr in email_addresses:
                email_obj = addr.get("email_address", "")
                if email_obj and not email_obj.endswith("@placeholder.local"):
                    logger.info(
                        "Email réel résolu via API Clerk: user_id=%s email=%s",
                        user_id, email_obj,
                    )
                    return email_obj

            # Fallback : utiliser le premier email même si placeholder,
            # mais logger un avertissement
            if email_addresses:
                fallback = email_addresses[0].get("email_address", "")
                logger.warning(
                    "Aucun email non-placeholder trouvé pour Clerk user_id=%s, "
                    "fallback=%s",
                    user_id, fallback,
                )
                return fallback if fallback else None

            logger.warning("Aucune adresse email pour Clerk user_id=%s", user_id)
            return None

    except httpx.HTTPError as e:
        logger.error("Erreur réseau lors de la résolution email Clerk user_id=%s: %s", user_id, e)
        return None
    except Exception as e:
        logger.error("Erreur inattendue résolution email Clerk user_id=%s: %s", user_id, e)
        return None
