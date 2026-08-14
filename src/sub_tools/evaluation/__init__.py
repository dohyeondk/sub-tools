"""Reference-based evaluation for generated subtitle tracks."""

from .transcription import evaluate_transcription, load_srt

__all__ = ["evaluate_transcription", "load_srt"]
