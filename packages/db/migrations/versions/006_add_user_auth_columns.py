"""LXB-MVP: Add hashed_password and mfa_secret columns to users table.

Revision ID: 006
Revises: 005
Create Date: 2026-02-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "hashed_password",
            sa.String(255),
            nullable=True,
            comment="bcrypt hash — NULL for OIDC/Azure AD users",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "mfa_secret",
            sa.String(32),
            nullable=True,
            comment="TOTP secret for MFA (base32-encoded)",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "hashed_password")
