"""PROPHET prediction model."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin, TimestampMixin


class ProphetPrediction(TenantMixin, TimestampMixin, Base):
    """PROPHET ML-powered case outcome prediction."""

    __tablename__ = "prophet_predictions"

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
    prediction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="'outcome', 'amount', 'duration'",
    )
    predicted_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="0-1 for outcome, euros for amount, days for duration",
    )
    confidence_interval_low: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    confidence_interval_high: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="0.0-1.0",
    )
    model_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    features_used: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="All features used for prediction",
    )
    shap_values: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="SHAP explanation values",
    )
    risk_factors: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="[{'factor': '...', 'weight': 0.3}]",
    )
    positive_factors: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="[{'factor': '...', 'weight': 0.6}]",
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        comment="Most recent prediction for this case",
    )

    # Relationships
    # case: Mapped["Case"] = relationship("Case")

    def __repr__(self) -> str:
        return f"<ProphetPrediction {self.id} {self.prediction_type}>"
