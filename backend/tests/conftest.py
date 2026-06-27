"""
Shared pytest fixtures.

Spins up a real in-memory SQLite database (shared across the test via a
StaticPool) and a real ASGI client wired to the FastAPI app, with the `get_db`
dependency overridden to use the test database. These tests exercise the actual
application code — routes, services, middleware, ORM models — not re-implemented
copies of it.
"""
import os

# Must be set before any `src` import so get_settings() (lru_cached) picks them up.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.config.database import Base, get_db
from src.main import create_app
from src.middleware.rate_limit import reset_rate_limits
from src.models.core import Organization, User, UserRole
from src.services.auth_service import hash_password, create_access_token

# Import all model modules so every table is registered on Base.metadata.
import src.models.core  # noqa: F401
import src.models.supply_chain  # noqa: F401
import src.models.risk  # noqa: F401


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Each test starts with a clean rate-limit window."""
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest_asyncio.fixture
async def engine():
    """A fresh in-memory database per test, shared across sessions via StaticPool."""
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(session_factory) -> AsyncSession:
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(session_factory):
    """ASGI client with get_db overridden to use the test database."""
    app = create_app()

    async def _override_get_db():
        async with session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


# ── Data helpers ──────────────────────────────────────────────────────────────

async def make_org_and_user(
    db: AsyncSession,
    *,
    email: str = "admin@acme.test",
    role: UserRole = UserRole.ADMIN,
    org_name: str = "Acme Corp",
    password: str = "SuperSecret123!",
) -> User:
    org = Organization(name=org_name, industry="Manufacturing")
    db.add(org)
    await db.flush()
    user = User(
        organization_id=org.id,
        email=email,
        hashed_password=hash_password(password),
        full_name="Test User",
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def auth_header(user: User) -> dict:
    token = create_access_token(str(user.id), str(user.organization_id), user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_user(db):
    return await make_org_and_user(db, email="admin@acme.test", role=UserRole.ADMIN)
