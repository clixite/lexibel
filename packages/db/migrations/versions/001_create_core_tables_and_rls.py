"""LXB-005: Create core tables (tenants, users, audit_logs) with RLS policies.

Revision ID: 001
Revises: None
Create Date: 2026-02-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ──
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\"")

    # ── tenants ──
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(63), nullable=False, unique=True, index=True),
        sa.Column("plan", sa.String(20), nullable=False, server_default=sa.text("'solo'")),
        sa.Column("locale", sa.String(5), nullable=False, server_default=sa.text("'fr-BE'")),
        sa.Column("config", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    # No RLS on tenants — super-admin only access enforced at application layer.

    # ── users ──
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default=sa.text("'junior'")),
        sa.Column("auth_provider", sa.String(20), nullable=False, server_default=sa.text("'local'")),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("hourly_rate_cents", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    # ── audit_logs ──
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("action", sa.String(50), nullable=False, index=True),
        sa.Column("resource_type", sa.String(50), nullable=False, index=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )

    # ── Row-Level Security ──

    # -- users: tenant isolation
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_users ON users
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # -- audit_logs: tenant isolation
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_audit_logs ON audit_logs
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
    """)

    # ── audit_logs: INSERT-only (Principle P2) ──
    # Revoke UPDATE/DELETE for the application role.
    # The 'lexibel' role is the application connection user.
    op.execute("REVOKE UPDATE, DELETE ON audit_logs FROM lexibel")
    op.execute("GRANT INSERT, SELECT ON audit_logs TO lexibel")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO lexibel")


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_audit_logs ON audit_logs")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_users ON users")

    # Restore permissions
    op.execute("GRANT ALL ON audit_logs TO lexibel")

    # Drop tables in reverse dependency order
    op.drop_table("audit_logs")
    op.drop_table("users")
    op.drop_table("tenants")
