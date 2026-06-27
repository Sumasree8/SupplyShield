"""
Unit tests — exercise the REAL application code (no inline re-implementations).

Covers: password hashing, JWT issuance/decoding, the RBAC matrix, the password
policy validator, the alert transition rules, and the pure recommendation
scoring function — all imported from src.
"""
import types

import pytest

from src.services.auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    has_permission, ROLE_PERMISSIONS,
)
from src.models.core import UserRole
from src.models.risk import AlertStatus, is_valid_alert_transition
from src.api.schemas.auth import RegisterRequest
from src.services.recommendation_scoring import score_candidate


# ── Password hashing (real passlib/bcrypt path) ──────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext_and_verifies(self):
        h = hash_password("SuperSecret123!")
        assert h != "SuperSecret123!"
        assert h.startswith("$2")  # bcrypt prefix
        assert verify_password("SuperSecret123!", h) is True

    def test_wrong_password_fails(self):
        h = hash_password("SuperSecret123!")
        assert verify_password("wrong", h) is False

    def test_same_password_different_salts(self):
        assert hash_password("SuperSecret123!") != hash_password("SuperSecret123!")


# ── JWT issuance + decoding (real jose path) ─────────────────────────────────

class TestJWT:
    def test_access_token_roundtrip_and_type(self):
        tok = create_access_token("user-1", "org-1", "admin")
        payload = decode_token(tok)
        assert payload["sub"] == "user-1"
        assert payload["org"] == "org-1"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_refresh_token_marked_refresh(self):
        payload = decode_token(create_refresh_token("user-1"))
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user-1"

    def test_tampered_token_rejected(self):
        tok = create_access_token("user-1", "org-1", "admin")
        with pytest.raises(ValueError):
            decode_token(tok + "tamper")

    def test_token_signed_with_wrong_key_rejected(self):
        from jose import jwt
        forged = jwt.encode({"sub": "x", "type": "access"}, "wrong-key", algorithm="HS256")
        with pytest.raises(ValueError):
            decode_token(forged)


# ── RBAC matrix (real ROLE_PERMISSIONS / has_permission) ─────────────────────

class TestRBAC:
    def test_admin_can_delete_users(self):
        assert has_permission(UserRole.ADMIN, "users:delete") is True

    def test_executive_is_read_only(self):
        assert has_permission(UserRole.EXECUTIVE_VIEWER, "suppliers:read") is True
        assert has_permission(UserRole.EXECUTIVE_VIEWER, "suppliers:write") is False
        assert has_permission(UserRole.EXECUTIVE_VIEWER, "simulator:run") is False

    def test_procurement_cannot_write_risk(self):
        assert has_permission(UserRole.PROCUREMENT_MANAGER, "risk:read") is True
        assert has_permission(UserRole.PROCUREMENT_MANAGER, "risk:write") is False

    def test_every_role_defined(self):
        for role in UserRole:
            assert role in ROLE_PERMISSIONS

    def test_unknown_permission_denied(self):
        assert has_permission(UserRole.ADMIN, "nonsense:permission") is False


# ── Password policy (real pydantic validator) ────────────────────────────────

class TestPasswordPolicy:
    def test_short_password_rejected(self):
        with pytest.raises(ValueError):
            RegisterRequest(
                email="a@b.com", password="short", full_name="A", organization_name="O"
            )

    def test_long_password_accepted(self):
        req = RegisterRequest(
            email="a@b.com", password="LongEnough12", full_name="A", organization_name="O"
        )
        assert req.password == "LongEnough12"


# ── Alert lifecycle transitions (real is_valid_alert_transition) ─────────────

class TestAlertTransitions:
    def test_created_to_investigating_allowed(self):
        assert is_valid_alert_transition(AlertStatus.CREATED, AlertStatus.INVESTIGATING)

    def test_closed_is_terminal(self):
        for target in AlertStatus:
            assert is_valid_alert_transition(AlertStatus.CLOSED, target) is False

    def test_cannot_skip_created_to_resolved(self):
        assert is_valid_alert_transition(AlertStatus.CREATED, AlertStatus.RESOLVED) is False

    def test_self_transition_rejected(self):
        assert is_valid_alert_transition(AlertStatus.ASSIGNED, AlertStatus.ASSIGNED) is False

    def test_resolved_can_reopen(self):
        assert is_valid_alert_transition(AlertStatus.RESOLVED, AlertStatus.INVESTIGATING)


# ── Pure recommendation scoring (real score_candidate) ───────────────────────

def _supplier(**kw):
    """Minimal SupplierLike for the pure scorer."""
    base = dict(
        id="cand-1", name="Cand", country="USA", region="Midwest", city="Detroit",
        tier=1, industry="Automotive", employee_count=None, annual_revenue_usd=None,
        certifications=None, contact_email=None, website=None,
        status=types.SimpleNamespace(value="active"),
    )
    base.update(kw)
    return types.SimpleNamespace(**base)


class TestRecommendationScoring:
    def test_same_country_region_industry_tier_active(self):
        target = _supplier()
        cand = _supplier(id="cand-2")
        rec = score_candidate(target, cand, {})
        # 30 country + 15 region + 25 industry + 20 tier + 15 active = 105
        assert rec.ranking_score == 105.0
        factors = {r.factor for r in rec.reasons}
        assert {"Same country", "Same region", "Same industry",
                "Same supply chain tier", "Active status"} <= factors

    def test_different_country_adds_caveat(self):
        target = _supplier(country="USA")
        cand = _supplier(id="c", country="Germany", region="Bavaria")
        rec = score_candidate(target, cand, {})
        assert any("Different country" in c for c in rec.caveats)

    def test_risk_bonus_inverted(self):
        target = _supplier()
        cand = _supplier(id="c")
        low = score_candidate(target, cand, {"c": 0.0}).ranking_score
        high = score_candidate(target, cand, {"c": 100.0}).ranking_score
        assert low > high  # lower risk -> higher suitability

    def test_score_never_negative(self):
        # A wholly mismatched candidate must still floor at >= 0.
        target = _supplier(country="USA", region="A", industry="Auto", tier=1)
        cand = _supplier(id="c", country="China", region="B", industry="Textiles",
                         tier=4, status=types.SimpleNamespace(value="inactive"))
        rec = score_candidate(target, cand, {})
        assert rec.ranking_score >= 0.0
