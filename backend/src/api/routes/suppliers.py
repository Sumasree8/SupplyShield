"""Supplier management API routes."""
import math
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.core import AuditLog, User
from src.models.supply_chain import Supplier, SupplyRelationship
from src.services.graph_service import GraphService
from src.api.schemas.suppliers import (
    SupplierCreate, SupplierUpdate, SupplierResponse,
    SupplyRelationshipCreate, SupplyRelationshipResponse, PaginatedResponse
)
from src.middleware.auth import get_current_user, require_permission

log = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tier: Optional[int] = Query(None),
    country: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List suppliers with filtering and pagination."""
    query = select(Supplier).where(
        Supplier.organization_id == current_user.organization_id,
        Supplier.is_active == True,
    )

    if tier is not None:
        query = query.where(Supplier.tier == tier)
    if country:
        query = query.where(Supplier.country == country)
    if status:
        query = query.where(Supplier.status == status)
    if search:
        query = query.where(or_(
            Supplier.name.ilike(f"%{search}%"),
            Supplier.country.ilike(f"%{search}%"),
        ))

    # Count total
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Supplier.tier, Supplier.name)
    result = await db.execute(query)
    suppliers = result.scalars().all()

    return PaginatedResponse(
        items=[SupplierResponse.model_validate(s) for s in suppliers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
    )


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:write")),
):
    supplier = Supplier(
        organization_id=current_user.organization_id,
        **payload.model_dump(exclude_none=True),
    )
    db.add(supplier)
    await db.flush()

    # Sync to Neo4j if available
    graph_service = GraphService(db)
    await graph_service.upsert_supplier_in_neo4j(supplier)

    # Audit
    db.add(AuditLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="create_supplier",
        resource_type="supplier",
        resource_id=str(supplier.id),
    ))

    log.info("supplier.created", supplier_id=str(supplier.id), name=supplier.name, tier=supplier.tier)
    return SupplierResponse.model_validate(supplier)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return SupplierResponse.model_validate(supplier)


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:write")),
):
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    update_data = payload.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)

    await db.flush()

    db.add(AuditLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="update_supplier",
        resource_type="supplier",
        resource_id=supplier_id,
        detail=str(update_data),
    ))

    return SupplierResponse.model_validate(supplier)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:delete")),
):
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    supplier.is_active = False  # Soft delete

    db.add(AuditLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="delete_supplier",
        resource_type="supplier",
        resource_id=supplier_id,
    ))


@router.post("/relationships", response_model=SupplyRelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    payload: SupplyRelationshipCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("suppliers:write")),
):
    """Create a supply chain relationship between two suppliers."""
    rel = SupplyRelationship(
        organization_id=current_user.organization_id,
        **payload.model_dump(exclude_none=True),
    )
    db.add(rel)
    await db.flush()

    # Sync to Neo4j
    graph_service = GraphService(db)
    await graph_service.upsert_relationship_in_neo4j(rel)

    db.add(AuditLog(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        action="create_relationship",
        resource_type="supply_relationship",
        resource_id=str(rel.id),
    ))

    return SupplyRelationshipResponse.model_validate(rel)
