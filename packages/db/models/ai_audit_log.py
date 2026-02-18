"""AI Audit Log model — append-only, INSERT only.

Tracks every LLM API call for AI Act EU (Regulation 2024/1689) compliance.
Art. 13: Transparency — every AI usage is logged.
Art. 14: Human oversight — human_validated flag.
Art. 17: Quality management — performance metrics per provider.

Protected by RLS via tenant_id.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base, TenantMixin


class AIAuditLog(TenantMixin, Base):
    __tablename__ = "ai_audit_logs"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who initiated the LLM request",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="anthropic, openai, mistral, deepseek, glm, kimi",
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="claude-sonnet-4-20250514, gpt-4o, mistral-large-latest, etc.",
    )
    data_sensitivity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="public, semi, sensitive, critical",
    )
    was_anonymized: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    anonymization_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="regex_replacement, none",
    )
    prompt_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of the prompt (never the content itself)",
    )
    response_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of the response",
    )
    token_count_input: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    token_count_output: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    cost_estimate_eur: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    purpose: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="case_analysis, document_draft, legal_research, etc.",
    )
    human_validated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="AI Act Art. 14 — human-in-the-loop validation",
    )
    human_validator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who validated the AI output",
    )
    human_validated_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if the request failed",
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Additional context: routing decision, fallback chain, etc.",
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<AIAuditLog {self.id} {self.provider}/{self.model} [{self.data_sensitivity}]>"
