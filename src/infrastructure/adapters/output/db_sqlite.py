"""SQLite-backed persistence for tenants and templates.

Drop-in replacement for the JSON-file approach.  The DB file path is
configurable via the DB_PATH env-var (defaults to ``legal_engine.db``
in the project root).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from src.domain.models import TenantConfig, Entity, User
from src.domain.ports.out_ports import TenantRepositoryPort, TemplateRepositoryPort, EntityRepositoryPort, UserRepositoryPort
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_DB = "legal_engine.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id     TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    system_prompt TEXT NOT NULL DEFAULT '',
    legal_rules   TEXT NOT NULL DEFAULT '[]',
    branding      TEXT NOT NULL DEFAULT '{}',
    required_fields TEXT NOT NULL DEFAULT '[]',
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS templates (
    template_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    fields        TEXT NOT NULL DEFAULT '[]',
    system_prompt TEXT NOT NULL DEFAULT '',
    legal_rules   TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS template_documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id   TEXT NOT NULL,
    doc_name      TEXT NOT NULL,
    file_type     TEXT NOT NULL DEFAULT '',
    chunks_count  INTEGER NOT NULL DEFAULT 0,
    uploaded_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(template_id, doc_name)
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id     TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    nit           TEXT NOT NULL DEFAULT '',
    address       TEXT NOT NULL DEFAULT '',
    city          TEXT NOT NULL DEFAULT '',
    phone         TEXT NOT NULL DEFAULT '',
    email         TEXT NOT NULL DEFAULT '',
    legal_rep     TEXT NOT NULL DEFAULT '',
    entity_type   TEXT NOT NULL DEFAULT '',
    notes         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL DEFAULT '',
    role          TEXT NOT NULL DEFAULT 'pasante',
    active        INTEGER NOT NULL DEFAULT 1,
    password_hash TEXT NOT NULL DEFAULT ''
);
"""


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str | Path) -> None:
    """Create tables if they don't exist and migrate schema."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA_SQL)
        # Auto-migrate: add columns if missing
        cols = {r[1] for r in conn.execute("PRAGMA table_info(templates)").fetchall()}
        if "system_prompt" not in cols:
            conn.execute("ALTER TABLE templates ADD COLUMN system_prompt TEXT NOT NULL DEFAULT ''")
        if "legal_rules" not in cols:
            conn.execute("ALTER TABLE templates ADD COLUMN legal_rules TEXT NOT NULL DEFAULT '[]'")


# ---------------------------------------------------------------------------
# Tenant repository  (implements the domain port)
# ---------------------------------------------------------------------------

class SQLiteTenantRepository(TenantRepositoryPort, TemplateRepositoryPort, EntityRepositoryPort, UserRepositoryPort):

    def __init__(self, db_path: str | Path = _DEFAULT_DB) -> None:
        self._db_path = Path(db_path)
        init_db(self._db_path)
        logger.info("SQLiteTenantRepository ready — %s", self._db_path)

    def _conn(self) -> sqlite3.Connection:
        return _connect(self._db_path)

    # --- Port method ---
    async def get_by_id(self, tenant_id: str) -> TenantConfig | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,)
            ).fetchone()
        if row is None:
            logger.warning("get_by_id: tenant '%s' not found", tenant_id)
            return None
        logger.debug("get_by_id: tenant '%s' found", tenant_id)
        return TenantConfig(**_row_to_tenant(row))

    # --- CRUD used by the UI layer ---

    def get_all_tenants(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM tenants ORDER BY name").fetchall()
        return [_row_to_tenant(r) for r in rows]

    def upsert_tenant(self, tenant: dict[str, Any]) -> None:
        is_active = 1 if tenant.get("active", True) else 0
        with self._conn() as conn:
            # Only one tenant can be active at a time
            if is_active:
                conn.execute("UPDATE tenants SET active = 0 WHERE active = 1")
            conn.execute(
                """
                INSERT INTO tenants (tenant_id, name, system_prompt, legal_rules, branding, active)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id) DO UPDATE SET
                    name=excluded.name,
                    system_prompt=excluded.system_prompt,
                    legal_rules=excluded.legal_rules,
                    branding=excluded.branding,
                    active=excluded.active
                """,
                (
                    tenant["tenant_id"],
                    tenant["name"],
                    tenant.get("system_prompt", ""),
                    json.dumps(tenant.get("legal_rules", []), ensure_ascii=False),
                    json.dumps(tenant.get("branding", {}), ensure_ascii=False),
                    is_active,
                ),
            )

    def delete_tenant(self, tenant_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM tenants WHERE tenant_id = ?", (tenant_id,))

    # --- Templates CRUD ---

    def get_all_templates(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM templates ORDER BY name").fetchall()
        return [_row_to_template(r) for r in rows]

    def upsert_template(self, template: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO templates (template_id, name, description, fields, system_prompt, legal_rules)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(template_id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    fields=excluded.fields,
                    system_prompt=excluded.system_prompt,
                    legal_rules=excluded.legal_rules
                """,
                (
                    template["template_id"],
                    template["name"],
                    template.get("description", ""),
                    json.dumps(template.get("fields", []), ensure_ascii=False),
                    template.get("system_prompt", ""),
                    json.dumps(template.get("legal_rules", []), ensure_ascii=False),
                ),
            )

    def delete_template(self, template_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM templates WHERE template_id = ?", (template_id,))
            conn.execute("DELETE FROM template_documents WHERE template_id = ?", (template_id,))

    # --- Template documents CRUD ---

    def get_template_documents(self, template_id: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT doc_name, file_type, chunks_count, uploaded_at "
                "FROM template_documents WHERE template_id = ? ORDER BY uploaded_at DESC",
                (template_id,),
            ).fetchall()
        return [{"doc_name": r[0], "file_type": r[1], "chunks_count": r[2], "uploaded_at": r[3]} for r in rows]

    def upsert_template_document(self, template_id: str, doc_name: str, file_type: str, chunks_count: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO template_documents (template_id, doc_name, file_type, chunks_count) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(template_id, doc_name) DO UPDATE SET "
                "file_type=excluded.file_type, chunks_count=excluded.chunks_count, uploaded_at=datetime('now')",
                (template_id, doc_name, file_type, chunks_count),
            )

    def delete_template_document(self, template_id: str, doc_name: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM template_documents WHERE template_id = ? AND doc_name = ?",
                (template_id, doc_name),
            )

    # --- Entities CRUD (implements EntityRepositoryPort) ---

    def get_all(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM entities ORDER BY name").fetchall()
        return [_row_to_entity(r) for r in rows]

    def get_by_entity_id(self, entity_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM entities WHERE entity_id = ?", (entity_id,)
            ).fetchone()
        return _row_to_entity(row) if row else None

    def upsert(self, entity: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO entities (entity_id, name, nit, address, city, phone, email, legal_rep, entity_type, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    name=excluded.name, nit=excluded.nit, address=excluded.address,
                    city=excluded.city, phone=excluded.phone, email=excluded.email,
                    legal_rep=excluded.legal_rep, entity_type=excluded.entity_type, notes=excluded.notes
                """,
                (
                    entity["entity_id"], entity["name"],
                    entity.get("nit", ""), entity.get("address", ""),
                    entity.get("city", ""), entity.get("phone", ""),
                    entity.get("email", ""), entity.get("legal_rep", ""),
                    entity.get("entity_type", ""), entity.get("notes", ""),
                ),
            )

    def delete(self, entity_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM entities WHERE entity_id = ?", (entity_id,))

    # --- Users CRUD (implements UserRepositoryPort) ---

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        return _row_to_user(row) if row else None

    def get_all_users(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY full_name").fetchall()
        return [_row_to_user(r) for r in rows]

    def upsert_user(self, user: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, username, full_name, email, role, active, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username, full_name=excluded.full_name,
                    email=excluded.email, role=excluded.role,
                    active=excluded.active, password_hash=excluded.password_hash
                """,
                (
                    user["user_id"], user["username"], user["full_name"],
                    user.get("email", ""), user.get("role", "pasante"),
                    1 if user.get("active", True) else 0,
                    user.get("password_hash", ""),
                ),
            )

    def delete_user(self, user_id: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


# ---------------------------------------------------------------------------
# Row → dict converters
# ---------------------------------------------------------------------------

def _row_to_tenant(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "tenant_id": row["tenant_id"],
        "name": row["name"],
        "system_prompt": row["system_prompt"],
        "legal_rules": json.loads(row["legal_rules"]),
        "branding": json.loads(row["branding"]),
        "active": bool(row["active"]),
    }


def _row_to_template(row: sqlite3.Row) -> dict[str, Any]:
    d = {
        "template_id": row["template_id"],
        "name": row["name"],
        "description": row["description"],
        "fields": json.loads(row["fields"]),
    }
    # New columns (may not exist in old DBs before migration)
    try:
        d["system_prompt"] = row["system_prompt"]
        d["legal_rules"] = json.loads(row["legal_rules"])
    except (IndexError, KeyError):
        d["system_prompt"] = ""
        d["legal_rules"] = []
    return d


def _row_to_entity(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "entity_id": row["entity_id"],
        "name": row["name"],
        "nit": row["nit"],
        "address": row["address"],
        "city": row["city"],
        "phone": row["phone"],
        "email": row["email"],
        "legal_rep": row["legal_rep"],
        "entity_type": row["entity_type"],
        "notes": row["notes"],
    }


def _row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"],
        "active": bool(row["active"]),
        "password_hash": row["password_hash"],
    }


# ---------------------------------------------------------------------------
# Migration: JSON → SQLite  (run once)
# ---------------------------------------------------------------------------

def migrate_from_json(
    db_path: str | Path,
    tenants_json: str | Path | None = None,
    templates_json: str | Path | None = None,
    entities_json: str | Path | None = None,
) -> dict[str, int]:
    """Import existing JSON files into SQLite. Skips if tables already have data."""
    repo = SQLiteTenantRepository(db_path)
    counts: dict[str, int] = {"tenants": 0, "templates": 0, "entities": 0}

    if tenants_json and Path(tenants_json).exists() and not repo.get_all_tenants():
        with open(tenants_json, "r", encoding="utf-8") as fh:
            tenants = json.load(fh)
        for t in tenants:
            repo.upsert_tenant(t)
            counts["tenants"] += 1

    if templates_json and Path(templates_json).exists() and not repo.get_all_templates():
        with open(templates_json, "r", encoding="utf-8") as fh:
            templates = json.load(fh)
        for t in templates:
            repo.upsert_template(t)
            counts["templates"] += 1

    if entities_json and Path(entities_json).exists() and not repo.get_all():
        with open(entities_json, "r", encoding="utf-8") as fh:
            entities = json.load(fh)
        for e in entities:
            repo.upsert(e)
            counts["entities"] += 1

    return counts
