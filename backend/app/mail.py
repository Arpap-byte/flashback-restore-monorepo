"""
Utilitaire d'envoi d'emails via SMTP Gmail.

Utilise smtplib avec STARTTLS.
Nécessite les variables d'environnement SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM

logger = logging.getLogger(__name__)


def envoyer_email(destinataire: str, sujet: str, corps_html: str) -> bool:
    """
    Envoie un email HTML via SMTP.
    Retourne True si l'envoi a réussi, False sinon.
    """
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        logger.error("Configuration SMTP manquante. Email non envoyé.")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = destinataire
    msg["Subject"] = sujet
    msg.attach(MIMEText(corps_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(msg["From"], destinataire, msg.as_string())
        logger.info(f"Email envoyé à {destinataire} : {sujet}")
        return True
    except Exception as e:
        logger.error(f"Échec envoi email à {destinataire} : {e}")
        return False
