from __future__ import annotations

from typing import Any

from psycopg import sql
from psycopg.rows import dict_row

from app.database.db_manager import PostgresManager
from app.models.employee import Employee


class EmployeeRepository:
    def __init__(self, db: PostgresManager) -> None:
        self._db = db

    def search(
        self,
        *,
        org_id: int,
        allowed_columns: list[str],
        q: str | None,
        employment_status: str | None,
        location: str | None,
        company: str | None,
        department: str | None,
        job_title: str | None,
        limit: int,
        last_id: int | None,
    ) -> list[dict[str, Any]]:
        safe_cols = [c for c in allowed_columns if c in Employee.ALLOWED_COLUMNS]
        if not safe_cols:
            safe_cols = ["id"]

        fields = sql.SQL(", ").join(sql.Identifier(c) for c in safe_cols)

        where_parts: list[sql.Composable] = [sql.SQL("organization_id = %(org_id)s")]
        params: dict[str, Any] = {"org_id": org_id, "limit": limit}

        if last_id is not None:
            where_parts.append(sql.SQL("id > %(last_id)s"))
            params["last_id"] = last_id

        if employment_status:
            where_parts.append(sql.SQL("employment_status = %(employment_status)s"))
            params["employment_status"] = employment_status

        if location:
            where_parts.append(sql.SQL("location = %(location)s"))
            params["location"] = location

        if company:
            where_parts.append(sql.SQL("company = %(company)s"))
            params["company"] = company

        if department:
            where_parts.append(sql.SQL("department = %(department)s"))
            params["department"] = department

        if job_title:
            where_parts.append(sql.SQL("job_title = %(job_title)s"))
            params["job_title"] = job_title

        if q:
            where_parts.append(sql.SQL("(name ILIKE %(q)s OR email ILIKE %(q)s)"))
            params["q"] = f"%{q}%"

        query = sql.SQL(
            "SELECT {fields} "
            "FROM {table} "
            "WHERE {where} "
            "ORDER BY id ASC "
            "LIMIT %(limit)s"
        ).format(
            fields=fields,
            table=sql.Identifier(Employee.TABLE),
            where=sql.SQL(" AND ").join(where_parts),
        )

        with self._db.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return rows
