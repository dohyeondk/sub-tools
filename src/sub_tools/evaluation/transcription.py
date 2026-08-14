"""Reference-based transcription metrics.

The evaluator deliberately accepts subtitle files rather than calling a model.
That keeps the measurement independent from the run that produced a track and
makes it possible to compare WhisperX-only output with Gemini-proofread output
on byte-identical input.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
import re
import subprocess
import unicodedata
from typing import Iterable, Sequence

import pysrt
from suber.file_readers import read_input_file
from suber.hyp_to_ref_alignment import levenshtein_align_hypothesis_to_reference
from suber.metrics.cer import calculate_character_error_rate
from suber.metrics.jiwer_interface import calculate_word_error_rate
from suber.metrics.suber import calculate_SubER


NON_SPACED_LANGUAGES = {"zh", "ja", "th", "lo", "km", "my", "bo"}
SUBER_LANGUAGE_CODES = {"zh", "ja", "ko"}
BRACKETED_RE = re.compile(r"[\[(][^\])]*[\])]")
BOILERPLATE = (
    "thanks for watching",
    "thank you for watching",
    "subscribe",
    "subtitles by",
    "amara.org",
    "transcribed by",
    "please subscribe",
)

ONES = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
)
TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")


@dataclass(frozen=True)
class Segment:
    """A timed subtitle cue in seconds."""

    index: int
    start: float
    end: float
    text: str


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


def number_to_words(number: int) -> str:
    """Spell integers up to 9999 so ``2`` and ``two`` compare equally."""

    if number < 20:
        return ONES[number]
    if number < 100:
        rest = number % 10
        return TENS[number // 10] + (f" {ONES[rest]}" if rest else "")
    if number < 1000:
        rest = number % 100
        return f"{ONES[number // 100]} hundred" + (f" {number_to_words(rest)}" if rest else "")
    if number < 10000:
        rest = number % 1000
        return f"{number_to_words(number // 1000)} thousand" + (
            f" {number_to_words(rest)}" if rest else ""
        )
    return str(number)


def normalize_text(
    text: str,
    language: str = "en",
    *,
    keep_annotations: bool = False,
    spell_numbers: bool = True,
) -> str:
    """Fold formatting differences that are not transcription errors."""

    output = str(text or "")
    if not keep_annotations:
        output = BRACKETED_RE.sub(" ", output)
    output = output.replace("’", "'").replace("‘", "'")
    output = output.replace("“", '"').replace("”", '"').casefold()

    if spell_numbers and language.lower().startswith("en"):
        output = re.sub(
            r"\d+",
            lambda match: f" {number_to_words(int(match.group(0))) } "
            if len(match.group(0)) <= 4
            else match.group(0),
            output,
        )

    # Apostrophes are ignored (don't/dont); every other punctuation or symbol
    # becomes a separator, matching the JavaScript evaluator in Auditorium.
    output = output.replace("'", "")
    output = "".join(
        " " if unicodedata.category(char).startswith(("P", "S")) else char
        for char in output
    )
    return " ".join(output.split())


def is_non_spaced(language: str) -> bool:
    return language.split("-")[0].lower() in NON_SPACED_LANGUAGES


def tokens(text: str, language: str = "en") -> list[str]:
    normalized = normalize_text(text, language)
    if not normalized:
        return []
    if is_non_spaced(language):
        return list(normalized.replace(" ", ""))
    return normalized.split(" ")


def chars(text: str, language: str = "en") -> list[str]:
    return list(normalize_text(text, language).replace(" ", ""))


def parse_srt(content: str) -> list[Segment]:
    """Parse an SRT string with pysrt and return normalized timed cues."""

    subtitles = pysrt.from_string(content)
    if not subtitles:
        raise ValueError("No subtitle cues found in SRT input")
    return [
        Segment(
            index=index,
            start=item.start.ordinal / 1000,
            end=item.end.ordinal / 1000,
            text=item.text.strip(),
        )
        for index, item in enumerate(subtitles)
    ]


def load_srt(path: str | Path) -> list[Segment]:
    path = Path(path)
    return parse_srt(path.read_text(encoding="utf-8-sig"))


def _suber_language(language: str) -> str | None:
    """Map a BCP-47 language tag to SubER's optional tokenizer code."""

    code = language.split("-", 1)[0].lower()
    return code if code in SUBER_LANGUAGE_CODES else None


