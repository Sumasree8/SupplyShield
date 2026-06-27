"""Health check endpoint for load balancers and monitoring."""
import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.config.graph_db import get_graph_driver

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    checks = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Graph database check
    try:
        driver = get_graph_driver()
        if driver:
            # Neo4j driver is synchronous — offload so we don't block the loop.
            await asyncio.to_thread(driver.verify_connectivity)
            checks["graph_database"] = "ok"
        else:
            checks["graph_database"] = "not_configured (using NetworkX fallback)"
    except Exception as e:
        checks["graph_database"] = f"error: {str(e)}"

    all_ok = all("ok" in str(v) for v in checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
        "version": "1.0.0",
    }
