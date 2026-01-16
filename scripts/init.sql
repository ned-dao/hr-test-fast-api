-- PostgreSQL schema + indexes for HR Employee Search

-- Lookup tables (normalized relationships)
CREATE TABLE IF NOT EXISTS companies (
  id BIGSERIAL PRIMARY KEY,
  org_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NOT NULL DEFAULT 'system',
  UNIQUE (org_id, name)
);

CREATE TABLE IF NOT EXISTS departments (
  id BIGSERIAL PRIMARY KEY,
  org_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NOT NULL DEFAULT 'system',
  UNIQUE (org_id, name)
);

CREATE TABLE IF NOT EXISTS job_titles (
  id BIGSERIAL PRIMARY KEY,
  org_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NOT NULL DEFAULT 'system',
  UNIQUE (org_id, name)
);

CREATE TABLE IF NOT EXISTS locations (
  id BIGSERIAL PRIMARY KEY,
  org_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NOT NULL DEFAULT 'system',
  UNIQUE (org_id, name)
);

CREATE TABLE IF NOT EXISTS employment_statuses (
  id BIGSERIAL PRIMARY KEY,
  org_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NOT NULL DEFAULT 'system',
  UNIQUE (org_id, name)
);

CREATE TABLE IF NOT EXISTS employees (
  id BIGSERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  email TEXT,
  phone TEXT,

  -- Normalized relationships (preferred)
  company_id BIGINT,
  department_id BIGINT,
  job_title_id BIGINT,
  location_id BIGINT,
  employment_status_id BIGINT,

  -- Legacy denormalized columns (kept for compatibility / migration)
  job_title TEXT,
  department TEXT,
  location TEXT,
  company TEXT,
  employment_status TEXT NOT NULL DEFAULT 'active',

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT fk_employees_company FOREIGN KEY (company_id) REFERENCES companies(id),
  CONSTRAINT fk_employees_department FOREIGN KEY (department_id) REFERENCES departments(id),
  CONSTRAINT fk_employees_job_title FOREIGN KEY (job_title_id) REFERENCES job_titles(id),
  CONSTRAINT fk_employees_location FOREIGN KEY (location_id) REFERENCES locations(id),
  CONSTRAINT fk_employees_employment_status FOREIGN KEY (employment_status_id) REFERENCES employment_statuses(id)
);

-- Per-organization display config (dynamic projection)
CREATE TABLE IF NOT EXISTS org_display_config (
  org_id INTEGER PRIMARY KEY,
  allowed_columns JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NOT NULL DEFAULT 'system'
);

-- Per-organization API keys (auth)
CREATE TABLE IF NOT EXISTS org_api_keys (
  org_id INTEGER PRIMARY KEY,
  api_key TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by TEXT NOT NULL DEFAULT 'system'
);

-- Composite indexes for common multi-tenant filtering
CREATE INDEX IF NOT EXISTS idx_employees_org_id_id ON employees(organization_id, id);
CREATE INDEX IF NOT EXISTS idx_employees_org_status_id ON employees(organization_id, employment_status, id);
CREATE INDEX IF NOT EXISTS idx_employees_org_department_id ON employees(organization_id, department, id);
CREATE INDEX IF NOT EXISTS idx_employees_org_location_id ON employees(organization_id, location, id);
CREATE INDEX IF NOT EXISTS idx_employees_org_company_id ON employees(organization_id, company, id);

-- Lookup table indexes
CREATE INDEX IF NOT EXISTS idx_companies_org_name ON companies(org_id, name);
CREATE INDEX IF NOT EXISTS idx_departments_org_name ON departments(org_id, name);
CREATE INDEX IF NOT EXISTS idx_job_titles_org_name ON job_titles(org_id, name);
CREATE INDEX IF NOT EXISTS idx_locations_org_name ON locations(org_id, name);
CREATE INDEX IF NOT EXISTS idx_employment_statuses_org_name ON employment_statuses(org_id, name);

-- Employee FK indexes
CREATE INDEX IF NOT EXISTS idx_employees_org_company_fk_id ON employees(organization_id, company_id, id);
CREATE INDEX IF NOT EXISTS idx_employees_org_department_fk_id ON employees(organization_id, department_id, id);
CREATE INDEX IF NOT EXISTS idx_employees_org_job_title_fk_id ON employees(organization_id, job_title_id, id);
CREATE INDEX IF NOT EXISTS idx_employees_org_location_fk_id ON employees(organization_id, location_id, id);
CREATE INDEX IF NOT EXISTS idx_employees_org_employment_status_fk_id ON employees(organization_id, employment_status_id, id);

