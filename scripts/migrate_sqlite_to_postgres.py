"""One-shot data migration: SQLite -> PostgreSQL.

Usage:
    set DATABASE_URL=postgresql+asyncpg://user:password@host:5432/legal_engine
    py scripts/migrate_sqlite_to_postgres.py

Safe to run multiple times (idempotent via ON CONFLICT DO UPDATE).
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from src.infrastructure.adapters.output.db_postgres import PostgresRepository


async def migrate(sqlite_path: str, database_url: str) -> None:
    print(f"Source : {sqlite_path}")
    print(f"Target : {database_url.split('@')[-1]}")
    print("-" * 50)

    repo = PostgresRepository(database_url)
    await repo.init_schema()

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    counts: dict[str, int] = {
        "tenants": 0, "templates": 0,
        "template_documents": 0, "entities": 0, "users": 0,
    }

    for row in conn.execute("SELECT * FROM tenants").fetchall():
        repo.upsert_tenant({
            "tenant_id": row["tenant_id"],
            "name": row["name"],
            "system_prompt": row["system_prompt"],
            "legal_rules": json.loads(row["legal_rules"]),
            "branding": json.loads(row["branding"]),
            "active": bool(row["active"]),
        })
        counts["tenants"] += 1

    for row in conn.execute("SELECT * FROM templates").fetchall():
        keys = row.keys()
        repo.upsert_template({
            "template_id": row["template_id"],
            "name": row["name"],
            "description": row["description"],
            "fields": json.loads(row["fields"]),
            "system_prompt": row["system_prompt"] if "system_prompt" in keys else "",
            "legal_rules": json.loads(row["legal_rules"]) if "legal_rules" in keys else [],
        })
        counts["templates"] += 1

    for row in conn.execute("SELECT * FROM template_documents").fetchall():
        repo.upsert_template_document(
            row["template_id"], row["doc_name"], row["file_type"], row["chunks_count"]
        )
        counts["template_documents"] += 1

    for row in conn.execute("SELECT * FROM entities").fetchall():
        repo.upsert({
            "entity_id": row["entity_id"], "name": row["name"],
            "nit": row["nit"], "address": row["address"],
            "city": row["city"], "phone": row["phone"],
            "email": row["email"], "legal_rep": row["legal_rep"],
            "entity_type": row["entity_type"], "notes": row["notes"],
        })
        counts["entities"] += 1

    for row in conn.execute("SELECT * FROM users").fetchall():
        repo.upsert_user({
            "user_id": row["user_id"], "username": row["username"],
            "full_name": row["full_name"], "email": row["email"],
            "role": row["role"], "active": bool(row["active"]),
            "password_hash": row["password_hash"],
        })
        counts["users"] += 1

    conn.close()
    await repo.dispose()

    print("\nMigration complete:")
    for table, count in counts.items():
        print(f"  {table:<22} {count:>5} rows")


if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL env var is required.")
        sys.exit(1)

    sqlite_file = str(_PROJECT_ROOT / os.getenv("DB_PATH", "legal_engine.db"))
    if not Path(sqlite_file).exists():
        print(f"ERROR: SQLite file not found: {sqlite_file}")
        sys.exit(1)

    asyncio.run(migrate(sqlite_file, db_url))
