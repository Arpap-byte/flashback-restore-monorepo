"""
Base de données SQLite pour le suivi des travaux (jobs).

Utilise SQLite pour conserver l'historique des analyses, restaurations
et animations dans un fichier local.
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
        """)
        conn.commit()
    finally:
        conn.close()


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
