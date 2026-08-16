"""Repair the selected sub-tools output before scoring it."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from paths import model_variant

ROOT = Path(__file__).parent

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
    parser = argparse.ArgumentParser(description="Normalize one sub-tools model run before scoring.")
    parser.add_argument("--model", required=True, help="Gemini model used to generate the subtitles.")
    args = parser.parse_args()

    variant = model_variant(args.model)
    source_dir = ROOT / "output" / variant
    destination = ROOT / "scored" / variant

    if not source_dir.is_dir():
        raise SystemExit(
            f"missing {source_dir}; run evals/run_subtools.py --model {args.model} first"
        )

    destination.mkdir(parents=True, exist_ok=True)
    sources = sorted(source_dir.glob("*.srt"))
    if not sources:
        raise SystemExit(
            f"no subtitles found in {source_dir}; "
            f"run evals/run_subtools.py --model {args.model} first"
        )

    repaired = []
    for source_file in sources:
        original = source_file.read_text(encoding="utf-8")
        fixed = normalize(original)
        (destination / source_file.name).write_text(fixed, encoding="utf-8")
        if fixed.strip() != original.replace("\r\n", "\n").strip():
            repaired.append(source_file.stem)

    report = {
        "pipeline": "sub-tools",
        "model": args.model,
        "variant": variant,
        "files": len(sources),
        "needed_repair": repaired,
    }
    report_path = ROOT / "normalization" / f"{variant}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{args.model}: repaired {len(repaired)}/{len(sources)}")


if __name__ == "__main__":
    main()
