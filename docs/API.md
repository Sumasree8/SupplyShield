# SupplyShield AI — API Reference

Base URL: `https://your-domain.com/api/v1`  
Interactive docs (non-production): `http://localhost:8000/api/docs`

## Authentication

All endpoints (except `/auth/login` and `/auth/register`) require:
```
Authorization: Bearer <access_token>
```

---

## Auth

### POST /auth/register
Register a new organization and admin user.

**Request:**
```json
{
  "email": "admin@company.com",
  "password": "MinimumTwelveChars!",
  "full_name": "Jane Smith",
  "organization_name": "Acme Corp",
  "industry": "Automotive"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "email": "admin@company.com",
  "full_name": "Jane Smith",
  "role": "admin",
  "organization_id": "uuid",
  "organization_name": "Acme Corp",
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

### POST /auth/login
```json
{ "email": "admin@company.com", "password": "..." }
```
**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

### GET /auth/me
Returns the current authenticated user.

---

## Suppliers

### GET /suppliers
List suppliers with pagination and filtering.

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| page | int | Page number (default: 1) |
| page_size | int | Results per page (default: 20, max: 100) |
| tier | int | Filter by tier (1–4) |
| country | string | Filter by country name |
| status | string | active \| inactive \| under_review \| suspended |
| search | string | Full-text search on name |

**Response 200:**
```json
{
  "items": [...],
  "total": 147,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

---

### POST /suppliers
Create a supplier.

```json
{
  "name": "Foxconn Technology Group",
  "country": "Taiwan",
  "tier": 1,
  "industry": "Electronics Manufacturing",
  "latitude": 24.9788,
  "longitude": 121.5397,
  "certifications": {"ISO9001": "2024-12-31", "IATF16949": "2025-06-30"}
}
```

---

### GET /suppliers/{id}
Retrieve a single supplier.

---

### PATCH /suppliers/{id}
Partial update. Only include fields to change.

---

### DELETE /suppliers/{id}
Soft delete (sets `is_active=false`).

---

### POST /suppliers/relationships
Create a supply relationship between two suppliers.

```json
{
  "from_supplier_id": "uuid-of-upstream-supplier",
  "to_supplier_id": "uuid-of-downstream-supplier",
  "relationship_type": "SUPPLIES_TO",
  "annual_volume_usd": 12500000,
  "lead_time_days": 45
}
```

---

## Graph

### GET /graph/visualization
Returns all nodes and edges for graph rendering.

**Response:**
```json
{
  "nodes": [
    {"id": "uuid", "label": "Supplier Name", "tier": 1, "country": "Taiwan", "status": "active"}
  ],
  "edges": [
    {"id": "uuid->uuid", "source": "uuid", "target": "uuid", "type": "SUPPLIES_TO"}
  ],
  "stats": {
    "total_nodes": 42,
    "total_edges": 67,
    "tier_breakdown": {"1": 8, "2": 18, "3": 16},
    "country_breakdown": {"Taiwan": 12, "China": 10, "Mexico": 8}
  }
}
```

---

### GET /graph/suppliers/{id}/upstream
Traverse upstream dependencies.

**Query params:** `max_depth` (1–10, default: 5)

---

### GET /graph/tier-summary
Supplier count by tier and total relationship count.

---

## Risk

### POST /risk/suppliers/{id}/score
Calculate an explainable risk score. Score is computed from real ingested data and persisted.

**Response:**
```json
{
  "supplier_id": "uuid",
  "supplier_name": "Foxconn Technology Group",
  "overall_score": 61.5,
  "risk_level": "high",
  "category_scores": {
    "climate": 40.0,
    "geopolitical": 75.0,
    "operational": 0.0,
    "logistics": 20.0,
    "dependency": 30.0
  },
  "weights": {
    "climate": 0.25,
    "geopolitical": 0.25,
    "operational": 0.20,
    "logistics": 0.15,
    "dependency": 0.15
  },
  "contributing_factors": [
    {
      "description": "Trade tensions US-China elevated",
      "category": "geopolitical",
      "score_contribution": 25.0,
      "source": "gdelt",
      "evidence": "Ingested: 2025-01-15"
    }
  ],
  "data_sources": ["gdelt", "internal:supplier_records", "internal:supply_graph"],
  "calculated_at": "2025-01-15T14:32:00Z",
  "scoring_version": "1.0"
}
```

---

### GET /risk/suppliers/{id}/scores
Historical risk scores for trend analysis. Query param: `limit` (default: 10).

---

### GET /risk/events
List ingested external risk events.

**Query params:** `category` (climate|geopolitical|logistics|...), `limit`

---

## Alerts

### GET /alerts
List alerts. Query params: `severity`, `status`, `supplier_id`, `limit`

### GET /alerts/{id}
Alert detail with full status history audit trail.

### PATCH /alerts/{id}/status
Transition alert status.

```json
{
  "status": "assigned",
  "notes": "Assigned to APAC risk team",
  "assigned_to_id": "user-uuid"
}
```

Valid transitions:
- `created` → `assigned`, `closed`
- `assigned` → `investigating`, `resolved`, `closed`
- `investigating` → `resolved`, `closed`
- `resolved` → `closed`

---

## Simulator

### POST /simulator/suppliers/{id}/disruption
Simulate cascading supply chain impact of a supplier going offline.

**Response:**
```json
{
  "disrupted_supplier_id": "uuid",
  "total_affected": 23,
  "impact_by_tier": {
    "2": [{"supplier_id": "uuid", "name": "...", "distance_from_disruption": 1}],
    "3": [...]
  },
  "sole_source_vulnerabilities": [
    {"supplier_id": "uuid", "name": "Sole Source Inc.", "reason": "Single-source dependency"}
  ],
  "disruption_radius": 4
}
```

---

## Error Responses

All errors follow:
```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Validation error |
| 401 | Missing or invalid token |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate email) |
| 422 | Request body schema error |
| 500 | Internal server error |
