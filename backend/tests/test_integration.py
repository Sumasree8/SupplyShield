"""
Integration tests — drive the REAL FastAPI app and services against a real
(in-memory) database. These cover auth flows, the auth-bypass fix, multi-tenant
isolation, the alert lifecycle endpoints, and the risk/recommendation engines.
"""
import pytest

from tests.conftest import make_org_and_user, auth_header

from src.models.core import UserRole
from src.models.supply_chain import Supplier, SupplierStatus
from src.services.auth_service import create_refresh_token
from src.services.risk_scoring_service import RiskScoringEngine, DEFAULT_WEIGHTS
from src.services.recommendation_service import RecommendationEngine


# ── Auth flow + the auth-bypass fix ──────────────────────────────────────────

class TestAuthFlow:
    async def test_register_login_me(self, client):
        reg = await client.post("/api/v1/auth/register", json={
            "email": "founder@acme.com", "password": "SuperSecret123!",
            "full_name": "Founder", "organization_name": "Acme",
        })
        assert reg.status_code == 201, reg.text
        body = reg.json()
        assert body["role"] == "admin"
        assert body["created_at"] is not None  # regression: created_at was None

        login = await client.post("/api/v1/auth/login", json={
            "email": "founder@acme.com", "password": "SuperSecret123!",
        })
        assert login.status_code == 200, login.text
        access = login.json()["access_token"]

        me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200
        assert me.json()["email"] == "founder@acme.com"

    async def test_refresh_token_cannot_authenticate_protected_route(self, client, db):
        """A refresh token must NOT be accepted as an access token (auth-bypass fix)."""
        user = await make_org_and_user(db, email="a@acme.test")
        refresh = create_refresh_token(str(user.id))
        resp = await client.get(
            "/api/v1/suppliers", headers={"Authorization": f"Bearer {refresh}"}
        )
        assert resp.status_code == 401

    async def test_no_token_is_unauthorized(self, client):
        assert (await client.get("/api/v1/suppliers")).status_code in (401, 403)

    async def test_duplicate_email_rejected(self, client):
        payload = {
            "email": "dup@acme.com", "password": "SuperSecret123!",
            "full_name": "X", "organization_name": "Org",
        }
        assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
        assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 409


# ── Multi-tenant isolation ───────────────────────────────────────────────────

class TestTenancy:
    async def test_supplier_create_and_list_scoped_to_org(self, client, db):
        admin = await make_org_and_user(db, email="admin@org-a.test", org_name="Org A")
        resp = await client.post("/api/v1/suppliers", headers=auth_header(admin), json={
            "name": "Steel Co", "country": "USA", "tier": 1,
        })
        assert resp.status_code == 201, resp.text

        listing = await client.get("/api/v1/suppliers", headers=auth_header(admin))
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

    async def test_other_org_cannot_see_suppliers(self, client, db):
        admin_a = await make_org_and_user(db, email="a@org-a.test", org_name="Org A")
        admin_b = await make_org_and_user(db, email="b@org-b.test", org_name="Org B")
        await client.post("/api/v1/suppliers", headers=auth_header(admin_a), json={
            "name": "Secret Supplier", "country": "USA", "tier": 1,
        })
        listing_b = await client.get("/api/v1/suppliers", headers=auth_header(admin_b))
        assert listing_b.json()["total"] == 0  # tenant isolation

    async def test_executive_viewer_cannot_create_supplier(self, client, db):
        viewer = await make_org_and_user(
            db, email="exec@org.test", role=UserRole.EXECUTIVE_VIEWER
        )
        resp = await client.post("/api/v1/suppliers", headers=auth_header(viewer), json={
            "name": "X", "country": "USA", "tier": 1,
        })
        assert resp.status_code == 403  # RBAC enforced


# ── Alert lifecycle through the API ──────────────────────────────────────────