def authoritative_metrics(
    reference_path: str | Path,
    hypothesis_path: str | Path,
    language: str = "en",
) -> dict:
    """Calculate published, reference-based subtitle metrics.

    SubER is the primary metric because it evaluates text, segmentation, and
    timing together. AS-WER and AS-CER are the package's automatic-segmentation
    lexical diagnostics; the Levenshtein alignment makes them valid when the
    hypothesis and reference have different cue boundaries.
    """

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


def full_text(segments: Sequence[Segment]) -> str:
    return " ".join(segment.text for segment in segments)


def _edit_ops(reference: Sequence[str], hypothesis: Sequence[str]) -> dict[str, int | float]:
    """Levenshtein distance with a deterministic substitution/insertion split."""

    previous = [(j, 0, j, 0) for j in range(len(hypothesis) + 1)]
    for ref_index, ref_token in enumerate(reference, start=1):
        current: list[tuple[int, int, int, int]] = [(ref_index, 0, 0, ref_index)]
        for hyp_index, hyp_token in enumerate(hypothesis, start=1):
            if ref_token == hyp_token:
                current.append(previous[hyp_index - 1])
                continue
            substitution = previous[hyp_index - 1]
            insertion = current[hyp_index - 1]
            deletion = previous[hyp_index]
            if substitution[0] <= insertion[0] and substitution[0] <= deletion[0]:
                current.append((substitution[0] + 1, substitution[1] + 1, substitution[2], substitution[3]))
            elif insertion[0] <= deletion[0]:
                current.append((insertion[0] + 1, insertion[1], insertion[2] + 1, insertion[3]))
            else:
                current.append((deletion[0] + 1, deletion[1], deletion[2], deletion[3] + 1))
        previous = current

    distance, substitutions, insertions, deletions = previous[-1]
    reference_length = len(reference)
    return {
        "distance": distance,
        "substitutions": substitutions,
        "insertions": insertions,
        "deletions": deletions,
        "reference_length": reference_length,
        "hypothesis_length": len(hypothesis),
        "rate": distance / reference_length if reference_length else (1.0 if hypothesis else 0.0),
    }


def _primary_error_rate(reference: str, hypothesis: str, language: str) -> dict:
    word_errors = _edit_ops(tokens(reference, language), tokens(hypothesis, language))
    character_errors = _edit_ops(chars(reference, language), chars(hypothesis, language))
    rate = character_errors["rate"] if is_non_spaced(language) else word_errors["rate"]
    return {
        "unit": "cer" if is_non_spaced(language) else "wer",
        "rate": rate,
        "accuracy": max(0.0, 1.0 - rate),
        "wer": word_errors,
        "cer": character_errors,
    }


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def _quantile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.floor(percentile * len(ordered)))]


def _coverage(segments: Sequence[Segment], duration_seconds: float, threshold: float = 3.0) -> dict:
    sorted_segments = sorted(segments, key=lambda segment: (segment.start, segment.end))
    covered = 0.0
    cursor = 0.0
    all_gaps: list[float] = []
    long_gaps: list[float] = []
    overlap_seconds = 0.0
    overlaps = 0

    for position, segment in enumerate(sorted_segments):
        start = max(0.0, segment.start)
        end = min(duration_seconds, max(start, segment.end))
        if start > cursor:
            gap = start - cursor
            all_gaps.append(gap)
            if gap > threshold:
                long_gaps.append(gap)
        if position and start < sorted_segments[position - 1].end - 1e-6:
            overlaps += 1
        if start < cursor:
            overlap_seconds += max(0.0, min(cursor, end) - start)
        if end > cursor:
            covered += end - max(cursor, start)
            cursor = end

    if cursor < duration_seconds:
        gap = duration_seconds - cursor
        all_gaps.append(gap)
        if gap > threshold:
            long_gaps.append(gap)

    return {
        "duration_seconds": duration_seconds,
        "covered_seconds": covered,
        "coverage_ratio": covered / duration_seconds if duration_seconds > 0 else 0.0,
        "uncovered_seconds": sum(all_gaps),
        "gap_seconds": sum(long_gaps),
        "largest_gap_seconds": max(long_gaps, default=0.0),
        "largest_any_gap_seconds": max(all_gaps, default=0.0),
        "gaps": len(long_gaps),
        "overlaps": overlaps,
        "overlap_seconds": overlap_seconds,
    }


