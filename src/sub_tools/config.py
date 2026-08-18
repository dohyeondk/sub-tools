"""
Configuration for sub-tools.
"""

from dataclasses import dataclass, field, fields
from typing import Any

DEFAULT_MODEL = "gemini-3.7-flash"

# Prefixes that identify an OpenAI model name, e.g. gpt-5.6-luna.
OPENAI_MODEL_PREFIXES = ("gpt", "chatgpt", "o1", "o3", "o4")

SUPPORTED_PROVIDERS = ("google", "gemini", "anthropic", "openai", "openrouter")


def normalize_provider(provider: str) -> str:
    """Return a supported provider name, preserving ``gemini`` for compatibility."""
    value = provider.strip().lower()
    if value not in SUPPORTED_PROVIDERS:
        supported = ", ".join(SUPPORTED_PROVIDERS)
        raise ValueError(
            f"Unsupported provider {provider!r}; choose one of: {supported}"
        )
    return value


def infer_provider(model: str) -> str:
    """Infer a provider for callers that do not explicitly select one."""
    name = model.strip().lower()
    if name.startswith(OPENAI_MODEL_PREFIXES):
        return "openai"
    if name.startswith(("claude", "anthropic")):
        return "anthropic"
    if name.startswith("openrouter"):
        return "openrouter"
    return "gemini"


@dataclass
class Config:
    """
    Unified configuration for all sub-tools operations.
    """

    # CLI-provided/runtime options
    tasks: list[str] = field(
        default_factory=lambda: [
            "video",
            "audio",
            "signature",
            "transcribe",
            "translate",
        ]
    )
    url: str | None = None
    output_directory: str = "output"  # Destination for generated artifacts
    video_file: str = "video.mp4"
    audio_file: str = "audio.mp3"
    signature_file: str = "message.shazamsignature"
    source_language: str = "en"
    languages: list[str] = field(default_factory=lambda: ["en"])
    overwrite: bool = False
    retry: int = 3
    debug: bool = False

    # Model / provider
    model: str = DEFAULT_MODEL
    provider: str | None = None
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    audio_model: str | None = None  # Provider default is used when unset
    tts_model: str | None = None  # Provider default is used when unset
    tts_voice: str | None = None  # Provider default is used when unset

    _provider_explicit: bool = field(init=False, repr=False, default=False)

    # Validation
    max_valid_duration: int = (
        20_000  # Maximum allowed duration for any single subtitle (ms)
    )
    begin_gap_threshold: int = 5_000  # Maximum allowed gap at the beginning (ms)
    end_gap_threshold: int = 10_000  # Maximum allowed gap at the end (ms)
    inter_item_gap_threshold: int = (
        6_000  # Maximum allowed gap between consecutive subtitles (ms)
    )
    min_subtitles: int = 1  # Minimum number of subtitles
    max_missing_ratio: float = (
        0.02  # Share of source subtitles a translation may drop before it is rejected
    )

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "provider" and hasattr(self, "_provider_explicit"):
            if value is not None:
                value = normalize_provider(value)
            object.__setattr__(self, "_provider_explicit", value is not None)
        if name == "model" and hasattr(self, "_provider_explicit"):
            object.__setattr__(self, name, value)
            if not self._provider_explicit:
                object.__setattr__(self, "provider", infer_provider(value))
            return
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        self.set_provider(self.provider, explicit=self.provider is not None)

    def set_provider(self, provider: str | None, *, explicit: bool = True) -> None:
        """Select a provider, or infer it from the model when ``None`` is given."""
        if provider is None:
            value = infer_provider(self.model)
            explicit = False
        else:
            value = normalize_provider(provider)
        object.__setattr__(self, "provider", value)
        object.__setattr__(self, "_provider_explicit", explicit)

    @property
    def resolved_provider(self) -> str:
        """Return the provider currently selected for the configured model."""
        if not self._provider_explicit:
            return infer_provider(self.model)
        return self.provider  # type: ignore[return-value]

    @property
    def api_key(self) -> str | None:
        """
        The API key for the selected provider.
        """
        keys = {
            "google": self.gemini_api_key,
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "openrouter": self.openrouter_api_key,
        }
        return keys[self.resolved_provider]


# Global config instance
config = Config()


def apply_namespace(source: Any) -> Config:
    """
    Copy matching attributes from an argparse.Namespace-like object into config.
    """
    for field_def in fields(Config):
        if field_def.name.startswith("_") or field_def.name == "provider":
            continue
        if hasattr(source, field_def.name):
            setattr(config, field_def.name, getattr(source, field_def.name))

    requested_provider = getattr(source, "provider", None)
    config.set_provider(requested_provider, explicit=requested_provider is not None)
    return config
