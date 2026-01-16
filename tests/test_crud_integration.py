import os
import uuid

from fastapi.testclient import TestClient

from main import create_app


def test_admin_can_crud_lookup_values() -> None:
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search")
    os.environ.setdefault("ADMIN_API_KEY", "admin")

    app = create_app()

    kind = "departments"
    name = f"CRUD-Dept-{uuid.uuid4().hex[:8]}"

    with TestClient(app) as client:
        created = client.post(
            f"/api/v1/admin/orgs/1/lookups/{kind}",
            headers={"X-Admin-Key": "admin", "X-Admin-User": "pytest"},
            json={"name": name},
        )
        assert created.status_code == 200
        body = created.json()
        assert body["org_id"] == 1
        assert body["name"] == name
        item_id = body["id"]

        got = client.get(
            f"/api/v1/admin/orgs/1/lookups/{kind}/{item_id}",
            headers={"X-Admin-Key": "admin"},
        )
        assert got.status_code == 200
        assert got.json()["name"] == name

        updated_name = f"{name}-updated"
        updated = client.put(
            f"/api/v1/admin/orgs/1/lookups/{kind}/{item_id}",
            headers={"X-Admin-Key": "admin", "X-Admin-User": "pytest"},
            json={"name": updated_name},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == updated_name

        deleted = client.delete(
            f"/api/v1/admin/orgs/1/lookups/{kind}/{item_id}",
            headers={"X-Admin-Key": "admin"},
        )
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True

        missing = client.get(
            f"/api/v1/admin/orgs/1/lookups/{kind}/{item_id}",
            headers={"X-Admin-Key": "admin"},
        )
        assert missing.status_code == 404


def test_admin_can_crud_employees_and_org_can_read_by_id() -> None:
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@db:5432/hr_search")
    os.environ.setdefault("ADMIN_API_KEY", "admin")

    app = create_app()

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/admin/orgs/1/employees",
            headers={"X-Admin-Key": "admin", "X-Admin-User": "pytest"},
            json={
                "name": f"CRUD Employee {uuid.uuid4().hex[:8]}",
                "email": "crud.employee@org1.example",
                "department": "Engineering",
                "employment_status": "active",
            },
        )
        assert created.status_code == 200
        employee = created.json()
        employee_id = employee["id"]
        assert employee.get("organization_id") == 1

        # Org can read their employee by id; projection still applies.
        got = client.get(
            f"/api/v1/employees/{employee_id}",
            headers={"X-API-Key": "demo-org-1"},
        )
        assert got.status_code == 200
        got_body = got.json()
        assert got_body["id"] == employee_id
        assert got_body.get("organization_id") == 1

        # Update
        updated = client.patch(
            f"/api/v1/admin/orgs/1/employees/{employee_id}",
            headers={"X-Admin-Key": "admin", "X-Admin-User": "pytest"},
            json={"employment_status": "inactive"},
        )
        assert updated.status_code == 200

        # Delete
        deleted = client.delete(
            f"/api/v1/admin/orgs/1/employees/{employee_id}",
            headers={"X-Admin-Key": "admin"},
        )
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True

        missing = client.get(
            f"/api/v1/employees/{employee_id}",
            headers={"X-API-Key": "demo-org-1"},
        )
        assert missing.status_code == 404
