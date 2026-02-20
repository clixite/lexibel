"""LXB-019: Add metadata JSONB column to contacts table.

Stores extended Belgian-specific fields: civility, birth_date,
national_register, company_form, VAT number, etc.

Revision ID: 019
Revises: 018
Create Date: 2026-02-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contacts",
        sa.Column(
            "metadata",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Extended Belgian fields: civility, birth_date, national_register, etc.",
        ),
    )


def downgrade() -> None:
    op.drop_column("contacts", "metadata")
