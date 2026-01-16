from __future__ import annotations

import json
from typing import Any

from psycopg.rows import dict_row

from app.database.db_manager import PostgresManager
from app.models.org_display_config import OrgDisplayConfig


class OrgConfigRepository:
    def __init__(self, db: PostgresManager) -> None:
        self._db = db

    def get_config(self, org_id: int) -> OrgDisplayConfig | None:
        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT org_id, allowed_columns, created_at, updated_at, updated_by "
                    "FROM org_display_config WHERE org_id = %s",
                    (org_id,),
                )
                row = cur.fetchone()

        if not row:
            return None

        allowed_columns = row.get("allowed_columns")
        if isinstance(allowed_columns, str):
            try:
                allowed_columns = json.loads(allowed_columns)
            except json.JSONDecodeError:
                return None

        if isinstance(allowed_columns, list) and all(isinstance(c, str) for c in allowed_columns):
            return OrgDisplayConfig(
                org_id=int(row["org_id"]),
                allowed_columns=allowed_columns,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                updated_by=str(row["updated_by"]),
            )

        return None

    def upsert_allowed_columns(self, org_id: int, allowed_columns: list[str], *, updated_by: str) -> None:
        payload: Any = allowed_columns
        with self._db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO org_display_config (org_id, allowed_columns, updated_by)
                    VALUES (%s, %s::jsonb, %s)
                    ON CONFLICT (org_id)
                    DO UPDATE SET allowed_columns = EXCLUDED.allowed_columns,
                                  updated_at = now(),
                                  updated_by = EXCLUDED.updated_by
                    """,
                    (org_id, json.dumps(payload), updated_by),
                )
                conn.commit()

    def list_all(self) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT org_id, allowed_columns, created_at, updated_at, updated_by "
                    "FROM org_display_config ORDER BY org_id ASC"
                )
                return cur.fetchall()

    def delete(self, org_id: int) -> bool:
        with self._db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM org_display_config WHERE org_id = %s", (org_id,))
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted

    def get_allowed_columns(self, org_id: int) -> list[str] | None:
        cfg = self.get_config(org_id)
        return cfg.allowed_columns if cfg else None
