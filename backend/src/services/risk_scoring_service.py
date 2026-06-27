"""
Risk Scoring Engine — Phase 3.
Generates explainable, weighted composite risk scores.
Every score includes contributing factors, weights, and data sources.
NO black-box outputs.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

import structlog
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.supply_chain import Supplier, SupplierMaterial
from src.models.risk import RiskScore, RiskEvent, RiskCategory

log = structlog.get_logger()

# Default scoring weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "climate": 0.25,
    "geopolitical": 0.25,
    "operational": 0.20,
    "logistics": 0.15,
    "dependency": 0.15,
}


@dataclass
class ScoringFactor:
    """A single contributing factor to a risk score."""
    description: str
    category: str
    score_contribution: float  # 0-100 impact on this category
    weight: float
    source: str
    evidence: Optional[str] = None


@dataclass
class RiskScoreResult:
    """Complete explainable risk score result."""
    supplier_id: str
    overall_score: float
    category_scores: Dict[str, float]
    weights: Dict[str, float]
    contributing_factors: List[Dict]
    data_sources: List[str]
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scoring_version: str = "1.0"


class RiskScoringEngine:
    """
    Calculates explainable risk scores for suppliers.

    Score breakdown:
    - Climate risk: derived from active weather events near supplier location
    - Geopolitical risk: derived from GDELT events and sanctions data
    - Operational risk: derived from supplier status, certifications, sole-source dependencies
    - Logistics risk: derived from port congestion and transportation data
    - Dependency risk: graph-based calculation of supply chain concentration
    """

    SCORING_VERSION = "1.0"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_supplier_risk(
        self,
        supplier: Supplier,
        organization_id: str,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> RiskScoreResult:
        """
        Calculate and explain a supplier's risk score.
        All sub-scores are computed from real data or clearly labeled as unavailable.
        """
        weights = custom_weights or DEFAULT_WEIGHTS
        factors: List[ScoringFactor] = []
        data_sources: List[str] = []
        category_scores: Dict[str, float] = {}

        # --- Climate Risk ---
        climate_score, climate_factors, climate_sources = await self._score_climate(supplier)
        category_scores["climate"] = climate_score
        factors.extend(climate_factors)
        data_sources.extend(climate_sources)

        # --- Geopolitical Risk ---
        geo_score, geo_factors, geo_sources = await self._score_geopolitical(supplier)
        category_scores["geopolitical"] = geo_score
        factors.extend(geo_factors)
        data_sources.extend(geo_sources)

        # --- Operational Risk ---
        ops_score, ops_factors = await self._score_operational(supplier)
        category_scores["operational"] = ops_score
        factors.extend(ops_factors)
        data_sources.append("internal:supplier_records")

        # --- Logistics Risk ---
        log_score, log_factors, log_sources = await self._score_logistics(supplier)
        category_scores["logistics"] = log_score
        factors.extend(log_factors)
        data_sources.extend(log_sources)

        # --- Dependency Risk ---
        dep_score, dep_factors = await self._score_dependency(supplier, organization_id)
        category_scores["dependency"] = dep_score
        factors.extend(dep_factors)
        data_sources.append("internal:supply_graph")

        # --- Composite Score ---
        overall = sum(
            category_scores.get(cat, 0) * weights.get(cat, 0)
            for cat in weights
        )

        result = RiskScoreResult(
            supplier_id=str(supplier.id),
            overall_score=round(overall, 2),
            category_scores={k: round(v, 2) for k, v in category_scores.items()},
            weights=weights,
            contributing_factors=[
                {
                    "description": f.description,
                    "category": f.category,
                    "score_contribution": f.score_contribution,
                    "source": f.source,
                    "evidence": f.evidence,
                }
                for f in sorted(factors, key=lambda x: x.score_contribution, reverse=True)
            ],
            data_sources=list(set(data_sources)),
        )

        log.info(
            "risk.score_calculated",
            supplier_id=str(supplier.id),
            overall=result.overall_score,
            version=self.SCORING_VERSION,
        )

        return result

    async def _score_climate(self, supplier: Supplier):
        """
        Score climate risk based on active weather events near supplier location.
        Uses RiskEvent table populated by NOAA/OpenWeather ingestion jobs.
        """
        factors = []
        sources = []
        base_score = 0.0

        if not supplier.country:
            return 0.0, [], []

        # Query active climate events for supplier's country/region
        result = await self.db.execute(
            select(RiskEvent).where(
                RiskEvent.category == RiskCategory.CLIMATE,
                RiskEvent.is_active == True,
            ).order_by(desc(RiskEvent.ingested_at)).limit(20)
        )
        events = result.scalars().all()

        # Filter to supplier geography
        relevant_events = [
            e for e in events
            if e.affected_countries and supplier.country in e.affected_countries
        ]

        if relevant_events:
            for event in relevant_events[:5]:
                # Record the actual source of each contributing event rather than
                # assuming a fixed set — keeps data_sources honest/explainable.
                if event.source:
                    sources.append(event.source)
                severity_map = {"extreme": 30, "severe": 20, "moderate": 10, "minor": 5}
                impact = severity_map.get(event.severity or "minor", 5)
                base_score = min(100, base_score + impact)
                factors.append(ScoringFactor(
                    description=event.title,
                    category="climate",
                    score_contribution=impact,
                    weight=DEFAULT_WEIGHTS["climate"],
                    source=event.source,
                    evidence=f"Event date: {event.event_date}",
                ))
        else:
            # No active climate events — score reflects baseline geographic risk
            # This is NOT a fake score; it means no events currently ingested
            factors.append(ScoringFactor(
                description=f"No active climate alerts for {supplier.country} in current dataset",
                category="climate",
                score_contribution=0,
                weight=DEFAULT_WEIGHTS["climate"],
                source="internal:risk_events",
                evidence="Score reflects absence of ingested climate events",
            ))

        return min(100.0, base_score), factors, sources

    async def _score_geopolitical(self, supplier: Supplier):
        """Score geopolitical risk from GDELT events and sanctions data."""
        factors = []
        sources = []
        base_score = 0.0

        result = await self.db.execute(
            select(RiskEvent).where(
                RiskEvent.category == RiskCategory.GEOPOLITICAL,
                RiskEvent.is_active == True,
            ).order_by(desc(RiskEvent.ingested_at)).limit(20)
        )
        events = result.scalars().all()

        relevant_events = [
            e for e in events
            if e.affected_countries and supplier.country in e.affected_countries
        ]

        if relevant_events:
            sources.append("gdelt")
            for event in relevant_events[:5]:
                severity_map = {"extreme": 35, "severe": 25, "moderate": 15, "minor": 5}
                impact = severity_map.get(event.severity or "minor", 5)
                base_score = min(100, base_score + impact)
                factors.append(ScoringFactor(
                    description=event.title,
                    category="geopolitical",
                    score_contribution=impact,
                    weight=DEFAULT_WEIGHTS["geopolitical"],
                    source="gdelt",
                    evidence=f"Ingested: {event.ingested_at.date()}",
                ))
        else:
            factors.append(ScoringFactor(
                description=f"No active geopolitical alerts for {supplier.country}",
                category="geopolitical",
                score_contribution=0,
                weight=DEFAULT_WEIGHTS["geopolitical"],
                source="internal:risk_events",
                evidence="No GDELT events currently matched to this geography",
            ))

        return min(100.0, base_score), factors, sources

    async def _score_operational(self, supplier: Supplier):
        """Score operational risk from internal supplier records."""
        factors = []
        base_score = 0.0

        # Status-based score
        status_scores = {
            "active": 0,
            "under_review": 30,
            "inactive": 50,
            "suspended": 80,
        }
        # `status` is normally the SupplierStatus enum, but tolerate a raw string
        # (e.g. set directly on a not-yet-reloaded ORM instance).
        status_value = supplier.status.value if hasattr(supplier.status, "value") else str(supplier.status)
        status_score = status_scores.get(status_value, 0)
        if status_score > 0:
            base_score += status_score
            factors.append(ScoringFactor(
                description=f"Supplier status: {status_value}",
                category="operational",
                score_contribution=status_score,
                weight=DEFAULT_WEIGHTS["operational"],
                source="internal:supplier_records",
            ))

        # Sole-source dependency check
        result = await self.db.execute(
            select(SupplierMaterial).where(
                SupplierMaterial.supplier_id == supplier.id,
                SupplierMaterial.is_sole_source == True,
            )
        )
        sole_source_materials = result.scalars().all()
        if sole_source_materials:
            sole_impact = min(40, len(sole_source_materials) * 10)
            base_score = min(100, base_score + sole_impact)
            factors.append(ScoringFactor(
                description=f"Sole-source supplier for {len(sole_source_materials)} material(s)",
                category="operational",
                score_contribution=sole_impact,
                weight=DEFAULT_WEIGHTS["operational"],
                source="internal:supplier_materials",
                evidence=f"No alternative source identified for these materials",
            ))

        # Missing certifications
        if not supplier.certifications:
            base_score = min(100, base_score + 10)
            factors.append(ScoringFactor(
                description="No quality certifications recorded",
                category="operational",
                score_contribution=10,
                weight=DEFAULT_WEIGHTS["operational"],
                source="internal:supplier_records",
            ))

        if not factors:
            factors.append(ScoringFactor(
                description="Supplier operational status is active with no flags",
                category="operational",
                score_contribution=0,
                weight=DEFAULT_WEIGHTS["operational"],
                source="internal:supplier_records",
            ))

        return min(100.0, base_score), factors

    async def _score_logistics(self, supplier: Supplier):
        """Score logistics risk from transportation disruption events."""
        factors = []
        sources = []
        base_score = 0.0

        result = await self.db.execute(
            select(RiskEvent).where(
                RiskEvent.category == RiskCategory.LOGISTICS,
                RiskEvent.is_active == True,
            ).limit(20)
        )
        events = result.scalars().all()

        relevant = [
            e for e in events
            if e.affected_countries and supplier.country in e.affected_countries
        ]

        if relevant:
            sources.append("port_congestion_api")
            for event in relevant[:3]:
                impact = 20
                base_score = min(100, base_score + impact)
                factors.append(ScoringFactor(
                    description=event.title,
                    category="logistics",
                    score_contribution=impact,
                    weight=DEFAULT_WEIGHTS["logistics"],
                    source=event.source,
                ))
        else:
            factors.append(ScoringFactor(
                description=f"No active logistics disruptions for {supplier.country}",
                category="logistics",
                score_contribution=0,
                weight=DEFAULT_WEIGHTS["logistics"],
                source="internal:risk_events",
            ))

        return min(100.0, base_score), factors, sources

    async def _score_dependency(self, supplier: Supplier, organization_id: str):
        """
        Score dependency risk: concentration of supply chain.
        Sole-source, geographic clustering, high tier concentration.
        """
        factors = []
        base_score = 0.0

        # Check how many downstream buyers depend on this supplier
        from src.models.supply_chain import SupplyRelationship
        result = await self.db.execute(
            select(SupplyRelationship).where(
                SupplyRelationship.from_supplier_id == supplier.id,
                SupplyRelationship.organization_id == organization_id,
                SupplyRelationship.is_active == True,
            )
        )
        downstream_rels = result.scalars().all()

        if len(downstream_rels) >= 5:
            impact = min(40, len(downstream_rels) * 5)
            base_score += impact
            factors.append(ScoringFactor(
                description=f"High criticality: {len(downstream_rels)} downstream buyers depend on this supplier",
                category="dependency",
                score_contribution=impact,
                weight=DEFAULT_WEIGHTS["dependency"],
                source="internal:supply_graph",
            ))

        # Geographic concentration (single country = higher risk)
        factors.append(ScoringFactor(
            description=f"Single-country supplier ({supplier.country}) — geographic concentration risk",
            category="dependency",
            score_contribution=10,
            weight=DEFAULT_WEIGHTS["dependency"],
            source="internal:supplier_records",
        ))
        base_score += 10

        return min(100.0, base_score), factors

    async def persist_score(self, result: RiskScoreResult, organization_id: str) -> RiskScore:
        """Save computed risk score to database."""
        score = RiskScore(
            supplier_id=result.supplier_id,
            organization_id=organization_id,
            overall_score=result.overall_score,
            climate_score=result.category_scores.get("climate"),
            geopolitical_score=result.category_scores.get("geopolitical"),
            operational_score=result.category_scores.get("operational"),
            logistics_score=result.category_scores.get("logistics"),
            dependency_score=result.category_scores.get("dependency"),
            weights=result.weights,
            contributing_factors=result.contributing_factors,
            data_sources=result.data_sources,
            scoring_version=result.scoring_version,
        )
        self.db.add(score)
        await self.db.flush()
        return score
