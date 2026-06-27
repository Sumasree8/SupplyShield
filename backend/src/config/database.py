"""
Async PostgreSQL database configuration.
Uses SQLAlchemy 2.0 async engine for non-blocking I/O.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from src.config.settings import get_settings

settings = get_settings()

# Connection-pool sizing only applies to server-backed drivers (e.g. asyncpg).
# SQLite's async dialect uses a non-queue pool and rejects pool_size/max_overflow,
# so we only pass them for non-SQLite URLs. This keeps the same module importable
# under SQLite for tests and lightweight local runs.
_engine_kwargs = {"echo": settings.DEBUG, "future": True}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
