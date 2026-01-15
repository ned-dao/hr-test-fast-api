from __future__ import annotations

from app.database.db_manager import PostgresManager


def ensure_schema(db: PostgresManager) -> None:
    """Best-effort schema migration for local/dev.

    This keeps the project runnable even if the Postgres volume already exists
    and init.sql won't re-run.
    """

    statements = [
        # Base table
        """
        CREATE TABLE IF NOT EXISTS org_display_config (
          org_id INTEGER PRIMARY KEY,
          allowed_columns JSONB NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_by TEXT NOT NULL DEFAULT 'system'
        );
        """,
        # Add audit columns if the table existed previously
        "ALTER TABLE org_display_config ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE org_display_config ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE org_display_config ADD COLUMN IF NOT EXISTS updated_by TEXT NOT NULL DEFAULT 'system';",
    ]

    with db.connection() as conn:
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
            conn.commit()
