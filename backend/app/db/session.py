"""
Session SQLAlchemy asynchrone pour Flashback Restore.

Utilise aiosqlite comme driver pour SQLite (WAL mode).
"""
import logging
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

# Engine partagé (créé une seule fois)
_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

# Factory de sessions async
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """Retourne une nouvelle session async (générateur pour dépendance FastAPI)."""
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Crée les tables si elles n'existent pas et vérifie l'état du WAL."""
    from app.models.db_models import Base

    # Vérification WAL au démarrage (récupération post-crash)
    db_path = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "flashback.db"))
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        # Vérifier que le mode WAL est actif
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        if journal_mode.lower() != "wal":
            logger.warning(f"journal_mode={journal_mode}, passage en WAL...")
            conn.execute("PRAGMA journal_mode=WAL")

        # Vérifier l'état du WAL (taille, frames non checkpointées)
        wal_info = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
        # wal_checkpoint retourne (busy, log, checkpointed) ou (0, N, N)
        if wal_info:
            logger.info(f"WAL checkpoint démarrage : {wal_info}")

        # Vérifier l'intégrité
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            logger.error(f"INTÉGRITÉ DB ÉCHEC : {integrity}")
        else:
            logger.info("DB integrity_check OK au démarrage")

        conn.close()
    except Exception as e:
        logger.warning(f"Vérification WAL démarrage échouée (non-bloquant) : {e}")

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Ferme proprement le moteur de base de données.

    Force un WAL checkpoint (TRUNCATE) avant de fermer les connexions
    pour garantir qu'aucune donnée n'est perdue en cas de crash ultérieur.
    """
    # Forcer le WAL checkpoint AVANT de fermer les connexions
    db_path = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "flashback.db"))
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        logger.info("WAL checkpoint forcé (TRUNCATE) avant fermeture DB.")
    except Exception as e:
        logger.warning(f"WAL checkpoint échoué (non-bloquant) : {e}")

    await _engine.dispose()
