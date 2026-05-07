"""
Routes de l'API Flaskback Restore.

Endpoints :
- POST /api/analyze   : Analyser les défauts d'une photo
- POST /api/restore   : Restaurer une photo ancienne
- POST /api/animate   : Créer une animation
- GET  /api/animate/{id} : Suivre le statut d'une animation
- GET  /api/health    : Vérifier la santé du service
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from PIL import Image, ImageEnhance, ImageFilter

from app.config import DID_API_KEY, DID_BASE_URL, GEMINI_API_KEY, UPLOAD_DIR
from app.auth import exiger_utilisateur
from app.db.database import (
    CREDITS_PAR_PLAN,
    consommer_credit,
    crediter_utilisateur,
    creer_abonnement,
    creer_travail,
    enregistrer_achat_credits,
    mettre_a_jour_abonnement,
    mettre_a_jour_attribution_credits,
    mettre_a_jour_job_externe_id,
    mettre_a_jour_travail,
    obtenir_abonnement,
    obtenir_travail,
    obtenir_travail_par_job_externe,
    obtenir_utilisateur_par_email,
)
from app.limiter import limiter
from app.models.schemas import (
    AnalyseReponse,
    AnimationReponse,
    AnimationRequete,
    CheckoutReponse,
    CheckoutRequete,
    EtatAbonnement,
    ParametresRestauration,
    RestaurationReponse,
    SanteReponse,
    StatutAnimation,
    StatutAnimationReponse,
    WebhookReponse,
)
from app.services.did_service import creer_animation, verifier_statut_animation
from app.services.gemini_service import analyser_photo, obtenir_parametres_restauration
from app.services.stripe_service import (
    creer_session_paiement,
    creer_session_paiement_credits,
    obtenir_abonnement_stripe,
    traiter_webhook,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Taille maximale des uploads : 20 Mo
TAILLE_MAX_UPLOAD = 20 * 1024 * 1024

# Formats d'image acceptés
FORMATS_ACCEPTES = {"image/jpeg", "image/png", "image/webp", "image/tiff"}

# URLs de redirection Stripe (frontend)
URL_SUCCES_STRIPE = "http://localhost:3000/abonnement/succes"
URL_ANNULATION_STRIPE = "http://localhost:3000/abonnement/annulation"


# ---------------------------------------------------------------------------
# Santé
# ---------------------------------------------------------------------------

@router.get("/health", response_model=SanteReponse)
@limiter.limit("10/minute")
async def sante(request: Request):
    """
    Vérification de l'état du service.

    Retourne le statut de l'API et teste réellement la connectivité
    aux services externes (Gemini et le service d'animation).
    """
    import httpx
    from google import genai

    # Test Gemini : tentative de listage des modèles
    gemini_ok = False
    if GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            # Tente de lister les modèles pour vérifier la connectivité
            client.models.list()
            gemini_ok = True
        except Exception as e:
            logger.warning(f"Test de connectivité Gemini échoué : {e}")

    # Test D-ID : appel GET à l'API
    did_ok = False
    if DID_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{DID_BASE_URL}/talks",
                    headers={
                        "Authorization": f"Basic {DID_API_KEY}",
                        "Accept": "application/json",
                    },
                )
                # Une réponse 200 ou 401 (auth OK mais pas de talks) indique que le service est joignable
                did_ok = response.status_code in (200, 401)
        except Exception as e:
            logger.warning(f"Test de connectivité D-ID échoué : {e}")

    return SanteReponse(
        statut="OK",
        version="1.0.0",
        gemini_disponible=gemini_ok,
        did_disponible=did_ok,
    )


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=AnalyseReponse)
async def analyser(
    fichier: UploadFile = File(...),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Analyse une photo ancienne pour détecter ses défauts.

    L'image est analysée par IA pour identifier rayures, décoloration,
    taches, déchirures, bruit et fournit des recommandations de restauration.

    Args:
        fichier: Le fichier image à analyser (JPEG, PNG, WebP, TIFF).

    Returns:
        Un rapport d'analyse complet en français.
    """
    # Validation
    if fichier.content_type and fichier.content_type not in FORMATS_ACCEPTES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non accepté : {fichier.content_type}. "
                   f"Formats acceptés : {', '.join(FORMATS_ACCEPTES)}",
        )

    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux ({len(contenu)} octets). "
                   f"Taille maximale : {TAILLE_MAX_UPLOAD} octets.",
        )

    # Sauvegarde du fichier
    nom_fichier = f"{uuid.uuid4()}_{fichier.filename or 'photo.jpg'}"
    chemin = UPLOAD_DIR / nom_fichier
    chemin.write_bytes(contenu)

    # Création du travail dans la base
    travail_id = creer_travail("analyse", chemin_photo=str(chemin), utilisateur_id=utilisateur["id"])
    mettre_a_jour_travail(travail_id, statut="en_cours")

    try:
        resultat = await analyser_photo(str(chemin))
        mettre_a_jour_travail(
            travail_id,
            statut="termine",
            resultat_json=resultat.model_dump_json(),
        )
        return resultat
    except Exception as e:
        logger.exception(f"Erreur lors de l'analyse : {e}")
        mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'analyse : {str(e)}",
        )


