# SupplyShield AI — User Guide

## Getting Started

### Registering Your Organization

1. Navigate to `/register`
2. Enter your work email, full name, organization name, and industry
3. Choose a password (minimum 12 characters)
4. You will be logged in as the organization **Admin**

---

## Supplier Management

### Adding Suppliers

Navigate to **Suppliers → Add Supplier**

Required fields:
- **Name** — supplier's trading name
- **Country** — ISO country name
- **Tier** — 1 (direct), 2, 3, or 4+

Optional but recommended:
- **External ID** — reference to your ERP system
- **Coordinates** — enables geographic risk matching
- **Industry** — used in risk categorization
- **Certifications** — ISO 9001, IATF 16949, etc.

### Defining Relationships

After adding suppliers, create relationships under **Supply Graph → Add Relationship**:

- `SUPPLIES_TO` — supplier A provides materials/components to supplier B
- Optionally attach a material and annual volume

These relationships power the graph visualization and disruption simulator.

### Supplier Tiers

| Tier | Meaning |
|------|---------|
| Tier 1 | Direct suppliers — you buy from them |
| Tier 2 | Your Tier 1's suppliers |
| Tier 3 | Your Tier 2's suppliers |
| Tier 4+ | Sub-tier raw material / commodity suppliers |

---

## Supply Chain Graph

The **Graph** page shows your entire supply network as an interactive force-directed graph.

- **Drag nodes** to rearrange
- **Scroll to zoom**
- **Click a node** to open the inspector panel
- **Colors** represent tiers (blue=T1, purple=T2, cyan=T3, grey=T4)

Node inspector shows supplier name, country, status, and links to the full supplier record.

---

## Risk Intelligence

### Risk Scores

Navigate to a supplier's detail page and click **Calculate Risk Score**.

Each score includes:
- **Overall score** (0–100, higher = more risk)
- **Category breakdown** — climate, geopolitical, operational, logistics, dependency
- **Contributing factors** — exact reasons driving the score, with data source attribution
- **Weights** — how each category is weighted in the composite

Risk levels:
| Score | Level |
|-------|-------|
| 0–24 | Low |
| 25–49 | Medium |
| 50–74 | High |
| 75–100 | Critical |

### External Risk Events

The **Risk Intelligence** page shows events ingested from:
- **NOAA** — US weather alerts (requires API key)
- **GDELT** — global news and geopolitical events (free)
- **OpenWeather** — current weather conditions (requires API key)

Events are matched to your suppliers by country/region to drive risk scores.

### Configuring Ingestion

Add API keys to your `.env` file and restart the Celery workers. Events are ingested:
- NOAA: hourly
- GDELT: every 4 hours
- OpenWeather: every 6 hours

---

## Early Warning Alerts

Alerts are created when:
- A risk score crosses a threshold (e.g., climate score > 70)
- A new high-severity risk event affects a supplier's geography
- A sole-source dependency is detected

### Alert Lifecycle

```
Created → Assigned → Investigating → Resolved → Closed
```

**Created**: Alert raised automatically  
**Assigned**: Risk analyst takes ownership  
**Investigating**: Active investigation underway  
**Resolved**: Issue addressed, root cause identified  
**Closed**: Alert archived  

Every status change is recorded with a timestamp and optional notes in the audit trail.

---

## Impact Simulator

The **Impact Simulator** answers: *"What happens if this supplier goes offline?"*

1. Select a supplier from the dropdown
2. Click **Run Simulation**
3. Review:
   - Total affected downstream suppliers
   - Impact by tier
   - **Sole-source vulnerabilities** (suppliers with no alternative upstream — critical risk)
   - Disruption radius (how many supply chain hops)

All results are derived from your actual stored supplier relationships — not modeled assumptions.

---

## User Management (Admin only)

Navigate to **Users** to:
- View all users in your organization
- Create new users with specific roles
- Deactivate users

### Roles

| Role | Description |
|------|-------------|
| **Admin** | Full access including user management |
| **Risk Analyst** | Create/edit suppliers, calculate scores, manage alerts |
| **Procurement Manager** | Edit suppliers, view risk, run simulations |
| **Executive Viewer** | Read-only access to all data |
