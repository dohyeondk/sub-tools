# sub-tools 🎬

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A toolkit for multilingual subtitles: WhisperX transcribes, and Gemini proofreads and translates. Gemini 3.7 Flash is the primary model.

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

For a source checkout, run the setup script from a shell. It installs `uv` when it is
missing, provisions a supported Python interpreter if needed, and syncs the project
environment:

```shell
./setup.sh
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

# Specify a custom Gemini model for proofreading/translation
sub-tools -i https://example.com/video.mp4 --languages en --model gemini-3.6-flash

# Specify output directory (default: output)
sub-tools -i https://example.com/video.mp4 --languages en --output my-subtitles
```

### Pipeline Tasks

The tool operates as a multi-stage pipeline controlled by the `--tasks` parameter:

1. **video**: Downloads media from URL (HLS or direct) → `video.mp4`
2. **audio**: Extracts audio track → `audio.mp3`
3. **signature**: Generates Shazam signature for fingerprinting (macOS only)
4. **transcribe**: Transcription using WhisperX only → `transcript.srt`
5. **translate**: Proofreads and translates the WhisperX transcript using Gemini → `{language}.srt`

By default, all tasks run. You can customize which tasks to run with `--tasks`.

## 📏 Transcription evaluation

The evaluator is deliberately separate from model execution: it scores generated SRT
files against a human reference so multiple runs can be compared on identical input.
WhisperX is the only transcription engine in this project. Gemini models are evaluated
as a post-processing step over the same WhisperX transcript, with timestamps preserved;
the comparison therefore measures proofreading differences between Gemini models rather
than comparing different transcription engines.
The primary score is the published [SubER method](https://aclanthology.org/2022.iwslt-1.1/),
implemented by the pinned [`subtitle-edit-rate==0.4.0`](https://pypi.org/project/subtitle-edit-rate/)
package. SubER is reference-based and accounts for subtitle text, segmentation, and
timing; lower is better. It is a published academic method and reference
implementation, not an NIST certification.

The report also includes the package's automatic-segmentation lexical metrics for
SRTs with different cue boundaries: `AS-WER`, `AS-CER`, `AS-BLEU`, `AS-TER`, and
`AS-chrF`. `AS-WER` and `AS-CER` use the same substitution/insertion/deletion
edit-rate convention documented in [NIST SCTK/SCLITE](https://github.com/usnistgov/SCTK/blob/master/doc/sclite.htm);
BLEU, TER, and chrF are provided by SacreBLEU through `subtitle-edit-rate`.
The report also includes the package's timing-aligned `t-WER`, `t-CER`, `t-BLEU`,
`t-TER`, and `t-chrF` diagnostics. This command does not invoke SCTK itself. The
evaluator is intentionally package-only: it does not add a custom score, timing
metric, coverage metric, or release gate.

The package documents the AS alignment family as the established automatic
segmentation approach (Matusov et al., [IWSLT 2005](https://aclanthology.org/2005.iwslt-1.19/))
and the t-BLEU timing-alignment approach (Cherry et al.,
[Interspeech 2021](https://www.isca-archive.org/interspeech_2021/cherry21_interspeech.pdf)).
The implementation here calls the package APIs directly; it does not reimplement
either alignment or any metric.

SubER is the primary score because it is the package's timing- and
segmentation-aware metric. AS-WER, AS-CER, and AS-TER are error rates (lower is
better); AS-BLEU and AS-chrF are similarity scores (higher is better). BLEU can be
low on very short samples because it requires n-gram matches, so it should be read
alongside the other metrics rather than used alone. The `t-*` metrics re-segment
the hypothesis using subtitle timings; they are supplemental diagnostics and do
not replace SubER's joint timing/segmentation score.

Give each hypothesis a stable name with `NAME=PATH`; repeat `--hypothesis` to compare
models or pipeline stages:

```shell
sub-tools-eval \
  --reference reference/en.srt \
  --hypothesis whisperx=output/transcript.srt \
  --hypothesis gemini-3.7-flash=output/gemini-3.7-flash/en.srt \
  --hypothesis gemini-3.6-flash=output/gemini-3.6-flash/en.srt \
  --output evals/transcription.json \
  --markdown evals/transcription.md
```

Only the reference and generated SRT files are inputs; no audio file or API key is
required. Private or copyrighted recordings are intentionally not bundled in the
package.

`sub-tools-eval` measures the text, segmentation, and timing quality of the assembled
SRT output, while `sub-tools` remains responsible for producing the SRT. In particular,
Gemini proofreading is evaluated with the timestamps WhisperX produced.

To compare models, generate one WhisperX transcript and pass each Gemini output as a
`--hypothesis`. The Markdown report shows one row per variant; lower error rates and
higher BLEU/chrF indicate a closer match to the reference.

### Build Docker

```shell
docker build -t sub-tools .
docker run -v $(pwd)/output:/app/output sub-tools sub-tools --gemini-api-key GEMINI_API_KEY -i URL -l en
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Development Setup

```shell
# Clone and setup
git clone https://github.com/dohyeondk/sub-tools.git
cd sub-tools
./setup.sh  # installs uv and runs uv sync
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
