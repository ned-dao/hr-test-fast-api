from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security.api_key import APIKeyHeader

from app.core.config import Settings
from app.models.employee import Employee
from app.repositories.org_config_repo import OrgConfigRepository
from app.repositories.api_keys_repo import ApiKeysRepository


@dataclass(frozen=True)
class OrgContext:
    org_id: int
    allowed_columns: list[str]


@dataclass(frozen=True)
class AdminContext:
    role: str = "admin"
    actor: str = "admin"


api_key_header = APIKeyHeader(name="X-API-Key", scheme_name="OrgApiKey", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", scheme_name="AdminApiKey", auto_error=False)
admin_user_header = APIKeyHeader(name="X-Admin-User", scheme_name="AdminUser", auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_org_context(
    request: Request,
    x_api_key: str | None = Depends(api_key_header),
) -> OrgContext:
    settings = get_settings(request)

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")

    # Master API key: allows access to any org (or all orgs).
    if x_api_key == settings.master_api_key:
        # Admin-only guard: require a valid X-Admin-Key when using the master API key.
        x_admin_key = request.headers.get("X-Admin-Key")
        if not x_admin_key:
            raise HTTPException(status_code=401, detail="Missing X-Admin-Key for master access")
        if x_admin_key != settings.admin_api_key:
            raise HTTPException(status_code=403, detail="Invalid admin key")

        # For master access, prefer a superset projection and always include organization_id
        # so results are attributable when querying across orgs.
        allowed_columns = ["id", "organization_id", *sorted(Employee.ALLOWED_COLUMNS - {"id", "organization_id"})]
        return OrgContext(org_id=0, allowed_columns=allowed_columns)

    org_id = settings.api_keys.get(x_api_key)
    if not org_id and not settings.api_keys_from_env:
        # When env keys aren't present, treat DB as the source of truth.
        repo = ApiKeysRepository(request.app.state.db)
        org_id = repo.get_org_id_by_api_key(x_api_key)

    if not org_id:
        raise HTTPException(status_code=401, detail="Invalid API key")

    allowed = settings.org_allowed_columns.get(org_id, ["id", "name"])
    if not settings.org_allowed_columns_from_env:
        # When env config isn't present, treat DB as the source of truth.
        repo = OrgConfigRepository(request.app.state.db)
        db_allowed = repo.get_allowed_columns(org_id)
        if db_allowed:
            allowed = db_allowed
    if "id" not in allowed:
        allowed = ["id", *allowed]

    return OrgContext(org_id=org_id, allowed_columns=allowed)


def get_admin_context(
    request: Request,
    x_admin_key: str | None = Security(admin_key_header),
    x_admin_user: str | None = Security(admin_user_header),
) -> AdminContext:
    settings = get_settings(request)

    if not x_admin_key:
        raise HTTPException(status_code=401, detail="Missing X-Admin-Key")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    actor = (x_admin_user or "admin").strip()
    if not actor:
        actor = "admin"
    return AdminContext(actor=actor)
