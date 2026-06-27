# SupplyShield AI — Architecture Documentation

## System Overview

SupplyShield AI is a production-grade B2B SaaS platform for supply chain risk intelligence. It provides end-to-end visibility into multi-tier supplier networks and proactively surfaces climate, geopolitical, operational, and dependency risks.

---

## Architecture Decisions

### Backend: FastAPI + Python 3.12
**Decision:** FastAPI over Django/Flask  
**Rationale:** Async-first, automatic OpenAPI documentation, Pydantic validation, and native support for high-concurrency workloads from concurrent API calls to external risk feeds.

### Primary Database: PostgreSQL 16
**Decision:** PostgreSQL with SQLAlchemy 2.0 async engine  
**Rationale:** JSONB for flexible risk event data, strong ACID guarantees for financial/audit data, mature ecosystem. Async engine prevents blocking on I/O-heavy operations.

### Graph Database: Neo4j (with NetworkX fallback)
**Decision:** Neo4j as primary, NetworkX + PostgreSQL as fallback  
**Rationale:** Supply chains are fundamentally graph problems. Cypher queries for multi-hop dependency traversal are more expressive than SQL JOINs. NetworkX fallback ensures the platform runs without Neo4j for teams that can't operate it.

**Key graph relationships:**
```
(Supplier)-[:SUPPLIES_TO]->(Supplier)
(Supplier)-[:DEPENDS_ON]->(Material)
(Supplier)-[:OPERATES]->(Facility)
(Facility)-[:PRODUCES]->(Product)
(Material)-[:COMPONENT_OF]->(Product)
```

### Risk Scoring: Explainable Weighted Composite
**Decision:** No black-box ML models in Phase 1-3  
**Rationale:** Enterprise procurement and risk teams require auditability. Every score includes contributing factors, data sources, and weight breakdown. ML models can be layered on top in Phase 4+.

**Default weights:**
| Category      | Weight |
|--------------|--------|
| Climate       | 25%    |
| Geopolitical  | 25%    |
| Operational   | 20%    |
| Logistics     | 15%    |
| Dependency    | 15%    |

### Frontend: React + TypeScript + Vite
**Decision:** Vite build tooling, TanStack Query for server state  
**Rationale:** Vite's fast HMR improves developer velocity. TanStack Query handles caching, background refetching, and loading states cleanly without boilerplate. D3.js for the graph visualization (canvas-level control needed for 500+ node graphs).

### Authentication: JWT with refresh tokens
**Decision:** Stateless JWT, not sessions  
**Rationale:** Enables horizontal scaling without sticky sessions. Access tokens (60min) + refresh tokens (7 days) balance security with UX. All tokens signed with HS256 using an environment-injected secret.

### Background Jobs: Celery + Redis
**Decision:** Celery Beat for scheduled ingestion, Redis as broker  
**Rationale:** Risk event ingestion (NOAA, GDELT, OpenWeather) must run on a schedule independent of HTTP requests. Celery provides retry logic, dead-letter queues, and monitoring.

---

## Data Flow

```
External APIs (NOAA/GDELT/OpenWeather)
         │
         ▼
   Celery Beat (scheduler)
         │
         ▼
   Ingestion Tasks (ETL)
         │
         ▼
   risk_events table (PostgreSQL)
         │
         ▼
   Risk Scoring Engine
   (on-demand, per supplier)
         │
         ├──▶ contributing_factors (explainable)
         ├──▶ risk_scores table
         └──▶ Alert generation (threshold breach)
                    │
                    ▼
              Notification channels
              (Dashboard / Email / Slack)
```

---

## Database Schema

### Core Tables
- `organizations` — tenant isolation root
- `users` — authentication + RBAC roles
- `audit_logs` — immutable action trail

### Supply Chain Tables
- `suppliers` — supplier master records with geo, tier, status
- `materials` — material/component catalog
- `supplier_materials` — supplier↔material junction (includes sole_source flag)
- `facilities` — physical locations per supplier
- `supply_relationships` — directed edges: from_supplier SUPPLIES_TO to_supplier

### Risk Tables
- `risk_events` — ingested external events (NOAA, GDELT, etc.)
- `risk_scores` — computed composite scores with full explainability
- `alerts` — early warning alerts with lifecycle tracking
- `alert_status_history` — immutable audit trail of status changes

---

## Multi-Tenancy

Every table containing business data includes `organization_id`. All API queries filter by the authenticated user's `organization_id`, enforced at the service layer. Users cannot access another organization's data.

---

## RBAC Permission Matrix

| Permission           | Admin | Risk Analyst | Procurement Mgr | Executive Viewer |
|---------------------|-------|-------------|-----------------|-----------------|
| suppliers:read       | ✓     | ✓           | ✓               | ✓               |
| suppliers:write      | ✓     | ✓           | ✓               |                 |
| suppliers:delete     | ✓     |             |                 |                 |
| risk:read            | ✓     | ✓           | ✓               | ✓               |
| risk:write           | ✓     | ✓           |                 |                 |
| alerts:read          | ✓     | ✓           | ✓               | ✓               |
| alerts:write         | ✓     | ✓           |                 |                 |
| simulator:run        | ✓     | ✓           | ✓               |                 |
| users:write          | ✓     |             |                 |                 |
| organization:manage  | ✓     |             |                 |                 |
| audit:read           | ✓     |             |                 |                 |

---

## API Design

All endpoints follow REST conventions:
- `GET /api/v1/suppliers` — list with filtering + pagination
- `POST /api/v1/suppliers` — create
- `GET /api/v1/suppliers/{id}` — retrieve
- `PATCH /api/v1/suppliers/{id}` — partial update
- `DELETE /api/v1/suppliers/{id}` — soft delete

Authentication: `Authorization: Bearer <access_token>`

Every write endpoint creates an `AuditLog` record with user, action, resource, and timestamp.

---

## Scalability

**Horizontal scaling:** The backend is stateless. Multiple uvicorn workers (or ECS tasks) can run behind a load balancer. Session state lives in JWT tokens; no server-side session store needed.

**Database connection pooling:** SQLAlchemy pool_size=10, max_overflow=20 per instance. At 4 workers per container, 40 active connections max before queuing.

**Graph performance:** For graphs with >10,000 nodes, NetworkX traversal should be replaced with Neo4j Cypher queries. Neo4j's native graph engine handles millions of nodes efficiently.

**Caching:** Redis available for caching graph traversal results and risk scores. TanStack Query handles client-side caching with 30s stale time.

---

## Security Posture

1. **No secrets in source** — all secrets via environment variables
2. **bcrypt password hashing** — cost factor 12 (default)
3. **JWT expiry** — 60-minute access tokens, 7-day refresh
4. **Soft deletes** — data is never hard-deleted; `is_active=False`
5. **Audit trail** — every write action creates an immutable `audit_log` entry
6. **Input validation** — Pydantic schemas validate all incoming data
7. **SQL injection** — impossible via SQLAlchemy parameterized queries
8. **CORS** — restrictive allowlist, configurable per environment
9. **TrustedHost middleware** — rejects requests with unexpected Host headers
