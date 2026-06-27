"""Phase 6 — Alternative Supplier Recommendation API."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.core import User
from src.services.recommendation_service import RecommendationEngine
from src.middleware.auth import get_current_user

router = APIRouter()


@router.get("/suppliers/{supplier_id}/alternatives")
async def get_alternative_suppliers(
    supplier_id: str,
    max_results: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recommend alternative suppliers for the given supplier.

    Rankings based on: geographic proximity, industry match, tier compatibility,
    operational status, and risk profile. All explanations included.
    No random or hardcoded suggestions — only real stored data.
    """
    engine = RecommendationEngine(db)
    result = await engine.recommend_alternatives(
        target_supplier_id=supplier_id,
        organization_id=str(current_user.organization_id),
        max_results=max_results,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/candidates")
async def list_recommendation_candidates(
    country: str = Query(None),
    industry: str = Query(None),
    tier: int = Query(None),
    max_results: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List suppliers that could serve as replacement candidates,
    filtered by country, industry, and/or tier.
    Useful for procurement teams browsing without a specific target.
    """
    from sqlalchemy import select
    from src.models.supply_chain import Supplier

    query = select(Supplier).where(
        Supplier.organization_id == current_user.organization_id,
        Supplier.is_active == True,
        Supplier.status == "active",
    )

    if country:
        query = query.where(Supplier.country == country)
    if industry:
        query = query.where(Supplier.industry == industry)
    if tier is not None:
        query = query.where(Supplier.tier == tier)

    query = query.order_by(Supplier.name).limit(max_results)
    result = await db.execute(query)
    suppliers = result.scalars().all()

    return {
        "candidates": [
            {
                "id": str(s.id),
                "name": s.name,
                "country": s.country,
                "tier": s.tier,
                "industry": s.industry,
                "status": s.status.value,
                "employee_count": s.employee_count,
                "certifications": s.certifications,
            }
            for s in suppliers
        ],
        "total": len(suppliers),
    }
