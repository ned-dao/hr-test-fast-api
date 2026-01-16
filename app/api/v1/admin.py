from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from pydantic import BaseModel, Field, ConfigDict

from app.api.v1.schemas import (
    EmployeeCreate,
    EmployeeOut,
    EmployeeSearchResponse,
    EmployeeUpdate,
    LookupListResponse,
    LookupUpsert,
)
from app.core.security import AdminContext, get_admin_context
from app.services.employees_service import EmployeesService
from app.services.api_keys_service import ApiKeysService
from app.services.lookups_service import LookupsService
from app.services.org_config_service import OrgConfigService
from app.services.search_service import SearchService


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def get_org_config_service(request: Request) -> OrgConfigService:
    return OrgConfigService(request.app.state.db)


def get_api_keys_service(request: Request) -> ApiKeysService:
    return ApiKeysService(request.app.state.db)


def get_lookups_service(request: Request) -> LookupsService:
    return LookupsService(request.app.state.db)


def get_employees_service(request: Request) -> EmployeesService:
    return EmployeesService(request.app.state.db)


def get_search_service(request: Request) -> SearchService:
    return SearchService(request.app.state.db)


class OrgDisplayConfigUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Org 2 - show phone, hide email",
                    "value": {
                        "allowed_columns": [
                            "id",
                            "org_id",
                            "name",
                            "phone",
                            "department",
                            "location",
                            "employment_status",
                        ]
                    },
                }
            ]
        }
    )

    allowed_columns: list[str] = Field(..., min_length=1, description="Allowed columns for this org")


class OrgDisplayConfigResponse(BaseModel):
    org_id: int
    allowed_columns: list[str]
    created_at: datetime
    updated_at: datetime
    updated_by: str


class OrgApiKeyResponse(BaseModel):
    org_id: int
    api_key: str
    created_at: datetime
    updated_at: datetime
    updated_by: str


class OrgApiKeyUpdate(BaseModel):
    api_key: str = Field(..., min_length=1, description="API key string for this org")


class ApiKeysExportResponse(BaseModel):
    api_keys: dict[str, int] = Field(
        ..., description="Mapping of api_key -> org_id (same shape as API_KEYS_JSON)"
    )
    api_keys_json: str = Field(
        ..., description="JSON string you can paste into API_KEYS_JSON"
    )


class LookupAdminItem(BaseModel):
    id: int
    org_id: int
    name: str
    created_at: datetime
    updated_at: datetime
    updated_by: str


LookupKind = Literal[
    "companies",
    "departments",
    "job_titles",
    "locations",
    "employment_statuses",
]


