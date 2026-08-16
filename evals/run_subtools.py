"""Run the sub-tools pipeline's Gemini proofreading stage over the shared WhisperX transcript.

Every "with sub-tools" variant reuses the same WhisperX output, so the only thing
that changes between them is the Gemini model passed to ``--model``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from paths import audio_path, load_manifest

ROOT = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--variant", required=True, help="Output directory name under evals/output.")
    parser.add_argument("--retry", type=int, default=8)
    args = parser.parse_args()

    manifest = load_manifest()
    destination = ROOT / "output" / args.variant
    destination.mkdir(parents=True, exist_ok=True)

    for sample in manifest:
        final = destination / f"{sample['name']}.srt"
        if final.exists():
            print(f"skip {final}")
            continue

        transcript = ROOT / "output" / "whisperx" / f"{sample['name']}.srt"
        if not transcript.exists():
            raise SystemExit(f"missing WhisperX transcript: {transcript}")

        workdir = destination / sample["name"]
        workdir.mkdir(exist_ok=True)
        shutil.copy(transcript, workdir / "transcript.srt")

        started = time.time()
        command = [
            "sub-tools",
            "--tasks", "translate",
            "--audio-file", str(audio_path(sample).resolve()),
            "--output", str(workdir.resolve()),
            "--languages", "en",
            "--model", args.model,
        ]
        produced = workdir / "en.srt"
        # sub-tools only retries ResourceExhausted, so a 503 exits the process;
        # retry the whole invocation here instead of changing pipeline behaviour.
        for attempt in range(args.retry):
            subprocess.run(command, check=False)
            if produced.exists():
                break
            if attempt == args.retry - 1:
                raise SystemExit(f"proofreading produced no output for {sample['name']}")
            wait = min(90, 5 * 2**attempt)
            print(f"  retry {attempt + 1}/{args.retry} after {wait}s", flush=True)
            time.sleep(wait)
        shutil.copy(produced, final)
        print(f"{sample['name']}: {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
