# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project Overview

sub-tools is a Python toolkit for converting video/audio content into accurate, multilingual subtitles using WhisperX for transcription and Google's Gemini API for proofreading and translation. The tool supports HLS streams, direct file URLs, and local files.

## Development Setup

```bash
# Install uv package manager if not already installed
# https://github.com/astral-sh/uv

# Clone and setup
git clone https://github.com/dohyeondk/sub-tools.git
cd sub-tools
uv sync
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

# Specify custom model
uv run sub-tools -i <url> --languages en --model gemini-3-pro-preview
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
4. **transcribe**: Transcription using WhisperX (handles its own segmentation internally)
5. **translate**: Proofreads and translates transcription using Gemini

### Key Components

**main.py**: Entry point that orchestrates the pipeline stages sequentially.

**intelligence/whisperx.py**: Transcription using WhisperX
- High-quality speech recognition with word-level alignment
- Uses config for all parameters (audio_file, source_language, model settings)

**intelligence/gemini.py**: Proofreading and translation using Gemini
- Proofread function: Fixes transcription errors using audio as reference
- Translate function: Translates to multiple target languages
- Uses config for all parameters (audio_file, languages, API key)

**config.py**: Central configuration dataclass
- Validation thresholds (max subtitle duration, gap thresholds)
- Shared across all modules

**arguments/parser.py**: CLI argument parsing
- `EnvDefault` custom action for environment variable fallbacks
- Dynamic version resolution from package metadata

**subtitles/**:
- `validator.py`: Validates SRT timing, coverage, gaps
- `serializer.py`: Writes subtitle objects to .srt files

**system/**:
- `directory.py`: Manages temp directories (URL-based caching in system temp)
- `console.py`: Rich-based CLI output formatting
- `language.py`: ISO language code to human-readable name mapping

**media/**:
- `converter.py`: FFmpeg wrapper for video/audio operations (all functions use config)

### Important Implementation Details

**Config-Based Architecture**: All functions use the global config object instead of parameters. Functions like `download_from_url()`, `video_to_audio()`, `transcribe()`, `proofread()`, and `translate()` take no parameters and get values from `config`.

**WhisperX Integration**: Uses WhisperX for state-of-the-art speech recognition with word-level timestamps. WhisperX handles audio segmentation internally using voice activity detection.

**Gemini Integration**: Uses Gemini API with audio files as reference for both proofreading transcriptions and translating to target languages.

## Project Structure

```
src/sub_tools/
├── main.py              # Pipeline orchestration
├── config.py            # Configuration dataclass
├── arguments/           # CLI parsing
├── intelligence/        # Transcription and translation
│   ├── whisperx.py      # WhisperX transcription
│   └── gemini.py        # Gemini proofreading and translation
├── subtitles/           # SRT validation and serialization
├── media/               # FFmpeg operations (video/audio conversion)
└── system/              # Console, directory, file utilities
```

## Dependencies

- **whisperx**: Speech recognition with word-level alignment
- **google-genai**: Google Gemini API for proofreading and translation
- **rich**: Terminal UI and progress bars
- **ffmpeg** (system dependency): Video/audio conversion
- **pycountry**: Language code handling

## Testing

Test coverage focuses on core utilities:
- `test_directory.py`: File path handling

No integration tests for transcription (would require large audio files and be slow).
