"""
Create a NOCTRA superuser.

Usage:
    python -m scripts.create_superuser

Prompts interactively for the username, email, full name, and password.
Aborts if the username or email is already taken.
"""

from __future__ import annotations

import asyncio
import getpass
import re
import sys

from sqlalchemy import select

from app.core.constants import RoleName
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole

# Register every model module before SQLAlchemy configures mappers.
import app.core.models_registry  # noqa: F401

USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,50}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def prompt(prompt_text: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt_text}{suffix}: ").strip()
    return value or (default or "")


def validate_username(value: str) -> bool:
    return bool(USERNAME_RE.match(value))


def validate_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value))


async def main() -> int:
    print("Create NOCTRA superuser\n")

    # ── Collect input ────────────────────────────────────
    username = prompt("Username (lowercase, 3-50 chars)").lower()
    if not validate_username(username):
        print("  ! invalid username (a-z, 0-9, _, . — 3-50 chars)", file=sys.stderr)
        return 1

    email = prompt("Email").lower()
    if not validate_email(email):
        print("  ! invalid email", file=sys.stderr)
        return 1

    full_name = prompt("Full name")
    if len(full_name) < 2:
        print("  ! full name too short", file=sys.stderr)
        return 1

    password = getpass.getpass("Password (min 8 chars): ")
    if len(password) < 8:
        print("  ! password must be at least 8 characters", file=sys.stderr)
        return 1

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("  ! passwords do not match", file=sys.stderr)
        return 1

    # ── Persist ──────────────────────────────────────────
    async with SessionLocal() as db:
        try:
            username_taken = (
                await db.execute(select(User.id).where(User.username == username))
            ).scalar_one_or_none()
            email_taken = (
                await db.execute(select(User.id).where(User.email == email))
            ).scalar_one_or_none()

            taken = [
                label
                for label, hit in (("username", username_taken), ("email", email_taken))
                if hit is not None
            ]
            if taken:
                print(
                    f"  ! {' and '.join(taken)} already taken",
                    file=sys.stderr,
                )
                return 1

            user = User(
                username=username,
                email=email,
                full_name=full_name,
                hashed_password=hash_password(password),
                is_active=True,
                is_superuser=True,
            )
            db.add(user)
            await db.flush()

            # Attach superuser role if it exists
            super_role = (
                await db.execute(
                    select(Role).where(Role.name == RoleName.SUPERUSER.value)
                )
            ).scalar_one_or_none()

            if super_role is None:
                print(
                    "  ! superuser role not found — run `python -m scripts.seed` first",
                    file=sys.stderr,
                )
                await db.rollback()
                return 1

            db.add(UserRole(user_id=user.id, role_id=super_role.id))

            await db.commit()
            print(f"\n✅ Created superuser: {user.username} <{user.email}>")
            return 0

        except Exception as exc:
            await db.rollback()
            print(f"\n❌ Failed to create superuser: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))