"""Score the sub-tools output with the shipped sub-tools-eval command."""

from __future__ import annotations

import json
import statistics
import subprocess
from pathlib import Path

from paths import load_manifest, reference_path

ROOT = Path(__file__).parent
VARIANT = "sub-tools"
REPORT_DIR = ROOT / "reports"
SCORED = ROOT / "scored" / VARIANT

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


def score_sample(sample: dict) -> dict:
    hypothesis = SCORED / f"{sample['name']}.srt"
    if not hypothesis.exists():
        raise SystemExit(f"missing normalized subtitles: {hypothesis}")

    report_path = REPORT_DIR / f"{sample['name']}.json"
    command = [
        "sub-tools-eval",
        "--reference",
        str(reference_path(sample)),
        "--language",
        "en",
        "--hypothesis",
        f"{VARIANT}={hypothesis}",
        "--output",
        str(report_path),
    ]
    subprocess.run(command, check=True)
    report = json.loads(report_path.read_text())
    return report["variants"][0]["metrics"]


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    per_sample = {}
    for sample in manifest:
        per_sample[sample["name"]] = score_sample(sample)
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
        "variant": VARIANT,
        "per_sample": per_sample,
        "aggregate": aggregate,
    }
    (ROOT / "results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )

    header = "| variant | " + " | ".join(label for _, label in METRICS) + " |"
    divider = "|---" + "|---:" * len(METRICS) + "|"
    cells = " | ".join(f"{aggregate[key]:.2f}" for key, _ in METRICS)
    table = "\n".join([header, divider, f"| {VARIANT} | {cells} |"])
    (ROOT / "results.md").write_text(table + "\n", encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
