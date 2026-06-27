"""
Phase 6 — Alternative Supplier Recommendation Engine.

Recommends replacement suppliers based on:
  1. Same country/region (geographic proximity)
  2. Same industry/category
  3. Same or adjacent tier
  4. Operational status (active only)
  5. Risk score (lower = better)
  6. Sole-source avoidance

All recommendations are explainable — each one includes a ranked
list of reasons. No random or hardcoded suggestions.
"""
from __future__ import annotations

from typing import List, Dict, Any

import structlog
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.supply_chain import Supplier, SupplyRelationship
from src.models.risk import RiskScore
from src.services.recommendation_scoring import (
    SupplierRecommendation,
    score_candidate,
    serialize_recommendation,
)

log = structlog.get_logger()


class RecommendationEngine:
    """
    Ranks alternative suppliers for a given target supplier.

    The actual scoring math lives in `recommendation_scoring.score_candidate`
    (a pure, DB-free, unit-tested function). This engine is responsible only
    for the data-access plumbing: loading the target, candidates, exclusions,
    and risk scores, then delegating ranking to the pure function. This keeps
    the production path identical to what the test suite exercises.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def recommend_alternatives(
        self,
        target_supplier_id: str,
        organization_id: str,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Find and rank alternative suppliers for a given supplier.

        Returns a ranked list with full explainability for each candidate.
        Excludes the target supplier itself and any supplier already in a
        direct supply relationship with it (they are dependencies, not replacements).
        """
        # Load the target supplier
        result = await self.db.execute(
            select(Supplier).where(
                Supplier.id == target_supplier_id,
                Supplier.organization_id == organization_id,
                Supplier.is_active == True,
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            return {"error": "Supplier not found", "recommendations": []}

        # Load all active suppliers in the same organization (excluding target)
        result = await self.db.execute(
            select(Supplier).where(
                Supplier.organization_id == organization_id,
                Supplier.id != target.id,
                Supplier.is_active == True,
                Supplier.status.in_(["active", "under_review"]),
            )
        )
        candidates = result.scalars().all()

        # Exclude suppliers already in a direct dependency relationship
        excluded_ids = await self._get_related_supplier_ids(target_supplier_id, organization_id)

        # Load latest risk scores in bulk
        risk_scores = await self._load_latest_risk_scores(
            [str(s.id) for s in candidates], organization_id
        )

        # Score each candidate
        ranked: List[SupplierRecommendation] = []
        for candidate in candidates:
            if str(candidate.id) in excluded_ids:
                continue

            rec = score_candidate(target, candidate, risk_scores)
            # Only include candidates with at least some relevance
            if rec.ranking_score > 0:
                ranked.append(rec)

        # Sort descending by ranking score
        ranked.sort(key=lambda r: r.ranking_score, reverse=True)
        top = ranked[:max_results]

        return {
            "target_supplier": {
                "id": str(target.id),
                "name": target.name,
                "country": target.country,
                "tier": target.tier,
                "industry": target.industry,
            },
            "total_candidates_evaluated": len(candidates),
            "total_matches": len(ranked),
            "recommendations": [serialize_recommendation(r) for r in top],
            "methodology": (
                "Candidates ranked by geographic proximity, industry match, "
                "tier compatibility, operational status, and risk profile. "
                "All scores derived from stored supplier records. "
                "Suppliers in an existing dependency relationship are excluded."
            ),
        }

    async def _get_related_supplier_ids(
        self, supplier_id: str, organization_id: str
    ) -> set[str]:
        """Return IDs of suppliers already in a direct relationship with the target."""
        result = await self.db.execute(
            select(SupplyRelationship).where(
                SupplyRelationship.organization_id == organization_id,
                or_(
                    SupplyRelationship.from_supplier_id == supplier_id,
                    SupplyRelationship.to_supplier_id == supplier_id,
                ),
                SupplyRelationship.is_active == True,
            )
        )
        rels = result.scalars().all()
        excluded = set()
        for r in rels:
            excluded.add(str(r.from_supplier_id))
            excluded.add(str(r.to_supplier_id))
        excluded.discard(supplier_id)
        return excluded

    async def _load_latest_risk_scores(
        self, supplier_ids: List[str], organization_id: str
    ) -> Dict[str, float]:
        """Load the most recent risk score for each supplier in a single query."""
        if not supplier_ids:
            return {}

        # Subquery: max calculated_at per supplier
        from sqlalchemy import func
        subq = (
            select(
                RiskScore.supplier_id,
                func.max(RiskScore.calculated_at).label("latest"),
            )
            .where(
                RiskScore.organization_id == organization_id,
                RiskScore.supplier_id.in_(supplier_ids),
            )
            .group_by(RiskScore.supplier_id)
            .subquery()
        )

        result = await self.db.execute(
            select(RiskScore).join(
                subq,
                and_(
                    RiskScore.supplier_id == subq.c.supplier_id,
                    RiskScore.calculated_at == subq.c.latest,
                ),
            )
        )
        scores = result.scalars().all()
        return {str(s.supplier_id): s.overall_score for s in scores}
