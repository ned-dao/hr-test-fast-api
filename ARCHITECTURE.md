# Design & Architecture Guide
## HR Employee Search Microservice - Senior Backend Engineer

Below is a detailed and optimized design approach for your Senior Backend Engineer technical assignment, adhering to strict constraints on avoiding external libraries and handling large-scale data.

---

## 1. Directory Structure (Project Structure)

For Senior-level requirements, you should organize your source code following **Clean Architecture** principles for easier scalability and maintenance.

```text
hr_search_service/
├── app/
│   ├── core/
│   │   ├── config.py          # System configuration, dynamic columns
│   │   ├── security.py        # Authorization handling, prevent data leaks
│   │   └── rate_limiter.py    # Custom Rate Limiting (Standard Lib only)
│   ├── database/
│   │   └── db_manager.py      # Database connection (using sqlite3 or standard driver)
│   ├── models/
│   │   └── employee.py        # Data schema definitions
│   ├── repositories/          # Data query layer (sharding logic goes here)
│   │   └── employee_repo.py
│   ├── services/              # Business logic for filtering & dynamic columns
│   │   └── search_service.py
│   └── api/
│       └── v1/
│           └── search.py      # FastAPI Routes
├── tests/                     # Unit tests
├── Dockerfile                 # Containerization
├── main.py                    # Entry point
└── README.md                  # Detailed guide
```

---

## 2. Rate Limiter Design (Without External Libraries)

To optimize and ensure thread-safety in Python environments, we use the **Token Bucket** or **Sliding Window** algorithm with `threading.Lock` and `time` from the Standard Library.

### Implementation Concept:

* Use an in-memory `dict` to store `user_id` or `IP` as keys.
* Each key contains information about remaining tokens and the last update time.
* Use `threading.Lock` to ensure consistency when multiple concurrent requests arrive.

### Basic Parameters:

```
rate_limit = 100  # requests per minute
refill_rate = 100 / 60  # tokens per second
max_tokens = 100  # bucket capacity
```

---

## 3. Handling Millions of Records & Performance (Scalability)

To handle millions of users, focus on these techniques:

### 3.1 Database Optimization

#### Indexing
Create B-Tree indexes on frequently filtered columns:
- `organization_id`
- `status`
- `department_id`
- `location_id`

```sql
CREATE INDEX idx_org_status ON employees(organization_id, status);
CREATE INDEX idx_org_department ON employees(organization_id, department_id);
CREATE INDEX idx_org_location ON employees(organization_id, location_id);
```

#### Database Sharding
Since the system serves multiple organizations, implement sharding by `organization_id`. Benefits:
- Data isolation between organizations
- Faster query performance (each shard contains data for a subset of organizations)
- Reduced lock contention

#### Pagination: Keyset Pagination (Seek Method)
Never use `OFFSET`. Instead, use **Keyset Pagination**:

```sql
-- Instead of:
SELECT * FROM employees WHERE org_id = 1 LIMIT 50 OFFSET 1000;

-- Use:
SELECT * FROM employees 
WHERE org_id = 1 AND id > last_seen_id 
LIMIT 50;
```

Benefits:
- Consistent performance regardless of page number
- Avoids full table scan with OFFSET

### 3.2 Dynamic Columns & Data Leak Prevention

To prevent data leaks and support dynamic columns:

#### 1. Config Storage
Store column configuration for each `org_id` as JSON or Dictionary:

```python
ORGANIZATION_CONFIG = {
    1: {
        "name": "Acme Corp",
        "allowed_columns": ["id", "name", "email", "job_title", "department"]
    },
    2: {
        "name": "Tech Startup",
        "allowed_columns": ["id", "name", "phone", "department", "location"]
    }
}
```

#### 2. SQL Projection
In the SQL query, only `SELECT` columns that the organization is allowed to see.

#### 3. Response Mapping
Use a Service layer to map database results to the Response Schema based on configuration, ensuring sensitive fields never appear in the returned JSON.

