"""
Configuration for sub-tools.
"""

from dataclasses import dataclass, field, fields
from typing import Any


DEFAULT_MODEL = "gemini-3.7-flash"

# Prefixes that identify an OpenAI model name, e.g. gpt-5.6-luna.
OPENAI_MODEL_PREFIXES = ("gpt", "chatgpt", "o1", "o3", "o4")


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
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    audio_model: str | None = None  # Provider default is used when unset
    tts_model: str | None = None  # Provider default is used when unset
    tts_voice: str | None = None  # Provider default is used when unset

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

    @property
    def provider(self) -> str:
        """
        The API provider implied by the model name: "openai" or "gemini".
        """
        name = self.model.lower()
        if name.startswith(OPENAI_MODEL_PREFIXES):
            return "openai"
        return "gemini"

    @property
    def api_key(self) -> str | None:
        """
        The API key for the selected provider.
        """
        if self.provider == "openai":
            return self.openai_api_key
        return self.gemini_api_key


# Global config instance
config = Config()


def apply_namespace(source: Any) -> Config:
    """
    Copy matching attributes from an argparse.Namespace-like object into config.
    """
    for field_def in fields(Config):
        if hasattr(source, field_def.name):
            setattr(config, field_def.name, getattr(source, field_def.name))
    return config
