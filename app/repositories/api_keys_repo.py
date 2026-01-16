from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row

from app.database.db_manager import PostgresManager


class ApiKeysRepository:
    def __init__(self, db: PostgresManager) -> None:
        self._db = db

    def get_org_id_by_api_key(self, api_key: str) -> int | None:
        with self._db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT org_id FROM org_api_keys WHERE api_key = %(api_key)s",
                    {"api_key": api_key},
                )
                row = cur.fetchone()
                return int(row[0]) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT org_id, api_key, created_at, updated_at, updated_by "
                    "FROM org_api_keys ORDER BY org_id ASC"
                )
                return cur.fetchall()

    def get_by_org_id(self, org_id: int) -> dict[str, Any] | None:
        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT org_id, api_key, created_at, updated_at, updated_by "
                    "FROM org_api_keys WHERE org_id = %(org_id)s",
                    {"org_id": org_id},
                )
                return cur.fetchone()

    def upsert(self, *, org_id: int, api_key: str, updated_by: str) -> None:
        with self._db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO org_api_keys (org_id, api_key, updated_by) "
                    "VALUES (%(org_id)s, %(api_key)s, %(updated_by)s) "
                    "ON CONFLICT (org_id) DO UPDATE SET "
                    "  api_key = EXCLUDED.api_key, "
                    "  updated_at = now(), "
                    "  updated_by = EXCLUDED.updated_by",
                    {"org_id": org_id, "api_key": api_key, "updated_by": updated_by},
                )
                conn.commit()
