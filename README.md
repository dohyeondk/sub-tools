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

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dohyeondk/sub-tools&type=Date)](https://star-history.com/#dohyeondk/sub-tools&Date)
