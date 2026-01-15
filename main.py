from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.search import router as search_router
from app.api.v1.admin import router as admin_router
from app.core.config import Settings
from app.core.rate_limiter import TokenBucketRateLimiter
from app.database.db_manager import PostgresManager
from app.database.migrations import ensure_schema
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
    app.include_router(admin_router)
    return app


app = create_app()
