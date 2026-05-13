"""
Vérification des tokens JWT Clerk.

Utilise PyJWKClient pour récupérer les clés publiques RS256
depuis l'endpoint JWKS de Clerk, avec cache LRU (1h).
"""

import logging
from functools import lru_cache
from typing import Any, Dict

import jwt
from jwt import PyJWKClient, PyJWKClientError

from app.config import CLERK_ISSUER, CLERK_JWKS_URL, CLERK_AUDIENCE

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
