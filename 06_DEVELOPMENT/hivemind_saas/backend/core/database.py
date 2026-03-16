"""
Async SQLAlchemy database setup with per-tenant RLS context.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create tables if they don't exist (dev only - use Alembic migrations in prod)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency - yields a database session."""
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def tenant_db_context(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Yields a session with the tenant_id set as a Postgres local variable.
    This activates Row-Level Security policies that filter by current_tenant_id.
    """
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("SET LOCAL app.current_tenant_id = :tid"),
            {"tid": tenant_id},
        )
        yield session
