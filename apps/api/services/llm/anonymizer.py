"""Data anonymizer for GDPR-compliant LLM routing.

Performs reversible anonymization: replaces PII with placeholders,
keeps a mapping in memory (never persisted, never sent to providers).

After receiving the LLM response, the mapping is used to restore
original values in the output.

GDPR Art. 4(5): Truly anonymized data falls outside GDPR scope.
However, pseudonymized data (reversible) still requires safeguards.
Our approach: reversible replacement with ephemeral in-memory mapping.
"""

from dataclasses import dataclass

from apps.api.services.llm.data_classifier import (
    DetectedEntity,
    _ADDRESS_KEYWORDS,
    _BCE_PATTERN,
    _DOB_PATTERN,
    _EMAIL_PATTERN,
    _IBAN_BE_PATTERN,
    _LEGAL_CONTEXT_NAME,
    _NISS_PATTERN,
    _PHONE_BE_PATTERN,
    _POSTAL_CODE_BE,
    _PROPER_NAME_PATTERN,
)


@dataclass
class AnonymizationResult:
    """Result of anonymization."""

    anonymized_text: str
    mapping: dict[str, str]  # placeholder → original
    entity_count: int
    method: str = "regex_replacement"


# Entity type → placeholder prefix
_PLACEHOLDER_MAP: dict[str, str] = {
    "niss": "NISS",
    "bce": "BCE",
    "person_name": "PERSONNE",
    "phone": "TELEPHONE",
    "iban": "IBAN",
    "email": "EMAIL",
    "address": "ADRESSE",
    "date_of_birth": "DATE_NAISSANCE",
    "company_name": "ENTREPRISE",
}


