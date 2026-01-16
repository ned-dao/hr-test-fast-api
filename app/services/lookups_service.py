from __future__ import annotations

from typing import Any

from app.database.db_manager import PostgresManager
from app.repositories.lookups_repo import LookupsRepository


class LookupsService:
    def __init__(self, db: PostgresManager) -> None:
        self._repo = LookupsRepository(db)

    def list_values(
        self,
        *,
        kind: str,
        org_id: int | None,
        q: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        return self._repo.list_values(kind=kind, org_id=org_id, q=q, limit=limit)
