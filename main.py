from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.v1.search import router as search_router
from app.api.v1.admin import router as admin_router
from app.api.v1.lookups import router as lookups_router
from app.core.config import Settings
from app.core.rate_limiter import TokenBucketRateLimiter
from app.database.db_manager import PostgresManager
from app.database.migrations import ensure_schema


ORG_API_KEY_SCHEME = "OrgApiKey"
ADMIN_API_KEY_SCHEME = "AdminApiKey"


def _apply_additional_security_requirements(openapi_schema: dict) -> None:
    """Adjust OpenAPI security for Swagger UX.

    We want Swagger's "Authorize" to include X-Admin-Key for endpoints that may
    require it (master X-API-Key mode), without forcing X-Admin-Key for normal org keys.

    OpenAPI supports alternatives via a list of SecurityRequirement objects:
      - {OrgApiKey: []} OR
      - {OrgApiKey: [], AdminApiKey: []}
    """

    paths = openapi_schema.get("paths", {})

    def patch_operation(path: str, method: str) -> None:
        op = paths.get(path, {}).get(method)
        if not isinstance(op, dict):
            return
        op["security"] = [
            {ORG_API_KEY_SCHEME: []},
            {ORG_API_KEY_SCHEME: [], ADMIN_API_KEY_SCHEME: []},
        ]

    patch_operation("/api/v1/employees/search", "get")
    patch_operation("/api/v1/lookups/{kind}", "get")
    patch_operation("/api/v1/lookups/{kind}/{item_id}", "get")
def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )

        settings = Settings.from_env()
        db = PostgresManager(settings.database_url)
        db.open()
        ensure_schema(db)

        limiter = TokenBucketRateLimiter(
            capacity=settings.rate_limit_burst,
            refill_rate_per_sec=settings.rate_limit_rpm / 60.0,
        )

        app.state.settings = settings
        app.state.db = db
        app.state.limiter = limiter

        logging.getLogger(__name__).info("App started")
        try:
            yield
        finally:
            db.close()
            logging.getLogger(__name__).info("App stopped")

    app = FastAPI(
        title="HR Employee Search Microservice",
        version="0.1.0",
        description=(
            "High-performance multi-tenant employee search service.\n\n"
            "Authentication: pass `X-API-Key` on every request."
        ),
        openapi_tags=[
            {"name": "health", "description": "Service health checks"},
            {"name": "employees", "description": "Employee search endpoints"},
            {"name": "lookups", "description": "Lookup endpoints for related entities"},
            {"name": "admin", "description": "Admin endpoints (org display config)"},
        ],
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict:
        return {"status": "ok"}

    app.include_router(search_router)
    app.include_router(lookups_router)
    app.include_router(admin_router)

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        _apply_additional_security_requirements(schema)
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app


app = create_app()
