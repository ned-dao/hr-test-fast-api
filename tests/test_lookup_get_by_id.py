import os

from fastapi.testclient import TestClient

from main import create_app


def test_public_lookup_get_by_id_works_for_org_key() -> None:
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search")

    app = create_app()

    with TestClient(app) as client:
        listed = client.get(
            "/api/v1/lookups/departments",
            headers={"X-API-Key": "demo-org-1"},
            params={"limit": 50},
        )
        assert listed.status_code == 200
        body = listed.json()
        assert body["count"] >= 1
        first = body["items"][0]

        got = client.get(
            f"/api/v1/lookups/departments/{first['id']}",
            headers={"X-API-Key": "demo-org-1"},
        )
        assert got.status_code == 200
        item = got.json()
        assert item["id"] == first["id"]
        assert item["name"] == first["name"]


def test_public_lookup_get_by_id_requires_org_id_in_master_mode() -> None:
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search")
    os.environ.setdefault("MASTER_API_KEY", "master")
    os.environ.setdefault("ADMIN_API_KEY", "admin")

    app = create_app()

    with TestClient(app) as client:
        listed = client.get(
            "/api/v1/lookups/departments",
            headers={"X-API-Key": "master", "X-Admin-Key": "admin"},
            params={"limit": 200},
        )
        assert listed.status_code == 200
        body = listed.json()
        assert body["count"] >= 1

        pick = None
        for it in body["items"]:
            if it.get("org_id") == 1:
                pick = it
                break
        assert pick is not None

        missing_scope = client.get(
            f"/api/v1/lookups/departments/{pick['id']}",
            headers={"X-API-Key": "master", "X-Admin-Key": "admin"},
        )
        assert missing_scope.status_code == 422

        scoped = client.get(
            f"/api/v1/lookups/departments/{pick['id']}",
            headers={"X-API-Key": "master", "X-Admin-Key": "admin"},
            params={"org_id": 1},
        )
        assert scoped.status_code == 200
        item = scoped.json()
        assert item["id"] == pick["id"]
        assert item["name"] == pick["name"]
