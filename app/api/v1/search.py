from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.schemas import EmployeeOut, EmployeeSearchQuery, EmployeeSearchResponse, ErrorResponse429

from app.core.rate_limiter import enforce_rate_limit
from app.core.security import OrgContext
from app.services.search_service import SearchService
from app.services.employees_service import EmployeesService


router = APIRouter(prefix="/api/v1/employees", tags=["employees"])


def get_search_service(request: Request) -> SearchService:
    return SearchService(request.app.state.db)


def get_employees_service(request: Request) -> EmployeesService:
    return EmployeesService(request.app.state.db)


@router.get(
    "/search",
    response_model=EmployeeSearchResponse,
    response_model_exclude_none=True,
    responses={429: {"model": ErrorResponse429, "description": "Rate limit exceeded"}},
)
def search_employees(
    request: Request,
    org: OrgContext = Depends(enforce_rate_limit),
    service: SearchService = Depends(get_search_service),
    query: EmployeeSearchQuery = Depends(),
) -> EmployeeSearchResponse:
    effective_org_id = org.org_id
    if org.org_id == 0:
        # Master key: allow overriding org scope; None means "all orgs".
        effective_org_id = query.org_id

    items = service.search_employees(
        org_id=effective_org_id,
        allowed_columns=org.allowed_columns,
        q=query.q,
        employment_status=query.employment_status,
        location=query.location,
        company=query.company,
        department=query.department,
        job_title=query.job_title,
        limit=query.limit,
        last_id=query.last_id,
    )

    next_last_id = items[-1]["id"] if items else None

    return EmployeeSearchResponse(
        org_id=0 if effective_org_id is None else int(effective_org_id),
        count=len(items),
        next_last_id=next_last_id,
        items=items,
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeOut,
    response_model_exclude_none=True,
    responses={429: {"model": ErrorResponse429, "description": "Rate limit exceeded"}},
)
def get_employee_by_id(
    employee_id: int,
    request: Request,
    org: OrgContext = Depends(enforce_rate_limit),
    service: EmployeesService = Depends(get_employees_service),
    org_id: int | None = None,
) -> EmployeeOut:
    effective_org_id = org.org_id
    if org.org_id == 0:
        # Master key: allow overriding org scope; None means "all orgs".
        effective_org_id = org_id

    row = service.get_employee(
        org_id=effective_org_id,
        allowed_columns=org.allowed_columns,
        employee_id=employee_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return EmployeeOut(**row)
