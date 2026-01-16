import os

from fastapi.testclient import TestClient

from main import create_app


def test_search_api_returns_only_org_data_and_projected_columns() -> None:
    # Ensure we can run this test in Docker by default.
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search"
    )

    app = create_app()

    with TestClient(app) as client:
        r = client.get(
            "/api/v1/employees/search",
            headers={"X-API-Key": "demo-org-1"},
            params={"limit": 5},
        )

        assert r.status_code == 200
        body = r.json()

        assert body["org_id"] == 1
        assert isinstance(body["items"], list)

        # Expect at least one seeded record for org 1
        assert body["count"] >= 1

        # Multi-tenant isolation: returned rows belong to org 1
        for item in body["items"]:
            assert item.get("organization_id") == 1

        # Dynamic projection: for org 1 config, phone should not be present
        for item in body["items"]:
            assert "phone" not in item


def test_search_api_projection_differs_by_org() -> None:
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search"
    )
    os.environ.setdefault("ADMIN_API_KEY", "admin")

    app = create_app()

    with TestClient(app) as client:
        before = client.get(
            "/api/v1/admin/orgs/2/display-config",
            headers={"X-Admin-Key": "admin"},
        )
        assert before.status_code == 200
        original_allowed = before.json()["allowed_columns"]

        try:
            # Force org2 config to the expected default for this test.
            client.put(
                "/api/v1/admin/orgs/2/display-config",
                headers={"X-Admin-Key": "admin"},
                json={
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
            )

            r = client.get(
                "/api/v1/employees/search",
                headers={"X-API-Key": "demo-org-2"},
                params={"limit": 5},
            )

            assert r.status_code == 200
            body = r.json()

            assert body["org_id"] == 2
            assert body["count"] >= 1

            # Org 2 config includes phone, but does not include email
            for item in body["items"]:
                assert item.get("organization_id") == 2
                assert "phone" in item
                assert "email" not in item
        finally:
            client.put(
                "/api/v1/admin/orgs/2/display-config",
                headers={"X-Admin-Key": "admin"},
                json={"allowed_columns": original_allowed},
            )


def test_admin_update_display_config_applies_to_search_immediately() -> None:
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search"
    )
    os.environ.setdefault("ADMIN_API_KEY", "admin")

    app = create_app()

    with TestClient(app) as client:
        # Snapshot current config so this test is order-independent.
        before = client.get(
            "/api/v1/admin/orgs/2/display-config",
            headers={"X-Admin-Key": "admin"},
        )
        assert before.status_code == 200
        original_allowed = before.json()["allowed_columns"]

        # Update org 2 config: add email, remove phone
        try:
            r = client.put(
                "/api/v1/admin/orgs/2/display-config",
                headers={"X-Admin-Key": "admin"},
                json={
                    "allowed_columns": [
                        "id",
                        "organization_id",
                        "name",
                        "email",
                        "department",
                        "location",
                        "employment_status",
                    ]
                },
            )
            assert r.status_code == 200
            updated = r.json()
            assert updated["org_id"] == 2
            assert updated["updated_by"] == "admin"
            assert "updated_at" in updated
            assert "created_at" in updated

            # Now search as org2 should reflect new projection (email present, phone absent)
            s = client.get(
                "/api/v1/employees/search",
                headers={"X-API-Key": "demo-org-2"},
                params={"limit": 2},
            )
            assert s.status_code == 200
            body = s.json()
            assert body["org_id"] == 2
            assert body["count"] >= 1

            for item in body["items"]:
                assert item.get("organization_id") == 2
                assert "phone" not in item
                assert "email" in item
        finally:
            # Restore original config for other tests.
            client.put(
                "/api/v1/admin/orgs/2/display-config",
                headers={"X-Admin-Key": "admin"},
                json={"allowed_columns": original_allowed},
            )


def test_lookups_endpoint_returns_backfilled_departments() -> None:
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search"
    )

    app = create_app()

    with TestClient(app) as client:
        r = client.get(
            "/api/v1/lookups/departments",
            headers={"X-API-Key": "demo-org-1"},
            params={"limit": 200},
        )

        assert r.status_code == 200
        body = r.json()
        assert body["kind"] == "departments"
        assert body["org_id"] == 1
        assert body["count"] >= 1
        names = {i["name"] for i in body["items"]}
        assert "Engineering" in names


def test_admin_can_export_api_keys_json_and_rotate_org_key() -> None:
    os.environ.setdefault(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search"
    )
    os.environ.setdefault("ADMIN_API_KEY", "admin")
    # Force DB-backed API key lookup for this test (docker-compose may set API_KEYS_JSON).
    os.environ.pop("API_KEYS_JSON", None)

    app = create_app()

    with TestClient(app) as client:
        before = client.get(
            "/api/v1/admin/orgs/1/api-key",
            headers={"X-Admin-Key": "admin"},
        )

        created = False
        if before.status_code == 404:
            # Existing DB volume may not have init.sql re-applied.
            original_key = "demo-org-1"
            r = client.put(
                "/api/v1/admin/orgs/1/api-key",
                headers={"X-Admin-Key": "admin", "X-Admin-User": "pytest"},
                json={"api_key": original_key},
            )
            assert r.status_code == 200
            created = True
        else:
            assert before.status_code == 200
            original_key = before.json()["api_key"]

        try:
            export = client.get(
                "/api/v1/admin/api-keys",
                headers={"X-Admin-Key": "admin"},
            )
            assert export.status_code == 200
            body = export.json()
            assert isinstance(body.get("api_keys"), dict)
            assert isinstance(body.get("api_keys_json"), str)

            rotated = client.put(
                "/api/v1/admin/orgs/1/api-key",
                headers={"X-Admin-Key": "admin", "X-Admin-User": "pytest"},
                json={"api_key": "demo-org-1-rotated"},
            )
            assert rotated.status_code == 200
            assert rotated.json()["updated_by"] == "pytest"

            # New key should authenticate immediately (DB source of truth when API_KEYS_JSON isn't used).
            search = client.get(
                "/api/v1/employees/search",
                headers={"X-API-Key": "demo-org-1-rotated"},
                params={"limit": 1},
            )
            assert search.status_code == 200
            assert search.json()["org_id"] == 1
        finally:
            client.put(
                "/api/v1/admin/orgs/1/api-key",
                headers={"X-Admin-Key": "admin"},
                json={"api_key": original_key},
            )
