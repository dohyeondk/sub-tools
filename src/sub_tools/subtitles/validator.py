import pysrt
from dataclasses import dataclass

from pysrt import SubRipFile
from ..config.base import BaseConfig
from ..config.errors import ValidationError
from ..config.validation import validate_min_count, validate_threshold, parse_subtitles


@dataclass
class ValidateConfig(BaseConfig):
    """
    Configuration for subtitle validation.
    """

    max_valid_duration: int = 20_000  # Maximum allowed duration for any single subtitle (ms)
    begin_gap_threshold: int = 5_000  # Maximum allowed gap at the beginning (ms)
    end_gap_threshold: int = 10_000  # Maximum allowed gap at the end (ms)
    inter_item_gap_threshold: int = 6_000  # Maximum allowed gap between consecutive subtitles (ms)
    min_subtitles: int = 1  # Minimum number of subtitles


class SubtitleValidationError(ValidationError):
    """
    Custom exception for subtitle validation errors.
    """
    pass


def validate_subtitles(
    content: str,
    duration: int,
    config: ValidateConfig = ValidateConfig(),
) -> None:
    """
    Validate subtitles against specified criteria.
    """
    try:
        subs = _parse_subtitles(content)
        _validate_subtitle_count(subs, config.min_subtitles)
        _validate_subtitle_durations(subs, config.max_valid_duration)
        _validate_time_boundaries(subs, duration, config)
        _validate_time_ordering(subs)
        _validate_gaps(subs, config.inter_item_gap_threshold)

    except SubtitleValidationError as e:
        raise


def _parse_subtitles(content: str) -> SubRipFile:
    """
    Parse SRT content into subtitle objects.
    """
    return parse_subtitles(content, SubtitleValidationError)


def _validate_subtitle_count(subs: SubRipFile, min_count: int) -> None:
    """
    Validate minimum number of subtitles.
    """
    validate_min_count(
        subs, 
        min_count, 
        "Not enough subtitles. Found {found}, minimum required: {min_count}"
    )


def _validate_subtitle_durations(subs: SubRipFile, max_duration: int) -> None:
    """
    Validate individual subtitle durations.
    """
    for item in subs:
        if item.duration.ordinal > max_duration:
            raise SubtitleValidationError(
                f"Subtitle duration too long: {item.duration.ordinal}ms "
                f"(max: {max_duration}ms) at {item.start} --> {item.end}"
            )


def _validate_time_boundaries(subs: SubRipFile, duration: int, config: ValidateConfig) -> None:
    """
    Validate start and end time boundaries.
    """
    begin_gap = abs(subs[0].start.ordinal)
    validate_threshold(
        begin_gap,
        config.begin_gap_threshold,
        "Initial gap too large: {value}ms (max: {threshold}ms)"
    )

    end_gap = abs(subs[-1].end.ordinal - duration)
    validate_threshold(
        end_gap,
        config.end_gap_threshold,
        "Final gap too large: {value}ms (max: {threshold}ms)"
    )


def _validate_time_ordering(subs: SubRipFile) -> None:
    """
    Validate subtitle timing order.
    """
    for i, item in enumerate(subs, 1):
        if item.start > item.end:
            raise SubtitleValidationError(
                f"Invalid timing in subtitle #{i}: " f"start ({item.start}) after end ({item.end})"
            )


def _validate_gaps(subs: SubRipFile, max_gap: int) -> None:
    """
    Validate gaps between consecutive subtitles.
    """
    for i in range(len(subs) - 1):
        gap = subs[i + 1].start.ordinal - subs[i].end.ordinal
        validate_threshold(
            gap,
            max_gap,
            f"Gap too large between subtitles #{i + 1} and #{i + 2}: {{value}}ms (max: {{threshold}}ms)"
        )
