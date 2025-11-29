# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sub-tools is a Python toolkit for converting video/audio content into accurate, multilingual subtitles using Google's Gemini API. The tool supports HLS streams, direct file URLs, and local files.

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
# Using installed package
uv run sub-tools -i <url> --languages en es fr

# With local audio file
uv run sub-tools --tasks transcribe --audio-file audio.mp3 --languages en

# Specify custom model
uv run sub-tools -i <url> --languages en --model gemini-2.5-flash-preview-04-17
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_rate_limiter.py

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

### Key Components

**main.py**: Entry point that orchestrates the pipeline stages sequentially.

**transcribe.py**: Transcription engine
- Uses WhisperX for high-quality speech recognition and word-level alignment
- Handles multiple languages with automatic language detection
- Progress tracking with Rich library

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
- `rate_limiter.py`: Async token bucket rate limiter with lock-based concurrency control
- `directory.py`: Manages temp directories (URL-based caching in system temp)
- `console.py`: Rich-based CLI output formatting
- `language.py`: ISO language code to human-readable name mapping

**media/**:
- `converter.py`: FFmpeg wrapper for video/audio operations

### Important Implementation Details

**URL-based Caching**: The tool creates temp directories based on URL hash (see `get_temp_directory()` in `system/directory.py`). This allows resuming interrupted transcriptions without re-processing.

**WhisperX Integration**: Uses WhisperX for state-of-the-art speech recognition with word-level timestamps. WhisperX handles audio segmentation internally using voice activity detection.

## Project Structure

```
src/sub_tools/
├── main.py              # Pipeline orchestration
├── transcribe.py        # Transcription engine (WhisperX)
├── config.py            # Configuration dataclass
├── arguments/           # CLI parsing
├── subtitles/           # SRT validation, combining, serialization
├── media/               # FFmpeg operations
└── system/              # Rate limiting, logging, file management
```

## Dependencies

- **whisperx**: Speech recognition with word-level alignment
- **pysrt**: SRT file parsing
- **rich**: Terminal UI and progress bars
- **python-ffmpeg**: FFmpeg Python wrapper
- **pycountry**: Language code handling

## Testing

Test coverage focuses on core utilities:
- `test_rate_limiter.py`: Async rate limiter correctness
- `test_directory.py`: File path handling

No integration tests for transcription (would require large audio files and be slow).
