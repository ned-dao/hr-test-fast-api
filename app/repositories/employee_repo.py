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

        select_map: dict[str, sql.Composable] = {
            "id": sql.SQL("e.id"),
            "organization_id": sql.SQL("e.organization_id"),
            "name": sql.SQL("e.name"),
            "email": sql.SQL("e.email"),
            "phone": sql.SQL("e.phone"),
            "created_at": sql.SQL("e.created_at"),
            "company_id": sql.SQL("e.company_id"),
            "department_id": sql.SQL("e.department_id"),
            "job_title_id": sql.SQL("e.job_title_id"),
            "location_id": sql.SQL("e.location_id"),
            "employment_status_id": sql.SQL("e.employment_status_id"),
            # Backward-compatible projections: prefer normalized name when present
            "company": sql.SQL("COALESCE(c.name, e.company) AS company"),
            "department": sql.SQL("COALESCE(d.name, e.department) AS department"),
            "job_title": sql.SQL("COALESCE(j.name, e.job_title) AS job_title"),
            "location": sql.SQL("COALESCE(l.name, e.location) AS location"),
            "employment_status": sql.SQL("COALESCE(s.name, e.employment_status) AS employment_status"),
        }

        fields = sql.SQL(", ").join(select_map[c] for c in safe_cols if c in select_map)

        where_parts: list[sql.Composable] = [sql.SQL("e.organization_id = %(org_id)s")]
        params: dict[str, Any] = {"org_id": org_id, "limit": limit}

        if last_id is not None:
            where_parts.append(sql.SQL("e.id > %(last_id)s"))
            params["last_id"] = last_id

        if employment_status:
            where_parts.append(sql.SQL("COALESCE(s.name, e.employment_status) = %(employment_status)s"))
            params["employment_status"] = employment_status

        if location:
            where_parts.append(sql.SQL("COALESCE(l.name, e.location) = %(location)s"))
            params["location"] = location

        if company:
            where_parts.append(sql.SQL("COALESCE(c.name, e.company) = %(company)s"))
            params["company"] = company

        if department:
            where_parts.append(sql.SQL("COALESCE(d.name, e.department) = %(department)s"))
            params["department"] = department

        if job_title:
            where_parts.append(sql.SQL("COALESCE(j.name, e.job_title) = %(job_title)s"))
            params["job_title"] = job_title

        if q:
            where_parts.append(sql.SQL("(e.name ILIKE %(q)s OR e.email ILIKE %(q)s)"))
            params["q"] = f"%{q}%"

        query = sql.SQL(
            "SELECT {fields} "
            "FROM {table} e "
            "LEFT JOIN companies c ON c.id = e.company_id AND c.org_id = e.organization_id "
            "LEFT JOIN departments d ON d.id = e.department_id AND d.org_id = e.organization_id "
            "LEFT JOIN job_titles j ON j.id = e.job_title_id AND j.org_id = e.organization_id "
            "LEFT JOIN locations l ON l.id = e.location_id AND l.org_id = e.organization_id "
            "LEFT JOIN employment_statuses s ON s.id = e.employment_status_id AND s.org_id = e.organization_id "
            "WHERE {where} "
            "ORDER BY e.id ASC "
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
