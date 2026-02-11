#!/usr/bin/env python3
"""Script non-interattivo per creare admin."""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def create_admin():
    from src.core.database import Base
    from src.core.models import License, LicenseStatus, User
    from src.core.config import settings

    # Credenziali admin
    EMAIL = "admin@Prometheus.dev"
    USERNAME = "Danny01"
    PASSWORD = "Lupo#Ferro#Cancellino"

    print("\n" + "=" * 60)
    print("SETUP ADMIN - PROMETHEUS TRADING")
    print("=" * 60)

    database_url = settings.DATABASE_URL
    print(f"\nDatabase: {database_url}")

    if database_url.startswith("sqlite"):
        engine = create_async_engine(database_url, echo=False)
    else:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Verifica se esiste già
        result = await session.execute(
            select(User).where(User.email == EMAIL)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"\nAdmin già esistente: {EMAIL}")
            print("Aggiorno la password...")
            existing.hashed_password = get_password_hash(PASSWORD)
            existing.is_superuser = True
            existing.is_active = True
            existing.is_verified = True
            await session.commit()
            admin = existing
        else:
            admin = User(
                email=EMAIL,
                username=USERNAME,
                hashed_password=get_password_hash(PASSWORD),
                full_name="Admin",
                is_active=True,
                is_verified=True,
                is_superuser=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)

        print(f"\nAdmin creato/aggiornato!")
        print(f"  Email: {EMAIL}")
        print(f"  Username: {USERNAME}")
        print(f"  Password: {PASSWORD}")
        print(f"  is_superuser: True")

        # Crea licenza
        result = await session.execute(
            select(License).where(License.status == LicenseStatus.ACTIVE)
        )
        existing_license = result.scalars().first()

        if not existing_license:
            license_key = License.generate_key("ADMIN")
            license = License(
                key=license_key,
                name="Admin License",
                description="Licenza admin",
                status=LicenseStatus.ACTIVE,
                is_active=True,
                max_uses=100,
                current_uses=0,
                expires_at=datetime.now(UTC) + timedelta(days=365),
                created_by=admin.id,
            )
            session.add(license)
            await session.commit()
            print(f"\nLicenza creata: {license_key}")
        else:
            print(f"\nLicenza esistente: {existing_license.key}")

        print("\n" + "=" * 60)
        print("Setup completato!")
        print("=" * 60 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())
