# hr-test-fast-api

HR Employee Search Microservice (FastAPI + PostgreSQL).

- Detailed docs (EN): [README_EN.md](README_EN.md)
- Architecture guide (EN): [ARCHITECTURE.md](ARCHITECTURE.md)

## Quickstart (Docker)

```bash
docker-compose up -d --build
```

Health check:

```bash
curl http://localhost:8000/healthz
```

Search API (example):

```bash
curl -H "X-API-Key: demo-org-1" "http://localhost:8000/api/v1/employees/search?limit=10&q=an"
```

Run unit tests (inside container):

```bash
docker-compose exec -T api pytest
```

## Notes

- Seed data lives in [scripts/init.sql](scripts/init.sql). Postgres only runs init scripts on a fresh volume.
- If you changed init scripts and want them re-applied: `docker-compose down -v` then `docker-compose up -d --build`.
- Allowed columns can be provided via `ORG_ALLOWED_COLUMNS_JSON`; if missing, the service loads from the `org_display_config` table.
- Admin endpoints use `X-Admin-Key` (required) and support `X-Admin-User` (optional) for audit `updated_by`.
- Master cross-org access: set `MASTER_API_KEY` and call search/lookups with `X-API-Key: <master>` plus `X-Admin-Key`. If `org_id` is omitted, results span all orgs.