"""
SupplyShield AI - Backend API Server
Production-grade Supply Chain Risk Intelligence Platform
"""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import make_asgi_app

from src.api.routes import auth, suppliers, graph, risk, alerts, users, simulator, health, recommendations
from src.config.settings import get_settings
from src.config.database import engine, Base
from src.config.graph_db import get_graph_driver
from src.middleware.logging import RequestLoggingMiddleware

log = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    log.info("supplychield.startup", version="1.0.0", environment=settings.ENVIRONMENT)

    # Initialize relational database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("database.initialized")

    # Verify graph database connection (sync driver — offload to a thread)
    try:
        driver = get_graph_driver()
        if driver:
            await asyncio.to_thread(driver.verify_connectivity)
            log.info("graph_database.connected")
        else:
            log.info("graph_database.not_configured", fallback="networkx")
    except Exception as e:
        log.warning("graph_database.unavailable", error=str(e), fallback="networkx")

    yield

    log.info("supplychield.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SupplyShield AI API",
        description="Enterprise Supply Chain Risk Intelligence Platform",
        version="1.0.0",
        docs_url="/api/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/api/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/api/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # NOTE: Starlette runs middleware in reverse order of registration — the
    # LAST one added is the OUTERMOST. We register CORS last so it wraps every
    # response (including those short-circuited by inner middleware).

    # Inner: structured request logging + Prometheus metrics
    app.add_middleware(RequestLoggingMiddleware)

    # Host allow-listing
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

    # Outermost: CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Register routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["Suppliers"])
    app.include_router(graph.router, prefix="/api/v1/graph", tags=["Supply Chain Graph"])
    app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk Intelligence"])
    app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Early Warning Alerts"])
    app.include_router(simulator.router, prefix="/api/v1/simulator", tags=["Disruption Simulator"])
    app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["Alternative Suppliers"])

    return app


app = create_app()
