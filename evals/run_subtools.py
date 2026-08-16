"""Run the sub-tools transcription pipeline with one selected Gemini model."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from paths import audio_path, load_manifest

ROOT = Path(__file__).parent
VARIANT = "sub-tools"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Gemini model passed to sub-tools.")
    parser.add_argument(
        "--retry",
        type=int,
        default=3,
        help="Retry count passed to sub-tools (default: %(default)s).",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    destination = ROOT / "output" / VARIANT
    destination.mkdir(parents=True, exist_ok=True)

    for sample in manifest:
        target = destination / f"{sample['name']}.srt"
        if target.exists():
            print(f"skip {target}")
            continue

        with tempfile.TemporaryDirectory(prefix=f"sub-tools-eval-{sample['name']}-") as workdir:
            command = [
                "sub-tools",
                "--tasks",
                "transcribe",
                "--audio-file",
                str(audio_path(sample).resolve()),
                "--languages",
                "en",
                "--output",
                workdir,
                "--model",
                args.model,
                "--retry",
                str(args.retry),
            ]
            subprocess.run(command, check=True)

            produced = Path(workdir) / "en.srt"
            if not produced.exists():
                raise SystemExit(f"sub-tools produced no subtitles for {sample['name']}")
            shutil.copyfile(produced, target)

        print(f"{sample['name']}: {target}", flush=True)


if __name__ == "__main__":
    main()
