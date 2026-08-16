"""Repair SRT syntax before scoring, identically for every variant.

Models asked for subtitles do not always emit syntactically valid SRT — a common
failure is dropping the hours field (``00:06,123`` instead of ``00:00:06,123``)
or wrapping the file in a Markdown code fence. Scoring would simply fail on those
files, so this pass applies a small set of syntax-only repairs to every variant
and records which files needed them. It never touches subtitle text or cue order,
so a well-formed file passes through byte-identical.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = ROOT / "output"
DESTINATION = ROOT / "scored"

FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*\n|\n\s*```\s*$")
CUE_LINE = re.compile(r"^(?P<start>[\d:,.]+)\s*-->\s*(?P<end>[\d:,.]+)(?P<rest>.*)$")
TIME_PARTS = re.compile(r"^(\d{1,3})[:,.](\d{1,2})[:,.](\d{1,2})[:,.](\d{1,3})$|^(\d{1,2})[:,.](\d{1,2})[:,.](\d{1,3})$")


def _timestamp(value: str) -> str | None:
    """Return ``HH:MM:SS,mmm`` for the timestamp spellings models actually emit."""

    match = TIME_PARTS.match(value.strip())
    if not match:
        return None
    groups = match.groups()
    if groups[0] is not None:
        hours, minutes, seconds, milliseconds = groups[0:4]
    else:
        # No hours field: the model wrote MM:SS,mmm.
        hours, (minutes, seconds, milliseconds) = "0", groups[4:7]
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"


def normalize(text: str) -> str:
    text = text.replace("﻿", "").replace("\r\n", "\n")
    text = FENCE.sub("", text).strip() + "\n"

    lines = []
    for line in text.split("\n"):
        match = CUE_LINE.match(line.strip())
        if match:
            start = _timestamp(match.group("start"))
            end = _timestamp(match.group("end"))
            if start and end:
                lines.append(f"{start} --> {end}{match.group('rest')}")
                continue
        lines.append(line)

    # Some outputs run cues together with no blank line between blocks, which
    # collapses the whole file into one cue. A digit-only line directly followed
    # by a timestamp line always starts a new cue, so separate them.
    spaced = []
    for index, line in enumerate(lines):
        starts_cue = (
            line.strip().isdigit()
            and index + 1 < len(lines)
            and "-->" in lines[index + 1]
        )
        if starts_cue and spaced and spaced[-1].strip():
            spaced.append("")
        spaced.append(line)
    return "\n".join(spaced)


def main() -> None:
    report = {}
    for variant_dir in sorted(p for p in SOURCE.iterdir() if p.is_dir()):
        target_dir = DESTINATION / variant_dir.name
        target_dir.mkdir(parents=True, exist_ok=True)
        repaired = []
        for source in sorted(variant_dir.glob("*.srt")):
            original = source.read_text(encoding="utf-8")
            fixed = normalize(original)
            (target_dir / source.name).write_text(fixed, encoding="utf-8")
            if fixed.strip() != original.replace("\r\n", "\n").strip():
                repaired.append(source.stem)
        report[variant_dir.name] = {
            "files": len(list(variant_dir.glob("*.srt"))),
            "needed_repair": repaired,
        }
        print(f"{variant_dir.name}: repaired {len(repaired)}/{report[variant_dir.name]['files']}")

    (ROOT / "normalization.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
