"""
Routes de contact et fallback — Flashback Restore.

Endpoint pour le formulaire de contact quand Stripe est indisponible (P2.4).
Envoie un email à l'équipe commerciale (apexcyber.eu@gmail.com).
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SITE_URL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contact", tags=["Contact"])


class SalesContactRequest(BaseModel):
    """Formulaire de contact commercial (fallback Stripe)."""
    name: str
    email: EmailStr
    plan: str = "inconnu"


@router.post("/sales")
async def sales_contact(body: SalesContactRequest):
    """
    Fallback formulaire de contact quand Stripe est HS (P2.4).

    Envoie un email à apexcyber.eu@gmail.com avec les infos du prospect
    pour un recontact manuel.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Flashback Restore] Demande d'abonnement — {body.plan}"
        msg["From"] = SMTP_FROM
        msg["To"] = "apexcyber.eu@gmail.com"
        msg["Reply-To"] = body.email

        html_body = f"""\
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px;">
  <h2 style="color: #f59e0b;">📬 Nouvelle demande d'abonnement</h2>
  <p><strong>Nom :</strong> {body.name}</p>
  <p><strong>Email :</strong> {body.email}</p>
  <p><strong>Plan souhaité :</strong> {body.plan}</p>
  <p><strong>Source :</strong> Formulaire de contact (fallback Stripe indisponible)</p>
  <p><strong>Site :</strong> <a href="{SITE_URL}">{SITE_URL}</a></p>
  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;" />
  <p style="color: #6b7280; font-size: 12px;">
    Cet email a été envoyé automatiquement depuis le formulaire de contact
    de Flashback Restore car le service de paiement Stripe était temporairement
    indisponible au moment de la demande.
  </p>
</body>
</html>"""

        text_body = f"""\
Nouvelle demande d'abonnement — Flashback Restore

Nom : {body.name}
Email : {body.email}
Plan souhaité : {body.plan}
Source : Formulaire de contact (fallback Stripe indisponible)
Site : {SITE_URL}

Cet email a été envoyé automatiquement depuis le formulaire de contact
de Flashback Restore car le service de paiement Stripe était temporairement
indisponible au moment de la demande.
"""

        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(
            "Email contact commercial envoyé : name=%s, email=%s, plan=%s",
            body.name, body.email, body.plan,
        )
        return {"ok": True, "message": "Demande envoyée. Nous vous recontacterons rapidement."}

    except smtplib.SMTPException as e:
        logger.error("Erreur SMTP envoi contact commercial : %s", e)
        raise HTTPException(status_code=500, detail="Erreur lors de l'envoi de l'email. Veuillez réessayer.")
    except Exception as e:
        logger.exception("Erreur inattendue contact commercial")
        raise HTTPException(status_code=500, detail="Une erreur est survenue. Veuillez réessayer.")
