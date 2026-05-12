"""
Service de paiement Stripe pour Flashback Restore.

Gère les sessions de paiement (Checkout), les webhooks entrants,
et la consultation des abonnements clients.
"""

import logging
from typing import Optional

import stripe

from app.config import (
    STRIPE_API_KEY,
    STRIPE_PRICE_ANNUEL,
    STRIPE_PRICE_CREDITS_30,
    STRIPE_PRICE_CREDITS_50,
    STRIPE_PRICE_CREDITS_110,
    STRIPE_PRICE_DECOUVERTE,
    STRIPE_PRICE_PREMIUM,
    STRIPE_WEBHOOK_SECRET,
)

logger = logging.getLogger(__name__)

# Initialisation du SDK Stripe avec la clé API
stripe.api_key = STRIPE_API_KEY

# ---------------------------------------------------------------------------
# Mapping des plans → identifiants de prix Stripe
# ---------------------------------------------------------------------------

PLAN_VERS_PRIX: dict[str, str] = {
    "decouverte": STRIPE_PRICE_DECOUVERTE,
    "premium": STRIPE_PRICE_PREMIUM,
    "annuel": STRIPE_PRICE_ANNUEL,
}

CREDIT_PLAN_VERS_PRIX: dict[str, str] = {
    "30": STRIPE_PRICE_CREDITS_30,
    "50": STRIPE_PRICE_CREDITS_50,
    "110": STRIPE_PRICE_CREDITS_110,
}


# ---------------------------------------------------------------------------
# Session de paiement (Checkout)
# ---------------------------------------------------------------------------

async def creer_session_paiement(
    plan: str,
    email_utilisateur: str,
    url_succes: str,
    url_annulation: str,
) -> dict:
    """
    Crée une session de paiement Stripe Checkout.

    Args:
        plan: Identifiant du plan choisi (« decouverte », « premium », « annuel »).
        email_utilisateur: Adresse email du client.
        url_succes: URL de redirection après paiement réussi.
        url_annulation: URL de redirection en cas d'annulation.

    Returns:
        Un dictionnaire contenant l'URL de la session Checkout.

    Raises:
        ValueError: Si le plan demandé n'existe pas.
    """
    prix_id = PLAN_VERS_PRIX.get(plan)
    if not prix_id:
        plans_valides = ", ".join(PLAN_VERS_PRIX.keys())
        raise ValueError(
            f"Plan « {plan} » inconnu. Plans disponibles : {plans_valides}"
        )

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=email_utilisateur,
            line_items=[
                {
                    "price": prix_id,
                    "quantity": 1,
                }
            ],
            success_url=url_succes + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_annulation,
            locale="fr",
            metadata={
                "plan": plan,
                "email_utilisateur": email_utilisateur,
            },
        )

        logger.info(
            f"Session Checkout créée pour {email_utilisateur} — "
            f"plan={plan}, session_id={session.id}"
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }

    except stripe.error.StripeError as e:
        logger.exception(f"Erreur Stripe lors de la création de session : {e}")
        raise


# ---------------------------------------------------------------------------
# Session de paiement pour crédits (one-time payment)
# ---------------------------------------------------------------------------

async def creer_session_paiement_credits(
    plan: str,
    email: str,
    url_succes: str,
    url_annulation: str,
) -> dict:
    """
    Crée une session de paiement Stripe Checkout pour un pack de crédits.

    Args:
        plan: Nombre de crédits souhaité (« 30 », « 50 » ou « 110 »).
        email: Adresse email de l'utilisateur.
        url_succes: URL de redirection après paiement réussi.
        url_annulation: URL de redirection en cas d'annulation.

    Returns:
        Un dictionnaire contenant l'URL de la session Checkout et l'ID de session.

    Raises:
        ValueError: Si le plan demandé n'existe pas.
    """
    prix_id = CREDIT_PLAN_VERS_PRIX.get(plan)
    if not prix_id:
        plans_valides = ", ".join(CREDIT_PLAN_VERS_PRIX.keys())
        raise ValueError(
            f"Pack de crédits « {plan} » inconnu. Packs disponibles : {plans_valides}"
        )

    try:
        credits_count = int(plan)
    except (TypeError, ValueError):
        raise ValueError(f"Plan de crédits invalide : {plan}")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            customer_email=email,
            line_items=[
                {
                    "price": prix_id,
                    "quantity": 1,
                }
            ],
            success_url=url_succes + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_annulation,
            locale="fr",
            metadata={
                "type": "credits",
                "credits": str(credits_count),
                "email": email,
            },
        )

        logger.info(
            f"Session Checkout crédits créée pour {email} — "
            f"credits={credits_count}, session_id={session.id}"
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }

    except stripe.error.StripeError as e:
        logger.exception(f"Erreur Stripe lors de la création de session crédits : {e}")
        raise


# ---------------------------------------------------------------------------
# Traitement des webhooks Stripe
# ---------------------------------------------------------------------------

async def traiter_webhook(
    corps: bytes,
    signature: str,
) -> dict:
    """
    Traite un événement webhook entrant de Stripe.

    Vérifie la signature du webhook puis extrait le type d'événement
    et les données associées.

    Args:
        corps: Le corps brut (bytes) de la requête entrante.
        signature: La valeur de l'en-tête HTTP « Stripe-Signature ».

    Returns:
        Un dictionnaire contenant le type d'événement et les données.

    Raises:
        ValueError: Si la signature est invalide.
        stripe.error.SignatureVerificationError: Si la vérification échoue.
    """
    try:
        evenement = stripe.Webhook.construct_event(
            payload=corps,
            sig_header=signature,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as e:
        logger.error(f"Corps de webhook invalide : {e}")
        raise
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Signature de webhook invalide : {e}")
        raise

    type_evenement = evenement["type"]
    donnees = evenement["data"]["object"]

    logger.info(f"Webhook reçu : type={type_evenement}, id={evenement['id']}")

    return {
        "type": type_evenement,
        "data": {
            "id": donnees.get("id"),
            "customer": donnees.get("customer"),
            "subscription": donnees.get("subscription"),
            "status": donnees.get("status"),
            "amount_total": donnees.get("amount_total"),
            "currency": donnees.get("currency"),
            "metadata": donnees.get("metadata", {}),
        },
    }


# ---------------------------------------------------------------------------
# Consultation d'abonnement
# ---------------------------------------------------------------------------

async def obtenir_abonnement_stripe(
    id_client: str,
) -> dict:
    """
    Récupère les informations d'abonnement d'un client Stripe.

    Args:
        id_client: L'identifiant client Stripe (ex: « cus_xxxx »).

    Returns:
        Un dictionnaire contenant le statut et les détails de l'abonnement.
    """
    try:
        abonnements = stripe.Subscription.list(
            customer=id_client,
            status="all",
            limit=1,
        )

        if not abonnements.data:
            return {
                "statut": "aucun",
                "message": "Aucun abonnement trouvé pour ce client.",
            }

        abonnement = abonnements.data[0]

        return {
            "statut": abonnement.status,
            "abonnement_id": abonnement.id,
            "client_id": id_client,
            "plan": abonnement["items"].data[0].price.id if abonnement["items"].data else None,
            "debut_periode": abonnement.current_period_start,
            "fin_periode": abonnement.current_period_end,
            "annulation_auto": abonnement.cancel_at_period_end,
        }

    except stripe.error.StripeError as e:
        logger.exception(f"Erreur lors de la récupération de l'abonnement : {e}")
        raise
