"""
Pure scoring logic for alternative supplier recommendations.
No database imports — fully testable in isolation.
Imported by recommendation_service.py and by tests directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Protocol, runtime_checkable


# ── Constants ──────────────────────────────────────────────────────────────────

GEO_SAME_COUNTRY = 30.0
GEO_SAME_REGION  = 15.0
INDUSTRY_MATCH   = 25.0
TIER_EXACT       = 20.0
TIER_ADJACENT    = 10.0
STATUS_ACTIVE    = 15.0
STATUS_REVIEW    =  5.0
RISK_BONUS_MAX   = 10.0


# ── Lightweight supplier protocol (no SQLAlchemy dependency) ──────────────────

@runtime_checkable
class SupplierLike(Protocol):
    id: Any
    name: str
    country: Optional[str]
    region: Optional[str]
    city: Optional[str]
    tier: int
    industry: Optional[str]
    employee_count: Optional[int]
    annual_revenue_usd: Optional[float]
    certifications: Optional[dict]
    contact_email: Optional[str]
    website: Optional[str]

    @property
    def status(self) -> Any: ...  # Has .value attribute


@dataclass
class RecommendationReason:
    factor: str
    weight: float
    detail: str


@dataclass
class SupplierRecommendation:
    supplier: Any
    ranking_score: float
    reasons: List[RecommendationReason] = field(default_factory=list)
    latest_risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    caveats: List[str] = field(default_factory=list)


def score_candidate(
    target: SupplierLike,
    candidate: SupplierLike,
    risk_scores: Dict[str, float],
) -> SupplierRecommendation:
    """
    Score a candidate supplier as an alternative to the target.
    Pure function — no I/O, no database, fully deterministic.
    """
    reasons: List[RecommendationReason] = []
    caveats: List[str] = []
    total = 0.0

    # ── Geographic match ───────────────────────────────────────────────────
    if candidate.country and target.country:
        if candidate.country == target.country:
            total += GEO_SAME_COUNTRY
            reasons.append(RecommendationReason(
                factor="Same country",
                weight=GEO_SAME_COUNTRY / 100,
                detail=f"Both located in {candidate.country} — minimal logistics change",
            ))
            if (candidate.region and target.region
                    and candidate.region == target.region):
                total += GEO_SAME_REGION
                reasons.append(RecommendationReason(
                    factor="Same region",
                    weight=GEO_SAME_REGION / 100,
                    detail=f"Same region ({candidate.region}) — lowest switching logistics cost",
                ))
        else:
            caveats.append(
                f"Different country ({candidate.country} vs {target.country}) "
                "— factor in import tariffs, lead time, and customs compliance"
            )

    # ── Industry match ─────────────────────────────────────────────────────
    if candidate.industry and target.industry:
        if candidate.industry == target.industry:
            total += INDUSTRY_MATCH
            reasons.append(RecommendationReason(
                factor="Same industry",
                weight=INDUSTRY_MATCH / 100,
                detail=f"Both in {candidate.industry} — likely capability overlap",
            ))
    elif not candidate.industry:
        caveats.append("Industry not recorded — verify capability manually")

    # ── Tier compatibility ─────────────────────────────────────────────────
    tier_diff = abs(candidate.tier - target.tier)
    if tier_diff == 0:
        total += TIER_EXACT
        reasons.append(RecommendationReason(
            factor="Same supply chain tier",
            weight=TIER_EXACT / 100,
            detail=f"Tier {candidate.tier} match — drop-in position replacement",
        ))
    elif tier_diff == 1:
        total += TIER_ADJACENT
        reasons.append(RecommendationReason(
            factor="Adjacent tier",
            weight=TIER_ADJACENT / 100,
            detail=(
                f"Tier {candidate.tier} (target is Tier {target.tier}) — "
                "requires relationship restructuring but feasible"
            ),
        ))
        caveats.append(
            f"Tier mismatch (candidate Tier {candidate.tier}, target Tier {target.tier}) "
            "— evaluate whether direct engagement is appropriate"
        )

    # ── Operational status ─────────────────────────────────────────────────
    status_val = candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status)
    if status_val == "active":
        total += STATUS_ACTIVE
        reasons.append(RecommendationReason(
            factor="Active status",
            weight=STATUS_ACTIVE / 100,
            detail="Supplier is currently active and operational",
        ))
    elif status_val == "under_review":
        total += STATUS_REVIEW
        reasons.append(RecommendationReason(
            factor="Under review",
            weight=STATUS_REVIEW / 100,
            detail="Supplier is active but undergoing qualification review",
        ))
        caveats.append("Supplier is under review — validate current operational status before engagement")

    # ── Risk score bonus ───────────────────────────────────────────────────
    candidate_risk = risk_scores.get(str(candidate.id))
    risk_level = None
    if candidate_risk is not None:
        risk_bonus = (100 - candidate_risk) / 100 * RISK_BONUS_MAX
        total += risk_bonus
        risk_level = _risk_level_label(candidate_risk)
        reasons.append(RecommendationReason(
            factor="Risk profile",
            weight=risk_bonus / 100,
            detail=(
                f"Risk score {round(candidate_risk, 1)}/100 ({risk_level}) — "
                f"{'lower risk improves suitability' if candidate_risk < 50 else 'elevated risk — review before onboarding'}"
            ),
        ))
        if candidate_risk >= 75:
            caveats.append(
                f"High risk score ({round(candidate_risk, 1)}) — "
                "resolve underlying risk factors before engagement"
            )
    else:
        caveats.append("No risk score calculated yet — run risk assessment before onboarding")

    # ── Scale & certifications ─────────────────────────────────────────────
    if candidate.employee_count and candidate.employee_count > 1000:
        total += 2
        reasons.append(RecommendationReason(
            factor="Established scale",
            weight=0.02,
            detail=f"{candidate.employee_count:,} employees — indicates operational capacity",
        ))

    if candidate.certifications:
        total += 2
        reasons.append(RecommendationReason(
            factor="Quality certifications",
            weight=0.02,
            detail=(
                f"Holds {len(candidate.certifications)} certification(s): "
                f"{', '.join(candidate.certifications.keys())}"
            ),
        ))

    return SupplierRecommendation(
        supplier=candidate,
        ranking_score=round(max(0.0, total), 2),
        reasons=sorted(reasons, key=lambda r: r.weight, reverse=True),
        latest_risk_score=round(candidate_risk, 1) if candidate_risk is not None else None,
        risk_level=risk_level,
        caveats=caveats,
    )


def serialize_recommendation(rec: SupplierRecommendation) -> Dict[str, Any]:
    s = rec.supplier
    return {
        "supplier_id": str(s.id),
        "name": s.name,
        "country": s.country,
        "region": s.region,
        "city": s.city,
        "tier": s.tier,
        "industry": s.industry,
        "status": s.status.value if hasattr(s.status, "value") else str(s.status),
        "employee_count": s.employee_count,
        "annual_revenue_usd": s.annual_revenue_usd,
        "certifications": s.certifications,
        "contact_email": s.contact_email,
        "website": s.website,
        "ranking_score": rec.ranking_score,
        "latest_risk_score": rec.latest_risk_score,
        "risk_level": rec.risk_level,
        "reasons": [
            {"factor": r.factor, "weight": round(r.weight, 3), "detail": r.detail}
            for r in rec.reasons
        ],
        "caveats": rec.caveats,
    }


def _risk_level_label(score: float) -> str:
    if score >= 75: return "critical"
    if score >= 50: return "high"
    if score >= 25: return "medium"
    return "low"
