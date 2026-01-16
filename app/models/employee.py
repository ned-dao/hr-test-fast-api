from __future__ import annotations


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
