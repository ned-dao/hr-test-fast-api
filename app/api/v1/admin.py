from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from pydantic import BaseModel, Field, ConfigDict

from app.core.security import AdminContext, get_admin_context
from app.services.org_config_service import OrgConfigService


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def get_org_config_service(request: Request) -> OrgConfigService:
    return OrgConfigService(request.app.state.db)


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
