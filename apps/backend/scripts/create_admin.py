#!/usr/bin/env python3
"""
Script per creare il primo admin e una licenza iniziale.
Eseguire dalla directory apps/backend:
    python scripts/create_admin.py

Oppure con variabili d'ambiente personalizzate:
    DATABASE_URL=postgresql://... python scripts/create_admin.py
"""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from getpass import getpass

# Aggiungi il percorso src al PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def create_admin_and_license():
    """Crea un utente admin e una licenza iniziale."""

    # Importa i modelli dopo aver configurato il path
    from src.core.database import Base
    from src.core.models import License, LicenseStatus, User
    from src.core.config import settings

    print("\n" + "=" * 60)
    print("🚀 SETUP INIZIALE - PROMETHEUS TRADING")
    print("=" * 60)

    # Connessione al database
    database_url = settings.DATABASE_URL
    print(f"\n📦 Database: {database_url.split('@')[-1] if '@' in database_url else database_url}")

    # Crea engine
    if database_url.startswith("sqlite"):
        engine = create_async_engine(database_url, echo=False)
    else:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )

    # Crea le tabelle se non esistono
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Crea sessione
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # ============================================
        # 1. CREAZIONE ADMIN
        # ============================================
        print("\n" + "-" * 40)
        print("👤 CREAZIONE UTENTE ADMIN")
        print("-" * 40)

        # Verifica se esiste già un admin
        result = await session.execute(
            select(User).where(User.is_superuser == True)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            print(f"\n⚠️  Esiste già un admin: {existing_admin.email}")
            create_new = input("Vuoi creare un altro admin? (s/N): ").strip().lower()
            if create_new != 's':
                admin = existing_admin
            else:
                admin = None
        else:
            admin = None

        if admin is None:
            # Raccolta dati admin
            print("\nInserisci i dati per l'utente admin:")

            while True:
                email = input("Email: ").strip()
                if "@" in email:
                    # Verifica che l'email non esista già
                    result = await session.execute(
                        select(User).where(User.email == email)
                    )
                    if result.scalar_one_or_none():
                        print("❌ Email già in uso. Scegli un'altra email.")
                        continue
                    break
                print("❌ Email non valida")

            while True:
                username = input("Username: ").strip()
                if len(username) >= 3:
                    # Verifica che lo username non esista già
                    result = await session.execute(
                        select(User).where(User.username == username)
                    )
                    if result.scalar_one_or_none():
                        print("❌ Username già in uso. Scegli un altro username.")
                        continue
                    break
                print("❌ Username troppo corto (min 3 caratteri)")

            full_name = input("Nome completo (opzionale): ").strip() or None

            while True:
                password = getpass("Password: ")
                if len(password) >= 8:
                    password_confirm = getpass("Conferma password: ")
                    if password == password_confirm:
                        break
                    print("❌ Le password non coincidono")
                else:
                    print("❌ Password troppo corta (min 8 caratteri)")

            # Crea admin
            admin = User(
                email=email,
                username=username,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                is_active=True,
                is_verified=True,  # Admin già verificato
                is_superuser=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)

            print(f"\n✅ Admin creato con successo!")
            print(f"   Email: {admin.email}")
            print(f"   Username: {admin.username}")

        # ============================================
        # 2. CREAZIONE LICENZA
        # ============================================
        print("\n" + "-" * 40)
        print("🔑 CREAZIONE LICENZA")
        print("-" * 40)

        create_license = input("\nVuoi creare una licenza per testare la registrazione? (S/n): ").strip().lower()

        if create_license != 'n':
            # Genera chiave licenza
            license_key = License.generate_key("ADMIN")

            # Chiedi durata
            duration_input = input("Durata in giorni (default: 365): ").strip()
            duration_days = int(duration_input) if duration_input.isdigit() else 365

            # Chiedi max utilizzi
            max_uses_input = input("Numero massimo di utilizzi (default: 10): ").strip()
            max_uses = int(max_uses_input) if max_uses_input.isdigit() else 10

            # Crea licenza
            license = License(
                key=license_key,
                name="Admin License",
                description="Licenza creata tramite setup iniziale",
                status=LicenseStatus.ACTIVE,
                is_active=True,
                max_uses=max_uses,
                current_uses=0,
                expires_at=datetime.now(UTC) + timedelta(days=duration_days),
                created_by=admin.id,
            )
            session.add(license)
            await session.commit()

            print(f"\n✅ Licenza creata con successo!")
            print(f"\n" + "=" * 60)
            print(f"🔑 CODICE LICENZA: {license_key}")
            print("=" * 60)
            print(f"\n   Nome: {license.name}")
            print(f"   Utilizzi: 0/{max_uses}")
            print(f"   Scadenza: {license.expires_at.strftime('%d/%m/%Y')}")
            print(f"\n   ⚠️  Salva questo codice! Serve per registrare nuovi utenti.")

        # ============================================
        # 3. RIEPILOGO
        # ============================================
        print("\n" + "=" * 60)
        print("📋 RIEPILOGO")
        print("=" * 60)
        print(f"\n✅ Admin: {admin.email} ({admin.username})")
        print(f"   - is_superuser: {admin.is_superuser}")
        print(f"   - is_verified: {admin.is_verified}")
        print(f"   - is_active: {admin.is_active}")

        # Conta licenze attive
        result = await session.execute(
            select(License).where(License.status == LicenseStatus.ACTIVE)
        )
        licenses = result.scalars().all()
        print(f"\n🔑 Licenze attive: {len(licenses)}")
        for lic in licenses:
            print(f"   - {lic.key} ({lic.current_uses}/{lic.max_uses} utilizzi)")

        print("\n" + "=" * 60)
        print("🎉 Setup completato!")
        print("=" * 60)
        print("\nOra puoi:")
        print("1. Accedere al pannello admin con le credenziali create")
        print("2. Creare nuove licenze dal pannello admin")
        print("3. Distribuire le licenze agli utenti per la registrazione")
        print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin_and_license())
