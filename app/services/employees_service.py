from __future__ import annotations

from typing import Any

from app.database.db_manager import PostgresManager
from app.models.employee import Employee
from app.repositories.employee_repo import EmployeeRepository


class EmployeesService:
    def __init__(self, db: PostgresManager) -> None:
        self._repo = EmployeeRepository(db)

    @staticmethod
    def _sanitize_allowed_columns(columns: list[str]) -> list[str]:
        sanitized = [c for c in columns if c in Employee.ALLOWED_COLUMNS]
        seen: set[str] = set()
        result: list[str] = []
        for c in sanitized:
            if c not in seen:
                seen.add(c)
                result.append(c)

        if "id" in result:
            result.remove("id")
        result.insert(0, "id")
        return result

    def get_employee(
        self,
        *,
        org_id: int | None,
        allowed_columns: list[str],
        employee_id: int,
    ) -> dict[str, Any] | None:
        allowed = self._sanitize_allowed_columns(allowed_columns)
        return self._repo.get_by_id(org_id=org_id, allowed_columns=allowed, employee_id=employee_id)

    def create_employee(self, *, org_id: int, payload: dict[str, Any]) -> int:
        return self._repo.create(org_id=org_id, payload=payload)

    def update_employee(self, *, org_id: int, employee_id: int, patch: dict[str, Any]) -> bool:
        return self._repo.update(org_id=org_id, employee_id=employee_id, patch=patch)

    def delete_employee(self, *, org_id: int, employee_id: int) -> bool:
        return self._repo.delete(org_id=org_id, employee_id=employee_id)

    @staticmethod
    def full_projection_columns() -> list[str]:
        # Deterministic ordering for stable API responses.
        return [
            "id",
            "organization_id",
            "name",
            "email",
            "phone",
            "company_id",
            "department_id",
            "job_title_id",
            "location_id",
            "employment_status_id",
            "job_title",
            "department",
            "location",
            "company",
            "employment_status",
            "created_at",
        ]
