# sub-tools 🎬

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A robust Python toolkit for converting video/audio content into accurate, multilingual subtitles using WhisperX for transcription and Google's Gemini API for proofreading and translation.

## ✨ Features

- 🎯 High-quality transcription using WhisperX with word-level alignment
- 🔍 AI-powered proofreading with Gemini to fix transcription errors
- 🌍 Multilingual translation support
- 📥 Support for HLS streams, direct file URLs, and local files
- 🎵 Audio fingerprinting using Shazam (macOS only)
- 📊 Progress tracking with rich terminal output

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- [FFmpeg](https://ffmpeg.org/) installed on your system

### Installation

```shell
pip install sub-tools
```

### Usage

```shell
export GEMINI_API_KEY={your_api_key}

# Full pipeline: download video, extract audio, transcribe, proofread, and translate
sub-tools -i https://example.com/video.mp4 --languages en es fr

# Using HLS stream URL
sub-tools -i https://example.com/hls/video.m3u8 --languages en es fr

# Using local audio file (skip video/audio tasks)
sub-tools --tasks transcribe translate --audio-file audio.mp3 --languages en es fr

# Only transcribe without translation
sub-tools --tasks transcribe --audio-file audio.mp3 --languages en

# Specify custom tasks (available: video, audio, signature, transcribe, translate)
sub-tools -i https://example.com/video.mp4 --tasks video audio transcribe translate --languages en es

# Specify a custom Gemini model (default: gemini-3-pro-preview)
sub-tools -i https://example.com/video.mp4 --languages en --model gemini-2.5-pro

# Specify output directory (default: output)
sub-tools -i https://example.com/video.mp4 --languages en --output my-subtitles
```

### Pipeline Tasks

The tool operates as a multi-stage pipeline controlled by the `--tasks` parameter:

1. **video**: Downloads media from URL (HLS or direct) → `video.mp4`
2. **audio**: Extracts audio track → `audio.mp3`
3. **signature**: Generates Shazam signature for fingerprinting (macOS only)
4. **transcribe**: Transcription using WhisperX → `transcript.srt`
5. **translate**: Proofreads and translates to target languages using Gemini → `{language}.srt`

By default, all tasks run. You can customize which tasks to run with `--tasks`.

## 📏 Transcription evaluation

The evaluator is deliberately separate from model execution: it scores generated SRT
files against a human reference so multiple runs can be compared on identical input.
It reports WER/CER, accuracy, anchor timing error and drift, lexical F1, coverage and
gaps, subtitle structure/readability, repetition/boilerplate signals, and hard gates.

Give each hypothesis a stable name with `NAME=PATH`; repeat `--hypothesis` to compare
models or pipeline stages:

```shell
sub-tools-eval \
  --duration 356.133 \
  --reference reference/en.srt \
  --hypothesis whisperx=output/transcript.srt \
  --hypothesis gemini-3.7=output/gemini-3.7/en.srt \
  --hypothesis gemini-3.6=output/gemini-3.6/en.srt \
  --output evals/transcription.json \
  --markdown evals/transcription.md
```

Use `--audio-file clip.mp3` instead of `--duration` when `ffprobe` is available. The
reference and audio are inputs to the evaluation and are intentionally not bundled in
the package; this keeps private or copyrighted recordings out of the repository.

`sub-tools-eval` measures the output of the full pipeline, while `sub-tools` remains
responsible for producing the SRT. In particular, Gemini proofreading is evaluated with
the timestamps WhisperX produced, so timing results belong to the assembled pipeline,
not to Gemini alone.

### Build Docker

```shell
docker build -t sub-tools .
docker run -v $(pwd)/output:/app/output sub-tools sub-tools --gemini-api-key GEMINI_API_KEY -i URL -l en
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Development Setup

```shell
# Install uv package manager
# https://github.com/astral-sh/uv

# Clone and setup
git clone https://github.com/dohyeondk/sub-tools.git
cd sub-tools
uv sync
```

## 🧪 Testing

```shell
uv run pytest -m "not slow"
```

The evaluation metrics have unit tests in `tests/test_evaluation.py` and do not require
an API key or an audio file.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dohyeondk/sub-tools&type=Date)](https://star-history.com/#dohyeondk/sub-tools&Date)