class DataAnonymizer:
    """Anonymizes Belgian PII data for safe transmission to non-EU LLM providers.

    The anonymization is reversible: a mapping is kept in memory to restore
    original values in the LLM response. The mapping is NEVER persisted or
    sent to any external service.
    """

    def anonymize(self, text: str) -> AnonymizationResult:
        """Anonymize text and return the result with mapping.

        Returns:
            AnonymizationResult with anonymized text and placeholder→original mapping.
            The mapping can be used with deanonymize() to restore the response.
        """
        entities = self._detect_entities(text)

        # Sort entities by position (end→start) to replace from end to beginning
        # This preserves indices as we modify the text
        entities.sort(key=lambda e: e.start, reverse=True)

        # Deduplicate by value (same entity appearing multiple times)
        seen_values: dict[str, str] = {}  # original_value → placeholder
        counters: dict[str, int] = {}  # entity_type → counter
        mapping: dict[str, str] = {}  # placeholder → original_value

        # First pass: assign placeholders to unique values
        for entity in sorted(entities, key=lambda e: e.start):
            if entity.value in seen_values:
                continue
            prefix = _PLACEHOLDER_MAP.get(entity.entity_type, "ENTITE")
            counters.setdefault(entity.entity_type, 0)
            counters[entity.entity_type] += 1
            placeholder = f"[{prefix}_{counters[entity.entity_type]}]"
            seen_values[entity.value] = placeholder
            mapping[placeholder] = entity.value

        # Second pass: replace all occurrences in text
        anonymized = text
        for original, placeholder in sorted(
            seen_values.items(), key=lambda x: len(x[0]), reverse=True
        ):
            anonymized = anonymized.replace(original, placeholder)

        return AnonymizationResult(
            anonymized_text=anonymized,
            mapping=mapping,
            entity_count=len(mapping),
            method="regex_replacement",
        )

    def deanonymize(self, text: str, mapping: dict[str, str]) -> str:
        """Replace placeholders with original values in LLM response.

        Args:
            text: The LLM response containing placeholders.
            mapping: The placeholder→original mapping from anonymize().

        Returns:
            Text with placeholders replaced by original values.
        """
        result = text
        # Replace longest placeholders first to avoid partial matches
        for placeholder, original in sorted(
            mapping.items(), key=lambda x: len(x[0]), reverse=True
        ):
            result = result.replace(placeholder, original)
        return result

    def anonymize_messages(
        self, messages: list[dict]
    ) -> tuple[list[dict], dict[str, str]]:
        """Anonymize a list of chat messages.

        Returns:
            Tuple of (anonymized_messages, combined_mapping).
        """
        combined_mapping: dict[str, str] = {}
        anonymized_messages = []

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                result = self.anonymize(content)
                combined_mapping.update(result.mapping)
                anonymized_messages.append({**msg, "content": result.anonymized_text})
            else:
                anonymized_messages.append(msg)

        return anonymized_messages, combined_mapping

    def deanonymize_text(self, text: str, mapping: dict[str, str]) -> str:
        """Alias for deanonymize — kept for API consistency."""
        return self.deanonymize(text, mapping)

    def verify_anonymization(
        self, anonymized_text: str, original_entities: list[DetectedEntity]
    ) -> bool:
        """Verify that NO original entity values remain in the anonymized text.

        CRITICAL: If this returns False, the request MUST be BLOCKED.
        An entity leak means PII would be sent to a non-EU provider.

        Args:
            anonymized_text: The text after anonymization.
            original_entities: The entities that were detected before anonymization.

        Returns:
            True if anonymization is verified (no leaks). False if any entity
            value is still present in the anonymized text.
        """
        for entity in original_entities:
            value = entity.value.strip()
            if not value or len(value) < 3:
                continue
            if value in anonymized_text:
                return False
        return True

    def _detect_entities(self, text: str) -> list[DetectedEntity]:
        """Detect all PII entities in text using regex patterns.

        Belgian-specific patterns:
        - NISS: XX.XX.XX-XXX.XX
        - BCE: 0XXX.XXX.XXX
        - Phone: +32 ...
        - IBAN: BE## #### #### ####
        - Email: standard email pattern
        - Address: Belgian street + postal code
        - Date of birth: after "né(e)" or "date de naissance"
        - Person names: after titles or capitalized proper names
        """
        entities: list[DetectedEntity] = []

        # NISS
        for m in _NISS_PATTERN.finditer(text):
            entities.append(DetectedEntity("niss", m.group(), m.start(), m.end()))

        # BCE
        for m in _BCE_PATTERN.finditer(text):
            entities.append(DetectedEntity("bce", m.group(), m.start(), m.end()))

        # Phone
        for m in _PHONE_BE_PATTERN.finditer(text):
            entities.append(DetectedEntity("phone", m.group(), m.start(), m.end()))

        # IBAN
        for m in _IBAN_BE_PATTERN.finditer(text):
            entities.append(DetectedEntity("iban", m.group(), m.start(), m.end()))

        # Email
        for m in _EMAIL_PATTERN.finditer(text):
            entities.append(DetectedEntity("email", m.group(), m.start(), m.end()))

        # Date of birth
        for m in _DOB_PATTERN.finditer(text):
            entities.append(
                DetectedEntity("date_of_birth", m.group(1), m.start(1), m.end(1))
            )

        # Person names (legal context — high confidence)
        for m in _LEGAL_CONTEXT_NAME.finditer(text):
            entities.append(
                DetectedEntity(
                    "person_name", m.group(), m.start(), m.end(), confidence=0.9
                )
            )

        # Person names (standalone proper names — medium confidence)
        for m in _PROPER_NAME_PATTERN.finditer(text):
            name = m.group(1)
            # Skip common legal terms
            if name.lower() not in {
                "code civil",
                "code pénal",
                "cour appel",
                "conseil état",
                "moniteur belge",
                "union européenne",
            }:
                entities.append(
                    DetectedEntity(
                        "person_name", name, m.start(1), m.end(1), confidence=0.6
                    )
                )

        # Addresses (street keyword + postal code)
        addr_matches = list(_ADDRESS_KEYWORDS.finditer(text))
        postal_matches = list(_POSTAL_CODE_BE.finditer(text))
        if addr_matches and postal_matches:
            # Pair each address keyword with the nearest following postal code
            for addr in addr_matches:
                # Find next postal code after this address keyword (within 100 chars)
                for postal in postal_matches:
                    if (
                        postal.start() > addr.start()
                        and (postal.start() - addr.start()) < 100
                    ):
                        entities.append(
                            DetectedEntity(
                                "address",
                                text[addr.start() : postal.end()],
                                addr.start(),
                                postal.end(),
                                confidence=0.7,
                            )
                        )
                        break

        return entities
