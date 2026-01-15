-- PostgreSQL schema + indexes for HR Employee Search

CREATE TABLE IF NOT EXISTS employees (
  id BIGSERIAL PRIMARY KEY,
  organization_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  job_title TEXT,
  department TEXT,
  location TEXT,
  company TEXT,
  employment_status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-organization display config (dynamic projection)
CREATE TABLE IF NOT EXISTS org_display_config (
  org_id INTEGER PRIMARY KEY,
  allowed_columns JSONB NOT NULL,
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
