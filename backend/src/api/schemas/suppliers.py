"""Supplier API schemas."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, EmailStr, BeforeValidator


def _to_str(v):
    """Coerce UUID (or any id) to its string form for JSON responses.

    ORM attributes backed by UUID columns return ``uuid.UUID`` objects on both
    PostgreSQL and SQLite; Pydantic v2 will not implicitly cast those to ``str``.
    """
    return str(v) if v is not None else v


# A string id field that accepts uuid.UUID / str from ORM attributes.
StrId = Annotated[str, BeforeValidator(_to_str)]
OptStrId = Annotated[Optional[str], BeforeValidator(_to_str)]


class SupplierCreate(BaseModel):
    name: str
    legal_name: Optional[str] = None
    country: str
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tier: int
    industry: Optional[str] = None
    annual_revenue_usd: Optional[float] = None
    employee_count: Optional[int] = None
    website: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    certifications: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    external_id: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tier: Optional[int] = None
    status: Optional[str] = None
    industry: Optional[str] = None
    annual_revenue_usd: Optional[float] = None
    employee_count: Optional[int] = None
    certifications: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class SupplierResponse(BaseModel):
    id: StrId
    organization_id: StrId
    external_id: Optional[str]
    name: str
    legal_name: Optional[str]
    country: str
    region: Optional[str]
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    tier: int
    status: str
    industry: Optional[str]
    annual_revenue_usd: Optional[float]
    employee_count: Optional[int]
    website: Optional[str]
    contact_email: Optional[str]
    certifications: Optional[Dict[str, Any]]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplyRelationshipCreate(BaseModel):
    from_supplier_id: str
    to_supplier_id: str
    material_id: Optional[str] = None
    relationship_type: str = "SUPPLIES_TO"
    annual_volume_usd: Optional[float] = None
    lead_time_days: Optional[int] = None


class SupplyRelationshipResponse(BaseModel):
    id: StrId
    from_supplier_id: StrId
    to_supplier_id: StrId
    material_id: OptStrId = None
    relationship_type: str
    annual_volume_usd: Optional[float]
    lead_time_days: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
