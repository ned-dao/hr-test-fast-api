from __future__ import annotations

from typing import Any

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

    def list_values(
        self,
        *,
        kind: str,
        org_id: int,
        q: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        table = self._TABLES.get(kind)
        if not table:
            raise ValueError(f"Unknown lookup kind: {kind}")

        where_parts: list[sql.Composable] = [sql.SQL("org_id = %(org_id)s")]
        params: dict[str, Any] = {"org_id": org_id, "limit": limit}

        if q:
            where_parts.append(sql.SQL("name ILIKE %(q)s"))
            params["q"] = f"%{q}%"

        query = sql.SQL(
            "SELECT id, name "
            "FROM {table} "
            "WHERE {where} "
            "ORDER BY name ASC "
            "LIMIT %(limit)s"
        ).format(
            table=sql.Identifier(table),
            where=sql.SQL(" AND ").join(where_parts),
        )

        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                return cur.fetchall()
