"""
Repair malformed SRT output from a language model.

Every rule here corresponds to a failure observed in real Gemini output, not a
hypothetical one. Models reliably get the words right and the container wrong:
they drop the hours field partway through a long recording, split a timestamp
across two lines, wrap the file in a code fence, or emit a stray cue whose text
is the timestamp of the cue that should have followed it.

Repairs are structural only. Subtitle text is never rewritten, so a repaired
file says exactly what the model said.
"""

import json
import re

# ``` or ```srt, opening or closing.
FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*$", re.M)

# A cue line, tolerating the separators models actually produce.
CUE = re.compile(r"^(?P<start>[\d:,.]+)\s*-->\s*(?P<end>[\d:,.]+)\s*$")

# HH:MM:SS,mmm or MM:SS,mmm, with ':' '.' or ',' before the milliseconds.
FULL_STAMP = re.compile(r"^(\d{1,3})[:,.](\d{1,2})[:,.](\d{1,2})[:,.](\d{1,3})$")
SHORT_STAMP = re.compile(r"^(\d{1,2})[:,.](\d{1,2})[:,.](\d{1,3})$")

# A timestamp whose end time landed on the following line.
DANGLING = re.compile(r"^[\d:,.]+\s*-->\s*$")
BARE = re.compile(r"^[\d:,.]+$")

MIN_CUE_SECONDS = 0.05


def repair_subtitles(
    content: str,
    duration: float | None = None,
    reference: str | None = None,
) -> tuple[str, list[str]]:
    """
    Return repaired SRT content and a note for each repair that was applied.

    An empty note list means the model's output was already well formed.
    """
    notes: list[str] = []

    text = content.replace("﻿", "").replace("\r\n", "\n")
    without_fences = FENCE.sub("", text)
    if without_fences != text:
        notes.append("removed Markdown code fences")
    text = without_fences.strip()

    text, unwrapped = _unwrap_json_envelope(text)
    if unwrapped:
        notes.append("unwrapped SRT from a JSON envelope")
        text = text.replace("\r\n", "\n").strip()

    lines, rejoined = _rejoin_split_timestamps(text.split("\n"))
    if rejoined:
        notes.append(f"rejoined {rejoined} timestamp(s) split across two lines")

    lines, normalized = _normalize_timestamps(lines)
    if normalized:
        notes.append(f"normalized {normalized} timestamp(s) to HH:MM:SS,mmm")

    lines, separated = _separate_cues(lines)
    if separated:
        notes.append(f"inserted {separated} missing blank line(s) between cues")

    cues, demoted = _parse_cues(lines)
    if demoted:
        notes.append(f"recovered {demoted} timestamp(s) demoted into subtitle text")

    # Discard an exact zero-length junk cue. Leave out-of-range cues untouched:
    # inventing a timestamp can silently move real words or drop the tail of a
    # transcription. Strict validation will reject them and make the model try
    # again.
    kept = [cue for cue in cues if abs(cue["end"] - cue["start"]) > MIN_CUE_SECONDS]
    if len(kept) != len(cues):
        notes.append(f"dropped {len(cues) - len(kept)} zero-length cue(s)")
    cues = kept

    cues, clamped = _clamp_backwards_ends(cues, duration)
    if clamped:
        notes.append(f"clamped {clamped} cue(s) that ended before they started")

    if reference is not None:
        cues, restored = _restore_from_reference(cues, reference)
        if restored:
            notes.append(f"restored {restored} timestamp(s) from the source subtitles")

    ordered = sorted(cues, key=lambda cue: cue["start"])
    if ordered != cues:
        notes.append("reordered cues by start time")

    return _render(ordered), notes


def _unwrap_json_envelope(text: str) -> tuple[str, bool]:
    """
    Extract the SRT when a model answered with JSON like {"result": "1\\n00:00..."}.

    Only a lone string field holding the subtitles is unwrapped; anything more
    ambiguous is left for validation to reject.
    """
    candidate = text.strip()
    if not candidate.startswith("{") or "-->" not in candidate:
        return text, False
    try:
        data = json.loads(candidate)
    except ValueError:
        return text, False
    if isinstance(data, dict):
        subtitle_fields = [
            value for value in data.values() if isinstance(value, str) and "-->" in value
        ]
        if len(subtitle_fields) == 1:
            return subtitle_fields[0], True
    return text, False


def _clamp_backwards_ends(cues: list[dict], duration: float | None) -> tuple[list[dict], int]:
    """
    Give a cue whose end precedes its start the one end that cannot be wrong:
    the moment the next cue begins.

    The start is trusted because the neighbouring cues confirm it; the end is
    the corrupt half. Clamping changes how long the words stay on screen, never
    the words themselves. These cues used to be left for a retry, but a model
    that writes one backwards timestamp in a long recording writes another on
    the next attempt, so retrying never converged.
    """
    fixed = 0
    for index, cue in enumerate(cues):
        if cue["end"] > cue["start"]:
            continue
        if index + 1 < len(cues) and cues[index + 1]["start"] > cue["start"]:
            cue["end"] = cues[index + 1]["start"]
        elif duration is not None and duration > cue["start"]:
            cue["end"] = duration
        else:
            continue
        fixed += 1
    return cues, fixed


