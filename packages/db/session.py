"""Async session factory with RLS tenant isolation.

Every database session sets `app.current_tenant_id` via SET LOCAL,
which scopes all RLS-enabled queries to a single tenant.
"""
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

# Default dev DSN — overridden by environment variable in production.
_DEFAULT_DSN = "postgresql+asyncpg://lexibel:lexibel_dev_2026@localhost:5432/lexibel"

engine = create_async_engine(
    _DEFAULT_DSN,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def configure_engine(database_url: str) -> None:
    """Reconfigure the module-level engine (call once at app startup)."""
    global engine, async_session_factory
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@asynccontextmanager
async def get_tenant_session(
    tenant_id: uuid.UUID,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession with RLS scoped to *tenant_id*.

    Usage::

        async with get_tenant_session(tenant_id) as session:
            result = await session.execute(select(User))
    """
    async with async_session_factory() as session:
        async with session.begin():
            # SET LOCAL is transaction-scoped: automatically reset on COMMIT/ROLLBACK.
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
            yield session


@asynccontextmanager
async def get_superadmin_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession WITHOUT tenant scoping (super-admin only).

    Use sparingly — bypasses RLS for cross-tenant operations like
    tenant provisioning and system-wide analytics.
    """
    async with async_session_factory() as session:
        async with session.begin():
            yield session
