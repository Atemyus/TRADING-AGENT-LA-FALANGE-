"""
Database configuration and session management.
Uses SQLAlchemy 2.0 async with PostgreSQL or SQLite.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
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


async def bootstrap_admin_and_license() -> None:
    """
    Bootstrap admin and optional license from environment variables.

    This is idempotent and safe to run on every startup.
    """
    from src.core.models import License, LicenseStatus, User
    from src.core.security import get_password_hash

    admin_email = (settings.ADMIN_EMAIL or "").strip().lower()
    admin_password = settings.ADMIN_PASSWORD or ""
    admin_username = (settings.ADMIN_USERNAME or "admin").strip() or "admin"
    admin_full_name = settings.ADMIN_FULL_NAME

    # Optional bootstrap license
    license_key = (settings.BOOTSTRAP_LICENSE_KEY or "").strip().upper()
    bootstrap_license_slots = max(1, int(getattr(settings, "BOOTSTRAP_LICENSE_BROKER_SLOTS", 5) or 5))

    async with async_session_maker() as session:
        if license_key:
            result = await session.execute(select(License).where(License.key == license_key))
            existing_license = result.scalar_one_or_none()
            if not existing_license:
                new_license = License(
                    key=license_key,
                    name=settings.BOOTSTRAP_LICENSE_NAME,
                    description="Auto-created at startup from environment",
                    status=LicenseStatus.ACTIVE,
                    is_active=True,
                    max_uses=max(1, int(settings.BOOTSTRAP_LICENSE_MAX_USES)),
                    current_uses=0,
                    broker_slots=bootstrap_license_slots,
                    expires_at=datetime.now(UTC) + timedelta(days=max(1, int(settings.BOOTSTRAP_LICENSE_DURATION_DAYS))),
                )
                session.add(new_license)
                print(f"✅ Bootstrap license created: {license_key}")

        if not admin_email or not admin_password:
            await session.commit()
            print("ℹ️ Admin bootstrap skipped (set ADMIN_EMAIL and ADMIN_PASSWORD)")
            return

        # bcrypt has a hard 72-byte input limit.
        password_bytes_len = len(admin_password.encode("utf-8"))
        if password_bytes_len > 72:
            await session.commit()
            print(
                "⚠️ Admin bootstrap skipped: ADMIN_PASSWORD is longer than "
                "72 bytes (bcrypt limit)."
            )
            return

        result = await session.execute(select(User).where(User.email == admin_email))
        admin_user = result.scalar_one_or_none()

        if admin_user is None:
            # Ensure username uniqueness for fresh creation.
            username_candidate = admin_username
            username_exists = await session.execute(
                select(User).where(User.username == username_candidate)
            )
            if username_exists.scalar_one_or_none():
                username_candidate = admin_email.split("@")[0][:100] or "admin"

            try:
                hashed_password = get_password_hash(admin_password)
            except Exception as exc:
                await session.rollback()
                print(f"⚠️ Admin bootstrap skipped: cannot hash ADMIN_PASSWORD ({exc})")
                return

            admin_user = User(
                email=admin_email,
                username=username_candidate,
                hashed_password=hashed_password,
                full_name=admin_full_name,
                is_active=True,
                is_verified=True,
                is_superuser=True,
            )
            session.add(admin_user)
            await session.commit()
            print(f"✅ Admin bootstrap created: {admin_email}")
            return

        # Keep existing user, enforce admin privileges, and refresh password from env
        admin_user.is_active = True
        admin_user.is_verified = True
        admin_user.is_superuser = True
        try:
            admin_user.hashed_password = get_password_hash(admin_password)
        except Exception as exc:
            await session.rollback()
            print(f"⚠️ Admin bootstrap skipped: cannot hash ADMIN_PASSWORD ({exc})")
            return
        if admin_full_name is not None:
            admin_user.full_name = admin_full_name

        # Only change username if it's free or already current.
        if admin_user.username != admin_username:
            username_exists = await session.execute(
                select(User).where(User.username == admin_username)
            )
            existing_username_user = username_exists.scalar_one_or_none()
            if existing_username_user is None or existing_username_user.id == admin_user.id:
                admin_user.username = admin_username

        await session.commit()
        print(f"✅ Admin bootstrap updated: {admin_email}")


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
            broker_slots INTEGER NOT NULL DEFAULT 5,
            expires_at TIMESTAMPTZ,
            created_by INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        "ALTER TABLE licenses ADD COLUMN IF NOT EXISTS broker_slots INTEGER NOT NULL DEFAULT 5",
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
        # Multi-broker ownership and slot support
        "ALTER TABLE broker_accounts ADD COLUMN IF NOT EXISTS user_id INTEGER",
        "ALTER TABLE broker_accounts ADD COLUMN IF NOT EXISTS slot_index INTEGER",
        "ALTER TABLE broker_accounts ADD COLUMN IF NOT EXISTS broker_catalog_id VARCHAR(100)",
        "ALTER TABLE broker_accounts ADD COLUMN IF NOT EXISTS platform_id VARCHAR(50)",
        "ALTER TABLE broker_accounts ADD COLUMN IF NOT EXISTS credentials_json TEXT",
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'broker_accounts_user_id_fkey'
            ) THEN
                ALTER TABLE broker_accounts
                ADD CONSTRAINT broker_accounts_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES users(id);
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_broker_accounts_user_slot'
            ) THEN
                ALTER TABLE broker_accounts
                ADD CONSTRAINT uq_broker_accounts_user_slot
                UNIQUE (user_id, slot_index);
            END IF;
        END $$;
        """,
        "CREATE INDEX IF NOT EXISTS ix_broker_accounts_user_id ON broker_accounts (user_id)",
        # Whop product -> license slot mapping support
        "ALTER TABLE whop_products ADD COLUMN IF NOT EXISTS license_broker_slots INTEGER NOT NULL DEFAULT 5",
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
    await bootstrap_admin_and_license()


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
