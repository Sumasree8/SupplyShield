# SupplyShield AI

**Enterprise Supply Chain Dependency & Risk Intelligence Platform**

---

## What It Does

SupplyShield AI gives procurement, risk, and operations teams complete visibility into their multi-tier supply chain and proactive intelligence on risks before they cascade.

### Core Capabilities

| Capability | Description |
|-----------|-------------|
| **Supply Chain Graph** | Interactive visualization of supplier tiers, materials, and relationships |
| **Risk Scoring** | Explainable composite scores across climate, geopolitical, operational, logistics, and dependency dimensions |
| **Disruption Simulator** | Model cascading impacts when a supplier goes offline |
| **Alternative Supplier Recommendations** | Explainable ranked candidates by geography, industry, tier, status, and risk |
| **Early Warning Alerts** | Threshold and trend-based alerts with full lifecycle management |
| **External Intelligence** | Live ingestion from NOAA, GDELT, OpenWeather |
| **RBAC** | Four roles: Admin, Risk Analyst, Procurement Manager, Executive Viewer |
| **Audit Trail** | Every action is logged with user, timestamp, and detail |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI 0.111, Python 3.12 |
| Primary DB | PostgreSQL 16 |
| Graph DB | Neo4j 5 (NetworkX fallback) |
| Job Queue | Celery + Redis |
| Frontend | React 18, TypeScript, Vite |
| Graph Viz | D3.js v7 |
| Charts | Recharts |
| Auth | JWT (python-jose) |
| Containers | Docker + Docker Compose |
| CI/CD | GitHub Actions → AWS ECS |
| Monitoring | Prometheus + Grafana |

---

## Quick Start

```bash
git clone https://github.com/your-org/supplychield.git
cd supplychield

cp .env.example .env
# Edit .env: set SECRET_KEY, POSTGRES_PASSWORD, NEO4J_PASSWORD

docker compose up -d
docker compose exec backend alembic upgrade head
```

Open http://localhost:3000 → Register your organization.

**Want to explore with sample data instead?** Run the demo seed script to populate a realistic
4-tier automotive supply chain — 14 suppliers, materials, relationships, a flagged sole-source
vulnerability, **pre-computed explainable risk scores**, and sample alerts:

```bash
docker compose exec backend python scripts/seed_demo.py
```

Then log in with the quick demo account:

| | |
|---|---|
| **Email** | `demo@gmail.com` |
| **Password** | `demo@1234` |
| **Role** | Admin (sees everything) |

The script also creates one login per role (`admin` / `analyst` / `procurement` / `executive`
`@demo.supplychield.ai`, password `DemoPassword123!`) to demonstrate RBAC. The seeder resets the
demo database on each run and refuses to run when `ENVIRONMENT=production`.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full setup instructions.

---

## Project Structure

```
supplychield/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── routes/          # FastAPI route handlers
│   │   │   └── schemas/         # Pydantic request/response models
│   │   ├── config/              # Settings, DB, graph DB connections
│   │   ├── middleware/          # Auth, logging, audit
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── core.py          # Users, Organizations, AuditLogs
│   │   │   ├── supply_chain.py  # Suppliers, Materials, Relationships
│   │   │   └── risk.py          # RiskScores, Alerts, RiskEvents
│   │   ├── services/            # Business logic
│   │   │   ├── auth_service.py  # JWT, RBAC
│   │   │   ├── graph_service.py # Graph traversal, disruption simulation
│   │   │   ├── risk_scoring_service.py  # Explainable risk engine
│   │   │   ├── recommendation_scoring.py  # Pure scoring logic (no DB deps)
│   │   │   └── recommendation_service.py  # Alternative supplier engine
│   │   └── tasks/
│   │       └── ingestion.py     # Celery tasks: NOAA, GDELT ingestion
│   ├── migrations/              # Alembic database migrations
│   ├── scripts/
│   │   └── seed_demo.py         # Demo data seeder (4-tier automotive supply chain)
│   ├── tests/
│   │   ├── test_core.py         # 19 unit tests
│   │   └── test_integration.py  # 25 integration tests (44 total, all passing)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/          # AppLayout, sidebar navigation
│   │   │   └── risk/            # RiskScorePanel, RiskLevelBadge
│   │   ├── pages/               # One page per major feature
│   │   ├── services/            # API client (axios)
│   │   ├── store/               # Zustand auth store
│   │   └── types/               # TypeScript domain types
│   ├── Dockerfile
│   └── nginx.conf
├── docker/
│   ├── prometheus.yml
│   └── grafana/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── USER_GUIDE.md
├── .github/workflows/ci.yml     # CI: test → build → deploy
├── docker-compose.yml
└── .env.example
```

---

## Design Principles

1. **No fake data** — every value comes from real APIs, real stored records, or clearly labeled simulations. Risk sub-scores reflect ingested events; where no events are present the factor is explicitly labelled "no active alerts" rather than invented. `data_sources` lists the actual source of each contributing event.
2. **Explainable scores** — every risk score includes contributing factors, data sources, and weights
3. **Audit on writes** — write actions (login, supplier CRUD, alert create/transition) are recorded in the `audit_logs` table with user, timestamp, and detail. Read endpoints are not audited.
4. **Soft deletes** — data is never permanently destroyed
5. **Multi-tenant** — operational data (suppliers, relationships, risk scores, alerts) is scoped to `organization_id`. External `risk_events` (NOAA/GDELT) are a shared global feed matched to suppliers by geography.

### Known limitations / roadmap

- **External ingestion** runs via Celery beat. NOAA and GDELT ingestion are implemented; **OpenWeather is a stub** (`ingest_openweather` returns `not_implemented`) pending per-facility coordinate wiring.
- **Automated alerting**: alerts can be created via `POST /api/v1/alerts` (with Slack/email dispatch when configured). A scheduled threshold/trend evaluator that auto-creates alerts from risk scores is planned, not yet implemented.
- **Token storage**: the SPA stores JWTs in `localStorage` for simplicity. For higher-security deployments, move the refresh token to an httpOnly, Secure, SameSite cookie issued by the backend.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [User Guide](docs/USER_GUIDE.md)

---

## Tests

The test suites exercise the **real application code** — routes, services, middleware, and ORM
models against a real (in-memory SQLite) database and a real ASGI client. They are not
re-implementations of business logic.

**Backend (38 tests)** — `backend/tests/`
```
test_core.py          Password hashing, JWT issuance/decoding, RBAC matrix,
                      password policy, alert transitions, pure recommendation scoring
test_integration.py   Register/login/me flow, the access-vs-refresh-token bypass guard,
                      multi-tenant isolation, RBAC enforcement, alert lifecycle endpoints,
                      the risk scoring engine, and the recommendation engine — all via the
                      live FastAPI app and services
```

```bash
cd backend
PYTHONPATH=. pytest tests/ -v          # 38 passed
PYTHONPATH=. pytest tests/ --cov=src   # with coverage
```

The suite runs on SQLite via dialect-portable column types (`src/models/types.py`), so no
Postgres is needed to run tests. Production still uses native PostgreSQL `UUID`/`JSONB`.

**Frontend (6 tests)** — `frontend/src/**/*.test.tsx`
```bash
cd frontend
npm run test       # vitest + jsdom: RiskLevelBadge, authStore (login/logout/error)
```

The recommendation scoring logic (`src/services/recommendation_scoring.py`) is a pure function
with no database or framework dependencies, and the `RecommendationEngine` service delegates to
it — so the unit tests and the production path run the exact same code.