-- Text search helpers (simple ILIKE usage will still benefit from org/id indexes;
-- production may add GIN trigram indexes or full-text, depending on constraints).

-- Seed data (for demo/testing)
INSERT INTO org_display_config (org_id, allowed_columns) VALUES
  (
    1,
    '["id","organization_id","name","email","job_title","department","location","employment_status"]'::jsonb
  ),
  (
    2,
    '["id","organization_id","name","phone","department","location","employment_status"]'::jsonb
  )
ON CONFLICT (org_id) DO UPDATE SET
  allowed_columns = EXCLUDED.allowed_columns,
  updated_at = now(),
  updated_by = 'system';

INSERT INTO org_api_keys (org_id, api_key) VALUES
  (1, 'demo-org-1'),
  (2, 'demo-org-2')
ON CONFLICT (org_id) DO UPDATE SET
  api_key = EXCLUDED.api_key,
  updated_at = now(),
  updated_by = 'system';

INSERT INTO employees (
  organization_id,
  name,
  email,
  phone,
  job_title,
  department,
  location,
  company,
  employment_status
) VALUES
  (1, 'An Nguyen', 'an.nguyen@org1.example', '+84900000001', 'Backend Engineer', 'Engineering', 'Hanoi', 'Org1', 'active'),
  (1, 'Binh Tran', 'binh.tran@org1.example', '+84900000002', 'QA Engineer', 'Engineering', 'Hanoi', 'Org1', 'active'),
  (1, 'Chi Le', 'chi.le@org1.example', '+84900000003', 'HR Specialist', 'HR', 'HCMC', 'Org1', 'inactive'),
  (1, 'Dung Pham', 'dung.pham@org1.example', '+84900000004', 'Product Manager', 'Product', 'HCMC', 'Org1', 'active'),
  (2, 'Evan Lee', 'evan.lee@org2.example', '+12025550101', 'Support Engineer', 'Support', 'Singapore', 'Org2', 'active'),
  (2, 'Fiona Chen', 'fiona.chen@org2.example', '+12025550102', 'Data Analyst', 'Data', 'Singapore', 'Org2', 'active'),
  (2, 'George Kim', 'george.kim@org2.example', '+12025550103', 'Sales Lead', 'Sales', 'Tokyo', 'Org2', 'active'),
  (2, 'Hana Park', 'hana.park@org2.example', '+12025550104', 'HR Manager', 'HR', 'Tokyo', 'Org2', 'inactive');

-- Backfill lookup tables + foreign keys (useful for first-time init)
INSERT INTO companies (org_id, name)
SELECT DISTINCT organization_id, company
FROM employees
WHERE company IS NOT NULL AND company <> ''
ON CONFLICT DO NOTHING;

INSERT INTO departments (org_id, name)
SELECT DISTINCT organization_id, department
FROM employees
WHERE department IS NOT NULL AND department <> ''
ON CONFLICT DO NOTHING;

INSERT INTO job_titles (org_id, name)
SELECT DISTINCT organization_id, job_title
FROM employees
WHERE job_title IS NOT NULL AND job_title <> ''
ON CONFLICT DO NOTHING;

INSERT INTO locations (org_id, name)
SELECT DISTINCT organization_id, location
FROM employees
WHERE location IS NOT NULL AND location <> ''
ON CONFLICT DO NOTHING;

INSERT INTO employment_statuses (org_id, name)
SELECT DISTINCT organization_id, employment_status
FROM employees
WHERE employment_status IS NOT NULL AND employment_status <> ''
ON CONFLICT DO NOTHING;

UPDATE employees e
SET company_id = c.id
FROM companies c
WHERE c.org_id = e.organization_id AND c.name = e.company AND e.company_id IS NULL;

UPDATE employees e
SET department_id = d.id
FROM departments d
WHERE d.org_id = e.organization_id AND d.name = e.department AND e.department_id IS NULL;

UPDATE employees e
SET job_title_id = j.id
FROM job_titles j
WHERE j.org_id = e.organization_id AND j.name = e.job_title AND e.job_title_id IS NULL;

UPDATE employees e
SET location_id = l.id
FROM locations l
WHERE l.org_id = e.organization_id AND l.name = e.location AND e.location_id IS NULL;

UPDATE employees e
SET employment_status_id = s.id
FROM employment_statuses s
WHERE s.org_id = e.organization_id AND s.name = e.employment_status AND e.employment_status_id IS NULL;
