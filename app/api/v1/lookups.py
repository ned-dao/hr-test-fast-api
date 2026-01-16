from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request

from app.api.v1.schemas import LookupListResponse
from app.core.rate_limiter import enforce_rate_limit
from app.core.security import OrgContext
from app.services.lookups_service import LookupsService


router = APIRouter(prefix="/api/v1/lookups", tags=["lookups"])


def get_lookups_service(request: Request) -> LookupsService:
    return LookupsService(request.app.state.db)


LookupKind = Literal[
    "companies",
    "departments",
    "job_titles",
    "locations",
    "employment_statuses",
]


@router.get("/{kind}", response_model=LookupListResponse)
def list_lookup_values(
    kind: LookupKind,
    request: Request,
    org: OrgContext = Depends(enforce_rate_limit),
    service: LookupsService = Depends(get_lookups_service),
    q: str | None = None,
    limit: int = 100,
    org_id: int | None = None,
) -> LookupListResponse:
    effective_org_id = org.org_id
    if org.org_id == 0:
        # Master key: allow overriding org scope; None means "all orgs".
        effective_org_id = org_id

    items = service.list_values(kind=kind, org_id=effective_org_id, q=q, limit=limit)
    return LookupListResponse(
        kind=kind,
        org_id=0 if effective_org_id is None else int(effective_org_id),
        count=len(items),
        items=items,
    )
