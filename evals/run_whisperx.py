"""Run WhisperX transcription directly, for comparing versions or settings.

Mirrors `sub_tools.intelligence.whisperx.transcribe` exactly — same model, device,
compute type, batch size, and alignment step — but takes the output directory and
``chunk_size`` as arguments so a specific variable can be isolated. Run it with a
different interpreter to compare WhisperX versions:

    /path/to/other-venv/bin/python evals/run_whisperx.py --variant whisperx-3.8.6

`sub_tools.intelligence.whisperx` never passes ``chunk_size``, so the pipeline
takes the WhisperX default of 30; that is the value to use when reproducing the
shipped behaviour.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import warnings
from pathlib import Path

import whisperx

from paths import audio_path, load_manifest

warnings.filterwarnings("ignore")
ROOT = Path(__file__).parent


def _load_serializer():
    """Load the shipped serializer by path so the SRT formatting is identical.

    Imported directly rather than as ``sub_tools.subtitles.serializer`` because
    the package ``__init__`` pulls in the Gemini client, which a WhisperX-only
    environment does not have.
    """

    path = ROOT.parent / "src" / "sub_tools" / "subtitles" / "serializer.py"
    spec = importlib.util.spec_from_file_location("_serializer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.serialize_subtitles


serialize_subtitles = _load_serializer()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True, help="Output directory name under evals/output.")
    parser.add_argument("--chunk-size", type=int, default=30, help="WhisperX default is 30.")
    parser.add_argument("--model", default="large-v2")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    print(f"whisperx {importlib.metadata.version('whisperx')}, chunk_size={args.chunk_size}", flush=True)

    manifest = load_manifest()
    destination = ROOT / "output" / args.variant
    destination.mkdir(parents=True, exist_ok=True)

    model = whisperx.load_model(args.model, device="cpu", compute_type="int8", language="en")
    align_model, metadata = whisperx.load_align_model(language_code="en", device="cpu")

    for sample in manifest:
        target = destination / f"{sample['name']}.srt"
        if target.exists():
            print(f"skip {sample['name']}", flush=True)
            continue
        audio = whisperx.load_audio(str(audio_path(sample)))
        result = model.transcribe(audio, batch_size=args.batch_size, chunk_size=args.chunk_size)
        result = whisperx.align(
            result["segments"], align_model, metadata, audio, "cpu",
            return_char_alignments=False,
        )
        serialize_subtitles(result["segments"], str(target))
        print(f"{sample['name']}: {len(result['segments'])} cues", flush=True)


if __name__ == "__main__":
    main()
