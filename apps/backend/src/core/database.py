"""
Database configuration and session management.
Uses SQLAlchemy 2.0 async with PostgreSQL or SQLite.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings


# Convert standard postgres/sqlite URL to async
def get_async_database_url() -> str:
    """Convert database URL to async driver format."""
    url = settings.DATABASE_URL

    # SQLite
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")

    # PostgreSQL
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")

    return url


DATABASE_URL = get_async_database_url()

# Engine kwargs differ by database type
engine_kwargs = {"echo": settings.DEBUG}
if DATABASE_URL.startswith("sqlite"):
    # SQLite doesn't support pool_size/max_overflow
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL supports connection pooling
    engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def init_db() -> None:
    """Initialize database tables."""
    # Import models to register them with Base.metadata
    from src.core import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
