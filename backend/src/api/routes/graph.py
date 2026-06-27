"""Supply chain graph API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.core import User
from src.services.graph_service import GraphService
from src.middleware.auth import get_current_user

router = APIRouter()


@router.get("/visualization")
async def get_graph_visualization(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns nodes and edges for D3.js/Cytoscape graph visualization.
    All data is real — derived from stored supplier relationships.
    """
    service = GraphService(db)
    return await service.get_graph_data_for_visualization(str(current_user.organization_id))


@router.get("/suppliers/{supplier_id}/upstream")
async def get_upstream_dependencies(
    supplier_id: str,
    max_depth: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Traverse upstream: who supplies to this supplier, up to max_depth tiers."""
    service = GraphService(db)
    return await service.get_upstream_dependencies(
        str(current_user.organization_id), supplier_id, max_depth
    )


@router.get("/tier-summary")
async def get_tier_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Supplier count by tier and overall graph statistics."""
    service = GraphService(db)
    return await service.get_tier_summary(str(current_user.organization_id))
