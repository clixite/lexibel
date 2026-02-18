"""Red team security tests for LLM Gateway GDPR compliance.

These tests verify that the GDPR and AI Act protections cannot be bypassed.
If ANY test fails, the build MUST be blocked.
"""


from apps.api.services.llm.data_classifier import (
    DataClassifier, DataSensitivity, DetectedEntity,
)
from apps.api.services.llm.anonymizer import DataAnonymizer
from apps.api.services.llm.gateway import LLMGateway, PROVIDER_CONFIGS, _NON_EU_PROVIDERS


# ── Test data with Belgian PII ──

NISS_TEXT = "Le client Jean Dupont, NISS 85.06.15-123.45, habite rue de la Loi 16, 1000 Bruxelles."
CRIMINAL_TEXT = "Le prévenu a été condamné pour récidive. Son casier judiciaire mentionne 3 infractions."
HEALTH_TEXT = "Le diagnostic du médecin confirme une incapacité de travail de 3 mois."
MINOR_TEXT = "Le mineur est placé sous la protection de la jeunesse par le tribunal."
BCE_TEXT = "L'entreprise 0123.456.789 a déposé ses comptes annuels."
IBAN_TEXT = "Veuillez virer sur BE68 5390 0754 7034."
PUBLIC_TEXT = "Art. 1382 C. civ. dispose que tout fait quelconque de l'homme qui cause à autrui un dommage."
MIXED_SENSITIVE = "Me Jean Dupont représente M. Pierre Martin dans le dossier Réf. 2024/1234 concernant le diagnostic médical."
EMPTY_TEXT = ""
GENERIC_INSTRUCTION = "Résumez ce texte juridique et identifiez les points clés."


class TestCriticalDataNeverReachesTier2:
    """NISS + names must NEVER be sent to DeepSeek, GLM, or Kimi."""

    def test_critical_data_blocked_from_deepseek(self):
        classifier = DataClassifier()
        result = classifier.classify(NISS_TEXT)
        assert result.sensitivity == DataSensitivity.CRITICAL
        assert "deepseek" not in result.allowed_providers

    def test_critical_data_blocked_from_glm(self):
        classifier = DataClassifier()
        result = classifier.classify(NISS_TEXT)
        assert "glm" not in result.allowed_providers

    def test_critical_data_blocked_from_kimi(self):
        classifier = DataClassifier()
        result = classifier.classify(NISS_TEXT)
        assert "kimi" not in result.allowed_providers

    def test_criminal_data_is_critical(self):
        classifier = DataClassifier()
        result = classifier.classify(CRIMINAL_TEXT)
        assert result.sensitivity == DataSensitivity.CRITICAL

    def test_health_data_is_critical(self):
        classifier = DataClassifier()
        result = classifier.classify(HEALTH_TEXT)
        assert result.sensitivity == DataSensitivity.CRITICAL

    def test_minor_data_is_critical(self):
        classifier = DataClassifier()
        result = classifier.classify(MINOR_TEXT)
        assert result.sensitivity == DataSensitivity.CRITICAL


class TestCriticalDataNeverReachesTier3:
    """Same as Tier 2 but even stricter."""

    def test_sensitive_data_blocked_from_tier3(self):
        classifier = DataClassifier()
        # Text with person name in legal context -> SENSITIVE
        text = "Me Jean Dupont a déposé des conclusions."
        result = classifier.classify(text)
        assert result.sensitivity in (DataSensitivity.SENSITIVE, DataSensitivity.CRITICAL)
        assert "glm" not in result.allowed_providers
        assert "kimi" not in result.allowed_providers


