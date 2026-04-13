"""Unit tests — auth_service."""

from __future__ import annotations

import pytest

from src.application.services.auth_service import (
    authenticate,
    ensure_default_admin,
    generate_secure_password,
    hash_password,
    verify_password,
)
from src.domain.exceptions import AuthenticationException


def test_hash_and_verify_roundtrip():
    pwd = "MyS3cur3P@ss"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed)
    assert not verify_password("wrong", hashed)


def test_generate_secure_password_length_and_uniqueness():
    p1 = generate_secure_password()
    p2 = generate_secure_password()
    assert len(p1) == 16
    assert p1 != p2  # astronomically unlikely to collide


def test_authenticate_success(tmp_repo):
    ensure_default_admin(tmp_repo)
    users = tmp_repo.get_all_users()
    # Passwords are random — we need to reset one to test authenticate
    from src.application.services.auth_service import hash_password
    tmp_repo.upsert_user({**users[0], "password_hash": hash_password("TestPass1!")})
    user = tmp_repo.get_all_users()[0]
    result = authenticate(tmp_repo, user["username"], "TestPass1!")
    assert result["username"] == user["username"]


def test_authenticate_wrong_password(tmp_repo):
    ensure_default_admin(tmp_repo)
    users = tmp_repo.get_all_users()
    with pytest.raises(AuthenticationException):
        authenticate(tmp_repo, users[0]["username"], "wrong_password")


def test_authenticate_inactive_user(tmp_repo):
    ensure_default_admin(tmp_repo)
    users = tmp_repo.get_all_users()
    tmp_repo.upsert_user({**users[0], "active": False})
    with pytest.raises(AuthenticationException):
        authenticate(tmp_repo, users[0]["username"], "any")


def test_ensure_default_admin_creates_all_roles(tmp_repo):
    assert tmp_repo.get_all_users() == []
    ensure_default_admin(tmp_repo)
    users = tmp_repo.get_all_users()
    roles = {u["role"] for u in users}
    assert roles == {"admin", "abogado", "pasante", "consulta"}


def test_ensure_default_admin_idempotent(tmp_repo):
    ensure_default_admin(tmp_repo)
    ensure_default_admin(tmp_repo)  # second call must not duplicate
    assert len(tmp_repo.get_all_users()) == 4
