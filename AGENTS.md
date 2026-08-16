# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Overview

sub-tools is a Python toolkit for converting video/audio content into accurate, multilingual subtitles using Google's Gemini API for both transcription and translation. Model output is repaired and strictly validated before it is accepted. The tool supports HLS streams, direct file URLs, and local files.

## Development Setup

```bash
# Clone and setup
git clone https://github.com/dohyeondk/sub-tools.git
cd sub-tools
./setup.sh  # installs uv and runs uv sync
```

## Common Commands

### Running the tool
```bash
# Using installed package (full pipeline)
uv run sub-tools -i <url> --languages en es fr

# With local audio file (skip video/audio tasks)
uv run sub-tools --tasks transcribe translate --audio-file audio.mp3 --languages en

# Only transcribe without translation
uv run sub-tools --tasks transcribe --audio-file audio.mp3 --languages en

# Specify a custom Gemini model for transcription and translation (default: gemini-3.7-flash)
uv run sub-tools -i <url> --languages en --model gemini-3.6-flash
```

### Testing
```bash
# Run all tests
uv run pytest -m "not slow"

# Run with verbose output
uv run pytest -v
```

### Contributing

When making changes to this repository, follow the contribution guidelines in `CONTRIBUTING.md`.

### Releasing

When creating a new release:
1. Update version in `pyproject.toml`
2. Run `uv sync` to update `uv.lock`
3. Commit both files: `git commit -m "chore: Bump version to X.Y.Z"`
4. Create and push tag: `git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z`

### Important: After Modifying pyproject.toml

**Always run `uv sync` after making changes to `pyproject.toml`** to update the lock file (`uv.lock`). This ensures dependencies are properly resolved and the lock file stays in sync with the project configuration.

## Architecture

### Pipeline Overview

The tool operates as a multi-stage pipeline controlled by the `--tasks` parameter:

1. **video**: Downloads media from URL (HLS or direct) → `output/video.mp4`
2. **audio**: Extracts audio track → `output/audio.mp3`
3. **signature**: Generates Shazam signature for fingerprinting (macOS only)
4. **transcribe**: Gemini turns the audio into `{source-language}.srt`
5. **translate**: Gemini translates that file into each target language

### Key Components

**main.py**: Entry point that orchestrates the pipeline stages sequentially.

**intelligence/gemini.py**: Transcription and translation using Gemini
- `transcribe()` turns audio into subtitles; `translate()` turns those subtitles into other languages
- Both run the same loop: ask the model, repair the answer, validate it, and ask again if it cannot be saved
- Exhausting the attempts raises `SubtitleValidationError`; no partial file is written
- Uses config for all parameters (audio_file, languages, API key)

**subtitles/repair.py**: Structural repair of model output
- Fixes only the container, never the words: code fences, missing hours fields, split timestamps, absent blank lines, timestamps demoted into subtitle text, junk cues, impossible ranges
- When translating, restores the source timings, aligning on start times if the model dropped a cue

**subtitles/validator.py**: Strict validation
- Parses SRT itself rather than using a lenient library, which accepted a file with 337 cues of content as 101 without error
- Errors mean retry (malformed, backwards, outside the audio, stops early, lost too much of a translation); warnings mean ship it and say so

**evaluation/transcription.py**: Reference-based scoring for generated SRT files
- Keeps evaluation independent from model execution so variants share the same input
- Delegates SubER, AS-WER, AS-CER, AS-BLEU, AS-TER, AS-chrF, t-WER, t-CER, t-BLEU, t-TER, and t-chrF to the pinned `subtitle-edit-rate` package
- Does not implement a local quality score or duplicate the package's edit-distance code
- Run through the `sub-tools-eval` script; it does not require an API key

**evals/**: Reproducible benchmark built on top of `sub-tools-eval` (see `evals/README.md`)
- Fetches a public-domain corpus with human-authored reference subtitles from Wikimedia Commons
- Compares transcription variants against the human references; the numbers behind the current design are in the project README
- `normalize.py` applies syntax-only SRT repairs to every variant identically; `verify_sync.py` rejects references that drift from their audio
- No media is checked in: `manifest.json` holds each clip's download URL and `corpus.py` caches the files outside the repo (`SUB_TOOLS_EVAL_CACHE`, default `~/.cache/sub-tools/evals`)

**config.py**: Central configuration dataclass
- Validation thresholds (max subtitle duration, gap thresholds)
- Shared across all modules

**arguments/parser.py**: CLI argument parsing
- `EnvDefault` custom action for environment variable fallbacks
- Dynamic version resolution from package metadata


**system/**:
- `console.py`: Rich-based CLI output formatting
- `file.py`: Output directory handling and skip-if-exists behaviour
- `language.py`: ISO language code to human-readable name mapping

**media/**:
- `converter.py`: FFmpeg wrapper for video/audio operations (all functions use config)

### Important Implementation Details

**Config-Based Architecture**: All functions use the global config object instead of parameters. Functions like `download_from_url()`, `video_to_audio()`, `transcribe()`, and `translate()` take no parameters and get values from `config`.

**Gemini Integration**: Gemini produces the subtitles directly from audio, and translates them from the source subtitle file plus the audio. Every answer passes through repair and validation before being written, because models get the words right far more reliably than the SRT container.

## Project Structure

```
src/sub_tools/
├── main.py              # Pipeline orchestration
├── config.py            # Configuration dataclass
├── arguments/           # CLI parsing
├── intelligence/        # Transcription and translation
│   └── gemini.py        # Gemini transcription and translation
├── subtitles/           # SRT repair and validation
├── media/               # FFmpeg operations (video/audio conversion)
└── system/              # Console, directory, file utilities
```

## Dependencies

- **google-genai**: Google Gemini API for transcription and translation
- **rich**: Terminal UI and progress bars
- **ffmpeg** (system dependency): Video/audio conversion
- **pycountry**: Language code handling

## Testing

Test coverage focuses on the parts that decide whether output ships:
- `test_repair.py`: every malformed shape a model actually returned
- `test_validator.py`: what must be rejected, including files a lenient parser accepts
- `test_directory.py`: File path handling

No integration tests for transcription (would require an API key and real audio).
