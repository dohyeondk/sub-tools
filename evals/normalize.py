"""Repair the selected sub-tools output before scoring it."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
VARIANT = "sub-tools"
SOURCE = ROOT / "output" / VARIANT
DESTINATION = ROOT / "scored" / VARIANT

FENCE = re.compile(r"^\s*\x60\x60\x60[a-zA-Z]*\s*\n|\n\s*\x60\x60\x60\s*$")
CUE_LINE = re.compile(r"^(?P<start>[\d:,.]+)\s*-->\s*(?P<end>[\d:,.]+)(?P<rest>.*)$")
TIME_PARTS = re.compile(r"^(\d{1,3})[:,.](\d{1,2})[:,.](\d{1,2})[:,.](\d{1,3})$|^(\d{1,2})[:,.](\d{1,2})[:,.](\d{1,3})$")


def _timestamp(value: str) -> str | None:
    """Return HH:MM:SS,mmm for timestamp spellings models emit."""

    match = TIME_PARTS.match(value.strip())
    if not match:
        return None
    groups = match.groups()
    if groups[0] is not None:
        hours, minutes, seconds, milliseconds = groups[0:4]
    else:
        hours, (minutes, seconds, milliseconds) = "0", groups[4:7]
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"


def normalize(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\r\n", "\n")
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
    if not SOURCE.is_dir():
        raise SystemExit(f"missing {SOURCE}; run evals/run_subtools.py first")

    DESTINATION.mkdir(parents=True, exist_ok=True)
    sources = sorted(SOURCE.glob("*.srt"))
    if not sources:
        raise SystemExit(f"no subtitles found in {SOURCE}; run evals/run_subtools.py first")

    repaired = []
    for source in sources:
        original = source.read_text(encoding="utf-8")
        fixed = normalize(original)
        (DESTINATION / source.name).write_text(fixed, encoding="utf-8")
        if fixed.strip() != original.replace("\r\n", "\n").strip():
            repaired.append(source.stem)

    report = {
        "variant": VARIANT,
        "files": len(sources),
        "needed_repair": repaired,
    }
    (ROOT / "normalization.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{VARIANT}: repaired {len(repaired)}/{len(sources)}")


if __name__ == "__main__":
    main()
