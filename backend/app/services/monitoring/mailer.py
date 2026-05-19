"""
Envoi d'emails via SMTP Gmail — Flashback Restore.

Utilise les credentials configurés dans .env :
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
"""

import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

logger = logging.getLogger(__name__)

# Configuration SMTP (depuis l'environnement)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "cuisinetousjours@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "Flashback Restore <cuisinetousjours@gmail.com>")


async def send_report(
    to: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    retry: int = 3,
) -> bool:
    """
    Envoie un email multipart (HTML + texte) via SMTP Gmail.

    Args:
        to: Adresse destinataire
        subject: Sujet de l'email
        html_body: Corps HTML
        text_body: Corps texte (optionnel, fallback pour clients basiques)
        retry: Nombre de tentatives en cas d'échec

    Returns:
        True si l'email a été envoyé avec succès
    """
    if not SMTP_PASSWORD:
        logger.error("❌ SMTP_PASSWORD non configuré — email non envoyé")
        return False

    # Construction du message multipart
    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject

    # Partie texte (fallback)
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))

    # Partie HTML
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Envoi avec retry
    last_error = None
    for attempt in range(1, retry + 1):
        try:
            # smtplib est synchrone — on l'exécute dans un thread
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                _send_sync,
                msg,
            )
            logger.info("📧 Email envoyé à %s (sujet: %s)", to, subject)
            return True
        except Exception as e:
            last_error = e
            logger.warning(
                "⚠️ Tentative %s/%s d'envoi email échouée: %s",
                attempt, retry, e,
            )
            if attempt < retry:
                await asyncio.sleep(2 ** attempt)  # Backoff exponentiel

    logger.error("❌ Échec de l'envoi email après %s tentatives: %s", retry, last_error)
    return False


def _send_sync(msg: MIMEMultipart) -> None:
    """Envoi SMTP synchrone (exécuté dans un thread)."""
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
