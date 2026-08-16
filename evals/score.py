"""Score every variant with the shipped ``sub-tools-eval`` command and aggregate.

``sub-tools-eval`` scores one reference at a time, so this runs it per sample and
macro-averages the per-sample metrics across the corpus (clips are within ~25%
of the same length, so each contributes roughly equally).
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys
from pathlib import Path

from paths import load_manifest, reference_path

ROOT = Path(__file__).parent
REPORT_DIR = ROOT / "reports"

# display name -> output directory
VARIANTS = {
    "whisperx": "whisperx",
    "gemini-3.7-flash (without sub-tools)": "gemini-3.7-flash-direct",
    "gemini-3.5-flash-lite (without sub-tools)": "gemini-3.5-flash-lite-direct",
    "gemini-3.7-flash (with sub-tools)": "gemini-3.7-flash-subtools",
    "gemini-3.5-flash-lite (with sub-tools)": "gemini-3.5-flash-lite-subtools",
}

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
    """Run sub-tools-eval once for this sample with every available variant."""

    command = [
        "sub-tools-eval",
        "--reference",
        str(reference_path(sample)),
        "--language",
        "en",
    ]
    present = []
    for name, directory in VARIANTS.items():
        path = ROOT / "scored" / directory / f"{sample['name']}.srt"
        if path.exists():
            command += ["--hypothesis", f"{name}={path}"]
            present.append(name)
    if not present:
        raise SystemExit(f"no hypotheses for {sample['name']}")

    report_path = REPORT_DIR / f"{sample['name']}.json"
    command += ["--output", str(report_path)]
    subprocess.run(command, check=True)
    return json.loads(report_path.read_text())


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    per_sample = {}
    for sample in manifest:
        report = score_sample(sample)
        per_sample[sample["name"]] = {v["name"]: v["metrics"] for v in report["variants"]}
        print(f"scored {sample['name']}", flush=True)

    aggregate = {}
    for name in VARIANTS:
        rows = [m[name] for m in per_sample.values() if name in m]
        if not rows:
            continue
        aggregate[name] = {
            "samples": len(rows),
            **{key: statistics.fmean(r[key] for r in rows) for key, _ in METRICS},
        }

    result = {
        "corpus": [
            {k: s[k] for k in ("name", "commons_file", "source_url", "duration_seconds", "cues")}
            for s in manifest
        ],
        "aggregation": "macro-average over samples",
        "per_sample": per_sample,
        "aggregate": aggregate,
    }
    (ROOT / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    header = "| variant | " + " | ".join(label for _, label in METRICS) + " |"
    divider = "|---" + "|---:" * len(METRICS) + "|"
    lines = [header, divider]
    for name, metrics in aggregate.items():
        cells = " | ".join(f"{metrics[key]:.2f}" for key, _ in METRICS)
        lines.append(f"| {name} | {cells} |")
    table = "\n".join(lines)
    (ROOT / "results.md").write_text(table + "\n", encoding="utf-8")
    print(table)


if __name__ == "__main__":
    sys.exit(main())
