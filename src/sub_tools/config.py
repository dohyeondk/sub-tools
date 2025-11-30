"""
Configuration for sub-tools.
"""

from dataclasses import dataclass, field, fields
from typing import Any


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
    srt_file: str = "transcript.srt"
    source_language: str = "en"
    languages: list[str] = field(default_factory=lambda: ["en"])
    overwrite: bool = False
    retry: int = 3
    debug: bool = False

    # Gemini
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3-pro-preview"

    # WhisperX
    whisperx_model: str = "large-v3"  # WhisperX model to use
    whisperx_device: str = "cpu"  # Device for WhisperX inference (cpu, cuda)
    whisperx_compute_type: str = "int8"  # Compute type (int8, float16, float32)
    whisperx_batch_size: int = 16  # Batch size for WhisperX inference

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