```python
def build_response(db_row: dict, org_id: int) -> dict:
    """
    Return only columns allowed for this organization
    """
    allowed_columns = ORGANIZATION_CONFIG[org_id]["allowed_columns"]
    return {col: db_row[col] for col in allowed_columns if col in db_row}
```

---

## 4. API Processing Workflow

When a request arrives, the system processes it in the following order:

```
┌─────────────────────────────────────┐
│ 1. Incoming Request                 │
│    (Filter params + API Key/Org ID) │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 2. Rate Limiter                     │
│    (Check request limits)           │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 3. Security Check                   │
│    (Authenticate Org ID)            │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 4. Config Retrieval                 │
│    (Fetch allowed columns for Org)  │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 5. Repository Query                 │
│    (Execute optimized DB query)     │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 6. Response Construction            │
│    (Return only Dynamic Columns)    │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ Response returned to Client         │
└─────────────────────────────────────┘
```

---

## 5. Senior-Level Best Practices

### Logging & Monitoring
Although not required, add Python's basic logging to track errors:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Search query executed with filters: %s", filters)
logger.error("Database connection failed: %s", error)
```

### Graceful Shutdown
Handle database connection closure when container stops:

```python
@app.on_event("shutdown")
async def shutdown_event():
    db.close()
    logger.info("Database connection closed")
```

### Type Hinting
Use comprehensive Python Type Hints for clarity and professionalism:

```python
from typing import List, Dict, Optional

def search_employees(
    org_id: int,
    filters: Dict[str, str],
    limit: int = 50,
    last_id: Optional[int] = None
) -> List[Dict]:
    """
    Search employees with optimized pagination
    """
    pass
```

### OpenAPI Documentation
Leverage FastAPI's automatic Swagger generation but write detailed descriptions for each filter parameter:

```python
from fastapi import Query

@router.get("/search")
async def search(
    org_id: int = Query(..., description="Organization ID"),
    status: str = Query(None, description="Employment status: active, inactive"),
    department: str = Query(None, description="Department name"),
    limit: int = Query(50, description="Results per page (max 100)"),
    last_id: int = Query(None, description="For keyset pagination")
):
    """Search employees with advanced filtering"""
    pass
```

---

## 6. Testing & Validation

### Unit Tests
Focus on testing:
- Rate limiter logic
- Dynamic columns filtering
- Keyset pagination boundaries
- Data isolation between organizations

### Integration Tests
- Database connections
- API endpoints
- End-to-end search workflows

### Performance Tests
- Query response time with 1M+ records
- Concurrent request handling
- Memory usage monitoring

---

## 7. Deployment & Scaling

### Horizontally Scalable
- Stateless API servers (Rate limiter can migrate to Redis later)
- Read replicas for database
- Load balancer in front

### Docker & Kubernetes Ready
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### Database Sharding Strategy
```
Org 1-100 → DB Shard 1
Org 101-200 → DB Shard 2
Org 201-300 → DB Shard 3
...
```

---

## 8. Summary of Advantages

✅ **Multi-tenant isolation:** Each org only sees its own data  
✅ **Dynamic columns:** Flexible configuration, prevents data leaks  
✅ **High performance:** Indexes + Keyset Pagination + Sharding  
✅ **Thread-safe:** Rate limiter uses threading.Lock  
✅ **No external dependencies:** Only Standard Library + FastAPI  
✅ **Production-ready:** Logging, monitoring, graceful shutdown  
✅ **Horizontally scalable:** Ready for Kubernetes, read replicas  

---

## 9. Next Steps

1. **Design Database Schema** with strategic indexes
2. **Implement Rate Limiter** using Token Bucket algorithm
3. **Build Repository Layer** with Keyset Pagination
4. **Write Service Layer** handling Dynamic Columns
5. **Create API Routes** with FastAPI
6. **Write Unit Tests** for each layer
7. **Docker + Deployment** on staging environment
