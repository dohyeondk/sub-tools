"""
Check whether subtitle content is structurally sound enough to ship.

This module deliberately parses SRT itself rather than leaning on a subtitle
library. Lenient parsers are the problem, not the solution: given a file whose
timestamps had lost their hours field, pysrt reported 101 well-formed cues for a
recording that actually contained 337, discarding two thirds of the transcript
without raising anything. A checker built on that cannot be trusted to say a
file is good.

So every rule below is explicit, and each one corresponds to a defect seen in
real model output:

  - timestamps that dropped the hours field partway through a long recording
  - a millisecond separator written as ':' instead of ','
  - a timestamp split across two lines, leaving a dangling '-->'
  - a stray cue whose text is the timestamp of the cue that should have followed
  - cues that end before they start, or run backwards
  - subtitles that stop well before the audio does
  - a translation whose timings drifted from the subtitles it was made from

Errors mean the answer is unusable and should be requested again. Warnings are
stylistic: unusual, often correct, always kept.
"""

import re
from dataclasses import dataclass

from ..config import Config, config as default_config

# The only timestamp spelling that is actually valid.
STAMP = r"\d{2}:\d{2}:\d{2},\d{3}"
CUE_LINE = re.compile(rf"^(?P<start>{STAMP}) --> (?P<end>{STAMP})$")

# Anything a model might have meant as a timestamp, however badly spelled. Used
# to spot timestamps hiding where subtitle text belongs.
STAMP_LIKE = re.compile(r"^\s*[\d:,.]{6,}\s*(-->.*)?$")
ARROW = re.compile(r"-->")


class SubtitleValidationError(Exception):
    """
    Raised when subtitle content cannot be used.
    """

    pass


@dataclass
class Cue:
    """
    One subtitle, as it appeared in the file.
    """

    index: int
    start: float
    end: float
    text: str


def parse_strict(content: str) -> tuple[list[Cue], list[str]]:
    """
    Parse SRT with no tolerance, returning the cues and every violation found.

    A caller that gets a non-empty error list must not use the cues.
    """
    errors: list[str] = []
    cues: list[Cue] = []

    text = content.replace("\r\n", "\n").strip()
    if not text:
        return [], ["file is empty"]

    for position, block in enumerate(text.split("\n\n"), start=1):
        rows = [row for row in block.split("\n") if row.strip()]
        if not rows:
            continue

        if len(rows) < 3:
            errors.append(f"block {position} has {len(rows)} line(s), expected an index, a timestamp and text")
            continue

        if not rows[0].strip().isdigit():
            errors.append(f"block {position} does not begin with a cue number")
            continue

        match = CUE_LINE.match(rows[1].strip())
        if not match:
            errors.append(f"block {position} has a malformed timestamp: {rows[1].strip()!r}")
            continue

        body = rows[2:]
        stray = [row for row in body if ARROW.search(row) or STAMP_LIKE.match(row)]
        if stray:
            errors.append(f"block {position} has a timestamp where subtitle text belongs: {stray[0].strip()!r}")
            continue

        cues.append(
            Cue(
                index=int(rows[0].strip()),
                start=_seconds(match["start"]),
                end=_seconds(match["end"]),
                text="\n".join(body).strip(),
            )
        )

    if not cues and not errors:
        errors.append("no subtitles found")
    return cues, errors[:5]


def find_problems(
    content: str,
    duration: float | None = None,
    reference: str | None = None,
    config: Config = None,
) -> tuple[list[str], list[str]]:
    """
    Return (errors, warnings) for the given subtitle content.
    """
    config = config or default_config

    cues, errors = parse_strict(content)
    if errors:
        return errors, []

    if len(cues) < config.min_subtitles:
        return [f"found {len(cues)} subtitles, expected at least {config.min_subtitles}"], []

    errors += _timing_errors(cues)
    errors += _range_errors(cues, duration)
    errors += _coverage_errors(cues, duration, config)
    errors += _reference_errors(cues, reference, config)

    warnings = _warnings(cues, config) + _reference_warnings(cues, reference)
    return errors[:5], warnings


def validate_subtitles(
    content: str,
    duration: float | None = None,
    reference: str | None = None,
    config: Config = None,
) -> list[str]:
    """
    Raise SubtitleValidationError if the content is unusable, else return warnings.
    """
    errors, warnings = find_problems(content, duration, reference, config)
    if errors:
        raise SubtitleValidationError("; ".join(errors))
    return warnings


