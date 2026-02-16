"""005 — Create migration_jobs and migration_mappings tables.

Revision ID: 005
Revises: 004
"""

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

TABLES = {
    "migration_jobs": """
        CREATE TABLE migration_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            source_system VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            total_records INT NOT NULL DEFAULT 0,
            imported_records INT NOT NULL DEFAULT 0,
            failed_records INT NOT NULL DEFAULT 0,
            error_log JSONB NOT NULL DEFAULT '[]'::jsonb,
            file_path TEXT,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """,
    "migration_mappings": """
        CREATE TABLE migration_mappings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
            job_id UUID NOT NULL REFERENCES migration_jobs(id) ON DELETE CASCADE,
            source_field VARCHAR(255) NOT NULL,
            target_table VARCHAR(100) NOT NULL,
            target_field VARCHAR(100) NOT NULL,
            transform_rule JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """,
}


def upgrade() -> None:
    for table_name, ddl in TABLES.items():
        op.execute(ddl)

        # Indexes
        op.execute(f"CREATE INDEX ix_{table_name}_tenant_id ON {table_name}(tenant_id)")

        # RLS
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""CREATE POLICY tenant_isolation ON {table_name}
                USING (tenant_id = current_setting('app.current_tenant_id')::uuid)"""
        )

    # Extra index for job lookup
    op.execute("CREATE INDEX ix_migration_jobs_status ON migration_jobs(status)")
    op.execute(
        "CREATE INDEX ix_migration_mappings_job_id ON migration_mappings(job_id)"
    )


def downgrade() -> None:
    for table_name in reversed(list(TABLES.keys())):
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
