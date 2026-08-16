"""Run the sub-tools transcription pipeline with one selected Gemini model."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from paths import audio_path, load_manifest, model_variant

ROOT = Path(__file__).parent


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
    variant = model_variant(args.model)
    destination = ROOT / "output" / variant
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
                # The corpus clips open with music and end with silence; the
                # human references leave those uncaptioned too, so a strict
                # coverage gate would reject correct transcriptions.
                "--begin-gap-threshold",
                "30000",
                "--end-gap-threshold",
                "30000",
            ]
            subprocess.run(command, check=True)

            produced = Path(workdir) / "en.srt"
            if not produced.exists():
                raise SystemExit(f"sub-tools produced no subtitles for {sample['name']}")
            shutil.copyfile(produced, target)

        print(f"{sample['name']}: {target}", flush=True)


if __name__ == "__main__":
    main()
