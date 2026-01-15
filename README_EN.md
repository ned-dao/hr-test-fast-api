# HR Employee Search Microservice
### Senior Backend Engineer Technical Assignment

---

## 1. Introduction

This repository contains a **high-performance, multi-tenant Employee Search Microservice** designed for large HR platforms serving multiple organizations.

The system is optimized for:
- Searching **millions of employee records**
- Strict **cross-organization data isolation**
- Dynamic, organization-level output configuration
- Thread-safe, custom-built **rate limiting without external libraries**

Built with **FastAPI**, the service is production-grade, horizontally scalable, and designed following Clean Architecture principles.

---

## 2. Business Requirements

| Requirement | Description |
|------------|----------|
| Multi-tenant | Each organization can only access its own employees |
| Dynamic fields | Each organization defines which columns are visible |
| High performance | Must handle millions of records |
| Data privacy | No leaking of hidden columns |
| Rate limit | API abuse prevention |
| Scalability | Ready for sharding and read replicas |

---

## 3. Core Features

### 3.1 Optimized Search API

- Search filters:
  - employment_status
  - location
  - company
  - department
  - job_title
- Full-text partial search on employee name & email
- Supports keyset pagination for large datasets

### 3.2 Organization-Based Dynamic Projection

Each organization has its own `display_config`:

| org_id | allowed_columns |
|-------|----------------|
| 1 | id, name, email, job_title |
| 2 | id, name, phone, department |

The system dynamically builds SELECT clauses based on this configuration.

### 3.3 Custom Rate Limiter (Standard Library Only)

- Algorithm: Token Bucket
- Thread-safe with `threading.Lock`
- Uses `time.time()` for refill calculation
- Per-organization & per-IP bucket isolation

### 3.4 Massive Dataset Optimization

| Technique | Purpose |
|---------|--------|
| Composite indexes | Fast multi-column filtering |
| Keyset pagination | Avoid OFFSET performance degradation |
| Projection | Only required columns are fetched |
| Read replicas | Ready for scaling reads |

---

## 4. Architecture

### Clean Architecture Layers

```
app/
├── api/            # FastAPI routes
├── services/       # Business logic
├── repositories/   # Database access layer
├── core/           # Shared components (rate limiter, config)
└── models/         # Domain entities
```

| Layer | Responsibility |
|-----|----------|
| API | Validation, routing |
| Service | Search logic, field mapping |
| Repository | SQL queries, optimization |
| Core | Rate limiting, caching |

---

## 5. Data Flow

```
Client Request
↓
Rate Limiter
↓
API Layer
↓
Service Layer
↓
Repository Layer
↓
Database
```

---

## 6. Technology Stack

- Python 3.11
- FastAPI
- PostgreSQL
- Docker / Docker Compose
- Pytest

---

## 7. Running the Project

### Prerequisites

- Docker
- Docker Compose

### Commands

```bash
docker-compose up --build
docker exec -it <container_id> pytest
```

---

## 8. Production Readiness

* Horizontal scaling ready
* Redis plug-in ready for rate limiter
* Compatible with Kubernetes
* Supports sharded databases
* Designed for API Gateway integration

---

## 9. Author



