"""Generate SRT files with Gemini alone — the "without sub-tools" baseline.

The model receives only the audio and is asked for a subtitle file, so it does
both transcription and segmentation. Generation settings mirror
``sub_tools.intelligence.gemini`` (thinking level HIGH, Google Search enabled)
so the comparison isolates the pipeline rather than the sampling knobs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types

from paths import audio_path, load_manifest

ROOT = Path(__file__).parent

SYSTEM_INSTRUCTION = """
You are a professional transcriptionist.
You will receive an English audio file.

Your task is to:
1. Listen to the audio carefully
2. Transcribe every spoken word accurately
3. Split the transcript into subtitle cues that follow the speech
4. Give every cue start and end timestamps that match when the words are spoken

CRITICAL REQUIREMENTS:
1. Output ONLY the SRT file. No code blocks, no explanations.
2. Preserve the SRT format perfectly (number, timestamp, text, blank line)
3. Timestamps use the HH:MM:SS,mmm --> HH:MM:SS,mmm format
4. Cover the entire audio from beginning to end
5. Use correct punctuation and capitalization
6. The output must be valid SRT format

Return the SRT file.
"""


def transcribe(client: genai.Client, model: str, audio_path: Path, retry: int) -> str:
    uploaded = client.files.upload(file=str(audio_path))
    for attempt in range(retry):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[uploaded, types.Part.from_text(text="Transcribe this audio into an SRT subtitle file.")],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_level=types.ThinkingLevel.HIGH,
                    ),
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            )
            # A response can come back as a stray tool-call rendering with no cues
            # at all; that is a dead response, not a formatting quirk, so retry it.
            if response.text and "-->" in response.text:
                return response.text
            preview = (response.text or "")[:80].replace("\n", " ")
            print(f"  no cues in response, retrying: {preview!r}", flush=True)
        except Exception as error:  # noqa: BLE001 - retried below, reported on give-up
            if attempt == retry - 1:
                raise
            # 503 "high demand" needs a longer wait than the pipeline's 1/2/4s backoff.
            wait = min(90, 5 * 2**attempt)
            print(f"  retry {attempt + 1}/{retry} after {wait}s: {error}", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"empty response for {audio_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--variant", required=True, help="Output directory name under evals/output.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--retry", type=int, default=8)
    args = parser.parse_args()

    manifest = load_manifest()
    destination = ROOT / "output" / args.variant
    destination.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=args.api_key)

    for sample in manifest:
        target = destination / f"{sample['name']}.srt"
        if target.exists():
            print(f"skip {target}")
            continue
        started = time.time()
        text = transcribe(client, args.model, audio_path(sample), args.retry)
        target.write_text(text, encoding="utf-8")
        print(f"{sample['name']}: {len(text)} chars in {time.time() - started:.0f}s", flush=True)


if __name__ == "__main__":
    sys.exit(main())