def _timing_errors(cues: list[Cue]) -> list[str]:
    """
    Cues must run forwards, and must not step backwards from one to the next.
    """
    errors = []
    for cue in cues:
        if cue.end <= cue.start:
            errors.append(f"subtitle #{cue.index} ends before it starts")
    for earlier, later in zip(cues, cues[1:]):
        if later.start < earlier.start:
            errors.append(f"subtitle #{later.index} starts before #{earlier.index}")
    return errors


def _range_errors(cues: list[Cue], duration: float | None) -> list[str]:
    """
    No cue may fall outside the recording.
    """
    if duration is None:
        return []
    beyond = [cue.index for cue in cues if cue.end > duration + 1]
    if beyond:
        return [f"{len(beyond)} subtitle(s) end after the audio does, first at #{beyond[0]}"]
    return []


def _coverage_errors(cues: list[Cue], duration: float | None, config: Config) -> list[str]:
    """
    Subtitles must span the recording rather than trailing off partway through.
    """
    if duration is None:
        return []

    errors = []
    if cues[0].start * 1000 > config.begin_gap_threshold:
        errors.append(
            f"subtitles start {cues[0].start:.0f}s in, "
            f"more than the {config.begin_gap_threshold / 1000:.0f}s allowed"
        )
    missing = duration - cues[-1].end
    if missing * 1000 > config.end_gap_threshold:
        errors.append(
            f"subtitles stop {missing:.0f}s before the audio ends, "
            f"more than the {config.end_gap_threshold / 1000:.0f}s allowed"
        )
    return errors


def _reference_errors(cues: list[Cue], reference: str | None, config: Config) -> list[str]:
    """
    A translation must keep the timings it was given and lose almost nothing.

    Dropping the odd cue from a long file is something models do routinely, and
    demanding an exact count makes every retry fail the same way without ever
    converging. Losing a meaningful share of the subtitles is different: that is
    a bad answer and worth asking again for.
    """
    if reference is None:
        return []

    source, errors = parse_strict(reference)
    if errors or not source:
        return []

    # The allowance scales with length and has no floor: losing one cue from
    # four hundred is routine, losing one from four is a broken answer.
    missing = len(source) - len(cues)
    allowed = int(len(source) * config.max_missing_ratio)
    if missing > allowed:
        return [
            f"translation lost {missing} of {len(source)} subtitles, "
            f"more than the {allowed} allowed"
        ]
    if len(cues) > len(source):
        return [f"translation has {len(cues) - len(source)} more subtitles than the source"]

    if len(source) == len(cues):
        drifted = [
            translated.index
            for original, translated in zip(source, cues)
            if abs(original.start - translated.start) > 0.001
            or abs(original.end - translated.end) > 0.001
        ]
        if drifted:
            return [
                f"{len(drifted)} subtitle(s) moved away from the source timings, "
                f"first at #{drifted[0]}"
            ]
    return []


def _reference_warnings(cues: list[Cue], reference: str | None) -> list[str]:
    """
    Say so when a translation came back short, even if it is within tolerance.
    """
    if reference is None:
        return []
    source, errors = parse_strict(reference)
    if errors or not source or len(cues) >= len(source):
        return []
    return [f"translation is missing {len(source) - len(cues)} of {len(source)} subtitles"]


def _warnings(cues: list[Cue], config: Config) -> list[str]:
    """
    Report unusual but publishable timing.
    """
    warnings = []
    long_cues = [c.index for c in cues if (c.end - c.start) * 1000 > config.max_valid_duration]
    if long_cues:
        warnings.append(
            f"{len(long_cues)} subtitle(s) run longer than "
            f"{config.max_valid_duration / 1000:.0f}s, first at #{long_cues[0]}"
        )

    gaps = [
        later.index
        for earlier, later in zip(cues, cues[1:])
        if (later.start - earlier.end) * 1000 > config.inter_item_gap_threshold
    ]
    if gaps:
        warnings.append(
            f"{len(gaps)} gap(s) longer than "
            f"{config.inter_item_gap_threshold / 1000:.0f}s, first before #{gaps[0]}"
        )
    return warnings


def _seconds(stamp: str) -> float:
    """
    Convert a canonical HH:MM:SS,mmm timestamp to seconds.
    """
    clock, milliseconds = stamp.split(",")
    hours, minutes, seconds = (int(part) for part in clock.split(":"))
    return hours * 3600 + minutes * 60 + seconds + int(milliseconds) / 1000
