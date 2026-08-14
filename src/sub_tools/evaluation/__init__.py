"""Reference-based evaluation for generated subtitle tracks."""

from .transcription import (
    EVALUATION_METHODOLOGY,
    authoritative_metrics,
    evaluate_transcription,
    load_srt,
)

__all__ = ["EVALUATION_METHODOLOGY", "authoritative_metrics", "evaluate_transcription", "load_srt"]
