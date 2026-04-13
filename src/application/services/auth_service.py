"""Authentication service — password hashing, verification, and secure first-run setup."""

from __future__ import annotations

import secrets
import string
import uuid

import bcrypt

from src.domain.exceptions import AuthenticationException
from src.domain.models import Role
from src.domain.ports.out_ports import UserRepositoryPort
from src.infrastructure.logging_config import get_logger
from src.infrastructure.security_config import create_secure_log_extra

logger = get_logger(__name__)

_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*"
_PASSWORD_LENGTH = 16


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def generate_secure_password() -> str:
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(_PASSWORD_LENGTH))


def authenticate(repo: UserRepositoryPort, username: str, password: str) -> dict:
    user = repo.get_user_by_username(username)
    if not user or not user.get("active", False):
        raise AuthenticationException()
    if not verify_password(password, user.get("password_hash", "")):
        raise AuthenticationException()
    return user


_DEFAULT_ROLES = [
    ("admin",    "Administrador", Role.ADMIN),
    ("abogado",  "Abogado",       Role.ABOGADO),
    ("pasante",  "Pasante",       Role.PASANTE),
    ("consulta", "Solo Consulta", Role.CONSULTA),
]


def ensure_default_admin(repo: UserRepositoryPort) -> None:
    """Create default users with random passwords if no users exist.

    Passwords are printed to stdout AND logged at WARNING level.
    They are never stored in plain text and never hardcoded.
    """
    if repo.get_all_users():
        return

    separator = "=" * 60
    header = [
        separator,
        "  PRIMER ARRANQUE — Credenciales iniciales generadas",
        "  Guarde estas contraseñas en un lugar seguro.",
        "  No se volverán a mostrar.",
        separator,
    ]
    for line in header:
        print(line)

    for username, full_name, role in _DEFAULT_ROLES:
        password = generate_secure_password()
        repo.upsert_user({
            "user_id": str(uuid.uuid4()),
            "username": username,
            "full_name": full_name,
            "email": "",
            "role": role.value,
            "active": True,
            "password_hash": hash_password(password),
        })
        # Print masked password for console visibility
        masked_password = password[:2] + "*" * (len(password) - 4) + password[-2:]
        credential_line = f"  {username:<10} → {masked_password} (full password in secure log)"
        print(credential_line)
        
        # Log with secure structured logging
        logger.warning(
            "Default user created with secure password",
            extra=create_secure_log_extra(
                username=username,
                role=role.value,
                password_length=len(password),
                secure_password=password  # Only in file logs, masked in console
            )
        )

    print(separator + "\n")
