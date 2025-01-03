# sub-tools 🎬

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A robust Python toolkit powered by Google's Gemini API for converting video content into accurate, multilingual subtitles.

## ✨ Features

- 📝 Subtitle generation from HLS video streams.
- 📚 Subtitle validation and quality control.
- 🎵 Audio fingerprinting and analysis using Shazam (macOS only).

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- [FFmpeg](https://ffmpeg.org/) installed on your system

### Installation

```shell
pip install sub-tools
```

### Usage

```shell
export GEMINI_API_KEY={your_api_key}
sub-tools --hls-url https://example.com/hls/video.m3u8 --languages en es fr
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

## 🧪 Testing

```shell
uv run pytest
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dohyeondk/sub-tools&type=Date)](https://star-history.com/#dohyeondk/sub-tools&Date)