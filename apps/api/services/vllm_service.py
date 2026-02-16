"""vLLM service — connect to local vLLM server with Multi-LoRA support.

Provides generation (standard + streaming), model listing, and LoRA adapter
management. Falls back to OpenAI API when vLLM is unavailable.
Health check with auto-reconnect.
"""
import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional

import httpx


# ── Constants ──

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://vllm:8000/v1")
OPENAI_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("LLM_API_KEY", "")
DEFAULT_MODEL = os.getenv("VLLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
VLLM_TIMEOUT = float(os.getenv("VLLM_TIMEOUT", "120"))
HEALTH_CHECK_INTERVAL = 30  # seconds


@dataclass
class VLLMResponse:
    """Response from vLLM generation."""
    text: str
    model: str = ""
    lora_adapter: str = ""
    tokens_used: int = 0
    finish_reason: str = ""
    backend: str = "vllm"  # vllm or openai


@dataclass
class ModelInfo:
    """Information about an available model."""
    id: str
    object: str = "model"
    owned_by: str = "local"


class VLLMService:
    """vLLM client with Multi-LoRA support and OpenAI fallback."""

    def __init__(
        self,
        vllm_url: str = VLLM_BASE_URL,
        openai_url: str = OPENAI_BASE_URL,
        openai_key: str = OPENAI_API_KEY,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self._vllm_url = vllm_url
        self._openai_url = openai_url
        self._openai_key = openai_key
        self._default_model = default_model
        self._vllm_available = False
        self._last_health_check = 0.0

    async def _check_health(self) -> bool:
        """Check if vLLM server is available."""
        now = time.time()
        if now - self._last_health_check < HEALTH_CHECK_INTERVAL:
            return self._vllm_available

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._vllm_url}/models")
                self._vllm_available = resp.status_code == 200
        except (httpx.HTTPError, Exception):
            self._vllm_available = False

        self._last_health_check = now
        return self._vllm_available

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        lora_adapter: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        system_prompt: str = "",
        messages: Optional[list[dict]] = None,
    ) -> VLLMResponse:
        """Generate text using vLLM or OpenAI fallback.

        Args:
            prompt: User prompt (ignored if messages provided)
            model: Model ID (default: configured model)
            lora_adapter: LoRA adapter name for Multi-LoRA
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: System prompt
            messages: Pre-built message list (overrides prompt/system_prompt)

        Returns:
            VLLMResponse with generated text
        """
        use_model = model or self._default_model

        # Build messages
        if not messages:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        # Try vLLM first
        vllm_ok = await self._check_health()

        if vllm_ok:
            return await self._generate_vllm(messages, use_model, lora_adapter, max_tokens, temperature)

        # Fallback to OpenAI
        return await self._generate_openai(messages, max_tokens, temperature)

    async def _generate_vllm(
        self,
        messages: list[dict],
        model: str,
        lora_adapter: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> VLLMResponse:
        """Generate using local vLLM server."""
        payload: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Multi-LoRA: specify adapter in model field
        if lora_adapter:
            payload["model"] = f"{model}:{lora_adapter}"

        try:
            async with httpx.AsyncClient(timeout=VLLM_TIMEOUT) as client:
                resp = await client.post(
                    f"{self._vllm_url}/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            choice = data["choices"][0]
            return VLLMResponse(
                text=choice["message"]["content"],
                model=data.get("model", model),
                lora_adapter=lora_adapter or "",
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=choice.get("finish_reason", ""),
                backend="vllm",
            )
        except Exception as e:
            # Fallback to OpenAI on vLLM error
            self._vllm_available = False
            return await self._generate_openai(messages, max_tokens, temperature)

    async def _generate_openai(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> VLLMResponse:
        """Generate using OpenAI API as fallback."""
        if not self._openai_key:
            return VLLMResponse(
                text="Erreur : vLLM indisponible et aucune clé OpenAI configurée.",
                backend="none",
            )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._openai_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._openai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            choice = data["choices"][0]
            return VLLMResponse(
                text=choice["message"]["content"],
                model=data.get("model", "gpt-4o-mini"),
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=choice.get("finish_reason", ""),
                backend="openai",
            )
        except Exception as e:
            return VLLMResponse(
                text=f"Erreur LLM : {str(e)}",
                backend="error",
            )

    async def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        lora_adapter: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream generate text token by token.

        Yields text chunks as they are generated.
        """
        use_model = model or self._default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        vllm_ok = await self._check_health()
        base_url = self._vllm_url if vllm_ok else self._openai_url

        payload: dict = {
            "model": use_model if vllm_ok else "gpt-4o-mini",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        if vllm_ok and lora_adapter:
            payload["model"] = f"{use_model}:{lora_adapter}"

        headers = {"Content-Type": "application/json"}
        if not vllm_ok and self._openai_key:
            headers["Authorization"] = f"Bearer {self._openai_key}"

        try:
            async with httpx.AsyncClient(timeout=VLLM_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk == "[DONE]":
                                break
                            try:
                                import json
                                data = json.loads(chunk)
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except (ValueError, KeyError):
                                continue
        except Exception as e:
            yield f"[Erreur streaming : {str(e)}]"

    async def list_models(self) -> list[ModelInfo]:
        """List available models from vLLM server."""
        vllm_ok = await self._check_health()
        if not vllm_ok:
            return [ModelInfo(id="gpt-4o-mini", owned_by="openai")]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._vllm_url}/models")
                resp.raise_for_status()
                data = resp.json()

            return [
                ModelInfo(id=m["id"], object=m.get("object", "model"), owned_by=m.get("owned_by", "local"))
                for m in data.get("data", [])
            ]
        except Exception:
            return []

    async def list_lora_adapters(self) -> list[str]:
        """List available LoRA adapters from vLLM.

        vLLM exposes LoRA adapters via the model listing endpoint
        as model_name:adapter_name variants.
        """
        models = await self.list_models()
        adapters = []
        for m in models:
            if ":" in m.id:
                adapter_name = m.id.split(":", 1)[1]
                adapters.append(adapter_name)
        return adapters


# ── Stub for testing ──


class StubVLLMService(VLLMService):
    """Stub vLLM service for testing without a real server."""

    def __init__(self, canned_response: str = "Réponse vLLM stub.") -> None:
        super().__init__()
        self._canned = canned_response
        self._vllm_available = False

    async def _check_health(self) -> bool:
        return False

    async def generate(self, prompt: str, **kwargs) -> VLLMResponse:
        return VLLMResponse(
            text=self._canned,
            model="stub",
            backend="stub",
            tokens_used=len(prompt.split()),
        )

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        for word in self._canned.split():
            yield word + " "

    async def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(id="stub-model")]

    async def list_lora_adapters(self) -> list[str]:
        return ["legal-fr", "legal-nl", "summarization", "drafting"]