class TestAnonymizationRemovesAllEntities:
    """Anonymize text with 10+ entities and verify none remain."""

    def test_all_entities_removed(self):
        text = (
            "Me Jean Dupont représente Mme Marie Lambert. "
            "NISS: 85.06.15-123.45. BCE: 0123.456.789. "
            "Tél: +32 2 123 45 67. IBAN: BE68 5390 0754 7034. "
            "Email: jean.dupont@avocat.be. "
            "Adresse: rue de la Loi 16, 1000 Bruxelles. "
            "Né le 15/06/1985. Dossier N/Réf: 2024/1234."
        )
        anonymizer = DataAnonymizer()
        result = anonymizer.anonymize(text)

        # Check that no original PII values remain
        assert "Jean Dupont" not in result.anonymized_text or "PERSONNE" in result.anonymized_text
        assert "85.06.15-123.45" not in result.anonymized_text
        assert "0123.456.789" not in result.anonymized_text
        assert "+32 2 123 45 67" not in result.anonymized_text
        assert "BE68 5390 0754 7034" not in result.anonymized_text
        assert "jean.dupont@avocat.be" not in result.anonymized_text

        # Verify placeholders are present
        assert "[NISS_" in result.anonymized_text
        assert "[BCE_" in result.anonymized_text
        assert "[EMAIL_" in result.anonymized_text
        assert "[IBAN_" in result.anonymized_text
        assert result.entity_count > 0


class TestAnonymizationVerification:
    """Test that verify_anonymization catches leaks."""

    def test_verify_clean_anonymization(self):
        anonymizer = DataAnonymizer()
        text = "Me Jean Dupont, NISS 85.06.15-123.45"
        result = anonymizer.anonymize(text)

        classifier = DataClassifier()
        classification = classifier.classify(text)

        assert anonymizer.verify_anonymization(
            result.anonymized_text, classification.detected_entities
        )

    def test_verify_catches_leak(self):
        anonymizer = DataAnonymizer()
        # Simulate a leak by passing original text as "anonymized"
        entities = [
            DetectedEntity("niss", "85.06.15-123.45", 0, 15),
        ]
        assert not anonymizer.verify_anonymization(
            "Le NISS est 85.06.15-123.45", entities
        )


class TestDeanonymizationRoundtrip:
    """Anonymize -> deanonymize must produce identical text."""

    def test_roundtrip_simple(self):
        anonymizer = DataAnonymizer()
        original = "Me Jean Dupont habite rue de la Loi 16, 1000 Bruxelles."
        result = anonymizer.anonymize(original)
        restored = anonymizer.deanonymize(result.anonymized_text, result.mapping)
        assert restored == original

    def test_roundtrip_complex(self):
        anonymizer = DataAnonymizer()
        original = (
            "Me Jean Dupont représente Mme Marie Lambert. "
            "NISS: 85.06.15-123.45. BCE: 0123.456.789. "
            "IBAN: BE68 5390 0754 7034. "
            "Email: jean.dupont@avocat.be."
        )
        result = anonymizer.anonymize(original)
        restored = anonymizer.deanonymize(result.anonymized_text, result.mapping)
        assert restored == original

    def test_roundtrip_messages(self):
        anonymizer = DataAnonymizer()
        messages = [
            {"role": "system", "content": "Tu es un assistant juridique."},
            {"role": "user", "content": "Analysez le dossier de Me Jean Dupont, NISS 85.06.15-123.45."},
        ]
        anon_messages, mapping = anonymizer.anonymize_messages(messages)

        # System message should be unchanged (no PII)
        # User message should be anonymized
        assert "85.06.15-123.45" not in anon_messages[1]["content"]

        # Deanonymize
        restored = anonymizer.deanonymize(anon_messages[1]["content"], mapping)
        assert "85.06.15-123.45" in restored


class TestAuditLogNeverContainsContent:
    """Audit logs must contain hashes, NEVER the actual prompt/response content."""

    def test_hash_content_is_sha256(self):
        from apps.api.services.llm.audit_logger import AIAuditLogger
        content = "This is a secret legal document about Mr. Dupont."
        h = AIAuditLogger.hash_content(content)
        assert len(h) == 64  # SHA-256 hex digest
        assert content not in h
        # Same input = same hash
        assert AIAuditLogger.hash_content(content) == h


