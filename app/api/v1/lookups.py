from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.v1.schemas import LookupItem, LookupListResponse
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


@router.get("/{kind}/{item_id}", response_model=LookupItem, response_model_exclude_none=True)
def get_lookup_value(
    kind: LookupKind,
    item_id: int,
    request: Request,
    org: OrgContext = Depends(enforce_rate_limit),
    service: LookupsService = Depends(get_lookups_service),
    org_id: int | None = None,
) -> LookupItem:
    effective_org_id = org.org_id
    if org.org_id == 0:
        # Master key: ids are not globally unique across orgs, so require org_id to disambiguate.
        if org_id is None:
            raise HTTPException(status_code=422, detail="org_id is required for master get-by-id")
        effective_org_id = org_id

    row = service.get_public_value(kind=kind, org_id=int(effective_org_id), item_id=item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Lookup value not found")
    return LookupItem(**row)
