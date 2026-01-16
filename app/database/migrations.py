from __future__ import annotations

from app.database.db_manager import PostgresManager


def ensure_schema(db: PostgresManager) -> None:
        """Best-effort schema migration for local/dev.

        This keeps the project runnable even if the Postgres volume already exists
        and init.sql won't re-run.
        """

        statements = [
                # Employees: rename organization_id -> org_id (idempotent, supports existing volumes)
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'employees' AND column_name = 'organization_id'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'employees' AND column_name = 'org_id'
                    ) THEN
                        ALTER TABLE employees RENAME COLUMN organization_id TO org_id;
                    ELSIF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'employees' AND column_name = 'organization_id'
                    ) AND EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'employees' AND column_name = 'org_id'
                    ) THEN
                        -- If both exist (manual migrations), keep org_id as source of truth.
                        UPDATE employees SET org_id = COALESCE(org_id, organization_id);
                    END IF;
                END $$;
                """,

                # If org_display_config still contains old column name, normalize it.
                """
                UPDATE org_display_config
                SET allowed_columns = (
                    SELECT jsonb_agg(CASE WHEN v = 'organization_id' THEN 'org_id' ELSE v END)
                    FROM jsonb_array_elements_text(allowed_columns) AS v
                )
                WHERE allowed_columns @> '["organization_id"]'::jsonb;
                """,

                # Per-organization display config
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

                # Per-organization API keys
                """
                CREATE TABLE IF NOT EXISTS org_api_keys (
                    org_id INTEGER PRIMARY KEY,
                    api_key TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_by TEXT NOT NULL DEFAULT 'system'
                );
                """,
                "ALTER TABLE org_api_keys ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();",
                "ALTER TABLE org_api_keys ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();",
                "ALTER TABLE org_api_keys ADD COLUMN IF NOT EXISTS updated_by TEXT NOT NULL DEFAULT 'system';",

                # Lookup tables
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id BIGSERIAL PRIMARY KEY,
                    org_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_by TEXT NOT NULL DEFAULT 'system',
                    UNIQUE (org_id, name)
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS departments (
                    id BIGSERIAL PRIMARY KEY,
                    org_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_by TEXT NOT NULL DEFAULT 'system',
                    UNIQUE (org_id, name)
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS job_titles (
                    id BIGSERIAL PRIMARY KEY,
                    org_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_by TEXT NOT NULL DEFAULT 'system',
                    UNIQUE (org_id, name)
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS locations (
                    id BIGSERIAL PRIMARY KEY,
                    org_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_by TEXT NOT NULL DEFAULT 'system',
                    UNIQUE (org_id, name)
                );
                """,
                """
                CREATE TABLE IF NOT EXISTS employment_statuses (
                    id BIGSERIAL PRIMARY KEY,
                    org_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_by TEXT NOT NULL DEFAULT 'system',
                    UNIQUE (org_id, name)
                );
                """,

                # Employee FK columns (keep legacy string columns as-is)
                "ALTER TABLE employees ADD COLUMN IF NOT EXISTS company_id BIGINT;",
                "ALTER TABLE employees ADD COLUMN IF NOT EXISTS department_id BIGINT;",
                "ALTER TABLE employees ADD COLUMN IF NOT EXISTS job_title_id BIGINT;",
                "ALTER TABLE employees ADD COLUMN IF NOT EXISTS location_id BIGINT;",
                "ALTER TABLE employees ADD COLUMN IF NOT EXISTS employment_status_id BIGINT;",

                # Indexes
                "CREATE INDEX IF NOT EXISTS idx_companies_org_name ON companies(org_id, name);",
                "CREATE INDEX IF NOT EXISTS idx_departments_org_name ON departments(org_id, name);",
                "CREATE INDEX IF NOT EXISTS idx_job_titles_org_name ON job_titles(org_id, name);",
                "CREATE INDEX IF NOT EXISTS idx_locations_org_name ON locations(org_id, name);",
                "CREATE INDEX IF NOT EXISTS idx_employment_statuses_org_name ON employment_statuses(org_id, name);",
                "CREATE INDEX IF NOT EXISTS idx_employees_org_company_fk_id ON employees(org_id, company_id, id);",
                "CREATE INDEX IF NOT EXISTS idx_employees_org_department_fk_id ON employees(org_id, department_id, id);",
                "CREATE INDEX IF NOT EXISTS idx_employees_org_job_title_fk_id ON employees(org_id, job_title_id, id);",
                "CREATE INDEX IF NOT EXISTS idx_employees_org_location_fk_id ON employees(org_id, location_id, id);",
                "CREATE INDEX IF NOT EXISTS idx_employees_org_employment_status_fk_id ON employees(org_id, employment_status_id, id);",

                # Foreign keys (Postgres doesn't support ADD CONSTRAINT IF NOT EXISTS)
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_employees_company') THEN
                        ALTER TABLE employees ADD CONSTRAINT fk_employees_company FOREIGN KEY (company_id) REFERENCES companies(id);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_employees_department') THEN
                        ALTER TABLE employees ADD CONSTRAINT fk_employees_department FOREIGN KEY (department_id) REFERENCES departments(id);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_employees_job_title') THEN
                        ALTER TABLE employees ADD CONSTRAINT fk_employees_job_title FOREIGN KEY (job_title_id) REFERENCES job_titles(id);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_employees_location') THEN
                        ALTER TABLE employees ADD CONSTRAINT fk_employees_location FOREIGN KEY (location_id) REFERENCES locations(id);
                    END IF;
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_employees_employment_status') THEN
                        ALTER TABLE employees ADD CONSTRAINT fk_employees_employment_status FOREIGN KEY (employment_status_id) REFERENCES employment_statuses(id);
                    END IF;
                END $$;
                """,

                # Backfill lookup tables from legacy employee text columns
                """
                INSERT INTO companies (org_id, name)
                SELECT DISTINCT org_id, company
                FROM employees
                WHERE company IS NOT NULL AND company <> ''
                ON CONFLICT DO NOTHING;
                """,
                """
                INSERT INTO departments (org_id, name)
                SELECT DISTINCT org_id, department
                FROM employees
                WHERE department IS NOT NULL AND department <> ''
                ON CONFLICT DO NOTHING;
                """,
                """
                INSERT INTO job_titles (org_id, name)
                SELECT DISTINCT org_id, job_title
                FROM employees
                WHERE job_title IS NOT NULL AND job_title <> ''
                ON CONFLICT DO NOTHING;
                """,
                """
                INSERT INTO locations (org_id, name)
                SELECT DISTINCT org_id, location
                FROM employees
                WHERE location IS NOT NULL AND location <> ''
                ON CONFLICT DO NOTHING;
                """,
                """
                INSERT INTO employment_statuses (org_id, name)
                SELECT DISTINCT org_id, employment_status
                FROM employees
                WHERE employment_status IS NOT NULL AND employment_status <> ''
                ON CONFLICT DO NOTHING;
                """,

                # Backfill employee FK ids
                """
                UPDATE employees e
                SET company_id = c.id
                FROM companies c
                WHERE c.org_id = e.org_id AND c.name = e.company AND e.company_id IS NULL;
                """,
                """
                UPDATE employees e
                SET department_id = d.id
                FROM departments d
                WHERE d.org_id = e.org_id AND d.name = e.department AND e.department_id IS NULL;
                """,
                """
                UPDATE employees e
                SET job_title_id = j.id
                FROM job_titles j
                WHERE j.org_id = e.org_id AND j.name = e.job_title AND e.job_title_id IS NULL;
                """,
                """
                UPDATE employees e
                SET location_id = l.id
                FROM locations l
                WHERE l.org_id = e.org_id AND l.name = e.location AND e.location_id IS NULL;
                """,
                """
                UPDATE employees e
                SET employment_status_id = s.id
                FROM employment_statuses s
                WHERE s.org_id = e.org_id AND s.name = e.employment_status AND e.employment_status_id IS NULL;
                """,
        ]

        with db.connection() as conn:
                with conn.cursor() as cur:
                        for stmt in statements:
                                cur.execute(stmt)
                        conn.commit()
