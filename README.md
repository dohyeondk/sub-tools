# sub-tools 🎬

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A toolkit for multilingual subtitles. Gemini transcribes the audio and translates the result; every answer is repaired and checked before it is accepted. Gemini 3.7 Flash is the primary model.

## ✨ Features

- 🎯 Transcription with Gemini straight from audio to SRT
- 🧰 Automatic repair of malformed model output, with a retry when repair cannot save it
- ✅ Strict validation that refuses to ship a broken subtitle file
- 🌍 Multilingual translation that preserves the source timings
- 🔊 Optional translated narration with Gemini TTS
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

# Full pipeline: download video, extract audio, transcribe, and translate
sub-tools -i https://example.com/video.mp4 --languages en es fr

# Using HLS stream URL
sub-tools -i https://example.com/hls/video.m3u8 --languages en es fr

# Using local audio file (skip video/audio tasks)
sub-tools --tasks transcribe translate --audio-file audio.mp3 --languages en es fr

# Only transcribe without translation
sub-tools --tasks transcribe --audio-file audio.mp3 --languages en

# Generate simple translated narration from existing translated SRT files
sub-tools --tasks dub --languages en es fr

# Specify custom tasks (available: video, audio, signature, transcribe, translate, dub)
sub-tools -i https://example.com/video.mp4 --tasks video audio transcribe translate --languages en es

# Specify a custom Gemini model for transcription and translation
sub-tools -i https://example.com/video.mp4 --languages en --model gemini-3.6-flash

# Specify output directory (default: output)
sub-tools -i https://example.com/video.mp4 --languages en --output my-subtitles
```

### Pipeline Tasks

The tool operates as a multi-stage pipeline controlled by the `--tasks` parameter:

1. **video**: Downloads media from URL (HLS or direct) → `video.mp4`
2. **audio**: Extracts audio track → `audio.mp3`
3. **signature**: Generates Shazam signature for fingerprinting (macOS only)
4. **transcribe**: Gemini turns the audio into subtitles → `{source-language}.srt`
5. **translate**: Gemini translates those subtitles into each target language → `{language}.srt`
6. **dub**: Gemini TTS reads each translated subtitle file → `{language}.wav`

The `dub` task is opt-in; the existing five tasks continue to run by
default. It uses `gemini-2.5-flash-preview-tts` and the `Sadaltager` voice unless you pass
`--tts-model` or `--tts-voice`.

Gemini 3.7 Flash supports audio input but not audio output, so `dub` sends the
translated SRT text to the dedicated TTS model. It fits gap-aware audio chunks
(up to 300 seconds by default) to the subtitle timeline and writes a WAV matching
the original duration. This does not preserve or mix the original speakers, music,
or audience reactions.

## 📏 Transcription evaluation

The evaluator is deliberately separate from model execution: it scores generated SRT
files against a human reference so multiple runs can be compared on identical input.
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
  --hypothesis gemini-3.7-flash=output/gemini-3.7-flash/en.srt \
  --hypothesis gemini-3.6-flash=output/gemini-3.6-flash/en.srt \
  --output evals/transcription.json \
  --markdown evals/transcription.md
```

Only the reference and generated SRT files are inputs; no audio file or API key is
required. Private or copyrighted recordings are intentionally not bundled in the
package.

`sub-tools-eval` measures the text, segmentation, and timing quality of the assembled
SRT output, while `sub-tools` remains responsible for producing the SRT.

To compare models or settings, pass each generated file as a `--hypothesis`. The
Markdown report shows one row per variant; lower error rates and higher BLEU/chrF
indicate a closer match to the reference.

For the reproducible evaluation harness and commands, see
[evals/README.md](evals/README.md).

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
