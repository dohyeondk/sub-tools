import pysrt
from pysrt import SubRipFile

from ..config import Config


class SubtitleValidationError(Exception):
    """
    Custom exception for subtitle validation errors.
    """

    pass


def validate_subtitles(
    content: str,
    duration: int,
    config: Config = Config(),
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

    except SubtitleValidationError:
        raise


def _parse_subtitles(content: str) -> SubRipFile:
    """
    Parse SRT content into subtitle objects.
    """
    try:
        return pysrt.from_string(content)
    except Exception as e:
        raise SubtitleValidationError(f"Failed to parse subtitles: {str(e)}") from e


def _validate_subtitle_count(subs: SubRipFile, min_count: int) -> None:
    """
    Validate minimum number of subtitles.
    """
    if len(subs) < min_count:
        raise SubtitleValidationError(
            f"Not enough subtitles. Found {len(subs)}, minimum required: {min_count}"
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


def _validate_time_boundaries(subs: SubRipFile, duration: int, config: Config) -> None:
    """
    Validate start and end time boundaries.
    """
    begin_gap = abs(subs[0].start.ordinal)
    if begin_gap > config.begin_gap_threshold:
        raise SubtitleValidationError(
            f"Initial gap too large: {begin_gap}ms (max: {config.begin_gap_threshold}ms)"
        )

    end_gap = abs(subs[-1].end.ordinal - duration)
    if end_gap > config.end_gap_threshold:
        raise SubtitleValidationError(
            f"Final gap too large: {end_gap}ms (max: {config.end_gap_threshold}ms)"
        )


def _validate_time_ordering(subs: SubRipFile) -> None:
    """
    Validate subtitle timing order.
    """
    for i, item in enumerate(subs, 1):
        if item.start > item.end:
            raise SubtitleValidationError(
                f"Invalid timing in subtitle #{i}: "
                f"start ({item.start}) after end ({item.end})"
            )


def _validate_gaps(subs: SubRipFile, max_gap: int) -> None:
    """
    Validate gaps between consecutive subtitles.
    """
    for i in range(len(subs) - 1):
        gap = subs[i + 1].start.ordinal - subs[i].end.ordinal
        if gap > max_gap:
            raise SubtitleValidationError(
                f"Gap too large between subtitles #{i + 1} and #{i + 2}: "
                f"{gap}ms (max: {max_gap}ms)"
            )
