"""Score the sub-tools output with the shipped sub-tools-eval command."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
from pathlib import Path

from paths import load_manifest, model_variant, reference_path

ROOT = Path(__file__).parent
PIPELINE = "sub-tools"

METRICS = [
    ("suber", "SubER ↓"),
    ("as_wer", "AS-WER ↓"),
    ("as_cer", "AS-CER ↓"),
    ("as_bleu", "AS-BLEU ↑"),
    ("as_ter", "AS-TER ↓"),
    ("as_chrf", "AS-chrF ↑"),
    ("t_wer", "t-WER ↓"),
    ("t_cer", "t-CER ↓"),
    ("t_bleu", "t-BLEU ↑"),
    ("t_ter", "t-TER ↓"),
    ("t_chrf", "t-chrF ↑"),
]


def score_sample(sample: dict, model: str, variant: str) -> dict:
    hypothesis = ROOT / "scored" / variant / f"{sample['name']}.srt"
    if not hypothesis.exists():
        raise SystemExit(f"missing normalized subtitles: {hypothesis}")

    report_path = ROOT / "reports" / variant / f"{sample['name']}.json"
    command = [
        "sub-tools-eval",
        "--reference",
        str(reference_path(sample)),
        "--language",
        "en",
        "--hypothesis",
        f"{model}={hypothesis}",
        "--output",
        str(report_path),
    ]
    subprocess.run(command, check=True)
    report = json.loads(report_path.read_text())
    return report["variants"][0]["metrics"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Score one sub-tools model run.")
    parser.add_argument("--model", required=True, help="Gemini model used to generate the subtitles.")
    args = parser.parse_args()

    variant = model_variant(args.model)
    manifest = load_manifest()

    per_sample = {}
    for sample in manifest:
        per_sample[sample["name"]] = score_sample(sample, args.model, variant)
        print(f"scored {sample['name']}", flush=True)

    aggregate = {
        "samples": len(per_sample),
        **{
            key: statistics.fmean(metrics[key] for metrics in per_sample.values())
            for key, _ in METRICS
        },
    }
    result = {
        "corpus": [
            {
                key: sample[key]
                for key in (
                    "name",
                    "commons_file",
                    "source_url",
                    "duration_seconds",
                    "cues",
                )
            }
            for sample in manifest
        ],
        "aggregation": "macro-average over samples",
        "pipeline": PIPELINE,
        "model": args.model,
        "variant": variant,
        "per_sample": per_sample,
        "aggregate": aggregate,
    }
    result_path = ROOT / "results" / f"{variant}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )

    header = "| model | " + " | ".join(label for _, label in METRICS) + " |"
    divider = "|---" + "|---:" * len(METRICS) + "|"
    cells = " | ".join(f"{aggregate[key]:.2f}" for key, _ in METRICS)
    table = "\n".join([header, divider, f"| {args.model} | {cells} |"])
    (ROOT / "results" / f"{variant}.md").write_text(table + "\n", encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
