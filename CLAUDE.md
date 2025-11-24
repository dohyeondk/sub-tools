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
uv run sub-tools --tasks segment transcribe combine --audio-file audio.mp3 --languages en

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

### Releasing

When creating a new release:
1. Update version in `pyproject.toml`
2. Run `uv sync` to update `uv.lock`
3. Commit both files: `git commit -m "chore: Bump version to X.Y.Z"`
4. Create and push tag: `git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z`

## Architecture

### Pipeline Overview

The tool operates as a multi-stage pipeline controlled by the `--tasks` parameter:

1. **video**: Downloads media from URL (HLS or direct) → `output/video.mp4`
2. **audio**: Extracts audio track → `output/audio.mp3`
3. **signature**: Generates Shazam signature for fingerprinting (macOS only)
4. **segment**: Splits audio into chunks (default: 5 minutes each)
5. **transcribe**: Parallel transcription using Gemini API
6. **combine**: Merges individual SRT files into final output

### Key Components

**main.py**: Entry point that orchestrates the pipeline stages sequentially.

**transcribe.py**: Async transcription engine
- Processes all segments in parallel using `asyncio.gather()`
- Built-in rate limiter (10 requests/60 seconds) prevents API throttling
- Retry logic with exponential backoff for validation failures
- Progress tracking with Rich library

**intelligence/client.py**: Gemini API integration
- Converts audio segments to SRT format using Google GenAI SDK
- Long, detailed system prompt ensures complete audio coverage and proper SRT formatting
- Critical: Instructs model to transcribe ENTIRE audio file (common issue is stopping early)
- Handles rate limit exceptions specifically

**config.py**: Central configuration dataclass
- Validation thresholds (max subtitle duration, gap thresholds)
- Segmentation parameters (silence detection, min/max lengths)
- Shared across all modules

**arguments/parser.py**: CLI argument parsing
- `EnvDefault` custom action for environment variable fallbacks
- Dynamic version resolution from package metadata

**subtitles/**:
- `validator.py`: Validates SRT timing, coverage, gaps
- `combiner.py`: Merges segment SRTs with offset adjustments
- `serializer.py`: Writes subtitle objects to .srt files

**system/**:
- `rate_limiter.py`: Async token bucket rate limiter with lock-based concurrency control
- `directory.py`: Manages temp directories (URL-based caching in system temp)
- `console.py`: Rich-based CLI output formatting
- `language.py`: ISO language code to human-readable name mapping

**media/**:
- `converter.py`: FFmpeg wrapper for video/audio operations
- `segmenter.py`: VAD-based audio splitting with silence detection
- `info.py`: Audio file metadata extraction

### Important Implementation Details

**URL-based Caching**: The tool creates temp directories based on URL hash (see `get_temp_directory()` in `system/directory.py`). This allows resuming interrupted transcriptions without re-processing.

**Parallel Transcription**: Each language × segment combination runs as an independent async task. Rate limiting is global across all tasks.

**Validation Strategy**: After each Gemini API call, subtitles are validated for:
- Complete coverage of audio duration
- No excessive gaps at beginning/end or between segments
- Proper timestamp formatting
- Reasonable subtitle duration (max 20 seconds)

Invalid results trigger retry with exponential backoff. Debug logs are written to `{lang}_{offset}_*.log` when `--debug` is enabled.

**Model Selection**: Default is `gemini-2.5-flash-lite` for cost efficiency. Users can override with `--model` parameter.

## Project Structure

```
src/sub_tools/
├── main.py              # Pipeline orchestration
├── transcribe.py        # Async transcription engine
├── config.py            # Configuration dataclass
├── arguments/           # CLI parsing
├── intelligence/        # Gemini API client
├── subtitles/           # SRT validation, combining, serialization
├── media/               # FFmpeg operations, segmentation
└── system/              # Rate limiting, logging, file management
```

## Dependencies

- **google-genai**: Official Google Generative AI SDK (replaced OpenAI SDK in v0.7.0+)
- **pydub**: Audio manipulation
- **silero-vad**: Voice activity detection for segmentation
- **pysrt**: SRT file parsing
- **rich**: Terminal UI and progress bars
- **python-ffmpeg**: FFmpeg Python wrapper

## Testing

Test coverage focuses on core utilities:
- `test_rate_limiter.py`: Async rate limiter correctness
- `test_segmentor.py`: Audio segmentation logic
- `test_directory.py`: File path handling

No integration tests for API calls (would require API keys and be expensive).
