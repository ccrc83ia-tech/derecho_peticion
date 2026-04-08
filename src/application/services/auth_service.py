"""Authentication service — password hashing and user verification."""

from __future__ import annotations

import uuid

import bcrypt

from src.domain.exceptions import AuthenticationException
from src.domain.models import Role
from src.domain.ports.out_ports import UserRepositoryPort


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def authenticate(repo: UserRepositoryPort, username: str, password: str) -> dict:
    user = repo.get_user_by_username(username)
    if not user or not user.get("active", False):
        raise AuthenticationException()
    if not verify_password(password, user.get("password_hash", "")):
        raise AuthenticationException()
    return user


_DEFAULT_USERS = [
    {"username": "admin",    "full_name": "admin",    "role": Role.ADMIN,    "password": "admin123"},
    {"username": "abogado",  "full_name": "abogado",  "role": Role.ABOGADO,  "password": "abogado123"},
    {"username": "pasante",  "full_name": "pasante",  "role": Role.PASANTE,  "password": "pasante123"},
    {"username": "consulta", "full_name": "consulta", "role": Role.CONSULTA, "password": "consulta123"},
]


def ensure_default_admin(repo: UserRepositoryPort) -> None:
    """Create default users (one per role) if no users exist."""
    if repo.get_all_users():
        return
    for u in _DEFAULT_USERS:
        repo.upsert_user({
            "user_id": str(uuid.uuid4()),
            "username": u["username"],
            "full_name": u["full_name"],
            "email": "",
            "role": u["role"].value,
            "active": True,
            "password_hash": hash_password(u["password"]),
        })
