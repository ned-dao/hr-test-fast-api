from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from psycopg import connect


def _load_org_allowed_columns_from_db(database_url: str) -> dict[int, list[str]]:
    """Load org allowed columns from Postgres.

    Expected schema:
      org_display_config(org_id int primary key, allowed_columns jsonb)
    """

    org_allowed_columns: dict[int, list[str]] = {}

    # One-shot connection is fine here because it's only used during startup
    # if the env var isn't provided.
    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT org_id, allowed_columns FROM org_display_config")
            rows = cur.fetchall()

    for org_id, allowed_columns in rows:
        try:
            org_id_int = int(org_id)
        except (TypeError, ValueError):
            continue

        # Depending on driver settings, jsonb may arrive as Python list or string.
        if isinstance(allowed_columns, str):
            try:
                allowed_columns = json.loads(allowed_columns)
            except json.JSONDecodeError:
                continue

        if isinstance(allowed_columns, list) and all(isinstance(c, str) for c in allowed_columns):
            org_allowed_columns[org_id_int] = allowed_columns

    return org_allowed_columns


def _load_api_keys_from_db(database_url: str) -> dict[str, int]:
    """Load API keys from Postgres.

    Expected schema:
      org_api_keys(org_id int primary key, api_key text unique)

    Returns mapping: api_key -> org_id
    """

    api_keys: dict[str, int] = {}

    with connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT org_id, api_key FROM org_api_keys")
            rows = cur.fetchall()

    for org_id, api_key in rows:
        if not api_key:
            continue
        try:
            org_id_int = int(org_id)
        except (TypeError, ValueError):
            continue
        api_keys[str(api_key)] = org_id_int

    return api_keys


def _parse_json_env(var_name: str) -> Any | None:
    raw = os.getenv(var_name)
    if not raw:
        return None
    return json.loads(raw)


@dataclass(frozen=True)
class Settings:
    database_url: str

    rate_limit_rpm: int
    rate_limit_burst: int

    admin_api_key: str
    master_api_key: str

    api_keys: dict[str, int]
    api_keys_from_env: bool
    org_allowed_columns: dict[int, list[str]]
    org_allowed_columns_from_env: bool

    @staticmethod
    def from_env() -> "Settings":
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hr_search")

        rate_limit_rpm = int(os.getenv("RATE_LIMIT_RPM", "120"))
        rate_limit_burst = int(os.getenv("RATE_LIMIT_BURST", "60"))

        admin_api_key = os.getenv("ADMIN_API_KEY", "admin")
        master_api_key = os.getenv("MASTER_API_KEY", "master")

        api_keys_from_env = False
        api_keys = _parse_json_env("API_KEYS_JSON")
        if isinstance(api_keys, dict) and api_keys:
            # Expect {"api-key-string": org_id_int}
            api_keys = {str(k): int(v) for k, v in api_keys.items()}
            api_keys_from_env = True
        else:
            try:
                api_keys = _load_api_keys_from_db(database_url)
            except Exception:
                api_keys = {}

        if not api_keys:
            api_keys = {"demo-org-1": 1, "demo-org-2": 2}

        raw_allowed = _parse_json_env("ORG_ALLOWED_COLUMNS_JSON")
        org_allowed_columns: dict[int, list[str]] = {}
        org_allowed_columns_from_env = False
        if isinstance(raw_allowed, dict):
            for key, cols in raw_allowed.items():
                try:
                    org_id = int(key)
                except (TypeError, ValueError):
                    continue
                if isinstance(cols, list) and all(isinstance(c, str) for c in cols):
                    org_allowed_columns[org_id] = cols
            if org_allowed_columns:
                org_allowed_columns_from_env = True

        if not org_allowed_columns:
            try:
                org_allowed_columns = _load_org_allowed_columns_from_db(database_url)
            except Exception:
                org_allowed_columns = {}

        if not org_allowed_columns:
            org_allowed_columns = {
                1: [
                    "id",
                    "organization_id",
                    "name",
                    "email",
                    "job_title",
                    "department",
                    "location",
                    "employment_status",
                ],
                2: [
                    "id",
                    "organization_id",
                    "name",
                    "phone",
                    "department",
                    "location",
                    "employment_status",
                ],
            }

        return Settings(
            database_url=database_url,
            rate_limit_rpm=rate_limit_rpm,
            rate_limit_burst=rate_limit_burst,
            admin_api_key=admin_api_key,
            master_api_key=master_api_key,
            api_keys=api_keys,
            api_keys_from_env=api_keys_from_env,
            org_allowed_columns=org_allowed_columns,
            org_allowed_columns_from_env=org_allowed_columns_from_env,
        )
