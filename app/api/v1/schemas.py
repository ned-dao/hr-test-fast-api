from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class EmployeeOut(BaseModel):
    """Employee representation.

    Note: Columns are dynamically projected per organization.
    Fields not allowed for the org will be omitted from responses.
    """

    model_config = ConfigDict(extra="ignore")

    id: int = Field(..., description="Employee ID")
    organization_id: int | None = Field(None, description="Organization ID (tenant)")

    name: str | None = Field(None, description="Full name")
    email: str | None = Field(None, description="Email")
    phone: str | None = Field(None, description="Phone number")

    company_id: int | None = Field(None, description="Company ID (normalized)")
    department_id: int | None = Field(None, description="Department ID (normalized)")
    job_title_id: int | None = Field(None, description="Job title ID (normalized)")
    location_id: int | None = Field(None, description="Location ID (normalized)")
    employment_status_id: int | None = Field(None, description="Employment status ID (normalized)")

    job_title: str | None = Field(None, description="Job title")
    department: str | None = Field(None, description="Department")
    location: str | None = Field(None, description="Location")
    company: str | None = Field(None, description="Company")

    employment_status: str | None = Field(None, description="Employment status")


class EmployeeSearchQuery(BaseModel):
    """Query params for the search endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Search by name/email",
                    "value": {"q": "an", "limit": 10},
                },
                {
                    "summary": "Filter + keyset pagination",
                    "value": {"department": "Engineering", "employment_status": "active", "limit": 50, "last_id": 1000},
                },
            ]
        }
    )

    q: str | None = Field(None, description="Partial match on name or email")
    employment_status: str | None = Field(None, description="Employment status")
    location: str | None = Field(None, description="Location")
    company: str | None = Field(None, description="Company")
    department: str | None = Field(None, description="Department")
    job_title: str | None = Field(None, description="Job title")

    limit: int = Field(50, ge=1, le=100, description="Page size (max 100)")
    last_id: int | None = Field(None, ge=0, description="Keyset pagination cursor (id)")

    org_id: int | None = Field(
        None,
        ge=0,
        description="(Master key only) Scope the search to a specific org. If omitted, returns results across all orgs.",
    )


class EmployeeSearchResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Org 1 example (email visible)",
                    "value": {
                        "org_id": 1,
                        "count": 2,
                        "next_last_id": 2,
                        "items": [
                            {
                                "id": 1,
                                "organization_id": 1,
                                "name": "An Nguyen",
                                "email": "an.nguyen@org1.example",
                                "job_title": "Backend Engineer",
                                "department": "Engineering",
                                "location": "Hanoi",
                                "employment_status": "active",
                            },
                            {
                                "id": 2,
                                "organization_id": 1,
                                "name": "Binh Tran",
                                "email": "binh.tran@org1.example",
                                "job_title": "QA Engineer",
                                "department": "Engineering",
                                "location": "Hanoi",
                                "employment_status": "active",
                            },
                        ],
                    },
                },
                {
                    "summary": "Org 2 example (phone visible, email hidden)",
                    "value": {
                        "org_id": 2,
                        "count": 2,
                        "next_last_id": 6,
                        "items": [
                            {
                                "id": 5,
                                "organization_id": 2,
                                "name": "Evan Lee",
                                "phone": "+12025550101",
                                "department": "Support",
                                "location": "Singapore",
                                "employment_status": "active",
                            },
                            {
                                "id": 6,
                                "organization_id": 2,
                                "name": "Fiona Chen",
                                "phone": "+12025550102",
                                "department": "Data",
                                "location": "Singapore",
                                "employment_status": "active",
                            },
                        ],
                    },
                },
            ]
        }
    )

    org_id: int = Field(..., description="Resolved org_id from X-API-Key")
    count: int = Field(..., description="Number of items returned")
    next_last_id: int | None = Field(None, description="Cursor value for the next page")
    items: list[EmployeeOut] = Field(default_factory=list, description="Search results")


class RateLimitError(BaseModel):
    message: Literal["Rate limit exceeded"] = Field("Rate limit exceeded")
    retry_after_seconds: float | None = Field(None, description="Seconds until next request should succeed")


class ErrorResponse429(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Rate limit exceeded",
                    "value": {
                        "detail": {"message": "Rate limit exceeded", "retry_after_seconds": 0.5}
                    },
                }
            ]
        }
    )

    detail: RateLimitError


class LookupItem(BaseModel):
    id: int
    name: str
    org_id: int | None = Field(None, description="Org ID for this lookup value (present when querying across all orgs)")


class LookupListResponse(BaseModel):
    kind: str = Field(..., description="Lookup kind (companies, departments, job_titles, locations, employment_statuses)")
    org_id: int = Field(..., description="Resolved org_id from X-API-Key")
    count: int
    items: list[LookupItem] = Field(default_factory=list)
