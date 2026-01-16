from __future__ import annotations

from typing import Any

from psycopg.errors import UniqueViolation
from psycopg import sql
from psycopg.rows import dict_row

from app.database.db_manager import PostgresManager


class LookupsRepository:
    _TABLES: dict[str, str] = {
        "companies": "companies",
        "departments": "departments",
        "job_titles": "job_titles",
        "locations": "locations",
        "employment_statuses": "employment_statuses",
    }

    def __init__(self, db: PostgresManager) -> None:
        self._db = db

    def get_value(
        self,
        *,
        kind: str,
        org_id: int,
        item_id: int,
    ) -> dict[str, Any] | None:
        table = self._TABLES.get(kind)
        if not table:
            raise ValueError(f"Unknown lookup kind: {kind}")

        query = sql.SQL(
            "SELECT id, name, org_id, created_at, updated_at, updated_by "
            "FROM {table} "
            "WHERE org_id = %(org_id)s AND id = %(id)s"
        ).format(table=sql.Identifier(table))

        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, {"org_id": org_id, "id": item_id})
                return cur.fetchone()

    def get_public_value(
        self,
        *,
        kind: str,
        org_id: int,
        item_id: int,
    ) -> dict[str, Any] | None:
        table = self._TABLES.get(kind)
        if not table:
            raise ValueError(f"Unknown lookup kind: {kind}")

        query = sql.SQL(
            "SELECT id, name, org_id "
            "FROM {table} "
            "WHERE org_id = %(org_id)s AND id = %(id)s"
        ).format(table=sql.Identifier(table))

        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, {"org_id": org_id, "id": item_id})
                return cur.fetchone()

    def create_value(
        self,
        *,
        kind: str,
        org_id: int,
        name: str,
        updated_by: str,
    ) -> dict[str, Any]:
        table = self._TABLES.get(kind)
        if not table:
            raise ValueError(f"Unknown lookup kind: {kind}")

        query = sql.SQL(
            "INSERT INTO {table} (org_id, name, updated_by) "
            "VALUES (%(org_id)s, %(name)s, %(updated_by)s) "
            "RETURNING id, name, org_id, created_at, updated_at, updated_by"
        ).format(table=sql.Identifier(table))

        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                try:
                    cur.execute(query, {"org_id": org_id, "name": name, "updated_by": updated_by})
                except UniqueViolation:
                    raise
                row = cur.fetchone()
                conn.commit()
                if not row:
                    raise RuntimeError("Failed to create lookup value")
                return row

    def update_value(
        self,
        *,
        kind: str,
        org_id: int,
        item_id: int,
        name: str,
        updated_by: str,
    ) -> dict[str, Any] | None:
        table = self._TABLES.get(kind)
        if not table:
            raise ValueError(f"Unknown lookup kind: {kind}")

        query = sql.SQL(
            "UPDATE {table} "
            "SET name = %(name)s, updated_at = now(), updated_by = %(updated_by)s "
            "WHERE org_id = %(org_id)s AND id = %(id)s "
            "RETURNING id, name, org_id, created_at, updated_at, updated_by"
        ).format(table=sql.Identifier(table))

        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                try:
                    cur.execute(
                        query,
                        {"org_id": org_id, "id": item_id, "name": name, "updated_by": updated_by},
                    )
                except UniqueViolation:
                    raise
                row = cur.fetchone()
                conn.commit()
                return row

    def delete_value(self, *, kind: str, org_id: int, item_id: int) -> bool:
        table = self._TABLES.get(kind)
        if not table:
            raise ValueError(f"Unknown lookup kind: {kind}")

        query = sql.SQL(
            "DELETE FROM {table} WHERE org_id = %(org_id)s AND id = %(id)s"
        ).format(table=sql.Identifier(table))

        with self._db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, {"org_id": org_id, "id": item_id})
                deleted = cur.rowcount > 0
                conn.commit()
                return deleted

    def list_values(
        self,
        *,
        kind: str,
        org_id: int | None,
        q: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        table = self._TABLES.get(kind)
        if not table:
            raise ValueError(f"Unknown lookup kind: {kind}")

        where_parts: list[sql.Composable] = []
        params: dict[str, Any] = {"limit": limit}

        if org_id is not None:
            where_parts.append(sql.SQL("org_id = %(org_id)s"))
            params["org_id"] = org_id

        if q:
            where_parts.append(sql.SQL("name ILIKE %(q)s"))
            params["q"] = f"%{q}%"

        where_sql = sql.SQL("TRUE") if not where_parts else sql.SQL(" AND ").join(where_parts)

        query = sql.SQL(
            "SELECT id, name, org_id "
            "FROM {table} "
            "WHERE {where} "
            "ORDER BY name ASC "
            "LIMIT %(limit)s"
        ).format(
            table=sql.Identifier(table),
            where=where_sql,
        )

        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                return cur.fetchall()
