from __future__ import annotations

from typing import Any

from app.database.db_manager import PostgresManager
from app.models.employee import Employee
from app.repositories.employee_repo import EmployeeRepository


class SearchService:
    def __init__(self, db: PostgresManager) -> None:
        self._repo = EmployeeRepository(db)

    @staticmethod
    def _sanitize_allowed_columns(columns: list[str]) -> list[str]:
        sanitized = [c for c in columns if c in Employee.ALLOWED_COLUMNS]
        # preserve order but de-dup
        seen: set[str] = set()
        result: list[str] = []
        for c in sanitized:
            if c not in seen:
                seen.add(c)
                result.append(c)

        # Force `id` to be the first column for keyset pagination.
        if "id" in result:
            result.remove("id")
        result.insert(0, "id")

        return result

    def search_employees(
        self,
        *,
        org_id: int | None,
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
        allowed = self._sanitize_allowed_columns(allowed_columns)
        return self._repo.search(
            org_id=org_id,
            allowed_columns=allowed,
            q=q,
            employment_status=employment_status,
            location=location,
            company=company,
            department=department,
            job_title=job_title,
            limit=limit,
            last_id=last_id,
        )
