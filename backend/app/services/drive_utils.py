"""
Utilitaire Google Drive — upload de rapports JSON.

Utilise le token OAuth stocké dans ~/.hermes/google_token.json
pour uploader les rapports de maintenance dans un dossier dédié.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_PATH = Path.home() / ".hermes" / "google_token.json"
GOOGLE_CLIENT_SECRET_PATH = Path.home() / ".hermes" / "google_client_secret.json"
DRIVE_FOLDER_NAME = "Flashback Restore — Rapports"
DRIVE_MIME_FOLDER = "application/vnd.google-apps.folder"
DRIVE_MIME_JSON = "application/json"


def _get_drive_service():
    """Crée un service Drive API authentifié."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not GOOGLE_TOKEN_PATH.exists():
        return None

    token_data = json.loads(GOOGLE_TOKEN_PATH.read_text())
    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes") or token_data.get("scope", "").split(),
    )

    # Refresh si expiré
    if not creds.valid:
        try:
            import google.auth.transport.requests
            creds.refresh(google.auth.transport.requests.Request())
            # Sauvegarder le token rafraîchi
            new_token = json.loads(creds.to_json())
            GOOGLE_TOKEN_PATH.write_text(json.dumps(new_token, indent=2))
        except Exception as e:
            logger.error("Échec refresh token Google: %s", e)
            return None

    return build("drive", "v3", credentials=creds)


def _find_or_create_folder(service, folder_name: str) -> str:
    """Trouve un dossier Drive par nom, ou le crée.

    Returns:
        L'ID du dossier Drive.
    """
    # Chercher le dossier existant
    response = service.files().list(
        q=f"name = '{folder_name}' and mimeType = '{DRIVE_MIME_FOLDER}' and trashed = false",
        spaces="drive",
        fields="files(id, name)",
        pageSize=1,
    ).execute()

    files = response.get("files", [])
    if files:
        return files[0]["id"]

    # Créer le dossier
    folder_metadata = {
        "name": folder_name,
        "mimeType": DRIVE_MIME_FOLDER,
    }
    folder = service.files().create(body=folder_metadata, fields="id").execute()
    logger.info("Dossier Drive créé : %s (%s)", folder_name, folder.get("id"))
    return folder["id"]


def upload_json_to_drive(content: str, filename: str) -> str | None:
    """Upload un fichier JSON sur Google Drive.

    Args:
        content: Contenu JSON (string)
        filename: Nom du fichier sur Drive (ex: cleanup_flashback_20260517.json)

    Returns:
        File ID Drive, ou None si échec / non configuré
    """
    try:
        service = _get_drive_service()
        if service is None:
            logger.info("Google Drive non configuré — skip upload")
            return None

        folder_id = _find_or_create_folder(service, DRIVE_FOLDER_NAME)

        # Upload
        from io import BytesIO
        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(
            BytesIO(content.encode("utf-8")),
            mimetype=DRIVE_MIME_JSON,
            resumable=False,
        )

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink",
        ).execute()

        logger.info(
            "📤 Rapport uploadé sur Drive : %s → %s",
            filename, uploaded.get("webViewLink", uploaded.get("id")),
        )
        return uploaded.get("id")

    except Exception:
        logger.exception("Échec upload Drive pour %s", filename)
        return None
