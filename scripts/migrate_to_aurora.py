"""Migration script: SQLite → Aurora Serverless v2 PostgreSQL.

Steps:
  1. Verify Aurora connectivity (handles cold start wait)
  2. Run Alembic migrations (create schema)
  3. Migrate all data from SQLite (idempotent)
  4. Verify row counts match

Usage:
    # Option A — DATABASE_URL in environment
    set DATABASE_URL=postgresql+asyncpg://legal_admin:PASSWORD@cluster.rds.amazonaws.com:5432/legal_engine
    py scripts/migrate_to_aurora.py

    # Option B — pull from Secrets Manager (requires boto3 + AWS credentials)
    set AWS_REGION=us-east-1
    py scripts/migrate_to_aurora.py --from-secrets
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_database_url(from_secrets: bool) -> str:
    if from_secrets:
        import boto3
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId="futurotech/prod/database-url")
        url = resp["SecretString"]
        print(f"  ✅ DATABASE_URL loaded from Secrets Manager")
        return url

    url = os.getenv("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL not set. Use --from-secrets or set the env var.")
        sys.exit(1)
    return url


def _get_sync_url(async_url: str) -> str:
    """Convert asyncpg URL to psycopg2 for Alembic."""
    return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


async def _wait_for_aurora(database_url: str, max_wait: int = 90) -> None:
    """Aurora Serverless v2 can take up to 30s to wake from pause."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    print(f"\n[1/4] Connecting to Aurora (max wait {max_wait}s for cold start)...")
    engine = create_async_engine(database_url, pool_pre_ping=True, connect_args={"timeout": 60})
    start = time.time()
    last_error = None

    for attempt in range(1, 10):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            elapsed = time.time() - start
            print(f"  ✅ Connected in {elapsed:.1f}s (attempt {attempt})")
            await engine.dispose()
            return
        except Exception as e:
            last_error = e
            elapsed = time.time() - start
            if elapsed > max_wait:
                break
            print(f"  ⏳ Attempt {attempt} failed ({elapsed:.0f}s elapsed) — Aurora may be waking up...")
            await asyncio.sleep(10)

    await engine.dispose()
    print(f"  ❌ Could not connect after {max_wait}s: {last_error}")
    sys.exit(1)


def _run_alembic(sync_url: str) -> None:
    print("\n[2/4] Running Alembic migrations...")
    env = {**os.environ, "DATABASE_URL": sync_url.replace("psycopg2", "asyncpg")}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(_PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ❌ Alembic failed:\n{result.stderr}")
        sys.exit(1)
    print(f"  ✅ Schema up to date")
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"     {line}")


def _count_sqlite(sqlite_path: str) -> dict[str, int]:
    conn = sqlite3.connect(sqlite_path)
    tables = ["tenants", "templates", "template_documents", "entities", "users"]
    counts = {}
    for t in tables:
        try:
            counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception:
            counts[t] = 0
    conn.close()
    return counts


async def _migrate_data(sqlite_path: str, database_url: str) -> dict[str, int]:
    print("\n[3/4] Migrating data from SQLite...")
    from src.infrastructure.adapters.output.db_postgres import PostgresRepository

    repo = PostgresRepository(database_url)
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    counts: dict[str, int] = {}

    # Tenants
    rows = conn.execute("SELECT * FROM tenants").fetchall()
    for row in rows:
        repo.upsert_tenant({
            "tenant_id": row["tenant_id"], "name": row["name"],
            "system_prompt": row["system_prompt"],
            "legal_rules": json.loads(row["legal_rules"]),
            "branding": json.loads(row["branding"]),
            "active": bool(row["active"]),
        })
    counts["tenants"] = len(rows)
    print(f"  ✅ tenants: {len(rows)} rows")

    # Templates
    rows = conn.execute("SELECT * FROM templates").fetchall()
    for row in rows:
        keys = row.keys()
        repo.upsert_template({
            "template_id": row["template_id"], "name": row["name"],
            "description": row["description"],
            "fields": json.loads(row["fields"]),
            "system_prompt": row["system_prompt"] if "system_prompt" in keys else "",
            "legal_rules": json.loads(row["legal_rules"]) if "legal_rules" in keys else [],
        })
    counts["templates"] = len(rows)
    print(f"  ✅ templates: {len(rows)} rows")

    # Template documents
    rows = conn.execute("SELECT * FROM template_documents").fetchall()
    for row in rows:
        repo.upsert_template_document(
            row["template_id"], row["doc_name"], row["file_type"], row["chunks_count"]
        )
    counts["template_documents"] = len(rows)
    print(f"  ✅ template_documents: {len(rows)} rows")

    # Entities
    rows = conn.execute("SELECT * FROM entities").fetchall()
    for row in rows:
        repo.upsert({
            "entity_id": row["entity_id"], "name": row["name"],
            "nit": row["nit"], "address": row["address"],
            "city": row["city"], "phone": row["phone"],
            "email": row["email"], "legal_rep": row["legal_rep"],
            "entity_type": row["entity_type"], "notes": row["notes"],
        })
    counts["entities"] = len(rows)
    print(f"  ✅ entities: {len(rows)} rows")

    # Users
    rows = conn.execute("SELECT * FROM users").fetchall()
    for row in rows:
        keys = row.keys()
        repo.upsert_user({
            "user_id": row["user_id"], "username": row["username"],
            "full_name": row["full_name"], "email": row["email"],
            "role": row["role"], "active": bool(row["active"]),
            "password_hash": row["password_hash"],
            "permissions": json.loads(row["permissions"]) if "permissions" in keys and row["permissions"] else None,
        })
    counts["users"] = len(rows)
    print(f"  ✅ users: {len(rows)} rows")

    conn.close()
    await repo.dispose()
    return counts


async def _verify(database_url: str, expected: dict[str, int]) -> None:
    print("\n[4/4] Verifying row counts in Aurora...")
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(database_url)
    all_ok = True
    async with engine.connect() as conn:
        for table, expected_count in expected.items():
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            actual = result.scalar()
            status = "✅" if actual >= expected_count else "❌"
            if actual < expected_count:
                all_ok = False
            print(f"  {status} {table:<25} expected={expected_count}  aurora={actual}")
    await engine.dispose()

    if not all_ok:
        print("\n  ⚠️  Some tables have fewer rows than expected. Check for errors above.")
        sys.exit(1)
    print("\n  ✅ All counts match — migration successful!")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(from_secrets: bool) -> None:
    print("=" * 60)
    print("  FuturoTech AI — SQLite → Aurora Serverless v2 Migration")
    print("=" * 60)

    database_url = _get_database_url(from_secrets)
    sync_url = _get_sync_url(database_url)

    sqlite_path = str(_PROJECT_ROOT / os.getenv("DB_PATH", "legal_engine.db"))
    if not Path(sqlite_path).exists():
        print(f"ERROR: SQLite file not found: {sqlite_path}")
        sys.exit(1)

    sqlite_counts = _count_sqlite(sqlite_path)
    print(f"\nSQLite source: {sqlite_path}")
    for t, c in sqlite_counts.items():
        print(f"  {t:<25} {c} rows")

    await _wait_for_aurora(database_url)
    _run_alembic(sync_url)
    await _migrate_data(sqlite_path, database_url)
    await _verify(database_url, sqlite_counts)

    print("\n" + "=" * 60)
    print("  Migration complete. Update DATABASE_URL in your environment.")
    print("  Local SQLite remains untouched as backup.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--from-secrets", action="store_true",
        help="Load DATABASE_URL from AWS Secrets Manager instead of env var"
    )
    args = parser.parse_args()
    asyncio.run(main(args.from_secrets))
