# sub-tools 🎬

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A robust Python toolkit powered by Google's Gemini API for converting video content into accurate, multilingual subtitles.

## ✨ Features

- 📝 Subtitle generation from HLS video streams.
- 📚 Subtitle validation and quality control.
- 🎵 Audio fingerprinting and analysis using Shazam (macOS only).

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

# Using HLS
sub-tools --hls-url https://example.com/hls/video.m3u8 --languages en es fr

# Using MP3
sub-tools --tasks segment transcribe combine --audio-file audio.mp3 -languages en es fr
```

### Build Docker

```shell
docker build -t sub-tools .
docker run -v $(pwd)/output:/app/output sub-tools sub-tools --gemini-api-key GEMINI_API_KEY -i HLS_URL -l en
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/{feature-name}`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/{feature-name}`)
5. Open a Pull Request

### Prerequisites

- [uv](https://github.com/astral-sh/uv)

### Development Setup

```shell
git clone https://github.com/dohyeondk/sub-tools.git
cd sub-tools
uv sync
```

### Code Quality Tools

The project uses the following code quality tools:

- **Ruff** for linting
- **mypy** for type checking
- **Black** for code formatting

To install development dependencies:

```shell
uv sync -e dev
# or with pip
pip install -e ".[dev]"
```

To run the tools:

```shell
# Linting with Ruff
ruff check .

# Type checking with mypy
mypy src

# Formatting with Black
black .
```

## 🧪 Testing

```shell
uv run pytest
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dohyeondk/sub-tools&type=Date)](https://star-history.com/#dohyeondk/sub-tools&Date)
