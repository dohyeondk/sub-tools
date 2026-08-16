"""
Configuration for sub-tools.
"""

from dataclasses import dataclass, field, fields
from typing import Any


DEFAULT_GEMINI_MODEL = "gemini-3.7-flash"
DEFAULT_GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"


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

    # Gemini
    gemini_api_key: str | None = None
    gemini_model: str = DEFAULT_GEMINI_MODEL
    gemini_tts_model: str = DEFAULT_GEMINI_TTS_MODEL
    gemini_tts_voice: str = "Sadaltager"

    # Dub synchronization
    dub_chunk_duration: float = 300.0
    dub_gap_threshold: float = 2.0

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
