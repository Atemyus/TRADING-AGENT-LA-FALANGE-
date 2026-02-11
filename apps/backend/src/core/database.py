"""
Database configuration and session management.
Uses SQLAlchemy 2.0 async with PostgreSQL or SQLite.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
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


async def run_compat_migrations() -> None:
    """
    Apply lightweight idempotent schema fixes for existing PostgreSQL databases.

    This handles legacy deployments where new columns were added to SQLAlchemy models
    after initial table creation.
    """
    if not DATABASE_URL.startswith("postgresql"):
        return

    statements = [
        """
        CREATE TABLE IF NOT EXISTS licenses (
            id SERIAL PRIMARY KEY,
            key VARCHAR(64) UNIQUE NOT NULL,
            name VARCHAR(255),
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            max_uses INTEGER NOT NULL DEFAULT 1,
            current_uses INTEGER NOT NULL DEFAULT 0,
            expires_at TIMESTAMPTZ,
            created_by INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        # Bring legacy users table in sync with current User model
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS license_id INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS license_activated_at TIMESTAMPTZ",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token_expires TIMESTAMPTZ",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMPTZ",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ",
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'users_license_id_fkey'
            ) THEN
                ALTER TABLE users
                ADD CONSTRAINT users_license_id_fkey
                FOREIGN KEY (license_id) REFERENCES licenses(id);
            END IF;
        END $$;
        """,
        "CREATE INDEX IF NOT EXISTS ix_users_license_id ON users (license_id)",
    ]

    async with engine.begin() as conn:
        try:
            for statement in statements:
                await conn.execute(text(statement))
            print("✅ Compatibility migrations applied")
        except SQLAlchemyError as exc:
            print(f"⚠️ Compatibility migrations failed: {exc}")
            raise


async def init_db() -> None:
    """Initialize database tables."""
    # Import models to register them with Base.metadata
    from src.core import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await run_compat_migrations()


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
