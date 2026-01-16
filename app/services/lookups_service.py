from __future__ import annotations

from typing import Any

from psycopg.errors import UniqueViolation

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

    def get_value(self, *, kind: str, org_id: int, item_id: int) -> dict[str, Any] | None:
        return self._repo.get_value(kind=kind, org_id=org_id, item_id=item_id)

    def get_public_value(self, *, kind: str, org_id: int, item_id: int) -> dict[str, Any] | None:
        return self._repo.get_public_value(kind=kind, org_id=org_id, item_id=item_id)

    def create_value(self, *, kind: str, org_id: int, name: str, updated_by: str) -> dict[str, Any]:
        name = (name or "").strip()
        if not name:
            raise ValueError("name is required")
        try:
            return self._repo.create_value(kind=kind, org_id=org_id, name=name, updated_by=updated_by)
        except UniqueViolation as e:
            raise ValueError("name already exists") from e

    def update_value(
        self,
        *,
        kind: str,
        org_id: int,
        item_id: int,
        name: str,
        updated_by: str,
    ) -> dict[str, Any] | None:
        name = (name or "").strip()
        if not name:
            raise ValueError("name is required")
        try:
            return self._repo.update_value(
                kind=kind,
                org_id=org_id,
                item_id=item_id,
                name=name,
                updated_by=updated_by,
            )
        except UniqueViolation as e:
            raise ValueError("name already exists") from e

    def delete_value(self, *, kind: str, org_id: int, item_id: int) -> bool:
        return self._repo.delete_value(kind=kind, org_id=org_id, item_id=item_id)