# ---------------------------------------------------------------------------
# Restauration
# ---------------------------------------------------------------------------

def _appliquer_restauration_pillow(
    chemin_source: str,
    chemin_destination: str,
    params: ParametresRestauration,
) -> None:
    """
    Applique les paramètres de restauration à une image avec Pillow.

    Étapes :
    1. Ajustement de la luminosité
    2. Ajustement du contraste
    3. Ajustement de la saturation
    4. Ajustement de la netteté (filtre unsharp mask)
    5. Débruitage (filtre median)
    6. Correction des canaux de couleur (rouge, vert, bleu)
    """
    image = Image.open(chemin_source).convert("RGB")
    logger.info(
        f"Restauration de {chemin_source} — "
        f"taille={image.size}, params={params.model_dump()}"
    )

    # 1. Luminosité
    if params.luminosite != 1.0:
        ameliorateur = ImageEnhance.Brightness(image)
        image = ameliorateur.enhance(params.luminosite)

    # 2. Contraste
    if params.contraste != 1.0:
        ameliorateur = ImageEnhance.Contrast(image)
        image = ameliorateur.enhance(params.contraste)

    # 3. Saturation
    if params.saturation != 1.0:
        ameliorateur = ImageEnhance.Color(image)
        image = ameliorateur.enhance(params.saturation)

    # 4. Netteté (unsharp mask ou sharpen)
    if params.nettete > 1.0:
        ameliorateur = ImageEnhance.Sharpness(image)
        image = ameliorateur.enhance(params.nettete)
    elif params.nettete < 1.0:
        # Flou léger si nettete < 1
        rayon = int((1.0 - params.nettete) * 2)
        image = image.filter(ImageFilter.GaussianBlur(radius=max(1, rayon)))

    # 5. Débruitage (filtre médian)
    if params.debruitage > 0.1:
        # Taille du kernel : 1, 3 ou 5 selon l'intensité
        taille = 3 if params.debruitage < 0.5 else 5
        image = image.filter(ImageFilter.MedianFilter(size=taille))

    # 6. Correction des canaux de couleur
    if (
        params.correction_rouge != 1.0
        or params.correction_vert != 1.0
        or params.correction_bleu != 1.0
    ):
        r, g, b = image.split()
        r = r.point(lambda p: min(255, int(p * params.correction_rouge)))
        g = g.point(lambda p: min(255, int(p * params.correction_vert)))
        b = b.point(lambda p: min(255, int(p * params.correction_bleu)))
        image = Image.merge("RGB", (r, g, b))

    # Sauvegarde
    image.save(chemin_destination, quality=95)
    logger.info(f"Image restaurée sauvegardée : {chemin_destination}")


