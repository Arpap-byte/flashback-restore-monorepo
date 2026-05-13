"""
Stockage S3-compatible — Backblaze B2 via boto3.

Remplace le stockage local des photos uploadées. Les fichiers sont servis
via le bucket B2, avec option CDN Cloudflare.
"""
import logging
import os
from typing import Optional
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

B2_ENDPOINT = os.getenv("B2_ENDPOINT", "")
B2_KEY_ID = os.getenv("B2_KEY_ID", "")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY", "")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "flashback-restore")
B2_REGION = os.getenv("B2_REGION", "us-west-004")

_s3_client: Optional[boto3.client] = None


def _get_client() -> boto3.client:
    """Client S3 lazy-initialisé avec timeout et retries."""
    global _s3_client
    if _s3_client is None:
        if not B2_ENDPOINT or not B2_KEY_ID or not B2_APPLICATION_KEY:
            raise RuntimeError("Configuration B2 manquante (B2_ENDPOINT, B2_KEY_ID, B2_APPLICATION_KEY)")
        
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{B2_ENDPOINT}",
            aws_access_key_id=B2_KEY_ID,
            aws_secret_access_key=B2_APPLICATION_KEY,
            config=Config(
                region_name=B2_REGION,
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=10,
                read_timeout=30,
            ),
        )
        logger.info("Client S3/B2 initialisé — endpoint=%s bucket=%s", B2_ENDPOINT, B2_BUCKET_NAME)
    return _s3_client


# ── Opérations upload ──────────────────────────────────────────────────────

def uploader_fichier(chemin_local: str, cle_distant: str, content_type: str = "image/jpeg") -> str:
    """
    Upload un fichier vers B2 et retourne l'URL publique.

    Args:
        chemin_local: Chemin absolu du fichier sur le VPS
        cle_distant: Clé (chemin) dans le bucket, ex. 'photos/abc123.jpg'
        content_type: MIME type (image/jpeg, image/png, video/mp4, etc.)

    Returns:
        URL publique du fichier (B2 ou CDN si configuré)
    """
    client = _get_client()
    
    try:
        client.upload_file(
            Filename=chemin_local,
            Bucket=B2_BUCKET_NAME,
            Key=cle_distant,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "public, max-age=31536000, immutable",
            },
        )
        logger.info("Fichier uploadé: %s → %s (%s)", chemin_local, cle_distant, content_type)
    except ClientError as e:
        logger.error("Échec upload B2: %s", e)
        raise

    return _url_publique(cle_distant)


def uploader_bytes(contenu: bytes, cle_distant: str, content_type: str = "image/jpeg") -> str:
    """
    Upload des bytes directement vers B2.

    Utile quand on a le contenu en mémoire (ex: après traitement Pillow).
    """
    client = _get_client()
    
    try:
        client.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=cle_distant,
            Body=contenu,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        logger.info("Bytes uploadés: %s (%d octets)", cle_distant, len(contenu))
    except ClientError as e:
        logger.error("Échec upload bytes B2: %s", e)
        raise

    return _url_publique(cle_distant)


# ── Opérations download ────────────────────────────────────────────────────

def telecharger_fichier(cle_distant: str, chemin_local: str) -> str:
    """
    Télécharge un fichier depuis B2 vers le disque local.

    Returns:
        Chemin local du fichier téléchargé.
    """
    client = _get_client()
    
    try:
        client.download_file(Bucket=B2_BUCKET_NAME, Key=cle_distant, Filename=chemin_local)
        logger.info("Fichier téléchargé: %s → %s", cle_distant, chemin_local)
    except ClientError as e:
        logger.error("Échec download B2: %s", e)
        raise

    return chemin_local


def telecharger_bytes(cle_distant: str) -> bytes:
    """Télécharge un fichier depuis B2 et retourne son contenu en bytes."""
    client = _get_client()
    
    try:
        response = client.get_object(Bucket=B2_BUCKET_NAME, Key=cle_distant)
        contenu = response["Body"].read()
        return contenu
    except ClientError as e:
        logger.error("Échec download bytes B2: %s", e)
        raise


# ── Opérations suppression ─────────────────────────────────────────────────

def supprimer_fichier(cle_distant: str) -> bool:
    """Supprime un fichier du bucket B2."""
    client = _get_client()
    
    try:
        client.delete_object(Bucket=B2_BUCKET_NAME, Key=cle_distant)
        logger.info("Fichier supprimé: %s", cle_distant)
        return True
    except ClientError as e:
        logger.error("Échec suppression B2: %s", e)
        return False


# ── Utilitaires ─────────────────────────────────────────────────────────────

def _url_publique(cle_distant: str) -> str:
    """
    Construit l'URL publique du fichier.

    Utilise le CDN si configuré, sinon l'endpoint B2 direct.
    """
    cdn = os.getenv("B2_CDN_URL", "")
    if cdn:
        return f"{cdn.rstrip('/')}/{cle_distant}"
    # URL B2 directe via S3 endpoint
    endpoint = B2_ENDPOINT or "s3.us-west-004.backblazeb2.com"
    return f"https://{endpoint}/{B2_BUCKET_NAME}/{cle_distant}"


def b2_est_disponible() -> bool:
    """Vérifie que B2 est configuré et accessible."""
    if not B2_ENDPOINT or not B2_KEY_ID or not B2_APPLICATION_KEY:
        return False
    try:
        client = _get_client()
        client.head_bucket(Bucket=B2_BUCKET_NAME)
        return True
    except Exception:
        return False


def generer_cle_distant(prefixe: str, nom_fichier: str) -> str:
    """
    Génère une clé unique dans le bucket.

    Format: {prefixe}/{YYYY/MM}/{uuid}_{nom_fichier}
    """
    import uuid
    from datetime import datetime

    maintenant = datetime.utcnow()
    dossier = f"{maintenant.year}/{maintenant.month:02d}"
    return f"{prefixe}/{dossier}/{uuid.uuid4().hex[:12]}_{nom_fichier}"