def _rejoin_split_timestamps(lines: list[str]) -> tuple[list[str], int]:
    """
    Join a cue line whose end time was emitted on the following line.
    """
    joined: list[str] = []
    count = 0
    index = 0
    while index < len(lines):
        current = lines[index].strip()
        following = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if DANGLING.match(current) and BARE.match(following):
            joined.append(f"{current} {following}")
            count += 1
            index += 2
            continue
        joined.append(lines[index])
        index += 1
    return joined, count


def _normalize_timestamps(lines: list[str]) -> tuple[list[str], int]:
    """
    Rewrite each cue line to HH:MM:SS,mmm, supplying an absent hours field.
    """
    result: list[str] = []
    count = 0
    for line in lines:
        match = CUE.match(line.strip())
        if not match:
            result.append(line)
            continue
        start = _seconds(match["start"])
        end = _seconds(match["end"])
        if start is None or end is None:
            result.append(line)
            continue
        rendered = f"{_stamp(start)} --> {_stamp(end)}"
        if rendered != line.strip():
            count += 1
        result.append(rendered)
    return result, count


def _separate_cues(lines: list[str]) -> tuple[list[str], int]:
    """
    Ensure a blank line precedes each cue index, which some models omit.
    """
    result: list[str] = []
    count = 0
    for index, line in enumerate(lines):
        starts_cue = (
            line.strip().isdigit()
            and index + 1 < len(lines)
            and "-->" in lines[index + 1]
        )
        if starts_cue and result and result[-1].strip():
            result.append("")
            count += 1
        result.append(line)
    return result, count


def _parse_cues(lines: list[str]) -> tuple[list[dict], int]:
    """
    Split into cues, recovering timestamps that were demoted into cue text.

    A model that emits a spurious cue immediately before a real one leaves the
    real timestamp as the first line of text. That timestamp is the correct one.
    """
    cues: list[dict] = []
    demoted = 0
    for block in "\n".join(lines).split("\n\n"):
        rows = [row for row in block.split("\n") if row.strip()]
        position = next((i for i, row in enumerate(rows) if "-->" in row), None)
        if position is None:
            continue

        match = CUE.match(rows[position].strip())
        body = rows[position + 1 :]
        if body and CUE.match(body[0].strip()):
            match = CUE.match(body[0].strip())
            body = body[1:]
            demoted += 1

        text = "\n".join(body).strip()
        if not match or not text:
            continue
        start, end = _seconds(match["start"]), _seconds(match["end"])
        if start is None or end is None:
            continue
        cues.append({"start": start, "end": end, "text": text})
    return cues, demoted


MATCH_TOLERANCE_SECONDS = 1.0


def _restore_from_reference(cues: list[dict], reference: str) -> tuple[list[dict], int]:
    """
    Put the source timings back when translating.

    Translation must not move timestamps, so any drift is the model's error and
    the source wins. Models also drop the occasional cue from a long file, which
    would make a strict cue-for-cue mapping fail on every retry and never
    converge. When the counts disagree, cues are matched on their start times
    instead; almost all of them come back unchanged, so the alignment is
    unambiguous and the few that drifted are still corrected.
    """
    source, _ = _parse_cues(reference.replace("\r\n", "\n").split("\n"))
    if not source:
        return cues, 0

    if len(source) == len(cues):
        restored = 0
        for original, translated in zip(source, cues):
            if (translated["start"], translated["end"]) != (original["start"], original["end"]):
                translated["start"] = original["start"]
                translated["end"] = original["end"]
                restored += 1
        return cues, restored

    restored = 0
    position = 0
    for translated in cues:
        best = None
        scan = position
        while scan < len(source):
            distance = abs(source[scan]["start"] - translated["start"])
            if best is None or distance < best[0]:
                best = (distance, scan)
            if source[scan]["start"] > translated["start"] + MATCH_TOLERANCE_SECONDS:
                break
            scan += 1

        if best and best[0] <= MATCH_TOLERANCE_SECONDS:
            original = source[best[1]]
            if (translated["start"], translated["end"]) != (original["start"], original["end"]):
                translated["start"] = original["start"]
                translated["end"] = original["end"]
                restored += 1
            position = best[1] + 1
    return cues, restored


def _seconds(stamp: str) -> float | None:
    """
    Convert a timestamp to seconds, assuming zero hours when the field is absent.
    """
    text = stamp.strip()
    match = FULL_STAMP.match(text)
    if match:
        hours, minutes, seconds, milliseconds = (int(g) for g in match.groups())
    else:
        match = SHORT_STAMP.match(text)
        if not match:
            return None
        hours = 0
        minutes, seconds, milliseconds = (int(g) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def _stamp(seconds: float) -> str:
    """
    Render seconds as an SRT timestamp.
    """
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    whole, fraction = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d},{fraction:03d}"


def _render(cues: list[dict]) -> str:
    """
    Serialize cues back to SRT, renumbered from one.
    """
    blocks = [
        f"{index}\n{_stamp(cue['start'])} --> {_stamp(cue['end'])}\n{cue['text']}\n"
        for index, cue in enumerate(cues, start=1)
    ]
    return "\n".join(blocks)
