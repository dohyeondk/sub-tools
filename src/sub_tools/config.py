"""
Configuration for sub-tools.
"""

from dataclasses import dataclass


@dataclass
class Config:
    """
    Unified configuration for all sub-tools operations.
    """

    # Shared
    directory: str | None = None
    output_file: str | None = None  # Custom output filename for combined subtitles

    # Gemini
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash-lite"
    gemini_max_retries: int = 3

    # WhisperX
    whisperx_model: str = "large-v2"  # WhisperX model to use
    whisperx_device: str = "cpu"  # Device for WhisperX inference (cpu, cuda)
    whisperx_compute_type: str = "int8"  # Compute type (int8, float16, float32)

    # Segmentation
    min_segment_length: int = 200  # 200 ms
    min_silent_length: int = 200  # 200 ms
    max_silence_length: int = 3_000  # 3 seconds
    segment_threshold: float = 0.5

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
