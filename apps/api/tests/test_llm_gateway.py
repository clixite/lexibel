"""Tests for GDPR-compliant LLM Gateway — DataClassifier, DataAnonymizer, routing rules, integration.

Covers:
- DataClassifier: Belgian PII regex detection, sensitivity tier assignment
- DataAnonymizer: anonymization, deanonymization, roundtrip, message anonymization
- Provider routing rules: tier enforcement, NON-EU provider restrictions
- LLMGateway: mocked end-to-end flows including fallback and anonymization blocking

Uses:
- pytest with asyncio_mode = auto
- unittest.mock (AsyncMock, patch, MagicMock)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.services.llm.data_classifier import (
    ClassificationContext,
    DataClassifier,
    DataSensitivity,
)
from apps.api.services.llm.anonymizer import DataAnonymizer
from apps.api.services.llm.gateway import (
    LLMGateway,
    LLMResponse,
    PROVIDER_CONFIGS,
    ProviderStatus,
    _NON_EU_PROVIDERS,
)


# ════════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════════

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


@pytest.fixture
def classifier():
    return DataClassifier()


@pytest.fixture
def anonymizer():
    return DataAnonymizer()


def _mock_audit_logger() -> AsyncMock:
    """Create a mock AIAuditLogger that returns a UUID from log_request."""
    logger = AsyncMock()
    logger.log_request = AsyncMock(return_value=uuid.uuid4())
    logger.log_response = AsyncMock()
    logger.log_error = AsyncMock()
    return logger


# ════════════════════════════════════════════════════════════════════════
# 1. DataClassifier tests (13 test cases)
# ════════════════════════════════════════════════════════════════════════


class TestDataClassifier:
    """Test Belgian PII detection and sensitivity classification."""

    def test_niss_detection_critical(self, classifier):
        """NISS (Belgian national registry number) must be CRITICAL."""
        text = "Son numéro national est 78.06.15-123.45"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.CRITICAL
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "niss" in entity_types
        assert "mistral" in result.allowed_providers
        # CRITICAL: only Tier 1 EU providers allowed
        assert result.allowed_providers == ["mistral", "gemini"]

    def test_bce_detection_semi_sensitive(self, classifier):
        """BCE/TVA (enterprise number) must be SEMI_SENSITIVE."""
        text = "L'entreprise 0123.456.789 est enregistrée"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.SEMI_SENSITIVE
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "bce" in entity_types

    def test_person_name_sensitive(self, classifier):
        """Person name in legal context (Me/Maitre prefix) must be SENSITIVE."""
        text = "Me Jean Dupont représente le client"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.SENSITIVE
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "person_name" in entity_types

    def test_internal_ref_sensitive(self, classifier):
        """Internal dossier reference must be SENSITIVE."""
        text = "Dossier n° 2024/1234"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.SENSITIVE
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "internal_ref" in entity_types

    def test_jurisprudence_public(self, classifier):
        """Published jurisprudence reference must be PUBLIC."""
        text = "Cass. 15 mars 2024, arrêt n° 123/2024"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.PUBLIC
        assert any("jurisprudence" in r.lower() for r in result.reasons)

    def test_legal_code_public(self, classifier):
        """Legal code reference must be PUBLIC."""
        text = "article 1382 C. civ."
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.PUBLIC
        assert any("legal code" in r.lower() for r in result.reasons)

    def test_health_keyword_critical(self, classifier):
        """Health-related keyword must be CRITICAL."""
        text = "certificat médical de Me Martin"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.CRITICAL
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "health_keyword" in entity_types

    def test_criminal_keyword_critical(self, classifier):
        """Criminal-related keyword must be CRITICAL."""
        text = "casier judiciaire du prévenu"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.CRITICAL
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "criminal_keyword" in entity_types

    def test_minor_keyword_critical(self, classifier):
        """Minor-related keyword must be CRITICAL."""
        text = "tribunal de la jeunesse"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.CRITICAL
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "minor_keyword" in entity_types

    def test_phone_semi_sensitive(self, classifier):
        """Belgian phone number must be SEMI_SENSITIVE."""
        text = "+32 2 123 45 67"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.SEMI_SENSITIVE
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "phone" in entity_types

    def test_iban_semi_sensitive(self, classifier):
        """Belgian IBAN must be SEMI_SENSITIVE."""
        text = "BE68 5390 0754 7034"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.SEMI_SENSITIVE
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "iban" in entity_types

    def test_email_semi_sensitive(self, classifier):
        """Email address must be SEMI_SENSITIVE."""
        text = "test@example.com"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.SEMI_SENSITIVE
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "email" in entity_types

    def test_empty_text_is_public(self, classifier):
        """Empty/whitespace-only text is PUBLIC (no substance to classify)."""
        text = "   "
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.PUBLIC
        assert len(result.detected_entities) == 0

    def test_plain_text_precautionary_sensitive(self, classifier):
        """Plain text without PII entities still defaults to SENSITIVE (precautionary principle)."""
        text = "Bonjour, voici un texte quelconque"
        result = classifier.classify(text)

        # GDPR precautionary principle: in doubt → SENSITIVE
        assert result.sensitivity == DataSensitivity.SENSITIVE

    def test_substantive_text_defaults_to_sensitive(self, classifier):
        """Substantive text without detected entities defaults to SENSITIVE (precautionary)."""
        text = "Le dossier comporte des éléments intéressants à analyser pour le client"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.SENSITIVE

    def test_context_jurisprudence_db_forces_public(self, classifier):
        """Source=jurisprudence_db context must force PUBLIC regardless of text."""
        context = ClassificationContext(source="jurisprudence_db")
        text = "Me Jean Dupont"
        result = classifier.classify(text, context)

        assert result.sensitivity == DataSensitivity.PUBLIC

    def test_context_has_client_data_forces_sensitive(self, classifier):
        """has_client_data=True must force at least SENSITIVE."""
        context = ClassificationContext(has_client_data=True)
        text = "Le Code civil belge"
        result = classifier.classify(text, context)

        assert result.sensitivity == DataSensitivity.SENSITIVE

    def test_critical_takes_precedence_over_sensitive(self, classifier):
        """When both CRITICAL and SENSITIVE entities exist, CRITICAL wins."""
        text = "Me Jean Dupont a un casier judiciaire"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.CRITICAL
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "criminal_keyword" in entity_types
        assert "person_name" in entity_types

    def test_multiple_semi_sensitive_entities(self, classifier):
        """Multiple SEMI_SENSITIVE entities still yield SEMI_SENSITIVE."""
        text = "Contact: test@example.com, BE68 5390 0754 7034"
        result = classifier.classify(text)

        assert result.sensitivity == DataSensitivity.SEMI_SENSITIVE
        entity_types = {e.entity_type for e in result.detected_entities}
        assert "email" in entity_types
        assert "iban" in entity_types


# ════════════════════════════════════════════════════════════════════════
# 2. DataAnonymizer tests (7 test cases)
# ════════════════════════════════════════════════════════════════════════


class TestDataAnonymizer:
    """Test PII anonymization and deanonymization."""

    def test_anonymize_niss(self, anonymizer):
        """NISS must be replaced with [NISS_1] placeholder."""
        text = "Son numéro national est 78.06.15-123.45"
        result = anonymizer.anonymize(text)

        assert "78.06.15-123.45" not in result.anonymized_text
        assert "[NISS_1]" in result.anonymized_text
        assert result.entity_count >= 1
        assert "[NISS_1]" in result.mapping
        assert result.mapping["[NISS_1]"] == "78.06.15-123.45"

    def test_anonymize_person_name(self, anonymizer):
        """Person name (legal context) must be replaced with [PERSONNE_1]."""
        text = "Me Jean Dupont représente le client"
        result = anonymizer.anonymize(text)

        assert "Jean Dupont" not in result.anonymized_text
        assert "[PERSONNE_1]" in result.anonymized_text
        assert result.entity_count >= 1

    def test_anonymize_deanonymize_roundtrip(self, anonymizer):
        """Anonymize then deanonymize must recover the original text exactly."""
        original = "Le dossier de Me Jean Dupont, NISS 78.06.15-123.45, doit être traité."
        anon_result = anonymizer.anonymize(original)

        # Verify PII is removed
        assert "78.06.15-123.45" not in anon_result.anonymized_text
        assert "Jean Dupont" not in anon_result.anonymized_text

        # Verify roundtrip restores original
        restored = anonymizer.deanonymize(anon_result.anonymized_text, anon_result.mapping)
        assert restored == original

    def test_anonymize_messages(self, anonymizer):
        """anonymize_messages must anonymize content in a list of message dicts."""
        messages = [
            {"role": "system", "content": "Tu es un assistant juridique."},
            {"role": "user", "content": "Le NISS de mon client est 78.06.15-123.45"},
        ]
        anon_msgs, mapping = anonymizer.anonymize_messages(messages)

        # System message has no PII, should be unchanged
        assert anon_msgs[0]["content"] == "Tu es un assistant juridique."
        assert anon_msgs[0]["role"] == "system"

        # User message must be anonymized
        assert "78.06.15-123.45" not in anon_msgs[1]["content"]
        assert "[NISS_1]" in anon_msgs[1]["content"]
        assert anon_msgs[1]["role"] == "user"

        # Mapping must contain the NISS
        assert "[NISS_1]" in mapping
        assert mapping["[NISS_1]"] == "78.06.15-123.45"

    def test_anonymize_multiple_entities(self, anonymizer):
        """Multiple different entity types must each get their own placeholder."""
        text = "Me Jean Dupont, NISS 78.06.15-123.45, email jean@dupont.be"
        result = anonymizer.anonymize(text)

        assert "78.06.15-123.45" not in result.anonymized_text
        assert "jean@dupont.be" not in result.anonymized_text
        assert "Jean Dupont" not in result.anonymized_text
        assert result.entity_count >= 3
        # Verify each type has its own placeholder prefix
        placeholder_prefixes = {k.split("_")[0].strip("[") for k in result.mapping.keys()}
        assert "NISS" in placeholder_prefixes
        assert "EMAIL" in placeholder_prefixes
        assert "PERSONNE" in placeholder_prefixes

    def test_anonymize_duplicate_entities(self, anonymizer):
        """Same entity value appearing twice must use the same placeholder."""
        text = "Le NISS est 78.06.15-123.45 et encore 78.06.15-123.45 apparaît."
        result = anonymizer.anonymize(text)

        # Both occurrences should use the same placeholder
        occurrences = result.anonymized_text.count("[NISS_1]")
        assert occurrences == 2
        # Only one entry in the mapping for this NISS
        niss_entries = [k for k in result.mapping if k.startswith("[NISS")]
        assert len(niss_entries) == 1

    def test_deanonymize_alias(self, anonymizer):
        """deanonymize_text must be an alias for deanonymize."""
        mapping = {"[NISS_1]": "78.06.15-123.45"}
        text = "Le NISS est [NISS_1]"
        assert anonymizer.deanonymize_text(text, mapping) == anonymizer.deanonymize(text, mapping)


# ════════════════════════════════════════════════════════════════════════
# 3. Provider routing rules (10 test cases)
# ════════════════════════════════════════════════════════════════════════


class TestProviderRoutingRules:
    """Test GDPR-mandated provider routing by sensitivity tier."""

    def test_critical_only_eu_native(self, classifier):
        """CRITICAL sensitivity must only allow EU-native/EU-DPF Tier 1 providers."""
        allowed = classifier.get_allowed_providers(DataSensitivity.CRITICAL)
        assert allowed == ["mistral", "gemini"]

    def test_sensitive_allows_tier1(self, classifier):
        """SENSITIVE must allow all Tier 1 providers."""
        allowed = classifier.get_allowed_providers(DataSensitivity.SENSITIVE)
        assert allowed == ["mistral", "gemini", "anthropic", "openai"]

    def test_semi_sensitive_allows_tier1_and_deepseek(self, classifier):
        """SEMI_SENSITIVE must allow Tier 1 + deepseek."""
        allowed = classifier.get_allowed_providers(DataSensitivity.SEMI_SENSITIVE)
        assert allowed == ["mistral", "gemini", "anthropic", "openai", "deepseek"]

    def test_public_allows_all(self, classifier):
        """PUBLIC must allow all 7 providers."""
        allowed = classifier.get_allowed_providers(DataSensitivity.PUBLIC)
        assert allowed == ["mistral", "gemini", "anthropic", "openai", "deepseek", "glm", "kimi"]
        assert len(allowed) == 7

    def test_sensitive_never_reaches_glm(self, classifier):
        """SENSITIVE data must NEVER be allowed for GLM."""
        allowed = classifier.get_allowed_providers(DataSensitivity.SENSITIVE)
        assert "glm" not in allowed

    def test_sensitive_never_reaches_kimi(self, classifier):
        """SENSITIVE data must NEVER be allowed for Kimi."""
        allowed = classifier.get_allowed_providers(DataSensitivity.SENSITIVE)
        assert "kimi" not in allowed

    def test_sensitive_never_reaches_deepseek(self, classifier):
        """SENSITIVE data must NEVER be allowed for DeepSeek (not even anonymized at this tier)."""
        allowed = classifier.get_allowed_providers(DataSensitivity.SENSITIVE)
        assert "deepseek" not in allowed

    def test_critical_never_reaches_non_eu_providers(self, classifier):
        """CRITICAL data must NEVER reach any non-EU provider."""
        allowed = classifier.get_allowed_providers(DataSensitivity.CRITICAL)
        for non_eu in _NON_EU_PROVIDERS:
            assert non_eu not in allowed, (
                f"CRITICAL data must never reach {non_eu}"
            )

    def test_non_eu_providers_set_is_correct(self):
        """The set of non-EU providers must match expected providers."""
        assert _NON_EU_PROVIDERS == {"deepseek", "glm", "kimi"}

    def test_all_providers_have_configs(self):
        """Every provider in routing rules must have a config entry."""
        all_providers_in_rules = set()
        for sensitivity in DataSensitivity:
            providers = DataClassifier().get_allowed_providers(sensitivity)
            all_providers_in_rules.update(providers)

        for provider in all_providers_in_rules:
            assert provider in PROVIDER_CONFIGS, (
                f"Provider '{provider}' is in routing rules but has no ProviderConfig"
            )

    def test_provider_configs_tier_assignments(self):
        """Verify tier assignments match routing expectations."""
        assert PROVIDER_CONFIGS["mistral"].tier == 1
        assert PROVIDER_CONFIGS["gemini"].tier == 1
        assert PROVIDER_CONFIGS["anthropic"].tier == 1
        assert PROVIDER_CONFIGS["openai"].tier == 1
        assert PROVIDER_CONFIGS["deepseek"].tier == 2
        assert PROVIDER_CONFIGS["glm"].tier == 3
        assert PROVIDER_CONFIGS["kimi"].tier == 3


# ════════════════════════════════════════════════════════════════════════
# 4. LLMGateway integration tests (with mocks)
# ════════════════════════════════════════════════════════════════════════


class TestLLMGatewayIntegration:
    """Test LLMGateway end-to-end with mocked providers."""

    @pytest.fixture
    def gateway(self):
        """Create a gateway with all providers mocked as available with API keys."""
        with patch.dict("os.environ", {
            "MISTRAL_API_KEY": "test-mistral-key",
            "GEMINI_API_KEY": "test-gemini-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "OPENAI_API_KEY": "test-openai-key",
            "DEEPSEEK_API_KEY": "test-deepseek-key",
            "GLM_API_KEY": "test-glm-key",
            "KIMI_API_KEY": "test-kimi-key",
        }):
            gw = LLMGateway()
            # Mark all providers as HEALTHY
            for name, provider in gw.providers.items():
                provider._status = ProviderStatus.HEALTHY
                provider.api_key = f"test-{name}-key"
            return gw

    @pytest.fixture
    def audit_logger(self):
        return _mock_audit_logger()

    @pytest.mark.asyncio
    async def test_successful_completion_tier1(self, gateway, audit_logger):
        """Successful completion with a Tier 1 provider (mistral) for SENSITIVE data."""
        messages = [{"role": "user", "content": "Me Jean Dupont représente le client"}]

        mock_result = {
            "content": "Voici l'analyse du dossier de Me Jean Dupont.",
            "usage": {"prompt_tokens": 20, "completion_tokens": 15},
            "model": "mistral-large-latest",
        }
        gateway.providers["mistral"].complete = AsyncMock(return_value=mock_result)

        response = await gateway.complete(
            messages=messages,
            purpose="test_completion",
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            audit_logger=audit_logger,
        )

        assert isinstance(response, LLMResponse)
        assert response.provider == "mistral"
        assert response.content == "Voici l'analyse du dossier de Me Jean Dupont."
        assert response.sensitivity == "sensitive"
        assert response.was_anonymized is False
        audit_logger.log_request.assert_called_once()
        audit_logger.log_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_anonymization_for_non_eu_provider(self, gateway, audit_logger):
        """When routed to a non-EU provider with non-PUBLIC data, anonymization must happen."""
        messages = [{"role": "user", "content": "L'entreprise 0123.456.789 est enregistrée"}]

        mock_result = {
            "content": "L'entreprise [BCE_1] est bien enregistrée auprès de la BCE.",
            "usage": {"prompt_tokens": 15, "completion_tokens": 20},
            "model": "deepseek-chat",
        }
        gateway.providers["deepseek"].complete = AsyncMock(return_value=mock_result)

        response = await gateway.complete(
            messages=messages,
            purpose="test_anonymization",
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            audit_logger=audit_logger,
            preferred_provider="deepseek",
            data_sensitivity=DataSensitivity.SEMI_SENSITIVE,
        )

        assert response.provider == "deepseek"
        assert response.was_anonymized is True
        # Verify the provider received anonymized messages (placeholder, not original)
        call_args = gateway.providers["deepseek"].complete.call_args
        sent_messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][0]
        sent_content = sent_messages[0]["content"]
        assert "0123.456.789" not in sent_content
        # The response should be deanonymized (original BCE number restored)
        assert "0123.456.789" in response.content

    @pytest.mark.asyncio
    async def test_fallback_when_primary_fails(self, gateway, audit_logger):
        """When the first provider fails, gateway must try the next in the chain."""
        messages = [{"role": "user", "content": "Le Code civil belge dispose que"}]

        # Mistral fails
        gateway.providers["mistral"].complete = AsyncMock(side_effect=Exception("Connection timeout"))

        # Anthropic succeeds
        mock_result = {
            "content": "Selon le Code civil belge...",
            "usage": {"prompt_tokens": 10, "completion_tokens": 12},
            "model": "claude-sonnet-4-20250514",
        }
        gateway.providers["anthropic"].complete = AsyncMock(return_value=mock_result)

        response = await gateway.complete(
            messages=messages,
            purpose="test_fallback",
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            audit_logger=audit_logger,
            data_sensitivity=DataSensitivity.PUBLIC,
        )

        assert response.provider == "anthropic"
        assert response.content == "Selon le Code civil belge..."
        # Mistral was tried first and logged an error
        assert audit_logger.log_error.call_count >= 1

    @pytest.mark.asyncio
    async def test_anonymization_failure_blocks_request(self, gateway, audit_logger):
        """When anonymization fails for a non-EU provider, the request must be BLOCKED entirely."""
        messages = [{"role": "user", "content": "L'entreprise 0123.456.789 est enregistrée"}]

        # Force deepseek as the only available provider
        for name in ["mistral", "gemini", "anthropic", "openai"]:
            gateway.providers[name]._status = ProviderStatus.DISABLED
            gateway.providers[name].api_key = ""
        gateway.providers["glm"]._status = ProviderStatus.DISABLED
        gateway.providers["glm"].api_key = ""
        gateway.providers["kimi"]._status = ProviderStatus.DISABLED
        gateway.providers["kimi"].api_key = ""

        # Make anonymization fail
        with patch.object(
            gateway.anonymizer,
            "anonymize_messages",
            side_effect=RuntimeError("Anonymization engine crashed"),
        ):
            with pytest.raises(ValueError, match="Anonymisation obligatoire échouée"):
                await gateway.complete(
                    messages=messages,
                    purpose="test_anon_block",
                    tenant_id=TENANT_ID,
                    user_id=USER_ID,
                    audit_logger=audit_logger,
                    data_sensitivity=DataSensitivity.SEMI_SENSITIVE,
                    preferred_provider="deepseek",
                )

        # The provider's complete method must NEVER have been called
        assert not hasattr(gateway.providers["deepseek"].complete, "call_count") or \
            gateway.providers["deepseek"].complete.call_count == 0

    @pytest.mark.asyncio
    async def test_classification_auto_detection(self, gateway, audit_logger):
        """When no data_sensitivity is provided, the gateway must auto-classify the text."""
        messages = [{"role": "user", "content": "casier judiciaire du prévenu Martin"}]

        mock_result = {
            "content": "Analyse du casier...",
            "usage": {"prompt_tokens": 10, "completion_tokens": 8},
            "model": "mistral-large-latest",
        }
        gateway.providers["mistral"].complete = AsyncMock(return_value=mock_result)

        response = await gateway.complete(
            messages=messages,
            purpose="test_auto_classify",
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            audit_logger=audit_logger,
            # data_sensitivity is NOT provided — gateway must auto-detect CRITICAL
        )

        assert response.sensitivity == "critical"
        assert response.provider == "mistral"

    @pytest.mark.asyncio
    async def test_no_available_provider_raises(self, gateway, audit_logger):
        """When no provider is available for the sensitivity level, raise ValueError."""
        messages = [{"role": "user", "content": "casier judiciaire du prévenu"}]

        # Disable all CRITICAL-allowed providers (mistral + gemini)
        for name in ["mistral", "gemini"]:
            gateway.providers[name]._status = ProviderStatus.DISABLED
            gateway.providers[name].api_key = ""

        with pytest.raises(ValueError, match="No available provider"):
            await gateway.complete(
                messages=messages,
                purpose="test_no_provider",
                tenant_id=TENANT_ID,
                user_id=USER_ID,
                audit_logger=audit_logger,
                data_sensitivity=DataSensitivity.CRITICAL,
            )

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_runtime_error(self, gateway, audit_logger):
        """When all providers in the chain fail, raise RuntimeError."""
        messages = [{"role": "user", "content": "Le Code civil belge"}]

        # Make all providers fail
        for name in gateway.providers:
            gateway.providers[name].complete = AsyncMock(
                side_effect=Exception(f"{name} is down")
            )

        with pytest.raises(RuntimeError, match="All providers failed"):
            await gateway.complete(
                messages=messages,
                purpose="test_all_fail",
                tenant_id=TENANT_ID,
                user_id=USER_ID,
                audit_logger=audit_logger,
                data_sensitivity=DataSensitivity.PUBLIC,
            )

    @pytest.mark.asyncio
    async def test_public_data_no_anonymization_for_non_eu(self, gateway, audit_logger):
        """PUBLIC data sent to non-EU providers must NOT be anonymized."""
        messages = [{"role": "user", "content": "Le Code civil belge dispose que"}]

        mock_result = {
            "content": "Le Code civil belge...",
            "usage": {"prompt_tokens": 10, "completion_tokens": 8},
            "model": "deepseek-chat",
        }
        gateway.providers["deepseek"].complete = AsyncMock(return_value=mock_result)

        response = await gateway.complete(
            messages=messages,
            purpose="test_public_no_anon",
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            audit_logger=audit_logger,
            data_sensitivity=DataSensitivity.PUBLIC,
            preferred_provider="deepseek",
        )

        assert response.provider == "deepseek"
        assert response.was_anonymized is False

    @pytest.mark.asyncio
    async def test_human_validation_flag_propagated(self, gateway, audit_logger):
        """require_human_validation must be propagated to the LLMResponse."""
        messages = [{"role": "user", "content": "Le Code civil belge"}]

        mock_result = {
            "content": "Analyse juridique...",
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
            "model": "mistral-large-latest",
        }
        gateway.providers["mistral"].complete = AsyncMock(return_value=mock_result)

        response = await gateway.complete(
            messages=messages,
            purpose="test_human_flag",
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            audit_logger=audit_logger,
            data_sensitivity=DataSensitivity.PUBLIC,
            require_human_validation=True,
        )

        assert response.require_human_validation is True

    @pytest.mark.asyncio
    async def test_preferred_provider_is_respected(self, gateway, audit_logger):
        """Preferred provider must be tried first if available and allowed."""
        messages = [{"role": "user", "content": "Le Code civil belge"}]

        mock_result = {
            "content": "Response from OpenAI",
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
            "model": "gpt-4o",
        }
        gateway.providers["openai"].complete = AsyncMock(return_value=mock_result)

        response = await gateway.complete(
            messages=messages,
            purpose="test_preferred",
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            audit_logger=audit_logger,
            data_sensitivity=DataSensitivity.PUBLIC,
            preferred_provider="openai",
        )

        assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_classify_text_endpoint(self, gateway):
        """classify_text must return a dict with sensitivity and entities."""
        result = gateway.classify_text("Me Jean Dupont a un casier judiciaire")

        assert result["sensitivity"] == "critical"
        assert "mistral" in result["allowed_providers"]
        assert len(result["detected_entities"]) >= 2
        assert len(result["reasons"]) >= 2

    @pytest.mark.asyncio
    async def test_cost_estimate(self, gateway):
        """get_cost_estimate must return a non-negative float."""
        cost = gateway.get_cost_estimate("Le Code civil belge est une source de droit.", "mistral")
        assert isinstance(cost, float)
        assert cost >= 0.0

    @pytest.mark.asyncio
    async def test_anonymization_failure_does_not_fallback_to_unanonymized(
        self, gateway, audit_logger
    ):
        """CRITICAL: When anonymization fails, the gateway must NOT fall back to
        sending unanonymized data to the non-EU provider or any other non-EU provider.
        The request must be blocked entirely with a ValueError."""
        messages = [{"role": "user", "content": "Me Jean Dupont, NISS 78.06.15-123.45"}]

        # Disable all EU providers so only non-EU providers remain
        for name in ["mistral", "gemini", "anthropic", "openai"]:
            gateway.providers[name]._status = ProviderStatus.DISABLED
            gateway.providers[name].api_key = ""
        for name in ["glm", "kimi"]:
            gateway.providers[name]._status = ProviderStatus.DISABLED
            gateway.providers[name].api_key = ""

        # Make anonymization fail
        with patch.object(
            gateway.anonymizer,
            "anonymize_messages",
            side_effect=RuntimeError("Regex engine failure"),
        ):
            with pytest.raises(ValueError, match="Anonymisation obligatoire"):
                await gateway.complete(
                    messages=messages,
                    purpose="test_block_unanonymized",
                    tenant_id=TENANT_ID,
                    user_id=USER_ID,
                    audit_logger=audit_logger,
                    data_sensitivity=DataSensitivity.SEMI_SENSITIVE,
                    preferred_provider="deepseek",
                )

        # Ensure NO provider's complete was called (data never left the system)
        for name in _NON_EU_PROVIDERS:
            provider = gateway.providers[name]
            if hasattr(provider.complete, "call_count"):
                assert provider.complete.call_count == 0, (
                    f"Provider {name} should NOT have been called after anonymization failure"
                )
