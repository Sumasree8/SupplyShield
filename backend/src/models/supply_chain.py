"""
Supply chain models: Suppliers, Materials, Products, Facilities, Relationships.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Float, Integer, JSON
from sqlalchemy import Enum as SAEnum, UniqueConstraint
from src.models.types import GUID, JSONColumn
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.config.database import Base


class SupplierTier(int, Enum):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3
    TIER_4_PLUS = 4


class SupplierStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_REVIEW = "under_review"
    SUSPENDED = "suspended"


class RelationshipType(str, Enum):
    SUPPLIES_TO = "SUPPLIES_TO"
    DEPENDS_ON = "DEPENDS_ON"
    SHIPS_TO = "SHIPS_TO"
    PRODUCES = "PRODUCES"
    USES_MATERIAL = "USES_MATERIAL"


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)  # ERP/external reference
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(500))
    country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[SupplierStatus] = mapped_column(SAEnum(SupplierStatus), default=SupplierStatus.ACTIVE, index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(200))
    annual_revenue_usd: Mapped[Optional[float]] = mapped_column(Float)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer)
    website: Mapped[Optional[str]] = mapped_column(String(500))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    certifications: Mapped[Optional[dict]] = mapped_column(JSONColumn(), default=dict)  # ISO, etc.
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship("Organization", back_populates="suppliers")
    materials: Mapped[List["SupplierMaterial"]] = relationship("SupplierMaterial", back_populates="supplier")
    facilities: Mapped[List["Facility"]] = relationship("Facility", back_populates="supplier")
    risk_scores: Mapped[List["RiskScore"]] = relationship("RiskScore", back_populates="supplier")

    # Outbound: this supplier supplies to others
    supply_relationships_out: Mapped[List["SupplyRelationship"]] = relationship(
        "SupplyRelationship", foreign_keys="SupplyRelationship.from_supplier_id", back_populates="from_supplier"
    )
    # Inbound: other suppliers supply to this one
    supply_relationships_in: Mapped[List["SupplyRelationship"]] = relationship(
        "SupplyRelationship", foreign_keys="SupplyRelationship.to_supplier_id", back_populates="to_supplier"
    )


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(200))
    hs_code: Mapped[Optional[str]] = mapped_column(String(20))  # Harmonized System code
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(50))
    criticality: Mapped[Optional[str]] = mapped_column(String(50))  # low, medium, high, critical
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    suppliers: Mapped[List["SupplierMaterial"]] = relationship("SupplierMaterial", back_populates="material")


class SupplierMaterial(Base):
    """Junction: which materials a supplier provides."""
    __tablename__ = "supplier_materials"
    __table_args__ = (UniqueConstraint("supplier_id", "material_id"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("materials.id"), nullable=False)
    is_sole_source: Mapped[bool] = mapped_column(Boolean, default=False)
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer)
    annual_spend_usd: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="materials")
    material: Mapped["Material"] = relationship("Material", back_populates="suppliers")


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    facility_type: Mapped[str] = mapped_column(String(100))  # manufacturing, warehouse, port, etc.
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    capacity_units: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="facilities")


class SupplyRelationship(Base):
    """
    Directed edge: from_supplier SUPPLIES_TO to_supplier.
    Maps to Neo4j SUPPLIES_TO relationship.
    """
    __tablename__ = "supply_relationships"
    __table_args__ = (UniqueConstraint("from_supplier_id", "to_supplier_id", "material_id"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), nullable=False)
    from_supplier_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False)
    to_supplier_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("suppliers.id"), nullable=False)
    material_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("materials.id"))
    relationship_type: Mapped[RelationshipType] = mapped_column(SAEnum(RelationshipType), default=RelationshipType.SUPPLIES_TO)
    annual_volume_usd: Mapped[Optional[float]] = mapped_column(Float)
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer)
    contract_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    from_supplier: Mapped["Supplier"] = relationship("Supplier", foreign_keys=[from_supplier_id], back_populates="supply_relationships_out")
    to_supplier: Mapped["Supplier"] = relationship("Supplier", foreign_keys=[to_supplier_id], back_populates="supply_relationships_in")


# Import here to avoid circular imports
from src.models.core import Organization  # noqa
from src.models.risk import RiskScore  # noqa
