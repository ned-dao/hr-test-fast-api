from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class Employee:
    TABLE = "employees"

    # Only columns in this allow-list can ever be projected into SQL SELECT.
    ALLOWED_COLUMNS: set[str] = {
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
    }


@dataclass(frozen=True)
class EmployeeEntity:
    """
    Full employee row representation (domain/entity layer).

    Note: Many fields are optional because:
    - some orgs may hide them via dynamic projection
    - some values may exist only in legacy (denormalized) columns during migration
    """
    id: int
    organization_id: int
    name: str

    email: str | None
    phone: str | None

    company_id: int | None
    department_id: int | None
    job_title_id: int | None
    location_id: int | None
    employment_status_id: int | None

    # legacy denormalized fields
    job_title: str | None
    department: str | None
    location: str | None
    company: str | None
    employment_status: str | None

    created_at: datetime
