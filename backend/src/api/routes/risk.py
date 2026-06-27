"""Risk intelligence API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.core import User
from src.models.supply_chain import Supplier
from src.models.risk import RiskScore, RiskEvent
from src.services.risk_scoring_service import RiskScoringEngine
from src.middleware.auth import get_current_user

router = APIRouter()


@router.post("/suppliers/{supplier_id}/score")
async def calculate_risk_score(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calculate and return an explainable risk score for a supplier.
    Score is computed from real ingested data — not hardcoded values.
    """
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    engine = RiskScoringEngine(db)
    score_result = await engine.calculate_supplier_risk(supplier, str(current_user.organization_id))
    score_record = await engine.persist_score(score_result, str(current_user.organization_id))

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.name,
        "overall_score": score_result.overall_score,
        "risk_level": _risk_level(score_result.overall_score),
        "category_scores": score_result.category_scores,
        "weights": score_result.weights,
        "contributing_factors": score_result.contributing_factors,
        "data_sources": score_result.data_sources,
        "calculated_at": score_result.calculated_at.isoformat(),
        "scoring_version": score_result.scoring_version,
        "score_id": str(score_record.id),
    }


@router.get("/suppliers/{supplier_id}/scores")
async def get_risk_score_history(
    supplier_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historical risk scores for a supplier — for trend analysis."""
    result = await db.execute(
        select(RiskScore).where(
            RiskScore.supplier_id == supplier_id,
            RiskScore.organization_id == current_user.organization_id,
        ).order_by(desc(RiskScore.calculated_at)).limit(limit)
    )
    scores = result.scalars().all()

    return {
        "supplier_id": supplier_id,
        "history": [
            {
                "score_id": str(s.id),
                "overall_score": s.overall_score,
                "risk_level": _risk_level(s.overall_score),
                "climate_score": s.climate_score,
                "geopolitical_score": s.geopolitical_score,
                "operational_score": s.operational_score,
                "logistics_score": s.logistics_score,
                "dependency_score": s.dependency_score,
                "calculated_at": s.calculated_at.isoformat(),
            }
            for s in scores
        ],
    }


@router.get("/scores")
async def list_latest_risk_scores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Latest computed risk score for every scored supplier in the organization.
    Powers the org-wide Risk Intelligence overview (most-at-risk first).
    """
    org_id = current_user.organization_id

    # Subquery: the most recent score timestamp per supplier.
    latest = (
        select(
            RiskScore.supplier_id,
            func.max(RiskScore.calculated_at).label("latest"),
        )
        .where(RiskScore.organization_id == org_id)
        .group_by(RiskScore.supplier_id)
        .subquery()
    )

    result = await db.execute(
        select(RiskScore, Supplier.name, Supplier.country, Supplier.tier)
        .join(
            latest,
            and_(
                RiskScore.supplier_id == latest.c.supplier_id,
                RiskScore.calculated_at == latest.c.latest,
            ),
        )
        .join(Supplier, Supplier.id == RiskScore.supplier_id)
        .order_by(desc(RiskScore.overall_score))
    )

    scores = [
        {
            "supplier_id": str(rs.supplier_id),
            "supplier_name": name,
            "country": country,
            "tier": tier,
            "overall_score": rs.overall_score,
            "risk_level": _risk_level(rs.overall_score),
            "climate_score": rs.climate_score,
            "geopolitical_score": rs.geopolitical_score,
            "operational_score": rs.operational_score,
            "logistics_score": rs.logistics_score,
            "dependency_score": rs.dependency_score,
            "calculated_at": rs.calculated_at.isoformat(),
        }
        for rs, name, country, tier in result.all()
    ]
    return {"scores": scores, "total": len(scores)}


@router.get("/events")
async def list_risk_events(
    category: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List ingested external risk events from NOAA, GDELT, etc."""
    query = select(RiskEvent).where(RiskEvent.is_active == True)
    if category:
        query = query.where(RiskEvent.category == category)

    result = await db.execute(query.order_by(desc(RiskEvent.ingested_at)).limit(limit))
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": str(e.id),
                "source": e.source,
                "category": e.category.value,
                "title": e.title,
                "description": e.description,
                "severity": e.severity,
                "affected_countries": e.affected_countries,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "ingested_at": e.ingested_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events),
    }


def _risk_level(score: float) -> str:
    if score >= 75:
        return "critical"
    elif score >= 50:
        return "high"
    elif score >= 25:
        return "medium"
    return "low"
