from __future__ import annotations

from typing import Any

from app.database.db_manager import PostgresManager
from app.repositories.api_keys_repo import ApiKeysRepository


class ApiKeysService:
    def __init__(self, db: PostgresManager) -> None:
        self._repo = ApiKeysRepository(db)

    def list_all(self) -> list[dict[str, Any]]:
        return self._repo.list_all()

    def get_by_org_id(self, org_id: int) -> dict[str, Any] | None:
        return self._repo.get_by_org_id(org_id)

    def upsert(self, *, org_id: int, api_key: str, updated_by: str) -> None:
        api_key = (api_key or "").strip()
        if not api_key:
            raise ValueError("api_key must be non-empty")
        self._repo.upsert(org_id=org_id, api_key=api_key, updated_by=updated_by)
