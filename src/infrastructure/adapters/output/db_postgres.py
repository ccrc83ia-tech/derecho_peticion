import json
from pathlib import Path

from src.domain.models import TenantConfig
from src.domain.ports.out_ports import TenantRepositoryPort


class PostgresTenantRepository(TenantRepositoryPort):
    """
    MVP: JSON-file backed implementation.
    Production: swap internals to asyncpg/SQLAlchemy without touching the port.
    """

    def __init__(self, datasource: str = "tenants.json") -> None:
        self._datasource = Path(datasource)

    def _load(self) -> dict[str, dict]:
        if not self._datasource.exists():
            return {}
        with self._datasource.open("r", encoding="utf-8") as f:
            tenants: list[dict] = json.load(f)
        return {t["tenant_id"]: t for t in tenants}

    async def get_by_id(self, tenant_id: str) -> TenantConfig | None:
        data = self._load()
        raw = data.get(tenant_id)
        return TenantConfig(**raw) if raw else None
