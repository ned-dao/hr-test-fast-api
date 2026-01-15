from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.v1.schemas import EmployeeSearchQuery, EmployeeSearchResponse, ErrorResponse429

from app.core.rate_limiter import enforce_rate_limit
from app.core.security import OrgContext
from app.services.search_service import SearchService


router = APIRouter(prefix="/api/v1/employees", tags=["employees"])


def get_search_service(request: Request) -> SearchService:
    return SearchService(request.app.state.db)


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
    items = service.search_employees(
        org_id=org.org_id,
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
        org_id=org.org_id,
        count=len(items),
        next_last_id=next_last_id,
        items=items,
    )
