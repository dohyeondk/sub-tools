"""Thin adapter around the published ``subtitle-edit-rate`` package.

This module intentionally contains no local transcription metric
implementation. SubER, AS-WER, and AS-CER all come from the pinned package so
the command uses the same algorithms as the upstream reference implementation.
"""

from __future__ import annotations

from pathlib import Path

from suber.file_readers import read_input_file
from suber.hyp_to_ref_alignment import levenshtein_align_hypothesis_to_reference
from suber.metrics.cer import calculate_character_error_rate
from suber.metrics.jiwer_interface import calculate_word_error_rate
from suber.metrics.suber import calculate_SubER


SUBER_LANGUAGE_CODES = {"zh", "ja", "ko"}

EVALUATION_METHODOLOGY = {
    "primary_metric": "SubER",
    "primary_direction": "lower_is_better",
    "lexical_metrics": ["AS-WER", "AS-CER"],
    "implementation": "subtitle-edit-rate==0.4.0",
    "sources": {
        "suber_paper": "https://aclanthology.org/2022.iwslt-1.1/",
        "suber_implementation": "https://github.com/apptek/SubER",
        "suber_package": "https://pypi.org/project/subtitle-edit-rate/",
        "nist_sclite": "https://github.com/usnistgov/SCTK/blob/master/doc/sclite.htm",
    },
}


def _suber_language(language: str) -> str | None:
    """Map a BCP-47 tag to the tokenizer codes accepted by SubER."""

    code = language.split("-", 1)[0].lower()
    return code if code in SUBER_LANGUAGE_CODES else None


def authoritative_metrics(
    reference_path: str | Path,
    hypothesis_path: str | Path,
    language: str = "en",
) -> dict[str, float]:
    """Return SubER, AS-WER, and AS-CER from ``subtitle-edit-rate``."""

    suber_language = _suber_language(language)
    reference = read_input_file(str(reference_path), "SRT")
    hypothesis = read_input_file(str(hypothesis_path), "SRT")
    aligned_hypothesis = levenshtein_align_hypothesis_to_reference(
        hypothesis=hypothesis,
        reference=reference,
        language=suber_language,
    )

    return {
        "suber": calculate_SubER(
            hypothesis=hypothesis,
            reference=reference,
            language=suber_language,
        ),
        "as_wer": calculate_word_error_rate(
            hypothesis=aligned_hypothesis,
            reference=reference,
            score_break_at_segment_end=True,
            language=suber_language,
        ),
        "as_cer": calculate_character_error_rate(
            hypothesis=aligned_hypothesis,
            reference=reference,
        ),
    }
