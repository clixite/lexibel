"""Add status and email_address to oauth_tokens

Revision ID: 015
Revises: 014
Create Date: 2026-02-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status and email_address columns to oauth_tokens table."""
    # Add status column
    op.add_column(
        "oauth_tokens",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
            comment="Token status: active, expired, revoked",
        ),
    )

    # Add email_address column
    op.add_column(
        "oauth_tokens",
        sa.Column(
            "email_address",
            sa.String(255),
            nullable=True,
            comment="Email address associated with this OAuth token",
        ),
    )

    # Create index on status for efficient filtering
    op.create_index(
        "ix_oauth_tokens_status",
        "oauth_tokens",
        ["status"],
    )

    # Create index on email_address for lookups
    op.create_index(
        "ix_oauth_tokens_email_address",
        "oauth_tokens",
        ["email_address"],
    )


def downgrade() -> None:
    """Remove status and email_address columns from oauth_tokens table."""
    op.drop_index("ix_oauth_tokens_email_address", table_name="oauth_tokens")
    op.drop_index("ix_oauth_tokens_status", table_name="oauth_tokens")
    op.drop_column("oauth_tokens", "email_address")
    op.drop_column("oauth_tokens", "status")
