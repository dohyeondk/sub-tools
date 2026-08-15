"""Command-line entry point for comparing subtitle tracks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .transcription import (
    EVALUATION_METHODOLOGY,
    authoritative_metrics,
    audio_duration_seconds,
    evaluate_transcription,
    load_srt,
)


def _hypothesis(value: str) -> tuple[str, Path]:
    if "=" in value:
        name, raw_path = value.split("=", 1)
        if name.strip() and raw_path.strip():
            return name.strip(), Path(raw_path.strip())
    path = Path(value)
    return path.stem, path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sub-tools-eval",
        description="Compare generated SRT files against a reference transcript.",
    )
    parser.add_argument("--reference", required=True, help="Human reference SRT file.")
    parser.add_argument(
        "--hypothesis",
        action="append",
        required=True,
        metavar="NAME=PATH",
        help="Generated SRT to score. Repeat to compare variants; a bare path uses its stem as the name.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="Audio duration in seconds. If omitted, --audio-file is probed with ffprobe.",
    )
    parser.add_argument("--audio-file", help="Audio file used to infer duration when --duration is omitted.")
    parser.add_argument("--language", default="en", help="BCP-47 source language tag (default: en).")
    parser.add_argument("--output", type=Path, help="Write the machine-readable JSON report here.")
    parser.add_argument("--markdown", type=Path, help="Write a human-readable Markdown report here.")
    return parser


def _milliseconds(value: float | None) -> str:
    return "—" if value is None else f"{value * 1000:.0f} ms"


def _percent(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value * 100:.{digits}f}%"


def _decimal(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _markdown(report: dict) -> str:
    lines = [
        "# Transcription evaluation",
        "",
        f"Reference: `{report['reference']}` · {report['duration_seconds']:.3f}s · `{report['language']}`",
        "",
        "Primary metric: [SubER](https://aclanthology.org/2022.iwslt-1.1/) via [`subtitle-edit-rate==0.4.0`](https://pypi.org/project/subtitle-edit-rate/) (lower is better); AS-WER and AS-CER are automatic-segmentation lexical error rates following the [NIST SCTK/SCLITE](https://github.com/usnistgov/SCTK/blob/master/doc/sclite.htm) edit-rate convention. The reference and hypotheses must use the same audio timeline. Coverage, gaps, anchor timing, readability, repetition, and gates are product diagnostics, not benchmark scores.",
        "",
        "Timing is median absolute anchor error / p90 absolute anchor error. Drift is the timing slope in seconds per minute.",
        "",
        "| variant | SubER ↓ (%) | AS-WER ↓ (%) | AS-CER ↓ (%) | anchor p50 / p90 | drift | coverage | segments | gates |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for variant in report["variants"]:
        authoritative = variant["authoritative"]
        timing = variant["timing"]
        intrinsic = variant["intrinsic"]
        coverage = intrinsic["coverage"]
        drift = timing["slope_seconds_per_minute"]
        gate_text = "; ".join(variant["gates"]) if variant["gates"] else "pass"
        lines.append(
            "| {name} | {suber} | {as_wer} | {as_cer} | {p50} / {p90} | {drift:+.3f} s/min | {coverage} | {segments} | {gates} |".format(
                name=variant["name"],
                suber=_decimal(authoritative["suber"], 3) + "%",
                as_wer=_decimal(authoritative["as_wer"], 3) + "%",
                as_cer=_decimal(authoritative["as_cer"], 3) + "%",
                p50=_milliseconds(timing["median_abs"]),
                p90=_milliseconds(timing["p90_abs"]),
                drift=drift or 0.0,
                coverage=_percent(coverage["coverage_ratio"]),
                segments=intrinsic["segments"],
                gates=gate_text,
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if args.duration is None and not args.audio_file:
        parser.error("one of --duration or --audio-file is required")

    try:
        duration = args.duration if args.duration is not None else audio_duration_seconds(args.audio_file)
        reference_path = Path(args.reference)
        reference = load_srt(reference_path)
        variants = []
        for raw_hypothesis in args.hypothesis:
            name, path = _hypothesis(raw_hypothesis)
            result = evaluate_transcription(reference, load_srt(path), duration, args.language)
            variants.append(
                {
                    "name": name,
                    "hypothesis": str(path),
                    "authoritative": authoritative_metrics(reference_path, path, args.language),
                    **result,
                }
            )
        report = {
            "reference": str(reference_path),
            "duration_seconds": duration,
            "language": args.language,
            "methodology": EVALUATION_METHODOLOGY,
            "variants": variants,
        }
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))

    rendered_json = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered_json, encoding="utf-8")
    else:
        sys.stdout.write(rendered_json)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
