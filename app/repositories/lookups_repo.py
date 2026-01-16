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
