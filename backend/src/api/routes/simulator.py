"""Supply chain disruption impact simulator — Phase 4."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.core import User
from src.services.graph_service import GraphService
from src.middleware.auth import get_current_user

router = APIRouter()


@router.post("/suppliers/{supplier_id}/disruption")
async def simulate_disruption(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simulate: what happens if this supplier goes offline?
    Returns cascading impact across the supply chain graph.
    All impact derived from real stored relationships.
    """
    service = GraphService(db)
    result = await service.simulate_disruption_impact(
        str(current_user.organization_id), supplier_id
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
