"""Thin adapter around the published ``subtitle-edit-rate`` package.

This module intentionally contains no local transcription metric
implementation. SubER and the AS-*/t-* metrics all come from the pinned package so
the command uses the same algorithms as the upstream reference implementation.
"""

from __future__ import annotations

from pathlib import Path

from suber.file_readers import read_input_file
from suber.hyp_to_ref_alignment import (
    levenshtein_align_hypothesis_to_reference,
    time_align_hypothesis_to_reference,
)
from suber.metrics.cer import calculate_character_error_rate
from suber.metrics.jiwer_interface import calculate_word_error_rate
from suber.metrics.sacrebleu_interface import calculate_sacrebleu_metric
from suber.metrics.suber import calculate_SubER


SUBER_LANGUAGE_CODES = {"zh", "ja", "ko"}

EVALUATION_METHODOLOGY = {
    "primary_metric": "SubER",
    "primary_direction": "lower_is_better",
    "lexical_metrics": ["AS-WER", "AS-CER", "AS-BLEU", "AS-TER", "AS-chrF"],
    "timing_aligned_metrics": ["t-WER", "t-CER", "t-BLEU", "t-TER", "t-chrF"],
    "directions": {
        "SubER": "lower_is_better",
        "AS-WER": "lower_is_better",
        "AS-CER": "lower_is_better",
        "AS-BLEU": "higher_is_better",
        "AS-TER": "lower_is_better",
        "AS-chrF": "higher_is_better",
        "t-WER": "lower_is_better",
        "t-CER": "lower_is_better",
        "t-BLEU": "higher_is_better",
        "t-TER": "lower_is_better",
        "t-chrF": "higher_is_better",
    },
    "implementation": "subtitle-edit-rate==0.4.0",
    "sources": {
        "suber_paper": "https://aclanthology.org/2022.iwslt-1.1/",
        "automatic_segmentation_metrics": "https://aclanthology.org/2005.iwslt-1.19/",
        "timing_aligned_bleu": "https://www.isca-archive.org/interspeech_2021/cherry21_interspeech.pdf",
        "suber_implementation": "https://github.com/apptek/SubER",
        "suber_package": "https://pypi.org/project/subtitle-edit-rate/0.4.0/",
        "sacrebleu": "https://github.com/mjpost/sacrebleu",
        "nist_sclite": "https://github.com/usnistgov/SCTK/blob/master/doc/sclite.htm",
    },
}


def _aligned_metrics(
    hypothesis: list,
    reference: list,
    language: str | None,
    prefix: str,
) -> dict[str, float]:
    """Call the package's lexical metrics for one package alignment mode."""

    return {
        f"{prefix}_wer": calculate_word_error_rate(
            hypothesis=hypothesis,
            reference=reference,
            score_break_at_segment_end=True,
            language=language,
        ),
        f"{prefix}_cer": calculate_character_error_rate(
            hypothesis=hypothesis,
            reference=reference,
        ),
        f"{prefix}_bleu": calculate_sacrebleu_metric(
            hypothesis=hypothesis,
            reference=reference,
            metric="BLEU",
            score_break_at_segment_end=True,
            language=language,
        ),
        f"{prefix}_ter": calculate_sacrebleu_metric(
            hypothesis=hypothesis,
            reference=reference,
            metric="TER",
            score_break_at_segment_end=True,
            language=language,
        ),
        f"{prefix}_chrf": calculate_sacrebleu_metric(
            hypothesis=hypothesis,
            reference=reference,
            metric="chrF",
            score_break_at_segment_end=True,
            language=language,
        ),
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
    """Return package-provided SubER and alignment-specific lexical metrics."""

    suber_language = _suber_language(language)
    reference = read_input_file(str(reference_path), "SRT")
    hypothesis = read_input_file(str(hypothesis_path), "SRT")
    aligned_hypothesis = levenshtein_align_hypothesis_to_reference(
        hypothesis=hypothesis,
        reference=reference,
        language=suber_language,
    )
    time_aligned_hypothesis = time_align_hypothesis_to_reference(
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
        **_aligned_metrics(aligned_hypothesis, reference, suber_language, "as"),
        **_aligned_metrics(time_aligned_hypothesis, reference, suber_language, "t"),
    }
