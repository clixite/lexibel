"""LXB-012: Create prophet_predictions and prophet_simulations tables.

Revision ID: 012
Revises: 011
Create Date: 2026-02-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── prophet_predictions ──
    op.create_table(
        "prophet_predictions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "prediction_type",
            sa.String(50),
            nullable=False,
            index=True,
            comment="'outcome', 'amount', 'duration'",
        ),
        sa.Column(
            "predicted_value",
            sa.Float,
            nullable=False,
            comment="0-1 for outcome, euros for amount, days for duration",
        ),
        sa.Column(
            "confidence_interval_low",
            sa.Float,
            nullable=False,
        ),
        sa.Column(
            "confidence_interval_high",
            sa.Float,
            nullable=False,
        ),
        sa.Column(
            "confidence_score",
            sa.Float,
            nullable=False,
            comment="0.0-1.0",
        ),
        sa.Column(
            "model_version",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "features_used",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="All features used for prediction",
        ),
        sa.Column(
            "shap_values",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="SHAP explanation values",
        ),
        sa.Column(
            "risk_factors",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="[{'factor': '...', 'weight': 0.3}]",
        ),
        sa.Column(
            "positive_factors",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="[{'factor': '...', 'weight': 0.6}]",
        ),
        sa.Column(
            "is_current",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Most recent prediction for this case",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # RLS for prophet_predictions
    op.execute("ALTER TABLE prophet_predictions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON prophet_predictions
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes for prophet_predictions
    op.create_index(
        "idx_prophet_predictions_tenant_case",
        "prophet_predictions",
        ["tenant_id", "case_id"],
    )
    op.create_index(
        "idx_prophet_predictions_is_current",
        "prophet_predictions",
        ["is_current"],
    )

    # ── prophet_simulations ──
    op.create_table(
        "prophet_simulations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "case_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "strategy_name",
            sa.String(100),
            nullable=False,
            index=True,
            comment="'procès', 'négociation', 'médiation'",
        ),
        sa.Column(
            "success_probability",
            sa.Float,
            nullable=False,
            comment="0.0-1.0",
        ),
        sa.Column(
            "estimated_amount_median",
            sa.Float,
            nullable=False,
            comment="Median estimated amount in euros",
        ),
        sa.Column(
            "estimated_amount_range_low",
            sa.Float,
            nullable=False,
        ),
        sa.Column(
            "estimated_amount_range_high",
            sa.Float,
            nullable=False,
        ),
        sa.Column(
            "estimated_duration_months",
            sa.Float,
            nullable=False,
        ),
        sa.Column(
            "estimated_costs",
            sa.Float,
            nullable=False,
            comment="Estimated costs in euros",
        ),
        sa.Column(
            "recommendation_score",
            sa.Float,
            nullable=False,
            comment="0.0-1.0 (higher = better strategy)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # RLS for prophet_simulations
    op.execute("ALTER TABLE prophet_simulations ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON prophet_simulations
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::uuid)
        """
    )

    # Indexes for prophet_simulations
    op.create_index(
        "idx_prophet_simulations_tenant_case",
        "prophet_simulations",
        ["tenant_id", "case_id"],
    )
    op.create_index(
        "idx_prophet_simulations_strategy",
        "prophet_simulations",
        ["strategy_name"],
    )


def downgrade() -> None:
    op.drop_table("prophet_simulations")
    op.drop_table("prophet_predictions")
