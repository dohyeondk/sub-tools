"""Command-line wrapper around the published ``subtitle-edit-rate`` metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .transcription import EVALUATION_METHODOLOGY, authoritative_metrics


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
        description="Compare generated SRT files with the published SubER metrics.",
    )
    parser.add_argument("--reference", required=True, help="Human reference SRT file.")
    parser.add_argument(
        "--hypothesis",
        action="append",
        required=True,
        metavar="NAME=PATH",
        help="Generated SRT to score. Repeat to compare variants; a bare path uses its stem as the name.",
    )
    parser.add_argument("--language", default="en", help="BCP-47 source language tag (default: en).")
    parser.add_argument("--output", type=Path, help="Write the machine-readable JSON report here.")
    parser.add_argument("--markdown", type=Path, help="Write a human-readable Markdown report here.")
    return parser


def _markdown(report: dict) -> str:
    lines = [
        "# Transcription evaluation",
        "",
        f"Reference: `{report['reference']}` · `{report['language']}`",
        "",
        "All scores below are calculated by the pinned [`subtitle-edit-rate==0.4.0`](https://pypi.org/project/subtitle-edit-rate/) package. SubER is timing- and segmentation-aware; AS-* metrics use automatic Levenshtein segmentation alignment, and t-* metrics use package timing alignment. Lower is better for SubER, AS-WER, AS-CER, AS-TER, t-WER, t-CER, and t-TER; higher is better for AS-BLEU, AS-chrF, t-BLEU, and t-chrF.",
        "",
        "| variant | SubER ↓ (%) | AS-WER ↓ (%) | AS-CER ↓ (%) | AS-BLEU ↑ (0–100) | AS-TER ↓ (%) | AS-chrF ↑ (0–100) | t-WER ↓ (%) | t-CER ↓ (%) | t-BLEU ↑ (0–100) | t-TER ↓ (%) | t-chrF ↑ (0–100) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in report["variants"]:
        metrics = variant["metrics"]
        lines.append(
            "| {name} | {suber:.3f}% | {as_wer:.3f}% | {as_cer:.3f}% | {as_bleu:.3f} | {as_ter:.3f}% | {as_chrf:.3f} | {t_wer:.3f}% | {t_cer:.3f}% | {t_bleu:.3f} | {t_ter:.3f}% | {t_chrf:.3f} |".format(
                name=variant["name"],
                suber=metrics["suber"],
                as_wer=metrics["as_wer"],
                as_cer=metrics["as_cer"],
                as_bleu=metrics["as_bleu"],
                as_ter=metrics["as_ter"],
                as_chrf=metrics["as_chrf"],
                t_wer=metrics["t_wer"],
                t_cer=metrics["t_cer"],
                t_bleu=metrics["t_bleu"],
                t_ter=metrics["t_ter"],
                t_chrf=metrics["t_chrf"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    reference_path = Path(args.reference)

    try:
        variants = []
        for raw_hypothesis in args.hypothesis:
            name, path = _hypothesis(raw_hypothesis)
            variants.append(
                {
                    "name": name,
                    "hypothesis": str(path),
                    "metrics": authoritative_metrics(reference_path, path, args.language),
                }
            )
        report = {
            "reference": str(reference_path),
            "language": args.language,
            "methodology": EVALUATION_METHODOLOGY,
            "variants": variants,
        }
    except Exception as error:
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