def _token_timeline(segments: Sequence[Segment], language: str) -> list[tuple[str, float]]:
    timeline: list[tuple[str, float]] = []
    for segment in segments:
        units = tokens(segment.text, language)
        if not units:
            continue
        span = max(0.0, segment.end - segment.start)
        for index, token in enumerate(units):
            timeline.append((token, segment.start + span * (index + 0.5) / len(units)))
    return timeline


def _unique_ngram_positions(timeline: Sequence[tuple[str, float]], n: int = 4) -> dict[tuple[str, ...], int]:
    positions: dict[tuple[str, ...], int] = {}
    for index in range(len(timeline) - n + 1):
        key = tuple(token for token, _ in timeline[index : index + n])
        if key in positions:
            positions[key] = -1
        else:
            positions[key] = index
    return positions


def _longest_increasing(pairs: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    tails: list[int] = []
    previous = [-1] * len(pairs)
    tail_indices: list[int] = []
    for index, (_, hypothesis_index) in enumerate(pairs):
        low, high = 0, len(tails)
        while low < high:
            middle = (low + high) // 2
            if tails[middle] < hypothesis_index:
                low = middle + 1
            else:
                high = middle
        if low == len(tails):
            tails.append(hypothesis_index)
            tail_indices.append(index)
        else:
            tails[low] = hypothesis_index
            tail_indices[low] = index
        previous[index] = tail_indices[low - 1] if low else -1

    output: list[tuple[int, int]] = []
    cursor = tail_indices[-1] if tail_indices else -1
    while cursor != -1:
        output.append(pairs[cursor])
        cursor = previous[cursor]
    return list(reversed(output))


def _anchors(reference: Sequence[Segment], hypothesis: Sequence[Segment], language: str) -> list[dict]:
    reference_timeline = _token_timeline(reference, language)
    hypothesis_timeline = _token_timeline(hypothesis, language)
    reference_positions = _unique_ngram_positions(reference_timeline)
    hypothesis_positions = _unique_ngram_positions(hypothesis_timeline)
    pairs: list[tuple[int, int]] = []
    for key, reference_index in reference_positions.items():
        hypothesis_index = hypothesis_positions.get(key)
        if reference_index < 0 or hypothesis_index is None or hypothesis_index < 0:
            continue
        pairs.append((reference_index, hypothesis_index))
    pairs.sort()
    anchors = []
    for reference_index, hypothesis_index in _longest_increasing(pairs):
        reference_time = reference_timeline[reference_index][1]
        hypothesis_time = hypothesis_timeline[hypothesis_index][1]
        anchors.append(
            {
                "reference_time": reference_time,
                "hypothesis_time": hypothesis_time,
                "delta": hypothesis_time - reference_time,
            }
        )
    return anchors


def _timing_stats(anchor_list: Sequence[dict]) -> dict:
    deltas = [anchor["delta"] for anchor in anchor_list]
    absolute = [abs(delta) for delta in deltas]
    if not deltas:
        return {
            "anchors": 0,
            "median_delta": None,
            "median_abs": None,
            "p90_abs": None,
            "max_abs": None,
            "slope_seconds_per_minute": None,
            "within_500ms": None,
            "within_1s": None,
        }

    median = _percentile(deltas, 0.5)
    mean_x = sum(anchor["reference_time"] for anchor in anchor_list) / len(anchor_list)
    mean_y = sum(deltas) / len(deltas)
    sxy = sum(
        (anchor["reference_time"] - mean_x) * (anchor["delta"] - mean_y)
        for anchor in anchor_list
    )
    sxx = sum((anchor["reference_time"] - mean_x) ** 2 for anchor in anchor_list)
    return {
        "anchors": len(deltas),
        "median_delta": median,
        "median_abs": _percentile(absolute, 0.5),
        "p90_abs": _quantile(absolute, 0.9),
        "max_abs": max(absolute),
        "slope_seconds_per_minute": (sxy / sxx) * 60 if sxx else 0.0,
        "within_500ms": sum(delta <= 0.5 for delta in absolute) / len(absolute),
        "within_1s": sum(delta <= 1.0 for delta in absolute) / len(absolute),
    }


def _binned_f1(reference: Sequence[Segment], hypothesis: Sequence[Segment], language: str, bin_seconds: float = 1.0) -> float:
    def bucket(segments: Sequence[Segment]) -> dict[int, Counter[str]]:
        buckets: dict[int, Counter[str]] = {}
        for token, timestamp in _token_timeline(segments, language):
            buckets.setdefault(math.floor(timestamp / bin_seconds), Counter())[token] += 1
        return buckets

    reference_bins = bucket(reference)
    hypothesis_bins = bucket(hypothesis)
    shared = reference_total = hypothesis_total = 0
    for key in set(reference_bins) | set(hypothesis_bins):
        reference_counts = reference_bins.get(key, Counter())
        hypothesis_counts = hypothesis_bins.get(key, Counter())
        reference_total += sum(reference_counts.values())
        hypothesis_total += sum(hypothesis_counts.values())
        shared += sum(min(count, hypothesis_counts.get(token, 0)) for token, count in reference_counts.items())
    precision = shared / hypothesis_total if hypothesis_total else 0.0
    recall = shared / reference_total if reference_total else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _proper_nouns(text: str) -> set[str]:
    lowercased = set()
    for word in text.split():
        clean = re.sub(r"^[^\w]+|[^\w]+$", "", word, flags=re.UNICODE)
        if clean and clean == clean.casefold():
            lowercased.add(clean.casefold())

    found = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
        for index, word in enumerate(sentence.strip().split()):
            clean = re.sub(r"^[^\w]+|[^\w]+$", "", word, flags=re.UNICODE)
            if index == 0 or len(clean) < 3:
                continue
            if not (clean[0].isupper() and clean[1:].islower()):
                continue
            if clean.casefold() in lowercased:
                continue
            found.add(clean.casefold())
    return found


def _max_repetition_share(text: str, language: str, n: int = 5) -> float:
    units = tokens(text, language)
    if len(units) < n * 3:
        return 0.0
    counts = Counter(tuple(units[index : index + n]) for index in range(len(units) - n + 1))
    worst = max(counts.values(), default=0)
    return worst * n / len(units)


def intrinsic_metrics(segments: Sequence[Segment], duration_seconds: float, language: str = "en") -> dict:
    durations = [max(0.0, segment.end - segment.start) for segment in segments]
    lengths = [len(segment.text) for segment in segments]
    cps = [
        len(segment.text) / (segment.end - segment.start)
        for segment in segments
        if segment.end - segment.start > 0.2
    ]
    lines = [segment.text.split("\n") for segment in segments]
    text = full_text(segments)
    coverage = _coverage(segments, duration_seconds)
    return {
        "segments": len(segments),
        "duration_seconds": duration_seconds,
        "segments_per_minute": len(segments) / duration_seconds * 60 if duration_seconds else 0.0,
        "coverage": coverage,
        "segment_seconds": {
            "p50": _percentile(durations, 0.5),
            "p90": _percentile(durations, 0.9),
            "max": max(durations, default=None),
            "share_in_target_band": sum(2 <= duration <= 5 for duration in durations) / len(durations)
            if durations
            else 0.0,
            "share_over_hard_limit": sum(duration > 20 for duration in durations) / len(durations)
            if durations
            else 0.0,
        },
        "readability": {
            "chars_p50": _percentile(lengths, 0.5),
            "chars_p90": _percentile(lengths, 0.9),
            "share_over_max_chars": sum(length > 84 for length in lengths) / len(lengths) if lengths else 0.0,
            "share_over_max_lines": sum(len(line) > 2 for line in lines) / len(lines) if lines else 0.0,
            "cps_p50": _percentile(cps, 0.5),
            "cps_p90": _percentile(cps, 0.9),
            "share_over_max_cps": sum(value > 20 for value in cps) / len(cps) if cps else 0.0,
        },
        "hallucination": {
            "repeated_segments": sum(
                index > 0 and segment.text.strip() == segments[index - 1].text.strip()
                for index, segment in enumerate(segments)
            ),
            "max_repeated_phrase_share": _max_repetition_share(text, language),
            "boilerplate_hits": [phrase for phrase in BOILERPLATE if phrase in text.casefold()],
        },
        "beyond_duration": sum(segment.end > duration_seconds + 0.5 for segment in segments),
    }


def reference_metrics(reference: Sequence[Segment], hypothesis: Sequence[Segment], language: str = "en") -> dict:
    errors = _primary_error_rate(full_text(reference), full_text(hypothesis), language)
    reference_nouns = _proper_nouns(full_text(reference))
    hypothesis_nouns = _proper_nouns(full_text(hypothesis))
    missed_nouns = sorted(reference_nouns - hypothesis_nouns)
    return {
        "unit": errors["unit"],
        "error_rate": errors["rate"],
        "accuracy": errors["accuracy"],
        "wer": errors["wer"],
        "cer": errors["cer"],
        "timing": _timing_stats(_anchors(reference, hypothesis, language)),
        "lexical_f1_per_second": _binned_f1(reference, hypothesis, language),
        "proper_noun_recall": (
            (len(reference_nouns) - len(missed_nouns)) / len(reference_nouns)
            if reference_nouns
            else None
        ),
        "missed_proper_nouns": missed_nouns[:25],
    }


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def score_transcription(intrinsic: dict, reference: dict) -> dict:
    parts = [
        ("coverage", 15, _clamp(intrinsic["coverage"]["coverage_ratio"] / 0.9)),
        (
            "structure",
            10,
            _clamp(
                1
                - intrinsic["segment_seconds"]["share_over_hard_limit"] * 2
                - (0.3 if intrinsic["coverage"]["overlaps"] else 0.0)
                - (0.2 if intrinsic["beyond_duration"] else 0.0)
                - _clamp(intrinsic["hallucination"]["max_repeated_phrase_share"] * 3)
                - (0.25 if intrinsic["hallucination"]["boilerplate_hits"] else 0.0)
            ),
        ),
        (
            "readability",
            10,
            _clamp(
                1
                - intrinsic["readability"]["share_over_max_cps"]
                - intrinsic["readability"]["share_over_max_chars"] * 0.5
                - intrinsic["readability"]["share_over_max_lines"] * 0.5
            ),
        ),
        ("accuracy", 40, _clamp(1 - reference["error_rate"] / 0.3)),
        (
            "timing",
            25,
            _clamp(1 - (reference["timing"]["median_abs"] or 0.0) / 1.5),
        ),
    ]
    score = sum(weight * value for _, weight, value in parts) / sum(weight for _, weight, _ in parts)
    return {
        "score": round(score * 1000) / 10,
        "parts": [
            {"name": name, "weight": weight, "value": value, "points": round(weight * value * 10) / 10}
            for name, weight, value in parts
        ],
    }


def transcription_gates(intrinsic: dict) -> list[str]:
    coverage = intrinsic["coverage"]
    failures: list[str] = []
    if intrinsic["segments"] < 2:
        failures.append("fewer than two segments")
    if coverage["coverage_ratio"] < 0.6:
        failures.append(f"covers only {coverage['coverage_ratio'] * 100:.0f}% of the audio")
    if coverage["largest_gap_seconds"] > 30:
        failures.append(f"a {coverage['largest_gap_seconds']:.0f}s stretch has no captions")
    if coverage["overlaps"]:
        failures.append(f"{coverage['overlaps']} overlapping segments")
    if intrinsic["beyond_duration"]:
        failures.append(f"{intrinsic['beyond_duration']} segments end after the audio does")
    if intrinsic["hallucination"]["max_repeated_phrase_share"] > 0.2:
        failures.append(
            f"one phrase fills {intrinsic['hallucination']['max_repeated_phrase_share'] * 100:.0f}% of the transcript"
        )
    if intrinsic["hallucination"]["boilerplate_hits"]:
        failures.append(
            "boilerplate in the transcript: " + ", ".join(intrinsic["hallucination"]["boilerplate_hits"])
        )
    return failures


def evaluate_transcription(
    reference: Sequence[Segment],
    hypothesis: Sequence[Segment],
    duration_seconds: float,
    language: str = "en",
) -> dict:
    """Evaluate one generated SRT against a human reference transcript."""

    intrinsic = intrinsic_metrics(hypothesis, duration_seconds, language)
    reference_result = reference_metrics(reference, hypothesis, language)
    score = score_transcription(intrinsic, reference_result)
    return {
        "heuristic_score": score["score"],
        "heuristic_score_parts": score["parts"],
        "accuracy": reference_result["accuracy"],
        "wer": reference_result["wer"],
        "cer": reference_result["cer"],
        "timing": reference_result["timing"],
        "lexical_f1_per_second": reference_result["lexical_f1_per_second"],
        "proper_noun_recall": reference_result["proper_noun_recall"],
        "missed_proper_nouns": reference_result["missed_proper_nouns"],
        "intrinsic": intrinsic,
        "gates": transcription_gates(intrinsic),
    }


def audio_duration_seconds(path: str | Path) -> float:
    """Read an audio duration through ffprobe for the CLI's convenience mode."""

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise RuntimeError("ffprobe is required when --duration is omitted") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or "unknown ffprobe error"
        raise RuntimeError(f"Could not read audio duration: {detail}") from error
    return float(result.stdout.strip())
