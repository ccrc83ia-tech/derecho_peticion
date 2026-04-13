"""PostgreSQL-backed repository using SQLAlchemy async + asyncpg.

Implements all four domain ports:
  TenantRepositoryPort, TemplateRepositoryPort,
  EntityRepositoryPort, UserRepositoryPort

The domain ports define sync signatures (get_all_tenants, upsert_tenant, etc.)
because the UI layer (Streamlit) is synchronous. We bridge sync→async using
anyio.from_thread.run_sync when called from a sync context, and call the async
methods directly when inside an async context (FastAPI).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import anyio
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.models import TenantConfig
from src.domain.ports.out_ports import (
    EntityRepositoryPort,
    TemplateRepositoryPort,
    TenantRepositoryPort,
    UserRepositoryPort,
)
from src.infrastructure.adapters.output.db_models import (
    Base,
    EntityModel,
    TemplateDocumentModel,
    TemplateModel,
    TenantModel,
    UserModel,
)
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)


def _run(coro):
    """Run a coroutine from sync context safely, regardless of event loop state."""
    try:
        loop = anyio.from_thread.run_sync  # noqa: F841 — just checking availability
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're inside an async context (FastAPI) — use a new thread-bound loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(anyio.run, lambda: coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        import asyncio
        return asyncio.run(coro)


def build_engine(database_url: str):
    """Build async engine tuned for Aurora Serverless v2.

    Aurora Serverless v2 can pause when idle and take 20-30s to resume.
    - pool_pre_ping: drops stale connections after resume
    - pool_recycle: prevents connections older than 30min (Aurora forcibly
      closes idle connections at the network level after ~1h)
    - connect_args timeout: gives Aurora time to wake up on first connect
    - pool_size=5: conservative for Serverless v2 (scales ACUs, not connections)
    """
    is_aurora = "rds.amazonaws.com" in database_url
    return create_async_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=60 if is_aurora else 30,   # extra wait for cold start
        echo=False,
        connect_args={"timeout": 60} if is_aurora else {},
    )


class PostgresRepository(
    TenantRepositoryPort,
    TemplateRepositoryPort,
    EntityRepositoryPort,
    UserRepositoryPort,
):
    def __init__(self, database_url: str) -> None:
        self._engine = build_engine(database_url)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        logger.info("PostgresRepository initialized — pool_size=10")

    async def init_schema(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema verified")

    async def dispose(self) -> None:
        await self._engine.dispose()

    # ------------------------------------------------------------------
    # TenantRepositoryPort
    # ------------------------------------------------------------------

    async def get_by_id(self, tenant_id: str) -> TenantConfig | None:
        async with self._session_factory() as s:
            row = await s.get(TenantModel, tenant_id)
        if row is None:
            logger.warning("Tenant '%s' not found", tenant_id)
            return None
        return TenantConfig(**_tenant_to_dict(row))

    def get_all_tenants(self) -> list[dict[str, Any]]:
        return _run(self._aget_all_tenants())

    async def _aget_all_tenants(self) -> list[dict[str, Any]]:
        async with self._session_factory() as s:
            rows = (await s.execute(select(TenantModel).order_by(TenantModel.name))).scalars().all()
        return [_tenant_to_dict(r) for r in rows]

    def upsert_tenant(self, tenant: dict[str, Any]) -> None:
        _run(self._aupsert_tenant(tenant))

    async def _aupsert_tenant(self, tenant: dict[str, Any]) -> None:
        async with self._session_factory() as s:
            async with s.begin():
                if tenant.get("active", True):
                    await s.execute(update(TenantModel).values(active=False))
                stmt = pg_insert(TenantModel).values(
                    tenant_id=tenant["tenant_id"],
                    name=tenant["name"],
                    system_prompt=tenant.get("system_prompt", ""),
                    legal_rules=tenant.get("legal_rules", []),
                    branding=tenant.get("branding", {}),
                    active=tenant.get("active", True),
                ).on_conflict_do_update(
                    index_elements=["tenant_id"],
                    set_={
                        "name": tenant["name"],
                        "system_prompt": tenant.get("system_prompt", ""),
                        "legal_rules": tenant.get("legal_rules", []),
                        "branding": tenant.get("branding", {}),
                        "active": tenant.get("active", True),
                    },
                )
                await s.execute(stmt)

    def delete_tenant(self, tenant_id: str) -> None:
        _run(self._adelete_tenant(tenant_id))

    async def _adelete_tenant(self, tenant_id: str) -> None:
        async with self._session_factory() as s:
            async with s.begin():
                await s.execute(delete(TenantModel).where(TenantModel.tenant_id == tenant_id))

    # ------------------------------------------------------------------
    # TemplateRepositoryPort
    # ------------------------------------------------------------------

    def get_all_templates(self) -> list[dict[str, Any]]:
        return _run(self._aget_all_templates())

    async def _aget_all_templates(self) -> list[dict[str, Any]]:
        async with self._session_factory() as s:
            rows = (await s.execute(select(TemplateModel).order_by(TemplateModel.name))).scalars().all()
        return [_template_to_dict(r) for r in rows]

    def upsert_template(self, template: dict[str, Any]) -> None:
        _run(self._aupsert_template(template))

    async def _aupsert_template(self, template: dict[str, Any]) -> None:
        async with self._session_factory() as s:
            async with s.begin():
                stmt = pg_insert(TemplateModel).values(
                    template_id=template["template_id"],
                    name=template["name"],
                    description=template.get("description", ""),
                    fields=template.get("fields", []),
                    system_prompt=template.get("system_prompt", ""),
                    legal_rules=template.get("legal_rules", []),
                ).on_conflict_do_update(
                    index_elements=["template_id"],
                    set_={
                        "name": template["name"],
                        "description": template.get("description", ""),
                        "fields": template.get("fields", []),
                        "system_prompt": template.get("system_prompt", ""),
                        "legal_rules": template.get("legal_rules", []),
                    },
                )
                await s.execute(stmt)

    def delete_template(self, template_id: str) -> None:
        _run(self._adelete_template(template_id))

    async def _adelete_template(self, template_id: str) -> None:
        async with self._session_factory() as s:
            async with s.begin():
                await s.execute(delete(TemplateModel).where(TemplateModel.template_id == template_id))

    def get_template_documents(self, template_id: str) -> list[dict[str, Any]]:
        return _run(self._aget_template_documents(template_id))

    async def _aget_template_documents(self, template_id: str) -> list[dict[str, Any]]:
        async with self._session_factory() as s:
            rows = (await s.execute(
                select(TemplateDocumentModel)
                .where(TemplateDocumentModel.template_id == template_id)
                .order_by(TemplateDocumentModel.uploaded_at.desc())
            )).scalars().all()
        return [_doc_to_dict(r) for r in rows]

    def upsert_template_document(self, template_id: str, doc_name: str, file_type: str, chunks_count: int) -> None:
        _run(self._aupsert_template_document(template_id, doc_name, file_type, chunks_count))

    async def _aupsert_template_document(
        self, template_id: str, doc_name: str, file_type: str, chunks_count: int
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._session_factory() as s:
            async with s.begin():
                stmt = pg_insert(TemplateDocumentModel).values(
                    template_id=template_id, doc_name=doc_name,
                    file_type=file_type, chunks_count=chunks_count, uploaded_at=now,
                ).on_conflict_do_update(
                    index_elements=["template_id", "doc_name"],
                    set_={"file_type": file_type, "chunks_count": chunks_count, "uploaded_at": now},
                )
                await s.execute(stmt)

    def delete_template_document(self, template_id: str, doc_name: str) -> None:
        _run(self._adelete_template_document(template_id, doc_name))

    async def _adelete_template_document(self, template_id: str, doc_name: str) -> None:
        async with self._session_factory() as s:
            async with s.begin():
                await s.execute(
                    delete(TemplateDocumentModel).where(
                        TemplateDocumentModel.template_id == template_id,
                        TemplateDocumentModel.doc_name == doc_name,
                    )
                )

    # ------------------------------------------------------------------
    # EntityRepositoryPort
    # ------------------------------------------------------------------

    def get_all(self) -> list[dict[str, Any]]:
        return _run(self._aget_all_entities())

    async def _aget_all_entities(self) -> list[dict[str, Any]]:
        async with self._session_factory() as s:
            rows = (await s.execute(select(EntityModel).order_by(EntityModel.name))).scalars().all()
        return [_entity_to_dict(r) for r in rows]

    def get_by_entity_id(self, entity_id: str) -> dict[str, Any] | None:
        return _run(self._aget_entity(entity_id))

    async def _aget_entity(self, entity_id: str) -> dict[str, Any] | None:
        async with self._session_factory() as s:
            row = await s.get(EntityModel, entity_id)
        return _entity_to_dict(row) if row else None

    def upsert(self, entity: dict[str, Any]) -> None:
        _run(self._aupsert_entity(entity))

    async def _aupsert_entity(self, entity: dict[str, Any]) -> None:
        vals = _entity_values(entity)
        async with self._session_factory() as s:
            async with s.begin():
                stmt = pg_insert(EntityModel).values(**vals).on_conflict_do_update(
                    index_elements=["entity_id"],
                    set_={k: v for k, v in vals.items() if k != "entity_id"},
                )
                await s.execute(stmt)

    def delete(self, entity_id: str) -> None:
        _run(self._adelete_entity(entity_id))

    async def _adelete_entity(self, entity_id: str) -> None:
        async with self._session_factory() as s:
            async with s.begin():
                await s.execute(delete(EntityModel).where(EntityModel.entity_id == entity_id))

    # ------------------------------------------------------------------
    # UserRepositoryPort
    # ------------------------------------------------------------------

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        return _run(self._aget_user_by_username(username))

    async def _aget_user_by_username(self, username: str) -> dict[str, Any] | None:
        async with self._session_factory() as s:
            row = (await s.execute(
                select(UserModel).where(UserModel.username == username)
            )).scalar_one_or_none()
        return _user_to_dict(row) if row else None

    def get_all_users(self) -> list[dict[str, Any]]:
        return _run(self._aget_all_users())

    async def _aget_all_users(self) -> list[dict[str, Any]]:
        async with self._session_factory() as s:
            rows = (await s.execute(select(UserModel).order_by(UserModel.full_name))).scalars().all()
        return [_user_to_dict(r) for r in rows]

    def upsert_user(self, user: dict[str, Any]) -> None:
        _run(self._aupsert_user(user))

    async def _aupsert_user(self, user: dict[str, Any]) -> None:
        async with self._session_factory() as s:
            async with s.begin():
                stmt = pg_insert(UserModel).values(
                    user_id=user["user_id"], username=user["username"],
                    full_name=user["full_name"], email=user.get("email", ""),
                    role=user.get("role", "pasante"), active=user.get("active", True),
                    password_hash=user.get("password_hash", ""),
                    permissions=user.get("permissions"),
                ).on_conflict_do_update(
                    index_elements=["user_id"],
                    set_={
                        "username": user["username"], "full_name": user["full_name"],
                        "email": user.get("email", ""), "role": user.get("role", "pasante"),
                        "active": user.get("active", True),
                        "password_hash": user.get("password_hash", ""),
                        "permissions": user.get("permissions"),
                    },
                )
                await s.execute(stmt)

    def delete_user(self, user_id: str) -> None:
        _run(self._adelete_user(user_id))

    async def _adelete_user(self, user_id: str) -> None:
        async with self._session_factory() as s:
            async with s.begin():
                await s.execute(delete(UserModel).where(UserModel.user_id == user_id))


# ------------------------------------------------------------------
# Row → dict helpers
# ------------------------------------------------------------------

def _tenant_to_dict(r: TenantModel) -> dict[str, Any]:
    return {
        "tenant_id": r.tenant_id, "name": r.name,
        "system_prompt": r.system_prompt, "legal_rules": r.legal_rules,
        "branding": r.branding, "active": r.active,
    }


def _template_to_dict(r: TemplateModel) -> dict[str, Any]:
    return {
        "template_id": r.template_id, "name": r.name,
        "description": r.description, "fields": r.fields,
        "system_prompt": r.system_prompt, "legal_rules": r.legal_rules,
    }


def _doc_to_dict(r: TemplateDocumentModel) -> dict[str, Any]:
    return {
        "doc_name": r.doc_name, "file_type": r.file_type,
        "chunks_count": r.chunks_count,
        "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else "",
    }


def _entity_to_dict(r: EntityModel) -> dict[str, Any]:
    return {
        "entity_id": r.entity_id, "name": r.name, "nit": r.nit,
        "address": r.address, "city": r.city, "phone": r.phone,
        "email": r.email, "legal_rep": r.legal_rep,
        "entity_type": r.entity_type, "notes": r.notes,
    }


def _entity_values(e: dict[str, Any]) -> dict[str, Any]:
    return {
        "entity_id": e["entity_id"], "name": e["name"],
        "nit": e.get("nit", ""), "address": e.get("address", ""),
        "city": e.get("city", ""), "phone": e.get("phone", ""),
        "email": e.get("email", ""), "legal_rep": e.get("legal_rep", ""),
        "entity_type": e.get("entity_type", ""), "notes": e.get("notes", ""),
    }


def _user_to_dict(r: UserModel) -> dict[str, Any]:
    return {
        "user_id": r.user_id, "username": r.username, "full_name": r.full_name,
        "email": r.email, "role": r.role, "active": r.active,
        "password_hash": r.password_hash,
        "permissions": r.permissions,
    }
