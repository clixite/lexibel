"""LLM Gateway — GDPR-compliant multi-provider routing.

6 providers across 3 trust tiers:
  Tier 1 (SENSITIVE+): Mistral (EU), Anthropic (DPF), OpenAI (DPF)
  Tier 2 (SEMI-SENSITIVE): + DeepSeek (anonymized only)
  Tier 3 (PUBLIC): + GLM-4, Kimi

Core principles:
  1. Automatic data sensitivity classification
  2. Routing to authorized providers based on tier
  3. Automatic anonymization before non-EU Tier 2-3 providers
  4. Complete audit trail (AI Act Art. 13)
  5. Human-in-the-loop support (AI Act Art. 14)
  6. Automatic fallback if a provider is down

NON-NEGOTIABLE: If data is SENSITIVE/CRITICAL and the target provider is
GLM, Kimi, or DeepSeek, anonymization MUST succeed before sending.
If anonymization fails, the request is BLOCKED.
"""

import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import AsyncIterator

import httpx

from apps.api.services.llm.anonymizer import DataAnonymizer
from apps.api.services.llm.audit_logger import AIAuditLogger
from apps.api.services.llm.data_classifier import (
    ClassificationContext,
    DataClassifier,
    DataSensitivity,
)

logger = logging.getLogger(__name__)


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DISABLED = "disabled"


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    provider: str
    model: str
    sensitivity: str
    was_anonymized: bool
    token_count_input: int | None = None
    token_count_output: int | None = None
    latency_ms: int | None = None
    cost_estimate_eur: float | None = None
    audit_id: str | None = None
    require_human_validation: bool = False


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    name: str
    tier: int
    base_url: str
    api_key_env: str
    default_model: str
    supports_streaming: bool = True
    max_context_tokens: int = 128000
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    is_openai_compatible: bool = False
    enabled: bool = True


# ── Provider configurations ──

PROVIDER_CONFIGS: dict[str, ProviderConfig] = {
    "mistral": ProviderConfig(
        name="mistral",
        tier=1,
        base_url="https://api.mistral.ai/v1",
        api_key_env="MISTRAL_API_KEY",
        default_model="mistral-large-latest",
        max_context_tokens=128000,
        cost_per_1k_input=0.002,
        cost_per_1k_output=0.006,
        is_openai_compatible=True,
    ),
    "anthropic": ProviderConfig(
        name="anthropic",
        tier=1,
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        default_model="claude-sonnet-4-20250514",
        max_context_tokens=200000,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        is_openai_compatible=False,
    ),
    "gemini": ProviderConfig(
        name="gemini",
        tier=1,
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key_env="GEMINI_API_KEY",
        default_model="gemini-2.5-pro",
        max_context_tokens=1000000,
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.005,
        is_openai_compatible=False,
    ),
    "openai": ProviderConfig(
        name="openai",
        tier=1,
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o",
        max_context_tokens=128000,
        cost_per_1k_input=0.0025,
        cost_per_1k_output=0.01,
        is_openai_compatible=True,
    ),
    "deepseek": ProviderConfig(
        name="deepseek",
        tier=2,
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        max_context_tokens=128000,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
        is_openai_compatible=True,
    ),
    "glm": ProviderConfig(
        name="glm",
        tier=3,
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key_env="GLM_API_KEY",
        default_model="glm-4-plus",
        max_context_tokens=128000,
        cost_per_1k_input=0.0005,
        cost_per_1k_output=0.0005,
        is_openai_compatible=True,
    ),
    "kimi": ProviderConfig(
        name="kimi",
        tier=3,
        base_url="https://api.moonshot.cn/v1",
        api_key_env="KIMI_API_KEY",
        default_model="moonshot-v1-128k",
        max_context_tokens=128000,
        cost_per_1k_input=0.0006,
        cost_per_1k_output=0.0006,
        is_openai_compatible=True,
    ),
}

# Providers requiring anonymization for non-PUBLIC data
_NON_EU_PROVIDERS = {"deepseek", "glm", "kimi"}


