"""LoRA Registry — manage available LoRA adapters for Multi-LoRA vLLM.

Task types: DRAFTING, SUMMARIZATION, ANALYSIS, TRANSLATION, CLASSIFICATION
Each adapter is associated with task types and languages.
Config loaded from YAML (infra/lora/adapters.yaml).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LoRAAdapter:
    """A registered LoRA adapter."""

    name: str
    base_model: str
    lora_path: str
    description: str = ""
    task_types: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    priority: int = 0  # Higher = preferred


# ── Valid task types ──

VALID_TASK_TYPES = {
    "DRAFTING",
    "SUMMARIZATION",
    "ANALYSIS",
    "TRANSLATION",
    "CLASSIFICATION",
}

# ── Default adapters (loaded from YAML or hardcoded fallback) ──

_DEFAULT_ADAPTERS = [
    LoRAAdapter(
        name="legal-fr",
        base_model="mistralai/Mistral-7B-Instruct-v0.2",
        lora_path="/models/lora/legal-fr",
        description="French Belgian legal language model",
        task_types=["DRAFTING", "SUMMARIZATION", "ANALYSIS"],
        languages=["fr"],
        priority=10,
    ),
    LoRAAdapter(
        name="legal-nl",
        base_model="mistralai/Mistral-7B-Instruct-v0.2",
        lora_path="/models/lora/legal-nl",
        description="Dutch Belgian legal language model",
        task_types=["DRAFTING", "SUMMARIZATION", "ANALYSIS"],
        languages=["nl"],
        priority=10,
    ),
    LoRAAdapter(
        name="summarization",
        base_model="mistralai/Mistral-7B-Instruct-v0.2",
        lora_path="/models/lora/summarization",
        description="Document summarization specialist",
        task_types=["SUMMARIZATION"],
        languages=["fr", "nl"],
        priority=5,
    ),
    LoRAAdapter(
        name="drafting",
        base_model="mistralai/Mistral-7B-Instruct-v0.2",
        lora_path="/models/lora/drafting",
        description="Legal document drafting specialist",
        task_types=["DRAFTING"],
        languages=["fr", "nl"],
        priority=5,
    ),
    LoRAAdapter(
        name="classification",
        base_model="mistralai/Mistral-7B-Instruct-v0.2",
        lora_path="/models/lora/classification",
        description="Email and document classifier",
        task_types=["CLASSIFICATION"],
        languages=["fr", "nl"],
        priority=5,
    ),
]


class LoRARegistry:
    """Registry of available LoRA adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, LoRAAdapter] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default adapter definitions."""
        for adapter in _DEFAULT_ADAPTERS:
            self._adapters[adapter.name] = adapter

    def _load_from_yaml(self, path: str) -> None:
        """Load adapters from YAML config file."""
        try:
            import yaml

            with open(path) as f:
                config = yaml.safe_load(f)

            for entry in config.get("adapters", []):
                adapter = LoRAAdapter(
                    name=entry["name"],
                    base_model=entry.get(
                        "base_model", "mistralai/Mistral-7B-Instruct-v0.2"
                    ),
                    lora_path=entry.get("lora_path", ""),
                    description=entry.get("description", ""),
                    task_types=entry.get("task_types", []),
                    languages=entry.get("languages", ["fr"]),
                    priority=entry.get("priority", 0),
                )
                self._adapters[adapter.name] = adapter
        except (FileNotFoundError, ImportError):
            pass  # Use defaults

    def register_adapter(
        self,
        name: str,
        lora_path: str,
        description: str = "",
        task_types: Optional[list[str]] = None,
        base_model: str = "mistralai/Mistral-7B-Instruct-v0.2",
        languages: Optional[list[str]] = None,
        priority: int = 0,
    ) -> LoRAAdapter:
        """Register a new LoRA adapter.

        Args:
            name: Unique adapter name
            lora_path: Path to LoRA weights
            description: Human-readable description
            task_types: List of supported task types
            base_model: Base model this adapter was trained on
            languages: Supported languages
            priority: Selection priority (higher = preferred)

        Returns:
            Registered LoRAAdapter
        """
        if task_types:
            invalid = set(task_types) - VALID_TASK_TYPES
            if invalid:
                raise ValueError(
                    f"Invalid task types: {invalid}. Valid: {VALID_TASK_TYPES}"
                )

        adapter = LoRAAdapter(
            name=name,
            base_model=base_model,
            lora_path=lora_path,
            description=description,
            task_types=task_types or [],
            languages=languages or ["fr"],
            priority=priority,
        )
        self._adapters[name] = adapter
        return adapter

    def get_adapter(self, name: str) -> Optional[LoRAAdapter]:
        """Get an adapter by name."""
        return self._adapters.get(name)

    def get_adapter_for_task(
        self,
        task_type: str,
        language: str = "fr",
    ) -> Optional[LoRAAdapter]:
        """Get the best adapter for a given task type and language.

        Selects by: task_type match → language match → highest priority.

        Args:
            task_type: One of VALID_TASK_TYPES
            language: Target language code

        Returns:
            Best matching LoRAAdapter or None
        """
        candidates = [a for a in self._adapters.values() if task_type in a.task_types]

        if not candidates:
            return None

        # Prefer language match
        lang_match = [a for a in candidates if language in a.languages]
        if lang_match:
            candidates = lang_match

        # Sort by priority descending
        candidates.sort(key=lambda a: a.priority, reverse=True)
        return candidates[0]

    def list_adapters(self) -> list[LoRAAdapter]:
        """List all registered adapters."""
        return list(self._adapters.values())

    def list_task_types(self) -> list[str]:
        """List all valid task types."""
        return sorted(VALID_TASK_TYPES)

    def reset(self) -> None:
        """Reset registry (for testing)."""
        self._adapters.clear()
        self._load_defaults()