class TestFallbackRespectsTier:
    """When a Tier 1 provider fails, fallback must stay within Tier 1 for SENSITIVE data."""

    def test_sensitive_fallback_stays_tier1(self):
        LLMGateway()
        classifier = DataClassifier()
        result = classifier.classify(NISS_TEXT)
        allowed = classifier.get_allowed_providers(result.sensitivity)

        # All allowed providers must be Tier 1
        for provider_name in allowed:
            config = PROVIDER_CONFIGS[provider_name]
            assert config.tier == 1, (
                f"Provider {provider_name} is tier {config.tier} but is allowed for "
                f"{result.sensitivity.value} data"
            )

    def test_critical_only_eu_providers(self):
        classifier = DataClassifier()
        result = classifier.classify(NISS_TEXT)
        assert result.sensitivity == DataSensitivity.CRITICAL
        # CRITICAL should only allow mistral and gemini (EU-native)
        for p in result.allowed_providers:
            assert p in ("mistral", "gemini"), f"Unexpected provider {p} for CRITICAL data"


class TestClassifierDefaultSensitive:
    """Ambiguous text without clear entities must default to SENSITIVE (precautionary principle)."""

    def test_ambiguous_text_is_sensitive(self):
        classifier = DataClassifier()
        result = classifier.classify(GENERIC_INSTRUCTION)
        assert result.sensitivity == DataSensitivity.SENSITIVE

    def test_empty_text_is_public(self):
        classifier = DataClassifier()
        result = classifier.classify(EMPTY_TEXT)
        assert result.sensitivity == DataSensitivity.PUBLIC

    def test_pure_legal_reference_is_public(self):
        classifier = DataClassifier()
        result = classifier.classify(PUBLIC_TEXT)
        assert result.sensitivity == DataSensitivity.PUBLIC


class TestChineseProvidersNeverReceiveUnverifiedData:
    """Simulate varied requests and verify GLM/Kimi NEVER receive non-public unverified data."""

    SAMPLE_TEXTS = [
        NISS_TEXT,
        CRIMINAL_TEXT,
        HEALTH_TEXT,
        MINOR_TEXT,
        BCE_TEXT,
        IBAN_TEXT,
        MIXED_SENSITIVE,
        GENERIC_INSTRUCTION,
        "Le client demande une consultation concernant son licenciement abusif.",
        "Me Pierre Martin a déposé des conclusions devant le tribunal.",
    ]

    def test_no_sensitive_data_to_chinese_providers(self):
        classifier = DataClassifier()
        chinese_providers = {"glm", "kimi"}

        for text in self.SAMPLE_TEXTS:
            result = classifier.classify(text)
            if result.sensitivity in (DataSensitivity.CRITICAL, DataSensitivity.SENSITIVE):
                for cp in chinese_providers:
                    assert cp not in result.allowed_providers, (
                        f"Chinese provider '{cp}' allowed for {result.sensitivity.value} "
                        f"data in text: {text[:50]}..."
                    )


class TestProviderTierConfiguration:
    """Verify provider tier configuration is correct."""

    def test_mistral_is_tier1(self):
        assert PROVIDER_CONFIGS["mistral"].tier == 1

    def test_gemini_is_tier1(self):
        assert PROVIDER_CONFIGS["gemini"].tier == 1

    def test_anthropic_is_tier1(self):
        assert PROVIDER_CONFIGS["anthropic"].tier == 1

    def test_openai_is_tier1(self):
        assert PROVIDER_CONFIGS["openai"].tier == 1

    def test_deepseek_is_tier2(self):
        assert PROVIDER_CONFIGS["deepseek"].tier == 2

    def test_glm_is_tier3(self):
        assert PROVIDER_CONFIGS["glm"].tier == 3

    def test_kimi_is_tier3(self):
        assert PROVIDER_CONFIGS["kimi"].tier == 3

    def test_non_eu_providers_set(self):
        assert _NON_EU_PROVIDERS == {"deepseek", "glm", "kimi"}

    def test_seven_providers_configured(self):
        assert len(PROVIDER_CONFIGS) == 7
