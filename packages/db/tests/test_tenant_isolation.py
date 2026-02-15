"""LXB-005: Test that RLS enforces strict tenant isolation.

Tenant A must NEVER see Tenant B data.
Uses a real PostgreSQL database with RLS policies active.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.db.base import Base
from packages.db.models.tenant import Tenant
from packages.db.models.user import User
from packages.db.models.audit_log import AuditLog


# ── Fixtures ──

TEST_DATABASE_URL = "postgresql+asyncpg://lexibel:lexibel_dev_2026@localhost:5432/lexibel_test"

TENANT_A_ID = uuid.uuid4()
TENANT_B_ID = uuid.uuid4()


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Enable RLS on users and audit_logs
        await conn.execute(text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text("ALTER TABLE users FORCE ROW LEVEL SECURITY"))
        await conn.execute(text("""
            CREATE POLICY IF NOT EXISTS tenant_isolation_users ON users
                USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        """))
        await conn.execute(text("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY"))
        await conn.execute(text("""
            CREATE POLICY IF NOT EXISTS tenant_isolation_audit_logs ON audit_logs
                USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        """))

    yield eng

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(scope="module")
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True, scope="module")
async def seed_data(session_factory):
    """Insert two tenants with one user each."""
    async with session_factory() as session:
        async with session.begin():
            # Create tenants (no RLS on tenants table)
            tenant_a = Tenant(id=TENANT_A_ID, name="Cabinet Alpha", slug="alpha")
            tenant_b = Tenant(id=TENANT_B_ID, name="Cabinet Beta", slug="beta")
            session.add_all([tenant_a, tenant_b])

        async with session.begin():
            # Create users scoped to each tenant
            user_a = User(
                tenant_id=TENANT_A_ID,
                email="alice@alpha.be",
                full_name="Alice Alpha",
                role="partner",
            )
            user_b = User(
                tenant_id=TENANT_B_ID,
                email="bob@beta.be",
                full_name="Bob Beta",
                role="associate",
            )
            session.add_all([user_a, user_b])

        async with session.begin():
            # Create audit logs scoped to each tenant
            log_a = AuditLog(
                tenant_id=TENANT_A_ID,
                action="LOGIN",
                resource_type="user",
            )
            log_b = AuditLog(
                tenant_id=TENANT_B_ID,
                action="LOGIN",
                resource_type="user",
            )
            session.add_all([log_a, log_b])


# ── Tests ──


@pytest.mark.asyncio
async def test_tenant_a_sees_only_own_users(session_factory: async_sessionmaker) -> None:
    """Tenant A must only see users belonging to Tenant A."""
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )
            result = await session.execute(select(User))
            users = result.scalars().all()

    assert len(users) == 1
    assert users[0].email == "alice@alpha.be"
    assert users[0].tenant_id == TENANT_A_ID


@pytest.mark.asyncio
async def test_tenant_b_sees_only_own_users(session_factory: async_sessionmaker) -> None:
    """Tenant B must only see users belonging to Tenant B."""
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tid"),
                {"tid": str(TENANT_B_ID)},
            )
            result = await session.execute(select(User))
            users = result.scalars().all()

    assert len(users) == 1
    assert users[0].email == "bob@beta.be"
    assert users[0].tenant_id == TENANT_B_ID


@pytest.mark.asyncio
async def test_tenant_a_cannot_see_tenant_b_audit_logs(session_factory: async_sessionmaker) -> None:
    """Tenant A must not see Tenant B's audit logs."""
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :tid"),
                {"tid": str(TENANT_A_ID)},
            )
            result = await session.execute(select(AuditLog))
            logs = result.scalars().all()

    assert len(logs) == 1
    assert logs[0].tenant_id == TENANT_A_ID


@pytest.mark.asyncio
async def test_cross_tenant_isolation_symmetric(session_factory: async_sessionmaker) -> None:
    """Both tenants must be fully isolated — no data leakage in either direction."""
    for tenant_id, expected_email in [
        (TENANT_A_ID, "alice@alpha.be"),
        (TENANT_B_ID, "bob@beta.be"),
    ]:
        async with session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("SET LOCAL app.current_tenant_id = :tid"),
                    {"tid": str(tenant_id)},
                )
                result = await session.execute(select(User))
                users = result.scalars().all()

        assert len(users) == 1, f"Tenant {tenant_id} sees {len(users)} users instead of 1"
        assert users[0].email == expected_email
