"""PROPHET simulation model."""

import uuid

from sqlalchemy import Float, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class ProphetSimulation(TenantMixin, TimestampMixin, Base):
    """PROPHET strategy simulation (procès, négociation, médiation)."""

    __tablename__ = "prophet_simulations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="'procès', 'négociation', 'médiation'",
    )
    success_probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="0.0-1.0",
    )
    estimated_amount_median: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Median estimated amount in euros",
    )
    estimated_amount_range_low: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    estimated_amount_range_high: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    estimated_duration_months: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    estimated_costs: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Estimated costs in euros",
    )
    recommendation_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="0.0-1.0 (higher = better strategy)",
    )

    def __repr__(self) -> str:
        return f"<ProphetSimulation {self.id} {self.strategy_name}>"
