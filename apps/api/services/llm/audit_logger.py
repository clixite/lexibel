"""AI Audit Logger for AI Act EU (Regulation 2024/1689) compliance.

Art. 13: Transparency — every AI usage is logged with full context.
Art. 14: Human oversight — human_validated flag for each LLM output.
Art. 17: Quality management — usage stats and DPIA report export.

GDPR Art. 35: Data Protection Impact Assessment (DPIA) is mandatory
for high-risk processing. This logger provides data for DPIA reports.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.models.ai_audit_log import AIAuditLog


class AIAuditLogger:
    """Audit logger for AI Act EU compliance."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def hash_content(content: str) -> str:
        """SHA-256 hash of content (never store the content itself)."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def log_request(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        provider: str,
        model: str,
        data_sensitivity: str,
        was_anonymized: bool,
        anonymization_method: str | None,
        prompt_content: str,
        purpose: str,
        metadata: dict | None = None,
    ) -> uuid.UUID:
        """Log an LLM request before sending it.

        Returns the audit log ID for later completion with log_response().
        """
        log = AIAuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider,
            model=model,
            data_sensitivity=data_sensitivity,
            was_anonymized=was_anonymized,
            anonymization_method=anonymization_method,
            prompt_hash=self.hash_content(prompt_content),
            purpose=purpose,
            metadata_=metadata or {},
        )
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log.id

    async def log_response(
        self,
        request_id: uuid.UUID,
        response_content: str,
        token_count_input: int | None = None,
        token_count_output: int | None = None,
        latency_ms: int | None = None,
        cost_estimate_eur: Decimal | None = None,
        error: str | None = None,
    ) -> None:
        """Complete an audit log entry with response data."""
        result = await self.session.execute(
            select(AIAuditLog).where(AIAuditLog.id == request_id)
        )
        log = result.scalar_one_or_none()
        if log is None:
            return

        log.response_hash = self.hash_content(response_content) if response_content else None
        log.token_count_input = token_count_input
        log.token_count_output = token_count_output
        log.latency_ms = latency_ms
        log.cost_estimate_eur = cost_estimate_eur
        log.error = error
        await self.session.flush()

    async def log_error(
        self,
        request_id: uuid.UUID,
        error: str,
    ) -> None:
        """Log an error for a failed request."""
        result = await self.session.execute(
            select(AIAuditLog).where(AIAuditLog.id == request_id)
        )
        log = result.scalar_one_or_none()
        if log is None:
            return
        log.error = error
        await self.session.flush()

    async def mark_human_validated(
        self,
        request_id: uuid.UUID,
        validator_id: uuid.UUID,
    ) -> None:
        """Mark an AI output as validated by a human (AI Act Art. 14)."""
        result = await self.session.execute(
            select(AIAuditLog).where(AIAuditLog.id == request_id)
        )
        log = result.scalar_one_or_none()
        if log is None:
            return

        log.human_validated = True
        log.human_validator_id = validator_id
        log.human_validated_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def get_audit_logs(
        self,
        tenant_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        provider: str | None = None,
        sensitivity: str | None = None,
        purpose: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list[AIAuditLog], int]:
        """Get paginated audit logs with filters."""
        query = select(AIAuditLog).where(AIAuditLog.tenant_id == tenant_id)

        if provider:
            query = query.where(AIAuditLog.provider == provider)
        if sensitivity:
            query = query.where(AIAuditLog.data_sensitivity == sensitivity)
        if purpose:
            query = query.where(AIAuditLog.purpose == purpose)
        if date_from:
            query = query.where(AIAuditLog.created_at >= date_from)
        if date_to:
            query = query.where(AIAuditLog.created_at <= date_to)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        # Paginate
        query = (
            query.order_by(AIAuditLog.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.session.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def get_usage_stats(
        self,
        tenant_id: uuid.UUID,
        days: int = 30,
    ) -> dict:
        """Usage statistics for the last N days.

        Returns breakdown by provider, sensitivity level, and cost.
        """
        cutoff = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        from datetime import timedelta

        cutoff = cutoff - timedelta(days=days)

        base = select(AIAuditLog).where(
            AIAuditLog.tenant_id == tenant_id,
            AIAuditLog.created_at >= cutoff,
        )

        # Total requests
        total_q = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(total_q)).scalar_one()

        # By provider
        by_provider_q = (
            select(
                AIAuditLog.provider,
                func.count().label("count"),
                func.sum(AIAuditLog.cost_estimate_eur).label("cost"),
                func.sum(AIAuditLog.token_count_input).label("tokens_in"),
                func.sum(AIAuditLog.token_count_output).label("tokens_out"),
                func.avg(AIAuditLog.latency_ms).label("avg_latency"),
            )
            .where(
                AIAuditLog.tenant_id == tenant_id,
                AIAuditLog.created_at >= cutoff,
            )
            .group_by(AIAuditLog.provider)
        )
        by_provider_rows = (await self.session.execute(by_provider_q)).all()
        by_provider = [
            {
                "provider": r.provider,
                "count": r.count,
                "cost_eur": float(r.cost) if r.cost else 0.0,
                "tokens_in": r.tokens_in or 0,
                "tokens_out": r.tokens_out or 0,
                "avg_latency_ms": round(float(r.avg_latency)) if r.avg_latency else 0,
            }
            for r in by_provider_rows
        ]

        # By sensitivity
        by_sens_q = (
            select(
                AIAuditLog.data_sensitivity,
                func.count().label("count"),
            )
            .where(
                AIAuditLog.tenant_id == tenant_id,
                AIAuditLog.created_at >= cutoff,
            )
            .group_by(AIAuditLog.data_sensitivity)
        )
        by_sens_rows = (await self.session.execute(by_sens_q)).all()
        by_sensitivity = {r.data_sensitivity: r.count for r in by_sens_rows}

        # Human validation rate
        validated_q = (
            select(func.count())
            .select_from(AIAuditLog)
            .where(
                AIAuditLog.tenant_id == tenant_id,
                AIAuditLog.created_at >= cutoff,
                AIAuditLog.human_validated.is_(True),
            )
        )
        validated = (await self.session.execute(validated_q)).scalar_one()

        # Total cost
        total_cost_q = (
            select(func.sum(AIAuditLog.cost_estimate_eur))
            .where(
                AIAuditLog.tenant_id == tenant_id,
                AIAuditLog.created_at >= cutoff,
            )
        )
        total_cost = (await self.session.execute(total_cost_q)).scalar_one()

        return {
            "period_days": days,
            "total_requests": total,
            "total_cost_eur": float(total_cost) if total_cost else 0.0,
            "human_validated_count": validated,
            "human_validation_rate": round(validated / total * 100, 1) if total > 0 else 0.0,
            "by_provider": by_provider,
            "by_sensitivity": by_sensitivity,
        }

    async def export_dpia_report(self, tenant_id: uuid.UUID) -> dict:
        """Export Data Protection Impact Assessment report.

        Required by GDPR Art. 35 for high-risk AI processing.
        """
        stats = await self.get_usage_stats(tenant_id, days=365)

        # Get distinct providers used
        providers_q = (
            select(AIAuditLog.provider)
            .where(AIAuditLog.tenant_id == tenant_id)
            .distinct()
        )
        providers = [
            r[0] for r in (await self.session.execute(providers_q)).all()
        ]

        # Anonymization stats
        anon_q = (
            select(
                func.count().label("total"),
                func.sum(
                    func.cast(AIAuditLog.was_anonymized, func.literal_column("integer"))
                ).label("anonymized"),
            )
            .where(AIAuditLog.tenant_id == tenant_id)
        )
        # Simpler approach
        total_q = select(func.count()).select_from(AIAuditLog).where(
            AIAuditLog.tenant_id == tenant_id
        )
        total_all = (await self.session.execute(total_q)).scalar_one()

        anon_count_q = select(func.count()).select_from(AIAuditLog).where(
            AIAuditLog.tenant_id == tenant_id,
            AIAuditLog.was_anonymized.is_(True),
        )
        anon_count = (await self.session.execute(anon_count_q)).scalar_one()

        # Error rate
        error_q = select(func.count()).select_from(AIAuditLog).where(
            AIAuditLog.tenant_id == tenant_id,
            AIAuditLog.error.isnot(None),
        )
        error_count = (await self.session.execute(error_q)).scalar_one()

        provider_details = {
            "mistral": {
                "name": "Mistral AI",
                "jurisdiction": "France (EU)",
                "dpa_signed": True,
                "data_residency": "100% EU (France)",
                "tier": 1,
                "transfer_basis": "No transfer — EU-native",
            },
            "gemini": {
                "name": "Google Gemini (Vertex AI)",
                "jurisdiction": "Belgium (EU) via europe-west1",
                "dpa_signed": True,
                "data_residency": "Belgium (Saint-Ghislain, europe-west1)",
                "tier": 1,
                "transfer_basis": "No transfer — EU data residency",
            },
            "anthropic": {
                "name": "Anthropic (Claude)",
                "jurisdiction": "US (EU-US DPF)",
                "dpa_signed": True,
                "data_residency": "US (EU-US Data Privacy Framework)",
                "tier": 1,
                "transfer_basis": "EU-US DPF adequacy decision (10 July 2023)",
            },
            "openai": {
                "name": "OpenAI (GPT-4o)",
                "jurisdiction": "US (EU-US DPF)",
                "dpa_signed": True,
                "data_residency": "US / EU via Azure OpenAI",
                "tier": 1,
                "transfer_basis": "EU-US DPF adequacy decision (10 July 2023)",
            },
            "deepseek": {
                "name": "DeepSeek",
                "jurisdiction": "China (no adequacy decision)",
                "dpa_signed": False,
                "data_residency": "China",
                "tier": 2,
                "restriction": "Only anonymized/pseudonymized data",
                "transfer_basis": "Art. 49(1)(a) GDPR — explicit consent + anonymization",
            },
            "glm": {
                "name": "GLM-4 (Zhipu AI)",
                "jurisdiction": "China (no adequacy decision)",
                "dpa_signed": False,
                "data_residency": "China",
                "tier": 3,
                "restriction": "Only public data (no personal data)",
                "transfer_basis": "No personal data transferred (public legal texts only)",
            },
            "kimi": {
                "name": "Kimi (Moonshot AI)",
                "jurisdiction": "China (no adequacy decision)",
                "dpa_signed": False,
                "data_residency": "China",
                "tier": 3,
                "restriction": "Only public data (no personal data)",
                "transfer_basis": "No personal data transferred (public legal texts only)",
            },
        }

        return {
            "report_type": "DPIA",
            "regulation": "GDPR Art. 35 + AI Act EU (2024/1689)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "system_classification": "HIGH-RISK (AI Act Annex III — administration of justice)",
            "processing_description": {
                "purpose": "AI-assisted legal document drafting, case analysis, and legal research",
                "legal_basis": "Legitimate interest + explicit client consent",
                "data_categories": [
                    "Legal case files (sensitive — professional secrecy Art. 458 C.P.)",
                    "Client personal data (GDPR Art. 9 special categories)",
                    "Published jurisprudence and legal doctrine (public)",
                ],
                "data_subjects": "Clients of the law firm, opposing parties, witnesses",
                "retention_period": "Audit logs: 5 years (Belgian limitation period)",
            },
            "sub_processors": {
                p: provider_details.get(p, {"name": p}) for p in providers
            },
            "safeguards": {
                "data_classification": "Automatic sensitivity classification (4 tiers)",
                "anonymization": "Automatic PII anonymization before non-EU transfers",
                "routing": "Tier-based provider routing — sensitive data never leaves EU",
                "audit_trail": "Complete logging of every LLM interaction",
                "human_oversight": "Human validation flag for AI-generated outputs",
                "encryption": "TLS 1.3 for all API communications",
            },
            "statistics": {
                "total_requests": total_all,
                "anonymized_requests": anon_count,
                "anonymization_rate": round(anon_count / total_all * 100, 1) if total_all > 0 else 0.0,
                "error_count": error_count,
                "error_rate": round(error_count / total_all * 100, 1) if total_all > 0 else 0.0,
                "usage_by_provider": stats["by_provider"],
                "usage_by_sensitivity": stats["by_sensitivity"],
                "human_validation_rate": stats["human_validation_rate"],
                "total_cost_eur": stats["total_cost_eur"],
            },
            "risk_assessment": {
                "identified_risks": [
                    "Transfer of sensitive legal data to non-EU jurisdictions",
                    "Potential re-identification of anonymized data",
                    "AI hallucination in legal context (incorrect legal advice)",
                    "Unauthorized access to audit logs",
                ],
                "mitigation_measures": [
                    "Tier-based routing: CRITICAL data → EU-only providers (Mistral)",
                    "Automatic anonymization with regex-based PII detection",
                    "Human-in-the-loop validation for all legal advice (AI Act Art. 14)",
                    "RLS + tenant isolation for audit logs",
                    "Hash-only storage of prompts/responses (no plaintext)",
                ],
                "residual_risk": "LOW — with all safeguards active",
            },
        }

    async def export_article30_register(self, tenant_id: uuid.UUID) -> dict:
        """Export GDPR Article 30 Record of Processing Activities.

        Required by GDPR Art. 30 for all processing activities.
        Must include: purposes, categories, recipients, transfers, retention.
        """
        # Get distinct providers used
        providers_q = (
            select(AIAuditLog.provider)
            .where(AIAuditLog.tenant_id == tenant_id)
            .distinct()
        )
        providers_used = [
            r[0] for r in (await self.session.execute(providers_q)).all()
        ]

        # Get distinct purposes
        purposes_q = (
            select(AIAuditLog.purpose)
            .where(AIAuditLog.tenant_id == tenant_id)
            .distinct()
        )
        purposes_used = [
            r[0] for r in (await self.session.execute(purposes_q)).all()
        ]

        provider_details = {
            "mistral": {
                "name": "Mistral AI (La Plateforme)",
                "country": "France",
                "transfer_mechanism": "N/A — EU-native processor",
                "dpa_reference": "Mistral AI DPA",
            },
            "gemini": {
                "name": "Google LLC (Vertex AI europe-west1)",
                "country": "Belgium (Saint-Ghislain)",
                "transfer_mechanism": "N/A — EU data residency (europe-west1)",
                "dpa_reference": "Google Cloud DPA",
            },
            "anthropic": {
                "name": "Anthropic PBC",
                "country": "United States",
                "transfer_mechanism": "EU-US Data Privacy Framework",
                "dpa_reference": "Anthropic API DPA",
            },
            "openai": {
                "name": "OpenAI LP",
                "country": "United States",
                "transfer_mechanism": "EU-US Data Privacy Framework",
                "dpa_reference": "OpenAI API DPA",
            },
            "deepseek": {
                "name": "DeepSeek (Hangzhou DeepSeek AI)",
                "country": "China",
                "transfer_mechanism": "Art. 49(1)(a) GDPR — only anonymized data",
                "dpa_reference": "N/A — no personal data transferred",
            },
            "glm": {
                "name": "Zhipu AI (Beijing Zhipu Huazhang)",
                "country": "China",
                "transfer_mechanism": "Art. 49 — only public legal data",
                "dpa_reference": "N/A — no personal data transferred",
            },
            "kimi": {
                "name": "Moonshot AI",
                "country": "China",
                "transfer_mechanism": "Art. 49 — only public legal data",
                "dpa_reference": "N/A — no personal data transferred",
            },
        }

        return {
            "register_type": "GDPR Article 30 — Record of Processing Activities",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "controller": {
                "name": "[Law Firm Name — to be configured per tenant]",
                "role": "Controller (Art. 4(7) GDPR)",
                "dpo_contact": "[DPO contact — to be configured]",
            },
            "processing_activities": [
                {
                    "activity": "AI-assisted legal document analysis and generation",
                    "purposes": purposes_used or [
                        "case_analysis",
                        "document_draft",
                        "legal_research",
                        "translation",
                        "summarization",
                    ],
                    "legal_basis": "Art. 6(1)(f) GDPR — legitimate interest + Art. 9(2)(f) for judicial data",
                    "categories_of_data_subjects": [
                        "Clients of the law firm",
                        "Opposing parties",
                        "Witnesses",
                        "Third parties mentioned in legal documents",
                    ],
                    "categories_of_personal_data": [
                        "Names and identification data",
                        "National registry numbers (NISS)",
                        "Contact information (address, phone, email)",
                        "Financial data (IBAN, BCE/TVA)",
                        "Legal case data (judicial, potentially Art. 10 GDPR)",
                        "Health data (if relevant to case, Art. 9 GDPR)",
                    ],
                    "recipients": {
                        p: provider_details.get(p, {"name": p})
                        for p in providers_used
                    },
                    "international_transfers": [
                        {
                            "provider": p,
                            "country": provider_details.get(p, {}).get("country", "Unknown"),
                            "mechanism": provider_details.get(p, {}).get(
                                "transfer_mechanism", "Unknown"
                            ),
                        }
                        for p in providers_used
                        if provider_details.get(p, {}).get("country", "") not in (
                            "France", "Belgium (Saint-Ghislain)"
                        )
                    ],
                    "retention_period": "Audit logs: 5 years (Belgian limitation period). "
                    "Prompt/response content: NOT stored (professional secrecy Art. 458 C.P.).",
                    "security_measures": [
                        "Automatic data sensitivity classification (4 tiers)",
                        "Automatic PII anonymization before non-EU transfers",
                        "Tier-based provider routing (sensitive data restricted to EU)",
                        "TLS 1.3 encryption in transit",
                        "AES-256 encryption for stored API keys",
                        "Row-Level Security (RLS) for multi-tenant isolation",
                        "SHA-256 hash-only storage (no plaintext prompts/responses)",
                        "Human-in-the-loop validation (AI Act Art. 14)",
                        "Complete audit trail for every AI interaction",
                    ],
                },
            ],
        }