class LLMProviderBase(ABC):
    """Abstract base for LLM provider implementations."""

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = os.getenv(config.api_key_env, "")
        self._status = ProviderStatus.HEALTHY if self.api_key else ProviderStatus.DISABLED
        self._client: httpx.AsyncClient | None = None

    @property
    def is_available(self) -> bool:
        return self._status in (ProviderStatus.HEALTHY, ProviderStatus.DEGRADED) and bool(
            self.api_key
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        return self._client

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        """Send completion request. Returns raw response dict."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream completion. Yields content chunks."""
        ...

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in EUR."""
        return (
            input_tokens / 1000 * self.config.cost_per_1k_input
            + output_tokens / 1000 * self.config.cost_per_1k_output
        )

    async def health_check(self) -> ProviderStatus:
        """Check provider health."""
        if not self.api_key:
            self._status = ProviderStatus.DISABLED
            return self._status
        try:
            client = await self._get_client()
            # Simple HEAD/GET to check connectivity
            resp = await client.get(
                f"{self.config.base_url}/models",
                headers=self._auth_headers(),
                timeout=5.0,
            )
            self._status = (
                ProviderStatus.HEALTHY if resp.status_code < 500 else ProviderStatus.UNHEALTHY
            )
        except Exception:
            self._status = ProviderStatus.UNHEALTHY
        return self._status

    @abstractmethod
    def _auth_headers(self) -> dict[str, str]:
        ...


class OpenAICompatibleProvider(LLMProviderBase):
    """Provider using OpenAI-compatible chat completions API.

    Works for: Mistral, OpenAI, DeepSeek, GLM, Kimi.
    """

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        client = await self._get_client()
        payload = {
            "model": model or self.config.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = await client.post(
            f"{self.config.base_url}/chat/completions",
            json=payload,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "content": data["choices"][0]["message"]["content"],
            "usage": data.get("usage", {}),
            "model": data.get("model", model or self.config.default_model),
        }

    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        payload = {
            "model": model or self.config.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with client.stream(
            "POST",
            f"{self.config.base_url}/chat/completions",
            json=payload,
            headers=self._auth_headers(),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        break
                    import json

                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue


class AnthropicProvider(LLMProviderBase):
    """Provider for Anthropic Claude API (Messages format)."""

    def _auth_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        client = await self._get_client()

        # Convert from OpenAI format to Anthropic format
        system_msg = None
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": model or self.config.default_model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_msg:
            payload["system"] = system_msg

        resp = await client.post(
            f"{self.config.base_url}/messages",
            json=payload,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage = data.get("usage", {})
        return {
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            },
            "model": data.get("model", model or self.config.default_model),
        }

    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        client = await self._get_client()

        system_msg = None
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": model or self.config.default_model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if system_msg:
            payload["system"] = system_msg

        async with client.stream(
            "POST",
            f"{self.config.base_url}/messages",
            json=payload,
            headers=self._auth_headers(),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    import json

                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            text = data.get("delta", {}).get("text", "")
                            if text:
                                yield text
                    except (json.JSONDecodeError, KeyError):
                        continue

    async def health_check(self) -> ProviderStatus:
        if not self.api_key:
            self._status = ProviderStatus.DISABLED
            return self._status
        # Anthropic doesn't have a /models endpoint; just check key presence
        self._status = ProviderStatus.HEALTHY
        return self._status


class GeminiProvider(LLMProviderBase):
    """Provider for Google Gemini API (generateContent format).

    Supports both the public API and Vertex AI (europe-west1 for EU data residency).
    When GEMINI_API_KEY is set, uses the public API.
    For Vertex AI, set GOOGLE_APPLICATION_CREDENTIALS + GEMINI_PROJECT_ID + GEMINI_REGION.
    """

    def _auth_headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _get_url(self, model: str, stream: bool = False) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        return (
            f"{self.config.base_url}/models/{model}:{action}"
            f"?key={self.api_key}"
        )

    @staticmethod
    def _convert_messages(messages: list[dict]) -> tuple[str | None, list[dict]]:
        """Convert OpenAI-format messages to Gemini contents format."""
        system_instruction = None
        contents = []
        for msg in messages:
            role = msg["role"]
            text = msg.get("content", "")
            if role == "system":
                system_instruction = text
            else:
                gemini_role = "user" if role == "user" else "model"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": text}],
                })
        return system_instruction, contents

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict:
        client = await self._get_client()
        use_model = model or self.config.default_model
        system_instruction, contents = self._convert_messages(messages)

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        resp = await client.post(
            self._get_url(use_model),
            json=payload,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract text from Gemini response
        content = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        return {
            "content": content,
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
            "model": use_model,
        }

    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        use_model = model or self.config.default_model
        system_instruction, contents = self._convert_messages(messages)

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        import json as _json

        async with client.stream(
            "POST",
            self._get_url(use_model, stream=True) + "&alt=sse",
            json=payload,
            headers=self._auth_headers(),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    try:
                        chunk = _json.loads(line[6:])
                        candidates = chunk.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                text = part.get("text", "")
                                if text:
                                    yield text
                    except (_json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def health_check(self) -> ProviderStatus:
        if not self.api_key:
            self._status = ProviderStatus.DISABLED
            return self._status
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{self.config.base_url}/models?key={self.api_key}",
                timeout=5.0,
            )
            self._status = (
                ProviderStatus.HEALTHY if resp.status_code < 400 else ProviderStatus.UNHEALTHY
            )
        except Exception:
            self._status = ProviderStatus.UNHEALTHY
        return self._status


def _create_provider(config: ProviderConfig) -> LLMProviderBase:
    """Factory for provider instances."""
    if config.name == "anthropic":
        return AnthropicProvider(config)
    if config.name == "gemini":
        return GeminiProvider(config)
    return OpenAICompatibleProvider(config)


class LLMGateway:
    """GDPR-compliant multi-provider LLM Gateway.

    Handles:
    - Automatic data sensitivity classification
    - Tier-based provider routing
    - Automatic PII anonymization for non-EU providers
    - AI Act audit logging
    - Fallback to alternative providers on failure
    """

    def __init__(self):
        self.providers: dict[str, LLMProviderBase] = {}
        self.classifier = DataClassifier()
        self.anonymizer = DataAnonymizer()

        # Initialize providers
        for name, config in PROVIDER_CONFIGS.items():
            self.providers[name] = _create_provider(config)

    def _get_messages_text(self, messages: list[dict]) -> str:
        """Extract all text content from messages for classification."""
        parts = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)
        return "\n".join(parts)

    def _select_provider(
        self,
        allowed_providers: list[str],
        preferred_provider: str | None = None,
    ) -> list[str]:
        """Select provider order: preferred first, then by availability and cost."""
        ordered = []
        if preferred_provider and preferred_provider in allowed_providers:
            if self.providers.get(preferred_provider, None) and self.providers[preferred_provider].is_available:
                ordered.append(preferred_provider)

        # Add remaining available providers sorted by tier (lowest first), then cost
        for name in allowed_providers:
            if name in ordered:
                continue
            provider = self.providers.get(name)
            if provider and provider.is_available:
                ordered.append(name)

        return ordered

    async def complete(
        self,
        messages: list[dict],
        purpose: str,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        audit_logger: AIAuditLogger,
        data_sensitivity: DataSensitivity | None = None,
        preferred_provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        require_human_validation: bool = False,
        context: ClassificationContext | None = None,
    ) -> LLMResponse:
        """Execute an LLM completion with GDPR-compliant routing.

        Flow:
        1. Classify data sensitivity (if not provided)
        2. Determine allowed providers
        3. Anonymize if needed (non-EU providers + non-PUBLIC data)
        4. Send request with fallback chain
        5. De-anonymize response if needed
        6. Log everything to audit trail
        """
        # Step 1: Classify
        text = self._get_messages_text(messages)
        if data_sensitivity is None:
            classification = self.classifier.classify(text, context)
            data_sensitivity = classification.sensitivity
        allowed = self.classifier.get_allowed_providers(data_sensitivity)

        # Step 2: Select provider chain
        provider_chain = self._select_provider(allowed, preferred_provider)
        if not provider_chain:
            raise ValueError(
                f"No available provider for sensitivity={data_sensitivity.value}. "
                f"Allowed: {allowed}"
            )

        # Step 3: Try each provider in the chain
        last_error: Exception | None = None
        for provider_name in provider_chain:
            provider = self.providers[provider_name]
            config = PROVIDER_CONFIGS[provider_name]
            use_model = model or config.default_model

            # Determine if anonymization is needed
            needs_anonymization = (
                provider_name in _NON_EU_PROVIDERS
                and data_sensitivity != DataSensitivity.PUBLIC
            )

            work_messages = messages
            anon_mapping: dict[str, str] | None = None
            was_anonymized = False

            if needs_anonymization:
                try:
                    work_messages, anon_mapping = self.anonymizer.anonymize_messages(messages)
                    was_anonymized = True

                    # CRITICAL: verify that anonymization actually removed all entities
                    classification = self.classifier.classify(text, context)
                    anon_text = self._get_messages_text(work_messages)
                    if not self.anonymizer.verify_anonymization(
                        anon_text, classification.detected_entities
                    ):
                        raise ValueError(
                            "Anonymization verification failed: entities still present "
                            "in anonymized text. Request BLOCKED for safety."
                        )
                except Exception as anon_err:
                    # CRITICAL: If anonymization fails, BLOCK the request
                    logger.error(
                        "Anonymization failed for provider=%s sensitivity=%s: %s",
                        provider_name,
                        data_sensitivity.value,
                        anon_err,
                    )
                    # Log the failure
                    audit_id = await audit_logger.log_request(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        provider=provider_name,
                        model=use_model,
                        data_sensitivity=data_sensitivity.value,
                        was_anonymized=False,
                        anonymization_method=None,
                        prompt_content=text,
                        purpose=purpose,
                        metadata={
                            "error": "anonymization_failed",
                            "anonymization_error": str(anon_err),
                        },
                    )
                    await audit_logger.log_error(
                        audit_id,
                        f"Anonymization failed: {anon_err}. Request BLOCKED.",
                    )
                    raise ValueError(
                        f"Anonymisation obligatoire échouée pour {provider_name}. "
                        f"Les données de sensibilité '{data_sensitivity.value}' ne peuvent pas "
                        f"être envoyées à un fournisseur non-EU sans anonymisation. "
                        f"Erreur: {anon_err}"
                    ) from anon_err

            # Log the request
            audit_id = await audit_logger.log_request(
                tenant_id=tenant_id,
                user_id=user_id,
                provider=provider_name,
                model=use_model,
                data_sensitivity=data_sensitivity.value,
                was_anonymized=was_anonymized,
                anonymization_method="regex_replacement" if was_anonymized else None,
                prompt_content=text,
                purpose=purpose,
                metadata={
                    "preferred_provider": preferred_provider,
                    "fallback_chain": provider_chain,
                    "require_human_validation": require_human_validation,
                },
            )

            # Execute request
            start_time = time.monotonic()
            try:
                result = await provider.complete(
                    messages=work_messages,
                    model=use_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                latency_ms = int((time.monotonic() - start_time) * 1000)
                content = result["content"]
                usage = result.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                cost = provider.estimate_cost(input_tokens, output_tokens)

                # De-anonymize if needed
                if was_anonymized and anon_mapping:
                    content = self.anonymizer.deanonymize(content, anon_mapping)

                # Log response
                await audit_logger.log_response(
                    request_id=audit_id,
                    response_content=content,
                    token_count_input=input_tokens,
                    token_count_output=output_tokens,
                    latency_ms=latency_ms,
                    cost_estimate_eur=Decimal(str(cost)),
                )

                return LLMResponse(
                    content=content,
                    provider=provider_name,
                    model=result.get("model", use_model),
                    sensitivity=data_sensitivity.value,
                    was_anonymized=was_anonymized,
                    token_count_input=input_tokens,
                    token_count_output=output_tokens,
                    latency_ms=latency_ms,
                    cost_estimate_eur=cost,
                    audit_id=str(audit_id),
                    require_human_validation=require_human_validation,
                )

            except httpx.HTTPStatusError as e:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                last_error = e
                logger.warning(
                    "Provider %s failed (HTTP %s), trying next: %s",
                    provider_name,
                    e.response.status_code,
                    e,
                )
                await audit_logger.log_error(
                    audit_id,
                    f"HTTP {e.response.status_code}: {str(e)[:500]}",
                )
                continue

            except Exception as e:
                latency_ms = int((time.monotonic() - start_time) * 1000)
                last_error = e
                logger.warning(
                    "Provider %s failed, trying next: %s", provider_name, e
                )
                await audit_logger.log_error(audit_id, str(e)[:500])
                continue

        # All providers failed
        raise RuntimeError(
            f"All providers failed for sensitivity={data_sensitivity.value}. "
            f"Tried: {provider_chain}. Last error: {last_error}"
        )

    async def stream(
        self,
        messages: list[dict],
        purpose: str,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        audit_logger: AIAuditLogger,
        data_sensitivity: DataSensitivity | None = None,
        preferred_provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        context: ClassificationContext | None = None,
    ) -> AsyncIterator[str]:
        """Stream an LLM completion with the same GDPR routing rules.

        Note: De-anonymization happens at the end for streaming, since we
        need the complete response to accurately replace placeholders.
        For streaming, we accumulate and yield chunks, then the caller
        must handle the final de-anonymization if needed.
        """
        text = self._get_messages_text(messages)
        if data_sensitivity is None:
            classification = self.classifier.classify(text, context)
            data_sensitivity = classification.sensitivity
        allowed = self.classifier.get_allowed_providers(data_sensitivity)

        provider_chain = self._select_provider(allowed, preferred_provider)
        if not provider_chain:
            raise ValueError(f"No available provider for sensitivity={data_sensitivity.value}")

        for provider_name in provider_chain:
            provider = self.providers[provider_name]
            config = PROVIDER_CONFIGS[provider_name]
            use_model = model or config.default_model

            needs_anonymization = (
                provider_name in _NON_EU_PROVIDERS
                and data_sensitivity != DataSensitivity.PUBLIC
            )

            work_messages = messages
            anon_mapping: dict[str, str] | None = None

            if needs_anonymization:
                try:
                    work_messages, anon_mapping = self.anonymizer.anonymize_messages(messages)
                except Exception as anon_err:
                    logger.error("Anonymization failed for streaming: %s", anon_err)
                    audit_id = await audit_logger.log_request(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        provider=provider_name,
                        model=use_model,
                        data_sensitivity=data_sensitivity.value,
                        was_anonymized=False,
                        anonymization_method=None,
                        prompt_content=text,
                        purpose=purpose,
                        metadata={"error": "anonymization_failed"},
                    )
                    await audit_logger.log_error(
                        audit_id, f"Anonymization failed: {anon_err}"
                    )
                    raise ValueError(
                        f"Anonymisation obligatoire échouée pour {provider_name}. "
                        f"Requête BLOQUÉE."
                    ) from anon_err

            # Log request
            audit_id = await audit_logger.log_request(
                tenant_id=tenant_id,
                user_id=user_id,
                provider=provider_name,
                model=use_model,
                data_sensitivity=data_sensitivity.value,
                was_anonymized=bool(anon_mapping),
                anonymization_method="regex_replacement" if anon_mapping else None,
                prompt_content=text,
                purpose=purpose,
            )

            start_time = time.monotonic()
            try:
                full_content = []
                async for chunk in provider.stream(
                    messages=work_messages,
                    model=use_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    full_content.append(chunk)
                    # For streaming, yield raw chunks (caller handles display)
                    yield chunk

                latency_ms = int((time.monotonic() - start_time) * 1000)
                complete_text = "".join(full_content)

                # Log response
                await audit_logger.log_response(
                    request_id=audit_id,
                    response_content=complete_text,
                    latency_ms=latency_ms,
                )
                return  # Success

            except Exception as e:
                logger.warning("Provider %s stream failed: %s", provider_name, e)
                await audit_logger.log_error(audit_id, str(e)[:500])
                continue

        raise RuntimeError(f"All providers failed for streaming. Tried: {provider_chain}")

    async def get_provider_status(self) -> dict[str, dict]:
        """Get health status of all providers."""
        statuses = {}
        for name, provider in self.providers.items():
            config = PROVIDER_CONFIGS[name]
            status = await provider.health_check()
            statuses[name] = {
                "name": name,
                "tier": config.tier,
                "status": status.value,
                "default_model": config.default_model,
                "max_context_tokens": config.max_context_tokens,
                "cost_per_1k_input": config.cost_per_1k_input,
                "cost_per_1k_output": config.cost_per_1k_output,
                "supports_streaming": config.supports_streaming,
                "enabled": config.enabled and provider.is_available,
            }
        return statuses

    def get_cost_estimate(self, text: str, provider_name: str) -> float:
        """Estimate cost for processing text with a specific provider."""
        # Rough token estimate: ~4 chars per token
        estimated_tokens = len(text) // 4
        provider = self.providers.get(provider_name)
        if not provider:
            return 0.0
        return provider.estimate_cost(estimated_tokens, estimated_tokens // 2)

    def classify_text(
        self, text: str, context: ClassificationContext | None = None
    ) -> dict:
        """Classify text sensitivity (for the /classify endpoint)."""
        result = self.classifier.classify(text, context)
        return {
            "sensitivity": result.sensitivity.value,
            "allowed_providers": result.allowed_providers,
            "detected_entities": [
                {
                    "type": e.entity_type,
                    "value": e.value[:20] + "..." if len(e.value) > 20 else e.value,
                    "confidence": e.confidence,
                }
                for e in result.detected_entities
            ],
            "reasons": result.reasons,
        }
