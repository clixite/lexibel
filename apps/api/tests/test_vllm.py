"""Tests for vLLM service and LoRA registry."""
import pytest

from apps.api.services.vllm_service import VLLMService, StubVLLMService, VLLMResponse, ModelInfo
from apps.api.services.lora_registry import LoRARegistry, LoRAAdapter


# ── StubVLLMService ──


class TestStubVLLMService:

    def setup_method(self):
        self.service = StubVLLMService()

    @pytest.mark.asyncio
    async def test_health_check(self):
        # Stub always returns False for _check_health
        result = await self.service._check_health()
        assert result is False

    @pytest.mark.asyncio
    async def test_generate(self):
        result = await self.service.generate("Résume ce texte.")
        assert isinstance(result, VLLMResponse)
        assert "stub" in result.text.lower() or len(result.text) > 0
        assert result.backend == "stub"

    @pytest.mark.asyncio
    async def test_generate_with_lora(self):
        result = await self.service.generate("Résume.", model="mistral", lora_adapter="legal-fr")
        assert isinstance(result, VLLMResponse)
        assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_list_models(self):
        models = await self.service.list_models()
        assert len(models) >= 1
        assert isinstance(models[0], ModelInfo)

    @pytest.mark.asyncio
    async def test_list_lora_adapters(self):
        adapters = await self.service.list_lora_adapters()
        assert isinstance(adapters, list)
        assert len(adapters) >= 1

    @pytest.mark.asyncio
    async def test_stream_generate(self):
        chunks = []
        async for chunk in self.service.stream_generate("Résume ce texte."):
            chunks.append(chunk)
        assert len(chunks) >= 1


# ── LoRA Registry ──


class TestLoRARegistry:

    def setup_method(self):
        self.registry = LoRARegistry()

    def test_default_adapters(self):
        adapters = self.registry.list_adapters()
        assert len(adapters) == 5
        names = [a.name for a in adapters]
        assert "legal-fr" in names
        assert "legal-nl" in names
        assert "summarization" in names
        assert "drafting" in names
        assert "classification" in names

    def test_get_adapter_for_drafting_fr(self):
        adapter = self.registry.get_adapter_for_task("DRAFTING", "fr")
        assert adapter is not None
        # legal-fr has priority 10 and supports DRAFTING+fr, vs drafting at priority 5
        assert adapter.name == "legal-fr"

    def test_get_adapter_for_analysis_fr(self):
        adapter = self.registry.get_adapter_for_task("ANALYSIS", "fr")
        assert adapter is not None
        assert adapter.name == "legal-fr"

    def test_get_adapter_for_analysis_nl(self):
        adapter = self.registry.get_adapter_for_task("ANALYSIS", "nl")
        assert adapter is not None
        assert adapter.name == "legal-nl"

    def test_get_adapter_for_summarization(self):
        adapter = self.registry.get_adapter_for_task("SUMMARIZATION")
        assert adapter is not None
        assert adapter.name in ("summarization", "legal-fr")

    def test_get_adapter_for_classification(self):
        adapter = self.registry.get_adapter_for_task("CLASSIFICATION")
        assert adapter is not None
        assert adapter.name == "classification"

    def test_get_adapter_for_unknown_task(self):
        adapter = self.registry.get_adapter_for_task("NONEXISTENT")
        assert adapter is None

    def test_register_custom_adapter(self):
        self.registry.register_adapter(
            name="custom-legal",
            lora_path="/models/custom",
            task_types=["ANALYSIS"],
            languages=["de"],
            base_model="mistral",
            priority=5,
        )
        adapters = self.registry.list_adapters()
        assert len(adapters) == 6
        assert any(a.name == "custom-legal" for a in adapters)

    def test_priority_ordering(self):
        """Higher priority adapter should be preferred."""
        self.registry.register_adapter(
            name="legal-fr-v2",
            lora_path="/models/legal-fr-v2",
            task_types=["ANALYSIS"],
            languages=["fr"],
            base_model="mistral",
            priority=20,
        )
        adapter = self.registry.get_adapter_for_task("ANALYSIS", "fr")
        assert adapter is not None
        assert adapter.name == "legal-fr-v2"

    def test_invalid_task_type_raises(self):
        with pytest.raises(ValueError, match="Invalid task types"):
            self.registry.register_adapter(
                name="bad",
                lora_path="/models/bad",
                task_types=["NONEXISTENT"],
            )

    def test_get_adapter_by_name(self):
        adapter = self.registry.get_adapter("legal-fr")
        assert adapter is not None
        assert adapter.name == "legal-fr"

    def test_get_unknown_adapter(self):
        adapter = self.registry.get_adapter("nonexistent")
        assert adapter is None

    def test_reset(self):
        self.registry.register_adapter(name="extra", lora_path="/x", task_types=["ANALYSIS"])
        assert len(self.registry.list_adapters()) == 6
        self.registry.reset()
        assert len(self.registry.list_adapters()) == 5


# ── LLM Gateway vLLM integration ──


class TestLLMGatewayVLLMBackend:

    def test_gateway_default_no_vllm(self):
        from apps.api.services.llm_gateway import LLMGateway
        gw = LLMGateway()
        assert gw._vllm_base_url == ""
        assert gw._vllm_available is None

    def test_gateway_with_vllm_url(self):
        from apps.api.services.llm_gateway import LLMGateway
        gw = LLMGateway(vllm_base_url="http://localhost:8001/v1")
        assert gw._vllm_base_url == "http://localhost:8001/v1"

    @pytest.mark.asyncio
    async def test_resolve_backend_fallback(self):
        from apps.api.services.llm_gateway import LLMGateway
        gw = LLMGateway(
            base_url="https://api.openai.com/v1",
            vllm_base_url="http://nonexistent:8001/v1",
        )
        backend = await gw._resolve_backend()
        # vLLM unreachable → falls back to OpenAI
        assert backend == "https://api.openai.com/v1"

    @pytest.mark.asyncio
    async def test_resolve_backend_no_vllm_configured(self):
        from apps.api.services.llm_gateway import LLMGateway
        gw = LLMGateway(base_url="https://api.openai.com/v1")
        backend = await gw._resolve_backend()
        assert backend == "https://api.openai.com/v1"
