import os

from fastapi.testclient import TestClient

from main import create_app


def test_openapi_includes_admin_key_for_search_and_lookups() -> None:
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search")

    app = create_app()

    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    schemes = schema["components"]["securitySchemes"]
    assert "OrgApiKey" in schemes
    assert "AdminApiKey" in schemes

    search_sec = schema["paths"]["/api/v1/employees/search"]["get"].get("security")
    assert {"OrgApiKey": []} in search_sec
    assert {"OrgApiKey": [], "AdminApiKey": []} in search_sec

    lookups_sec = schema["paths"]["/api/v1/lookups/{kind}"]["get"].get("security")
    assert {"OrgApiKey": []} in lookups_sec
    assert {"OrgApiKey": [], "AdminApiKey": []} in lookups_sec

    lookup_one = schema["paths"]["/api/v1/lookups/{kind}/{item_id}"]["get"].get("security")
    assert {"OrgApiKey": []} in lookup_one
    assert {"OrgApiKey": [], "AdminApiKey": []} in lookup_one
