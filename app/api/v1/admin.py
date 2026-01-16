from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from pydantic import BaseModel, Field, ConfigDict

from app.core.security import AdminContext, get_admin_context
from app.services.api_keys_service import ApiKeysService
from app.services.org_config_service import OrgConfigService


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def get_org_config_service(request: Request) -> OrgConfigService:
    return OrgConfigService(request.app.state.db)


def get_api_keys_service(request: Request) -> ApiKeysService:
    return ApiKeysService(request.app.state.db)


class OrgDisplayConfigUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Org 2 - show phone, hide email",
                    "value": {
                        "allowed_columns": [
                            "id",
                            "organization_id",
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
