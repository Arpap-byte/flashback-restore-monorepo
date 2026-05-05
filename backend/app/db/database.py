"""
Base de données SQLite pour le suivi des travaux (jobs) et des abonnements.

Utilise SQLite pour conserver l'historique des analyses, restaurations,
animations et abonnements Stripe dans un fichier local.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import DB_PATH


def _obtenir_connexion() -> sqlite3.Connection:
    """Retourne une connexion à la base SQLite."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialiser_base():
    """Crée les tables si elles n'existent pas encore."""
    conn = _obtenir_connexion()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS travaux (
                id              TEXT PRIMARY KEY,
                type            TEXT NOT NULL CHECK(type IN ('analyse', 'restauration', 'animation')),
                statut          TEXT NOT NULL DEFAULT 'cree'
                                CHECK(statut IN ('cree', 'en_cours', 'termine', 'erreur')),
                chemin_photo    TEXT,
                chemin_resultat TEXT,
                resultat_json   TEXT,
                job_externe_id  TEXT,
                message_erreur  TEXT,
                cree_le         TEXT NOT NULL,
                modifie_le      TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_travaux_statut ON travaux(statut);
            CREATE INDEX IF NOT EXISTS idx_travaux_type  ON travaux(type);

            CREATE TABLE IF NOT EXISTS abonnements (
                id                      TEXT PRIMARY KEY,
                stripe_customer_id      TEXT,
                stripe_subscription_id  TEXT,
                statut                  TEXT NOT NULL DEFAULT 'cree'
                                        CHECK(statut IN ('cree', 'actif', 'impaye', 'resilie', 'expire')),
                plan                    TEXT,
                email_utilisateur       TEXT,
                cree_le                 TEXT NOT NULL,
                modifie_le              TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_abonnements_stripe_customer
                ON abonnements(stripe_customer_id);
            CREATE INDEX IF NOT EXISTS idx_abonnements_stripe_subscription
                ON abonnements(stripe_subscription_id);
            CREATE INDEX IF NOT EXISTS idx_abonnements_statut
                ON abonnements(statut);
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Travaux (jobs)
# ---------------------------------------------------------------------------

def creer_travail(
    type_travail: str,
    chemin_photo: Optional[str] = None,
    job_externe_id: Optional[str] = None,
) -> str:
    """Crée une nouvelle entrée de travail et retourne son ID."""
    travail_id = str(uuid.uuid4())
    maintenant = datetime.now(timezone.utc).isoformat()
    conn = _obtenir_connexion()
    try:
        conn.execute(
            """INSERT INTO travaux (id, type, statut, chemin_photo, job_externe_id, cree_le, modifie_le)
               VALUES (?, ?, 'cree', ?, ?, ?, ?)""",
            (travail_id, type_travail, chemin_photo, job_externe_id, maintenant, maintenant),
        )
        conn.commit()
        return travail_id
    finally:
        conn.close()


def mettre_a_jour_travail(
    travail_id: str,
    statut: Optional[str] = None,
    chemin_resultat: Optional[str] = None,
    resultat_json: Optional[str] = None,
    message_erreur: Optional[str] = None,
) -> bool:
    """Met à jour le statut et les champs d'un travail existant."""
    maintenant = datetime.now(timezone.utc).isoformat()
    champs = ["modifie_le = ?"]
    valeurs = [maintenant]

    if statut is not None:
        champs.append("statut = ?")
        valeurs.append(statut)
    if chemin_resultat is not None:
        champs.append("chemin_resultat = ?")
        valeurs.append(chemin_resultat)
    if resultat_json is not None:
        champs.append("resultat_json = ?")
        valeurs.append(resultat_json)
    if message_erreur is not None:
        champs.append("message_erreur = ?")
        valeurs.append(message_erreur)

    valeurs.append(travail_id)
    conn = _obtenir_connexion()
    try:
        cur = conn.execute(
            f"UPDATE travaux SET {', '.join(champs)} WHERE id = ?",
            valeurs,
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def obtenir_travail(travail_id: str) -> Optional[dict]:
    """Récupère un travail par son ID."""
    conn = _obtenir_connexion()
    try:
        row = conn.execute(
            "SELECT * FROM travaux WHERE id = ?", (travail_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def obtenir_travail_par_job_externe(job_externe_id: str) -> Optional[dict]:
    """Récupère un travail par son ID externe (ex: job D-ID)."""
    conn = _obtenir_connexion()
    try:
        row = conn.execute(
            "SELECT * FROM travaux WHERE job_externe_id = ?", (job_externe_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Abonnements (Stripe)
# ---------------------------------------------------------------------------

def creer_abonnement(
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    statut: str = "actif",
    plan: Optional[str] = None,
    email_utilisateur: Optional[str] = None,
) -> str:
    """
    Crée un nouvel abonnement dans la base locale.

    Args:
        stripe_customer_id: Identifiant client Stripe.
        stripe_subscription_id: Identifiant d'abonnement Stripe.
        statut: Statut initial (par défaut « actif »).
        plan: Nom du plan souscrit.
        email_utilisateur: Email de l'utilisateur.

    Returns:
        L'identifiant unique de l'abonnement créé.
    """
    abonnement_id = str(uuid.uuid4())
    maintenant = datetime.now(timezone.utc).isoformat()
    conn = _obtenir_connexion()
    try:
        conn.execute(
            """INSERT INTO abonnements
               (id, stripe_customer_id, stripe_subscription_id, statut, plan,
                email_utilisateur, cree_le, modifie_le)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                abonnement_id,
                stripe_customer_id,
                stripe_subscription_id,
                statut,
                plan,
                email_utilisateur,
                maintenant,
                maintenant,
            ),
        )
        conn.commit()
        return abonnement_id
    finally:
        conn.close()


def obtenir_abonnement(
    abonnement_id: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Récupère un abonnement par son ID local, son ID client Stripe
    ou son ID d'abonnement Stripe.

    Args:
        abonnement_id: Identifiant local de l'abonnement.
        stripe_customer_id: Identifiant client Stripe.
        stripe_subscription_id: Identifiant d'abonnement Stripe.

    Returns:
        Un dictionnaire représentant l'abonnement, ou None.
    """
    conn = _obtenir_connexion()
    try:
        if abonnement_id:
            row = conn.execute(
                "SELECT * FROM abonnements WHERE id = ?", (abonnement_id,)
            ).fetchone()
        elif stripe_subscription_id:
            row = conn.execute(
                "SELECT * FROM abonnements WHERE stripe_subscription_id = ?",
                (stripe_subscription_id,),
            ).fetchone()
        elif stripe_customer_id:
            row = conn.execute(
                "SELECT * FROM abonnements WHERE stripe_customer_id = ? "
                "ORDER BY cree_le DESC LIMIT 1",
                (stripe_customer_id,),
            ).fetchone()
        else:
            return None
        return dict(row) if row else None
    finally:
        conn.close()


def mettre_a_jour_abonnement(
    abonnement_id: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    statut: Optional[str] = None,
    plan: Optional[str] = None,
    email_utilisateur: Optional[str] = None,
) -> bool:
    """
    Met à jour les informations d'un abonnement existant.

    L'abonnement peut être identifié par son ID local, son ID client Stripe
    ou son ID d'abonnement Stripe.

    Args:
        abonnement_id: Identifiant local de l'abonnement.
        stripe_customer_id: Identifiant client Stripe.
        stripe_subscription_id: Identifiant d'abonnement Stripe.
        statut: Nouveau statut.
        plan: Nouveau plan.
        email_utilisateur: Email de l'utilisateur.

    Returns:
        True si une ligne a été mise à jour, False sinon.
    """
    maintenant = datetime.now(timezone.utc).isoformat()
    champs = ["modifie_le = ?"]
    valeurs = [maintenant]

    if statut is not None:
        champs.append("statut = ?")
        valeurs.append(statut)
    if plan is not None:
        champs.append("plan = ?")
        valeurs.append(plan)
    if email_utilisateur is not None:
        champs.append("email_utilisateur = ?")
        valeurs.append(email_utilisateur)

    # Déterminer la clause WHERE selon l'identifiant fourni
    if abonnement_id:
        clause = "id = ?"
        valeurs.append(abonnement_id)
    elif stripe_subscription_id:
        clause = "stripe_subscription_id = ?"
        valeurs.append(stripe_subscription_id)
    elif stripe_customer_id:
        clause = "stripe_customer_id = ?"
        valeurs.append(stripe_customer_id)
    else:
        return False

    conn = _obtenir_connexion()
    try:
        cur = conn.execute(
            f"UPDATE abonnements SET {', '.join(champs)} WHERE {clause}",
            valeurs,
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
