from __future__ import annotations

import json

from app.database.db_manager import PostgresManager
from app.models.employee import Employee
from app.models.org_display_config import OrgDisplayConfig
from app.repositories.org_config_repo import OrgConfigRepository


class OrgConfigService:
    def __init__(self, db: PostgresManager) -> None:
        self._repo = OrgConfigRepository(db)

    @staticmethod
    def sanitize_columns(columns: list[str]) -> list[str]:
        # Only allow known, safe columns.
        sanitized = [c for c in columns if c in Employee.ALLOWED_COLUMNS]

        # de-dup, preserve order
        seen: set[str] = set()
        result: list[str] = []
        for c in sanitized:
            if c not in seen:
                seen.add(c)
                result.append(c)

        # Always require id to support pagination/cursor.
        if "id" in result:
            result.remove("id")
        result.insert(0, "id")

        return result

    def get_allowed_columns(self, org_id: int) -> list[str] | None:
        return self._repo.get_allowed_columns(org_id)

    def get_config(self, org_id: int) -> OrgDisplayConfig | None:
        return self._repo.get_config(org_id)

    def set_allowed_columns(self, org_id: int, columns: list[str], *, updated_by: str) -> list[str]:
        sanitized = self.sanitize_columns(columns)
        self._repo.upsert_allowed_columns(org_id, sanitized, updated_by=updated_by)
        return sanitized

    def list_all(self) -> list[OrgDisplayConfig]:
        rows = self._repo.list_all()
        result: list[OrgDisplayConfig] = []
        for row in rows:
            allowed_columns = row.get("allowed_columns")
            if isinstance(allowed_columns, str):
                try:
                    allowed_columns = json.loads(allowed_columns)
                except json.JSONDecodeError:
                    continue
            if not (isinstance(allowed_columns, list) and all(isinstance(c, str) for c in allowed_columns)):
                continue
            result.append(
                OrgDisplayConfig(
                    org_id=int(row["org_id"]),
                    allowed_columns=allowed_columns,
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    updated_by=str(row["updated_by"]),
                )
            )
        return result

    def delete(self, org_id: int) -> bool:
        return self._repo.delete(org_id)
