"""
Session SQLAlchemy asynchrone pour Flashback Restore.

Utilise asyncpg comme driver pour PostgreSQL.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import DATABASE_URL

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
    """Crée les tables si elles n'existent pas (équivalent de initialiser_base)."""
    from app.models.db_models import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Ferme proprement le moteur de base de données."""
    await _engine.dispose()
