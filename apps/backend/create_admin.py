"""
Create or update an admin user.

Usage:
  python create_admin.py --email admin@prometheus.dev --username admin
  python create_admin.py --email admin@prometheus.dev --username admin --password "StrongPass123!"
  python create_admin.py --email admin@prometheus.dev --username admin --update-password
"""

import argparse
import asyncio
import os
import sys
from getpass import getpass

from sqlalchemy import select

from src.core.database import async_session_maker
from src.core.models import User
from src.core.security import get_password_hash


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or promote an admin user.")
    parser.add_argument(
        "--email",
        default=os.getenv("ADMIN_EMAIL", "admin@prometheus.dev"),
        help="Admin email (default: %(default)s)",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("ADMIN_USERNAME", "admin"),
        help="Admin username (default: %(default)s)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("ADMIN_PASSWORD"),
        help="Admin password. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--full-name",
        default=os.getenv("ADMIN_FULL_NAME"),
        help="Optional full name.",
    )
    parser.add_argument(
        "--update-password",
        action="store_true",
        help="Update password if user already exists.",
    )
    return parser


def prompt_password() -> str:
    password = getpass("Admin password: ").strip()
    confirm = getpass("Confirm password: ").strip()

    if password != confirm:
        raise ValueError("Passwords do not match.")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    return password


async def create_or_update_admin(
    email: str,
    username: str,
    password: str,
    full_name: str | None,
    update_password: bool,
) -> None:
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                username=username,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                is_active=True,
                is_verified=True,
                is_superuser=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created admin user: {user.email} (id={user.id})")
            return

        updated = False

        if user.username != username:
            user.username = username
            updated = True

        if full_name and user.full_name != full_name:
            user.full_name = full_name
            updated = True

        if not user.is_active:
            user.is_active = True
            updated = True

        if not user.is_verified:
            user.is_verified = True
            updated = True

        if not user.is_superuser:
            user.is_superuser = True
            updated = True

        if update_password:
            user.hashed_password = get_password_hash(password)
            updated = True

        if updated:
            await session.commit()
            print(f"Updated admin user: {user.email} (id={user.id})")
        else:
            print(f"Admin user already configured: {user.email} (id={user.id})")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    password = (args.password or "").strip()
    if not password:
        try:
            password = prompt_password()
        except ValueError as exc:
            print(f"Error: {exc}")
            return 1

    if len(password) < 8:
        print("Error: password must be at least 8 characters.")
        return 1

    try:
        asyncio.run(
            create_or_update_admin(
                email=args.email.strip().lower(),
                username=args.username.strip(),
                password=password,
                full_name=args.full_name.strip() if args.full_name else None,
                update_password=args.update_password,
            )
        )
        return 0
    except Exception as exc:  # pragma: no cover
        print(f"Failed to create/update admin: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
