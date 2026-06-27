"""
Risk intelligence models: RiskScore, Alert, RiskEvent.
Every score is explainable — no black-box outputs.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import String, DateTime, ForeignKey, Text, Float, Integer, Boolean
from sqlalchemy import Enum as SAEnum
from src.models.types import GUID, JSONColumn
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.config.database import Base


class RiskCategory(str, Enum):
    CLIMATE = "climate"
    GEOPOLITICAL = "geopolitical"
    OPERATIONAL = "operational"
    LOGISTICS = "logistics"
    DEPENDENCY = "dependency"
    FINANCIAL = "financial"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    CREATED = "created"
    ASSIGNED = "assigned"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Allowed status transitions for the alert lifecycle. Any transition not listed
# here is rejected by the API. CLOSED is terminal.
ALERT_STATUS_TRANSITIONS: dict[AlertStatus, set[AlertStatus]] = {
    AlertStatus.CREATED: {AlertStatus.ASSIGNED, AlertStatus.INVESTIGATING, AlertStatus.CLOSED},
    AlertStatus.ASSIGNED: {AlertStatus.INVESTIGATING, AlertStatus.RESOLVED, AlertStatus.CLOSED},
    AlertStatus.INVESTIGATING: {AlertStatus.RESOLVED, AlertStatus.CLOSED},
    AlertStatus.RESOLVED: {AlertStatus.INVESTIGATING, AlertStatus.CLOSED},
    AlertStatus.CLOSED: set(),
}


def is_valid_alert_transition(current: AlertStatus, target: AlertStatus) -> bool:
    """True if an alert may move from `current` to `target`."""
    if current == target:
        return False
    return target in ALERT_STATUS_TRANSITIONS.get(current, set())


class RiskScore(Base):
    """
    Composite risk score for a supplier at a point in time.
    All sub-scores stored for full explainability.
    """
    __tablename__ = "risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), nullable=False)

    # Overall composite score (0-100, higher = more risk)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Category sub-scores
    climate_score: Mapped[Optional[float]] = mapped_column(Float)
    geopolitical_score: Mapped[Optional[float]] = mapped_column(Float)
    operational_score: Mapped[Optional[float]] = mapped_column(Float)
    logistics_score: Mapped[Optional[float]] = mapped_column(Float)
    dependency_score: Mapped[Optional[float]] = mapped_column(Float)
    financial_score: Mapped[Optional[float]] = mapped_column(Float)

    # Weights applied (must sum to 1.0)
    weights: Mapped[Optional[dict]] = mapped_column(JSONColumn())

    # Full explainability: factors that contributed to score
    contributing_factors: Mapped[Optional[list]] = mapped_column(JSONColumn())
    # Example:
    # [
    #   {"factor": "Hurricane season active in Gulf of Mexico", "category": "climate", "impact": 15},
    #   {"factor": "Trade tensions US-China elevated", "category": "geopolitical", "impact": 20},
    # ]

    # Data sources used for this calculation
    data_sources: Mapped[Optional[list]] = mapped_column(JSONColumn())

    scoring_version: Mapped[str] = mapped_column(String(20), default="1.0")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="risk_scores")


class Alert(Base):
    """
    Early warning alert with full lifecycle tracking.
    """
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), nullable=False)
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("suppliers.id"))
    risk_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("risk_events.id"))

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[RiskCategory] = mapped_column(SAEnum(RiskCategory), nullable=False, index=True)
    severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity), nullable=False, index=True)
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus), default=AlertStatus.CREATED, index=True)

    # Assignment
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id"))

    # Alert trigger details
    trigger_type: Mapped[str] = mapped_column(String(50))  # threshold, trend, region, manual
    trigger_data: Mapped[Optional[dict]] = mapped_column(JSONColumn())

    # Notification tracking
    notifications_sent: Mapped[Optional[list]] = mapped_column(JSONColumn(), default=list)

    # Lifecycle timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)

    supplier: Mapped[Optional["Supplier"]] = relationship("Supplier")
    assigned_to: Mapped[Optional["User"]] = relationship("User")
    status_history: Mapped[List["AlertStatusHistory"]] = relationship("AlertStatusHistory", back_populates="alert")


class AlertStatusHistory(Base):
    """Full audit trail of alert status changes."""
    __tablename__ = "alert_status_history"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("alerts.id"), nullable=False, index=True)
    changed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("users.id"))
    from_status: Mapped[Optional[AlertStatus]] = mapped_column(SAEnum(AlertStatus))
    to_status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    alert: Mapped["Alert"] = relationship("Alert", back_populates="status_history")


class RiskEvent(Base):
    """
    External risk event ingested from APIs (NOAA, GDELT, etc.).
    """
    __tablename__ = "risk_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # noaa, gdelt, openweather, etc.
    source_event_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    category: Mapped[RiskCategory] = mapped_column(SAEnum(RiskCategory), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    severity: Mapped[Optional[str]] = mapped_column(String(50))
    affected_countries: Mapped[Optional[list]] = mapped_column(JSONColumn())
    affected_regions: Mapped[Optional[list]] = mapped_column(JSONColumn())
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONColumn())
    event_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# Avoid circular imports
from src.models.supply_chain import Supplier  # noqa
from src.models.core import User  # noqa