@router.get("/orgs/{org_id}/display-config", response_model=OrgDisplayConfigResponse)
def get_display_config(
    org_id: int,
    _: AdminContext = Security(get_admin_context),
    service: OrgConfigService = Depends(get_org_config_service),
) -> OrgDisplayConfigResponse:
    cfg = service.get_config(org_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Org config not found")
    return OrgDisplayConfigResponse(
        org_id=cfg.org_id,
        allowed_columns=cfg.allowed_columns,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
        updated_by=cfg.updated_by,
    )


@router.put("/orgs/{org_id}/display-config", response_model=OrgDisplayConfigResponse)
def update_display_config(
    org_id: int,
    payload: OrgDisplayConfigUpdate,
    admin: AdminContext = Security(get_admin_context),
    service: OrgConfigService = Depends(get_org_config_service),
) -> OrgDisplayConfigResponse:
    cols = service.set_allowed_columns(org_id, payload.allowed_columns, updated_by=admin.actor)
    cfg = service.get_config(org_id)
    if cfg is None:
        raise HTTPException(status_code=500, detail="Failed to read updated config")
    return OrgDisplayConfigResponse(
        org_id=cfg.org_id,
        allowed_columns=cols,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
        updated_by=cfg.updated_by,
    )


@router.get("/display-configs", response_model=list[OrgDisplayConfigResponse])
def list_display_configs(
    _: AdminContext = Security(get_admin_context),
    service: OrgConfigService = Depends(get_org_config_service),
) -> list[OrgDisplayConfigResponse]:
    configs = service.list_all()
    return [
        OrgDisplayConfigResponse(
            org_id=c.org_id,
            allowed_columns=c.allowed_columns,
            created_at=c.created_at,
            updated_at=c.updated_at,
            updated_by=c.updated_by,
        )
        for c in configs
    ]


@router.delete("/orgs/{org_id}/display-config")
def delete_display_config(
    org_id: int,
    _: AdminContext = Security(get_admin_context),
    service: OrgConfigService = Depends(get_org_config_service),
) -> dict:
    deleted = service.delete(org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Org config not found")
    return {"deleted": True}


@router.get("/api-keys", response_model=ApiKeysExportResponse)
def export_api_keys(
    request: Request,
    _: AdminContext = Security(get_admin_context),
    service: ApiKeysService = Depends(get_api_keys_service),
) -> ApiKeysExportResponse:
    rows = service.list_all()

    # API_KEYS_JSON expects {"api_key": org_id}
    mapping: dict[str, int] = {str(r["api_key"]): int(r["org_id"]) for r in rows}
    # Include env/configured keys as a fallback (useful when DB volume existed before init.sql changes).
    for api_key, org_id in getattr(request.app.state, "settings").api_keys.items():
        mapping.setdefault(str(api_key), int(org_id))
    # Deterministic output for copy/paste
    items = sorted(mapping.items(), key=lambda kv: kv[1])
    api_keys_json = "{" + ",".join([f"\"{k}\":{v}" for k, v in items]) + "}"
    return ApiKeysExportResponse(api_keys=mapping, api_keys_json=api_keys_json)


@router.get("/org-api-keys", response_model=list[OrgApiKeyResponse])
def list_org_api_keys(
    _: AdminContext = Security(get_admin_context),
    service: ApiKeysService = Depends(get_api_keys_service),
) -> list[OrgApiKeyResponse]:
    rows = service.list_all()
    return [OrgApiKeyResponse(**r) for r in rows]


@router.get("/orgs/{org_id}/api-key", response_model=OrgApiKeyResponse)
def get_org_api_key(
    org_id: int,
    _: AdminContext = Security(get_admin_context),
    service: ApiKeysService = Depends(get_api_keys_service),
) -> OrgApiKeyResponse:
    row = service.get_by_org_id(org_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Org API key not found")
    return OrgApiKeyResponse(**row)


@router.put("/orgs/{org_id}/api-key", response_model=OrgApiKeyResponse)
def upsert_org_api_key(
    org_id: int,
    payload: OrgApiKeyUpdate,
    admin: AdminContext = Security(get_admin_context),
    service: ApiKeysService = Depends(get_api_keys_service),
) -> OrgApiKeyResponse:
    try:
        service.upsert(org_id=org_id, api_key=payload.api_key, updated_by=admin.actor)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    row = service.get_by_org_id(org_id)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to read updated API key")
    return OrgApiKeyResponse(**row)


@router.delete("/orgs/{org_id}/api-key")
def delete_org_api_key(
    org_id: int,
    _: AdminContext = Security(get_admin_context),
    service: ApiKeysService = Depends(get_api_keys_service),
) -> dict:
    deleted = service.delete(org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Org API key not found")
    return {"deleted": True}


@router.post("/orgs/{org_id}/employees", response_model=EmployeeOut, response_model_exclude_none=True)
def admin_create_employee(
    org_id: int,
    payload: EmployeeCreate,
    admin: AdminContext = Security(get_admin_context),
    service: EmployeesService = Depends(get_employees_service),
) -> EmployeeOut:
    try:
        employee_id = service.create_employee(org_id=org_id, payload=payload.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    row = service.get_employee(
        org_id=org_id,
        allowed_columns=EmployeesService.full_projection_columns(),
        employee_id=employee_id,
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to read created employee")
    return EmployeeOut(**row)


@router.get(
    "/orgs/{org_id}/employees/{employee_id}",
    response_model=EmployeeOut,
    response_model_exclude_none=True,
)
def admin_get_employee(
    org_id: int,
    employee_id: int,
    _: AdminContext = Security(get_admin_context),
    service: EmployeesService = Depends(get_employees_service),
) -> EmployeeOut:
    row = service.get_employee(
        org_id=org_id,
        allowed_columns=EmployeesService.full_projection_columns(),
        employee_id=employee_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return EmployeeOut(**row)


@router.patch(
    "/orgs/{org_id}/employees/{employee_id}",
    response_model=EmployeeOut,
    response_model_exclude_none=True,
)
def admin_update_employee(
    org_id: int,
    employee_id: int,
    payload: EmployeeUpdate,
    admin: AdminContext = Security(get_admin_context),
    service: EmployeesService = Depends(get_employees_service),
) -> EmployeeOut:
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=422, detail="No fields to update")

    updated = service.update_employee(org_id=org_id, employee_id=employee_id, patch=patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Employee not found")

    row = service.get_employee(
        org_id=org_id,
        allowed_columns=EmployeesService.full_projection_columns(),
        employee_id=employee_id,
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to read updated employee")
    return EmployeeOut(**row)


@router.delete("/orgs/{org_id}/employees/{employee_id}")
def admin_delete_employee(
    org_id: int,
    employee_id: int,
    _: AdminContext = Security(get_admin_context),
    service: EmployeesService = Depends(get_employees_service),
) -> dict:
    deleted = service.delete_employee(org_id=org_id, employee_id=employee_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"deleted": True}


@router.get(
    "/orgs/{org_id}/employees",
    response_model=EmployeeSearchResponse,
    response_model_exclude_none=True,
)
def admin_list_employees(
    org_id: int,
    _: AdminContext = Security(get_admin_context),
    service: SearchService = Depends(get_search_service),
    q: str | None = None,
    employment_status: str | None = None,
    location: str | None = None,
    company: str | None = None,
    department: str | None = None,
    job_title: str | None = None,
    limit: int = 50,
    last_id: int | None = None,
) -> EmployeeSearchResponse:
    items = service.search_employees(
        org_id=org_id,
        allowed_columns=EmployeesService.full_projection_columns(),
        q=q,
        employment_status=employment_status,
        location=location,
        company=company,
        department=department,
        job_title=job_title,
        limit=limit,
        last_id=last_id,
    )
    next_last_id = items[-1]["id"] if items else None
    return EmployeeSearchResponse(
        org_id=org_id,
        count=len(items),
        next_last_id=next_last_id,
        items=items,
    )


@router.get("/orgs/{org_id}/lookups/{kind}", response_model=LookupListResponse)
def admin_list_lookup_values(
    org_id: int,
    kind: LookupKind,
    _: AdminContext = Security(get_admin_context),
    service: LookupsService = Depends(get_lookups_service),
    q: str | None = None,
    limit: int = 200,
) -> LookupListResponse:
    try:
        items = service.list_values(kind=kind, org_id=org_id, q=q, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return LookupListResponse(kind=kind, org_id=org_id, count=len(items), items=items)


@router.post("/orgs/{org_id}/lookups/{kind}", response_model=LookupAdminItem)
def admin_create_lookup_value(
    org_id: int,
    kind: LookupKind,
    payload: LookupUpsert,
    admin: AdminContext = Security(get_admin_context),
    service: LookupsService = Depends(get_lookups_service),
) -> LookupAdminItem:
    try:
        row = service.create_value(kind=kind, org_id=org_id, name=payload.name, updated_by=admin.actor)
    except ValueError as e:
        msg = str(e)
        if "already exists" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=422, detail=msg)
    return LookupAdminItem(**row)


@router.get("/orgs/{org_id}/lookups/{kind}/{item_id}", response_model=LookupAdminItem)
def admin_get_lookup_value(
    org_id: int,
    kind: LookupKind,
    item_id: int,
    _: AdminContext = Security(get_admin_context),
    service: LookupsService = Depends(get_lookups_service),
) -> LookupAdminItem:
    row = service.get_value(kind=kind, org_id=org_id, item_id=item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Lookup value not found")
    return LookupAdminItem(**row)


@router.put("/orgs/{org_id}/lookups/{kind}/{item_id}", response_model=LookupAdminItem)
def admin_update_lookup_value(
    org_id: int,
    kind: LookupKind,
    item_id: int,
    payload: LookupUpsert,
    admin: AdminContext = Security(get_admin_context),
    service: LookupsService = Depends(get_lookups_service),
) -> LookupAdminItem:
    try:
        row = service.update_value(kind=kind, org_id=org_id, item_id=item_id, name=payload.name, updated_by=admin.actor)
    except ValueError as e:
        msg = str(e)
        if "already exists" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=422, detail=msg)
    if row is None:
        raise HTTPException(status_code=404, detail="Lookup value not found")
    return LookupAdminItem(**row)


@router.delete("/orgs/{org_id}/lookups/{kind}/{item_id}")
def admin_delete_lookup_value(
    org_id: int,
    kind: LookupKind,
    item_id: int,
    _: AdminContext = Security(get_admin_context),
    service: LookupsService = Depends(get_lookups_service),
) -> dict:
    deleted = service.delete_value(kind=kind, org_id=org_id, item_id=item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lookup value not found")
    return {"deleted": True}
