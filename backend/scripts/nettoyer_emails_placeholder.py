#!/usr/bin/env python3
"""
Script de nettoyage des comptes utilisateurs avec emails placeholder Clerk.

Parcourt tous les utilisateurs dont l'email se termine par @placeholder.local,
appelle l'API Clerk pour récupérer le vrai email, et met à jour la base de données.

Usage:
    cd /opt/flashback-restore-monorepo
    python backend/scripts/nettoyer_emails_placeholder.py [--dry-run]
"""

import asyncio
import os
import sys
from pathlib import Path

# Ajouter le backend au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le .env racine
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_API_URL = "https://api.clerk.com/v1"

if not CLERK_SECRET_KEY:
    print("ERREUR: CLERK_SECRET_KEY non configurée. Vérifiez le fichier .env")
    sys.exit(1)


async def resoudre_email_clerck_api(user_id: str) -> str | None:
    """Appelle l'API Clerk pour récupérer l'email d'un utilisateur."""
    headers = {
        "Authorization": f"Bearer {CLERK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{CLERK_API_URL}/users/{user_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"  [API] HTTP {resp.status_code} pour {user_id}")
                return None

            data = resp.json()
            email_addresses = data.get("email_addresses", [])
            for addr in email_addresses:
                email_obj = addr.get("email_address", "")
                if email_obj and not email_obj.endswith("@placeholder.local"):
                    return email_obj

            # Fallback
            if email_addresses:
                return email_addresses[0].get("email_address", None)
            return None
    except httpx.HTTPError as e:
        print(f"  [API] Erreur réseau pour {user_id}: {e}")
        return None
    except Exception as e:
        print(f"  [API] Erreur inattendue pour {user_id}: {e}")
        return None


async def nettoyer_emails_placeholder(dry_run: bool = False):
    """Nettoie tous les comptes avec email placeholder."""
    # Créer un engine dédié pour le script
    from app.config import DATABASE_URL
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Trouver tous les utilisateurs avec email placeholder
        result = await conn.execute(
            text("SELECT id, email, oauth_provider_id FROM utilisateurs WHERE email LIKE '%@placeholder.local'")
        )
        lignes = result.fetchall()

        if not lignes:
            print("✅ Aucun compte avec email placeholder trouvé.")
            return

        print(f"📋 {len(lignes)} compte(s) avec email placeholder trouvé(s):")
        for ligne in lignes:
            print(f"  - {ligne.email} (DB id={ligne.id}, Clerk id={ligne.oauth_provider_id})")

        print()

        for ligne in lignes:
            db_id = ligne.id
            old_email = ligne.email
            clerk_id = ligne.oauth_provider_id

            if not clerk_id:
                print(f"⚠️  Aucun oauth_provider_id pour {db_id} — ignoré")
                continue

            print(f"🔍 Résolution email pour Clerk user_id={clerk_id}...")
            email_reel = await resoudre_email_clerck_api(clerk_id)

            if email_reel and email_reel != old_email:
                if dry_run:
                    print(f"  [DRY-RUN] Remplacerait {old_email} → {email_reel}")
                else:
                    # Vérifier que le nouvel email n'est pas déjà pris
                    check = await conn.execute(
                        text("SELECT id FROM utilisateurs WHERE LOWER(email) = :email AND id != :uid"),
                        {"email": email_reel.lower(), "uid": db_id},
                    )
                    if check.fetchone():
                        print(f"  ⚠️  Email {email_reel} déjà utilisé par un autre compte — ignoré")
                        continue

                    await conn.execute(
                        text("UPDATE utilisateurs SET email = :nouveau WHERE id = :uid"),
                        {"nouveau": email_reel.lower(), "uid": db_id},
                    )
                    await conn.commit()
                    print(f"  ✅ Email mis à jour: {old_email} → {email_reel}")
            elif email_reel == old_email:
                print(f"  ℹ️  L'email est déjà {old_email} (pas de changement)")
            else:
                print(f"  ❌ Impossible de résoudre l'email pour {clerk_id}")


async def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("🔍 MODE DRY-RUN: aucune modification ne sera appliquée.\n")
    await nettoyer_emails_placeholder(dry_run=dry_run)
    print("\n✨ Nettoyage terminé.")


if __name__ == "__main__":
    asyncio.run(main())