@router.post("/restore", response_model=RestaurationReponse)
async def restaurer(
    fichier: UploadFile = File(...),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Restaure une photo ancienne en utilisant l'intelligence artificielle.

    Processus :
    1. La photo est d'abord analysée pour détecter ses défauts.
    2. L'IA détermine les paramètres de restauration optimaux.
    3. Pillow applique ces paramètres (luminosité, contraste, saturation,
       netteté, débruitage, correction colorimétrique).
    4. L'image restaurée est retournée.

    **Authentification requise** : un crédit ou essai gratuit est consommé.

    Args:
        fichier: Le fichier image à restaurer (JPEG, PNG, WebP, TIFF).

    Returns:
        L'analyse, les paramètres appliqués, et le chemin de l'image restaurée.
    """
    # Validation
    if fichier.content_type and fichier.content_type not in FORMATS_ACCEPTES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non accepté : {fichier.content_type}. "
                   f"Formats acceptés : {', '.join(FORMATS_ACCEPTES)}",
        )

    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux ({len(contenu)} octets). "
                   f"Taille maximale : {TAILLE_MAX_UPLOAD} octets.",
        )

    # Sauvegarde du fichier original
    nom_base = uuid.uuid4().hex
    nom_original = f"{nom_base}_{fichier.filename or 'photo.jpg'}"
    chemin_original = UPLOAD_DIR / nom_original
    chemin_original.write_bytes(contenu)

    # Création du travail
    travail_id = creer_travail("restauration", chemin_photo=str(chemin_original), utilisateur_id=utilisateur["id"])
    mettre_a_jour_travail(travail_id, statut="en_cours")

    # Vérification des crédits avant traitement
    resultat_credit = consommer_credit(utilisateur["id"], "restauration", travail_id)
    if not resultat_credit["succes"]:
        mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=resultat_credit.get("raison", "Crédits insuffisants"),
        )
        raise HTTPException(
            status_code=402,
            detail=resultat_credit.get("raison", "Crédits insuffisants. Achetez des crédits pour continuer."),
        )

    try:
        # Étape 1 : Analyse des défauts
        analyse = await analyser_photo(str(chemin_original))

        # Étape 2 : Paramètres de restauration
        params = await obtenir_parametres_restauration(str(chemin_original))

        # Étape 3 : Application avec Pillow
        nom_restaure = f"{nom_base}_restaure.jpg"
        chemin_restaure = UPLOAD_DIR / nom_restaure
        _appliquer_restauration_pillow(
            str(chemin_original),
            str(chemin_restaure),
            params,
        )

        # Succès
        resultat = RestaurationReponse(
            message="Photo restaurée avec succès !",
            analyse=analyse,
            parametres=params,
            url_image=f"/uploads/{nom_restaure}",
        )
        mettre_a_jour_travail(
            travail_id,
            statut="termine",
            chemin_resultat=str(chemin_restaure),
            resultat_json=json.dumps({
                "analyse": analyse.model_dump(),
                "parametres": params.model_dump(),
            }),
        )
        return resultat

    except Exception as e:
        logger.exception(f"Erreur lors de la restauration : {e}")
        mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la restauration : {str(e)}",
        )


# ---------------------------------------------------------------------------
# Animation (D-ID)
# ---------------------------------------------------------------------------

@router.post("/animate", response_model=AnimationReponse)
async def animer(
    fichier: UploadFile = File(...),
    texte: str = Form("Bonjour ! Je suis un souvenir restauré."),
    utilisateur: dict = Depends(exiger_utilisateur),
):
    """
    Crée une animation de portrait parlant (style Harry Potter).

    La photo est sauvegardée localement puis envoyée au service d'animation pour générer
    une vidéo où le visage s'anime et prononce le texte fourni.

    **Authentification requise** : un crédit ou essai gratuit est consommé.

    **Important** : Pour que le service d'animation puisse accéder à la photo, celle-ci doit
    être accessible via une URL publique. En développement, utilisez un
    service comme ngrok ou déployez le backend sur un serveur public.

    Args:
        fichier: La photo du visage à animer.
        texte: Le texte que le portrait va prononcer (français).

    Returns:
        L'identifiant du travail d'animation pour suivi ultérieur.
    """
    # Validation
    if fichier.content_type and fichier.content_type not in FORMATS_ACCEPTES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non accepté : {fichier.content_type}.",
        )

    contenu = await fichier.read()
    if len(contenu) > TAILLE_MAX_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail="Fichier trop volumineux.",
        )

    # Sauvegarde
    nom_fichier = f"{uuid.uuid4().hex}_{fichier.filename or 'portrait.jpg'}"
    chemin = UPLOAD_DIR / nom_fichier
    chemin.write_bytes(contenu)

    # Création du travail
    travail_id = creer_travail("animation", chemin_photo=str(chemin), utilisateur_id=utilisateur["id"])
    mettre_a_jour_travail(travail_id, statut="en_cours")

    # Vérification des crédits avant traitement
    resultat_credit = consommer_credit(utilisateur["id"], "animation", travail_id)
    if not resultat_credit["succes"]:
        mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=resultat_credit.get("raison", "Crédits insuffisants"),
        )
        raise HTTPException(
            status_code=402,
            detail=resultat_credit.get("raison", "Crédits insuffisants. Achetez des crédits pour continuer."),
        )

    try:
        # Construction de l'URL publique de la photo
        # En production, utilisez l'URL réelle de votre serveur
        url_photo = f"http://148.230.116.52:8000/uploads/{nom_fichier}"

        job_did = await creer_animation(url_photo, texte=texte)

        # Association du job D-ID au travail local
        # job_externe_id is stored in résultat_json and updated via a direct SQL call
        mettre_a_jour_travail(
            travail_id,
            statut="en_cours",
            resultat_json=json.dumps({"job_did": job_did}),
        )
        # Also update the job_externe_id column separately
        mettre_a_jour_job_externe_id(travail_id, job_did)

        return AnimationReponse(
            message="Animation créée avec succès. Vous pouvez suivre sa progression.",
            job_id=job_did,
        )

    except Exception as e:
        logger.exception(f"Erreur lors de la création d'animation : {e}")
        mettre_a_jour_travail(
            travail_id,
            statut="erreur",
            message_erreur=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la création d'animation : {str(e)}",
        )


@router.get("/animate/{job_id}", response_model=StatutAnimationReponse)
async def statut_animation(job_id: str):
    """
    Vérifie le statut d'une animation.

    Interroge le service d'animation pour connaître l'avancement d'une animation.
    Lorsque le statut est « done », l'URL de la vidéo est retournée.

    Args:
        job_id: L'identifiant du travail d'animation (retourné par POST /api/animate).

    Returns:
        Le statut actuel et l'URL de la vidéo si terminée.
    """
    try:
        data = await verifier_statut_animation(job_id)

        # Correspondance des statuts D-ID vers nos statuts
        correspondance_statut = {
            "created": StatutAnimation.EN_ATTENTE,
            "started": StatutAnimation.EN_COURS,
            "processing": StatutAnimation.EN_COURS,
            "done": StatutAnimation.TERMINE,
            "error": StatutAnimation.ERREUR,
        }
        statut_interne = correspondance_statut.get(
            data["statut"], StatutAnimation.EN_ATTENTE
        )

        # Mise à jour du travail local
        travail = obtenir_travail_par_job_externe(job_id)
        if travail:
            if statut_interne == StatutAnimation.TERMINE:
                mettre_a_jour_travail(
                    travail["id"],
                    statut="termine",
                    chemin_resultat=data.get("url_video"),
                    resultat_json=json.dumps(data),
                )
            elif statut_interne == StatutAnimation.ERREUR:
                mettre_a_jour_travail(
                    travail["id"],
                    statut="erreur",
                    message_erreur=data.get("message", "Erreur inconnue"),
                )

        return StatutAnimationReponse(
            job_id=job_id,
            statut=statut_interne,
            url_video=data.get("url_video"),
            message=data.get("message"),
        )

    except Exception as e:
        logger.exception(f"Erreur lors du suivi d'animation : {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du suivi d'animation : {str(e)}",
        )


# ---------------------------------------------------------------------------
# Stripe — Paiements et abonnements
# ---------------------------------------------------------------------------

@router.post("/stripe/create-checkout", response_model=CheckoutReponse)
async def creer_checkout(requete: CheckoutRequete):
    """
    Crée une session de paiement Stripe Checkout.

    Le client choisit un plan parmi « decouverte », « premium » ou « annuel ».
    Une session Stripe est créée et l'URL de paiement est retournée.

    Args:
        requete: Contient le plan choisi et l'email de l'utilisateur.

    Returns:
        L'URL de la session Checkout Stripe.
    """
    try:
        resultat = await creer_session_paiement(
            plan=requete.plan,
            email_utilisateur=requete.email_utilisateur,
            url_succes=URL_SUCCES_STRIPE,
            url_annulation=URL_ANNULATION_STRIPE,
        )
        return CheckoutReponse(
            checkout_url=resultat["checkout_url"],
            session_id=resultat["session_id"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur création checkout : {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la création de la session de paiement.",
        )


@router.post("/stripe/create-credit-checkout", response_model=CheckoutReponse)
async def creer_checkout_credits(requete: CheckoutRequete):
    """
    Crée une session de paiement Stripe Checkout pour acheter des crédits.

    Le client choisit un pack de crédits parmi « 30 », « 50 » ou « 110 ».
    Une session Stripe en mode paiement unique est créée.

    Args:
        requete: Contient le plan (30, 50, 110) et l'email de l'utilisateur.

    Returns:
        L'URL de la session Checkout Stripe.
    """
    try:
        resultat = await creer_session_paiement_credits(
            plan=requete.plan,
            email=requete.email_utilisateur,
            url_succes=URL_SUCCES_STRIPE,
            url_annulation=URL_ANNULATION_STRIPE,
        )
        return CheckoutReponse(
            checkout_url=resultat["checkout_url"],
            session_id=resultat["session_id"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Erreur création checkout crédits : {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la création de la session de paiement crédits.",
        )


@router.post("/stripe/webhook", response_model=WebhookReponse)
async def webhook_stripe(request: Request):
    """
    Reçoit les événements webhook de Stripe.

    Traite les événements tels que :
    - checkout.session.completed : Paiement validé → création d'abonnement
    - customer.subscription.deleted : Abonnement résilié
    - customer.subscription.updated : Abonnement modifié
    - invoice.payment_failed : Échec de paiement

    Args:
        request: La requête HTTP entrante (corps brut + en-tête Stripe-Signature).

    Returns:
        Le type d'événement reçu et un message de confirmation.
    """
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(
            status_code=400,
            detail="En-tête « Stripe-Signature » manquant.",
        )

    corps = await request.body()

    try:
        resultat = await traiter_webhook(corps, signature)
    except ValueError:
        raise HTTPException(status_code=400, detail="Corps de webhook invalide.")
    except Exception as e:
        logger.exception(f"Erreur webhook : {e}")
        raise HTTPException(
            status_code=400,
            detail="Signature de webhook invalide.",
        )

    type_evenement = resultat["type"]
    donnees = resultat["data"]

    # --- Traitement selon le type d'événement ---

    if type_evenement == "checkout.session.completed":
        # Paiement réussi : vérifier si c'est un achat de crédits ou un abonnement
        metadata = donnees.get("metadata", {})

        if metadata.get("type") == "credits":
            # --- Achat de crédits (paiement unique) ---
            try:
                email = metadata.get("email")
                nb_credits = int(metadata.get("credits", 0))
                session_id = donnees.get("id")
                montant = (donnees.get("amount_total") or 0) / 100.0

                utilisateur = obtenir_utilisateur_par_email(email) if email else None
                if utilisateur:
                    crediter_utilisateur(utilisateur["id"], nb_credits)
                    enregistrer_achat_credits(
                        utilisateur["id"], session_id, nb_credits, montant
                    )
                    logger.info(
                        f"Crédits ajoutés : email={email}, credits={nb_credits}, "
                        f"montant={montant}€, session={session_id}"
                    )
                else:
                    logger.warning(
                        f"Utilisateur introuvable pour créditation webhook : "
                        f"email={email}, credits={nb_credits}"
                    )
            except Exception as e:
                logger.exception(f"Erreur créditation webhook : {e}")
        else:
            # --- Abonnement (subscription) ---
            try:
                plan = metadata.get("plan", "inconnu")
                email = metadata.get("email_utilisateur", "")
                stripe_customer_id = donnees.get("customer")
                stripe_subscription_id = donnees.get("subscription")
                maintenant = datetime.now(timezone.utc).isoformat()

                # Créer l'abonnement en base avec le plan et l'email
                creer_abonnement(
                    stripe_customer_id=stripe_customer_id,
                    stripe_subscription_id=stripe_subscription_id,
                    statut="actif",
                    plan=plan,
                    email_utilisateur=email,
                    derniere_attribution=maintenant,
                )

                # Créditer l'utilisateur avec l'allocation mensuelle
                nb_credits = CREDITS_PAR_PLAN.get(plan, 0)
                if nb_credits > 0 and email:
                    utilisateur = obtenir_utilisateur_par_email(email)
                    if utilisateur:
                        crediter_utilisateur(utilisateur["id"], nb_credits)
                        logger.info(
                            f"Crédits d'abonnement ajoutés : email={email}, "
                            f"plan={plan}, credits={nb_credits}, "
                            f"subscription={stripe_subscription_id}"
                        )
                    else:
                        logger.warning(
                            f"Utilisateur introuvable pour crédits abonnement : email={email}"
                        )
                else:
                    logger.warning(f"Plan inconnu ou sans email : plan={plan}, email={email}")

                logger.info(
                    f"Abonnement créé : client={stripe_customer_id}, "
                    f"subscription={stripe_subscription_id}, plan={plan}"
                )
            except Exception as e:
                logger.exception(f"Erreur création abonnement en base : {e}")

    elif type_evenement == "invoice.paid":
        # --- Paiement de facture (renouvellement mensuel/annuel) ---
        try:
            stripe_subscription_id = donnees.get("subscription")
            if not stripe_subscription_id:
                logger.warning("invoice.paid sans subscription_id, ignoré")
            else:
                # Récupérer l'abonnement local
                abo = obtenir_abonnement(stripe_subscription_id=stripe_subscription_id)
                if not abo:
                    logger.warning(
                        f"Abonnement introuvable pour invoice.paid : {stripe_subscription_id}"
                    )
                else:
                    plan = abo.get("plan", "")
                    email = abo.get("email_utilisateur", "")
                    derniere_attr = abo.get("derniere_attribution_credits")
                    maintenant = datetime.now(timezone.utc).isoformat()

                    nb_credits = CREDITS_PAR_PLAN.get(plan, 0)
                    if nb_credits > 0 and email:
                        utilisateur = obtenir_utilisateur_par_email(email)
                        if utilisateur:
                            crediter_utilisateur(utilisateur["id"], nb_credits)
                            mettre_a_jour_attribution_credits(stripe_subscription_id, maintenant)
                            logger.info(
                                f"Crédits renouvelés (invoice.paid) : email={email}, "
                                f"plan={plan}, credits={nb_credits}, "
                                f"subscription={stripe_subscription_id}, "
                                f"dernière_attr={derniere_attr}"
                            )
                        else:
                            logger.warning(
                                f"Utilisateur introuvable pour renouvellement : email={email}"
                            )
                    else:
                        logger.info(
                            f"invoice.paid traité sans crédits : plan={plan}, "
                            f"subscription={stripe_subscription_id}"
                        )
        except Exception as e:
            logger.exception(f"Erreur traitement invoice.paid : {e}")

    elif type_evenement == "customer.subscription.deleted":
        # Abonnement résilié
        try:
            mettre_a_jour_abonnement(
                stripe_subscription_id=donnees.get("id"),
                statut="resilie",
            )
            logger.info(f"Abonnement résilié : {donnees.get('id')}")
        except Exception as e:
            logger.exception(f"Erreur mise à jour abonnement : {e}")

    elif type_evenement == "customer.subscription.updated":
        # Abonnement modifié
        try:
            mettre_a_jour_abonnement(
                stripe_subscription_id=donnees.get("id"),
                statut=donnees.get("status", "actif"),
            )
            logger.info(
                f"Abonnement mis à jour : {donnees.get('id')} → "
                f"statut={donnees.get('status')}"
            )
        except Exception as e:
            logger.exception(f"Erreur mise à jour abonnement : {e}")

    elif type_evenement == "invoice.payment_failed":
        # Échec de paiement
        logger.warning(
            f"Échec de paiement : client={donnees.get('customer')}"
        )
        try:
            mettre_a_jour_abonnement(
                stripe_customer_id=donnees.get("customer"),
                statut="impaye",
            )
        except Exception as e:
            logger.exception(f"Erreur mise à jour abonnement impayé : {e}")

    return WebhookReponse(
        type_evenement=type_evenement,
        message=f"Événement « {type_evenement} » traité avec succès.",
    )


@router.get("/stripe/subscription/{customer_id}", response_model=EtatAbonnement)
async def consulter_abonnement(customer_id: str):
    """
    Récupère l'état de l'abonnement d'un client Stripe.

    Args:
        customer_id: L'identifiant client Stripe (ex: « cus_xxxx »).

    Returns:
        Les informations détaillées de l'abonnement.
    """
    try:
        abonnement = await obtenir_abonnement_stripe(customer_id)
        return EtatAbonnement(**abonnement)

    except Exception as e:
        logger.exception(f"Erreur consultation abonnement : {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la consultation de l'abonnement.",
        )
