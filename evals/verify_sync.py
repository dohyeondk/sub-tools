"""Check that each reference track is actually in sync with its audio.

Commons subtitle tracks are human-authored but occasionally authored against a
different cut of the media. A desynced reference charges every variant the same
large timing penalty and drowns out the differences the evaluation is measuring,
so it has to be caught before scoring rather than explained away afterwards.

The check is independent of any one system: if several independently produced
transcripts agree with each other on when speech starts and all disagree with
the reference by the same amount, the reference is the odd one out.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from suber.file_readers import read_input_file

from paths import load_manifest, reference_path

ROOT = Path(__file__).parent
TOLERANCE_SECONDS = 1.5


def main() -> None:
    manifest = load_manifest()
    variants = sorted(p.name for p in (ROOT / "scored").iterdir() if p.is_dir())

    failures = []
    for sample in manifest:
        name = sample["name"]
        reference = read_input_file(str(reference_path(sample)), "SRT")
        starts = {}
        for variant in variants:
            path = ROOT / "scored" / variant / f"{name}.srt"
            if path.exists():
                starts[variant] = read_input_file(str(path), "SRT")[0].start_time

        if len(starts) < 2:
            print(f"{name}: not enough transcripts to check")
            continue

        consensus = statistics.median(starts.values())
        offset = reference[0].start_time - consensus
        spread = max(starts.values()) - min(starts.values())
        status = "OK " if abs(offset) <= TOLERANCE_SECONDS else "DESYNC"
        print(
            f"{status} {name:22s} reference starts {reference[0].start_time:6.2f}s, "
            f"transcripts agree on {consensus:6.2f}s (spread {spread:.2f}s), offset {offset:+.2f}s"
        )
        if abs(offset) > TOLERANCE_SECONDS:
            failures.append(name)

    if failures:
        print(f"\ndesynced references: {', '.join(failures)}")
        sys.exit(1)
    print("\nall references in sync")


if __name__ == "__main__":
    main()