class TestAlertLifecycle:
    async def _create_alert(self, client, headers):
        return await client.post("/api/v1/alerts", headers=headers, json={
            "title": "Port closure", "description": "Major port shut down",
            "category": "logistics", "severity": "high",
        })

    async def test_create_alert(self, client, db):
        admin = await make_org_and_user(db, email="admin@alert.test")
        resp = await self._create_alert(client, auth_header(admin))
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "created"
        assert body["notifications_sent"] == []  # no channels configured in tests

    async def test_valid_transition(self, client, db):
        admin = await make_org_and_user(db, email="admin2@alert.test")
        alert_id = (await self._create_alert(client, auth_header(admin))).json()["id"]
        resp = await client.patch(
            f"/api/v1/alerts/{alert_id}/status",
            headers=auth_header(admin), json={"status": "investigating"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "investigating"

    async def test_invalid_transition_rejected(self, client, db):
        admin = await make_org_and_user(db, email="admin3@alert.test")
        alert_id = (await self._create_alert(client, auth_header(admin))).json()["id"]
        # created -> resolved is not allowed
        resp = await client.patch(
            f"/api/v1/alerts/{alert_id}/status",
            headers=auth_header(admin), json={"status": "resolved"},
        )
        assert resp.status_code == 409

    async def test_unknown_status_rejected(self, client, db):
        admin = await make_org_and_user(db, email="admin4@alert.test")
        alert_id = (await self._create_alert(client, auth_header(admin))).json()["id"]
        resp = await client.patch(
            f"/api/v1/alerts/{alert_id}/status",
            headers=auth_header(admin), json={"status": "banana"},
        )
        assert resp.status_code == 422


# ── Risk scoring engine (real service against the DB) ────────────────────────

class TestRiskScoringEngine:
    async def test_score_is_bounded_and_explainable(self, db):
        admin = await make_org_and_user(db, email="risk@acme.test")
        supplier = Supplier(
            organization_id=admin.organization_id,
            name="Acme Parts", country="Taiwan", tier=1,
            status=SupplierStatus.SUSPENDED,
        )
        db.add(supplier)
        await db.commit()
        await db.refresh(supplier)

        engine = RiskScoringEngine(db)
        result = await engine.calculate_supplier_risk(supplier, str(admin.organization_id))

        assert 0.0 <= result.overall_score <= 100.0
        assert result.contributing_factors, "score must list contributing factors"
        assert set(result.category_scores) == set(DEFAULT_WEIGHTS)
        # Suspended supplier should carry operational risk
        assert result.category_scores["operational"] > 0

    async def test_weights_sum_to_one(self):
        assert round(sum(DEFAULT_WEIGHTS.values()), 6) == 1.0

    async def test_persist_score_writes_row(self, db):
        admin = await make_org_and_user(db, email="persist@acme.test")
        supplier = Supplier(
            organization_id=admin.organization_id, name="P", country="USA", tier=2,
        )
        db.add(supplier)
        await db.commit()
        await db.refresh(supplier)

        engine = RiskScoringEngine(db)
        result = await engine.calculate_supplier_risk(supplier, str(admin.organization_id))
        row = await engine.persist_score(result, str(admin.organization_id))
        assert row.id is not None
        assert row.overall_score == result.overall_score


# ── Recommendation engine (real service path) ────────────────────────────────

class TestRecommendationEngine:
    async def test_ranks_similar_supplier_higher(self, db):
        admin = await make_org_and_user(db, email="rec@acme.test")
        org_id = str(admin.organization_id)
        target = Supplier(organization_id=admin.organization_id, name="Target",
                          country="USA", region="Midwest", tier=1, industry="Auto",
                          status=SupplierStatus.ACTIVE)
        similar = Supplier(organization_id=admin.organization_id, name="Similar",
                           country="USA", region="Midwest", tier=1, industry="Auto",
                           status=SupplierStatus.ACTIVE)
        far = Supplier(organization_id=admin.organization_id, name="Far",
                       country="Brazil", region="South", tier=4, industry="Textiles",
                       status=SupplierStatus.ACTIVE)
        db.add_all([target, similar, far])
        await db.commit()
        await db.refresh(target)
        await db.refresh(similar)
        await db.refresh(far)

        engine = RecommendationEngine(db)
        out = await engine.recommend_alternatives(str(target.id), org_id)
        recs = out["recommendations"]
        assert recs[0]["name"] == "Similar"  # most similar ranked first
        assert recs[0]["ranking_score"] > 0
