"""Unit tests — SQLiteTenantRepository (CRUD + template versioning)."""

from __future__ import annotations

import pytest

from src.application.services.auth_service import ensure_default_admin


def test_upsert_and_get_tenant(tmp_repo, sample_tenant):
    tmp_repo.upsert_tenant(sample_tenant)
    tenants = tmp_repo.get_all_tenants()
    assert len(tenants) == 1
    assert tenants[0]["tenant_id"] == "tenant-test"
    assert tenants[0]["legal_rules"] == ["Ley 1755 de 2015"]


def test_delete_tenant(tmp_repo, sample_tenant):
    tmp_repo.upsert_tenant(sample_tenant)
    tmp_repo.delete_tenant("tenant-test")
    assert tmp_repo.get_all_tenants() == []


def test_only_one_active_tenant(tmp_repo):
    tmp_repo.upsert_tenant({"tenant_id": "t1", "name": "A", "system_prompt": "", "active": True})
    tmp_repo.upsert_tenant({"tenant_id": "t2", "name": "B", "system_prompt": "", "active": True})
    active = [t for t in tmp_repo.get_all_tenants() if t["active"]]
    assert len(active) == 1
    assert active[0]["tenant_id"] == "t2"


def test_upsert_template_creates_version(tmp_repo, sample_template):
    tmp_repo.upsert_template(sample_template)
    versions = tmp_repo.get_template_versions("tpl-test")
    assert len(versions) == 1
    assert versions[0]["version"] == 1
    assert versions[0]["name"] == "Derecho de Petición"


def test_upsert_template_increments_version(tmp_repo, sample_template):
    tmp_repo.upsert_template(sample_template)
    updated = {**sample_template, "name": "Derecho de Petición v2"}
    tmp_repo.upsert_template(updated)
    versions = tmp_repo.get_template_versions("tpl-test")
    assert len(versions) == 2
    assert versions[0]["version"] == 2  # ordered DESC
    assert versions[0]["name"] == "Derecho de Petición v2"


def test_delete_template_cascades_versions(tmp_repo, sample_template):
    tmp_repo.upsert_template(sample_template)
    tmp_repo.delete_template("tpl-test")
    assert tmp_repo.get_all_templates() == []
    assert tmp_repo.get_template_versions("tpl-test") == []


def test_upsert_and_get_entity(tmp_repo):
    entity = {"entity_id": "e1", "name": "EPS Sura", "entity_type": "EPS"}
    tmp_repo.upsert(entity)
    result = tmp_repo.get_by_entity_id("e1")
    assert result is not None
    assert result["name"] == "EPS Sura"


def test_user_crud(tmp_repo):
    ensure_default_admin(tmp_repo)
    users = tmp_repo.get_all_users()
    assert len(users) == 4
    admin = tmp_repo.get_user_by_username("admin")
    assert admin is not None
    tmp_repo.delete_user(admin["user_id"])
    assert tmp_repo.get_user_by_username("admin") is None
