# sub-tools 🎬

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A toolkit for multilingual subtitles. Gemini transcribes the audio and translates the result; every answer is repaired and checked before it is accepted. Gemini 3.7 Flash is the primary model.

## ✨ Features

- 🎯 Transcription with Gemini straight from audio to SRT
- 🧰 Automatic repair of malformed model output, with a retry when repair cannot save it
- ✅ Strict validation that refuses to ship a broken subtitle file
- 🌍 Multilingual translation that preserves the source timings
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

# Specify custom tasks (available: video, audio, signature, transcribe, translate)
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

By default, all tasks run. You can customize which tasks to run with `--tasks`.

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

### Results

These are the measurements that produced the current design. They were taken
when the pipeline still ran WhisperX and used Gemini only to proofread, and they
are the reason it no longer does.

Measured on 23.3 minutes of public-domain speech: three White House weekly
addresses (single speaker, prepared remarks) and two NASA videos (narration and a
multi-speaker interview). Each clip comes from Wikimedia Commons with a
human-authored English subtitle track as the reference. No media is checked in —
`evals/manifest.json` records each clip's download URL and `evals/corpus.py`
fetches it on demand.

"Direct" means the model was handed the audio and asked for a subtitle file, so
it did both transcription and segmentation. "Proofread" was the previous
architecture: WhisperX transcribed, and the model edited the text without moving
the timings. Both use identical generation settings.

Macro-averaged over the five clips:

| variant | SubER ↓ | AS-WER ↓ | AS-CER ↓ | AS-BLEU ↑ | AS-TER ↓ | AS-chrF ↑ | valid SRT |
|---|---:|---:|---:|---:|---:|---:|---:|
| whisperx alone | 15.34 | 2.60 | 1.36 | 87.78 | 7.00 | 95.67 | 5/5 |
| gemini-3.7-flash direct | **12.55** | **2.46** | 1.33 | **90.54** | **5.75** | **96.77** | 5/5 |
| gemini-3.5-flash-lite direct | 21.30 | 4.35 | 1.91 | 84.69 | 8.73 | 95.03 | 1/5 |
| gemini-3.7-flash proofread (old pipeline) | 15.27 | 2.52 | 1.46 | 88.12 | 6.82 | 95.69 | 5/5 |
| gemini-3.5-flash-lite proofread (old pipeline) | 15.34 | 2.54 | **1.32** | 87.92 | 6.94 | 95.78 | 5/5 |

SubER per clip (lower is better):

| clip | whisperx | 3.7-flash<br>direct | 3.5-flash-lite<br>direct | 3.7-flash<br>proofread | 3.5-flash-lite<br>proofread |
|---|---:|---:|---:|---:|---:|
| obama-2009-06-13 | 14.69 | 15.13 | 19.08 | 14.69 | 14.69 |
| obama-2009-09-12 | 15.69 | 13.04 | 15.47 | 16.02 | 15.47 |
| obama-2009-11-28 | 19.81 | 16.47 | 19.57 | 19.57 | 19.81 |
| nasa-hubble-36th | 14.64 | 7.81 | 20.22 | 14.23 | 14.78 |
| nasa-orion-10-days | 11.85 | 10.31 | **32.18** | 11.85 | 11.95 |
| **macro-average** | **15.34** | **12.55** | **21.30** | **15.27** | **15.34** |
| worst-to-best spread | 7.96 | 8.66 | 16.71 | 7.72 | 7.86 |

**Gemini 3.7 Flash is best on its own.** It leads every metric and beats WhisperX
on SubER by 18%, winning four of the five clips. Most of the gap is segmentation:
the references carry 423 cues, Gemini produces 370 unaided, and WhisperX produces
208 — cues roughly twice as long as a human would write. Because proofreading had
to preserve WhisperX's timings, no amount of text editing could recover that,
which is why the transcription stage is now Gemini's alone.

**The old pipeline's real value was protecting a weak model.** Gemini 3.5 Flash
Lite used directly averaged 21.30 and emitted syntactically invalid SRT on four
of five clips, once collapsing an entire five-minute clip into a single subtitle.
Routed through WhisperX it reached 15.34 with valid output every time, because
the structure came from somewhere else.

That protection is what the repair and validation stages now provide directly,
without a second transcription engine: malformed output is repaired where it can
be, the result is checked strictly, and the request is retried when it cannot.

To reproduce:

```shell
uv run python evals/corpus.py         # download media by URL into a local cache
uv run python evals/run_gemini_direct.py --model MODEL --variant NAME --api-key "$GEMINI_API_KEY"
uv run python evals/normalize.py      # repair SRT syntax, identically per variant
uv run python evals/verify_sync.py    # reject references that drift from the audio
uv run python evals/score.py          # run sub-tools-eval per clip and aggregate
```

`normalize.py` applies syntax-only repairs (code fences, malformed timestamps,
missing blank lines) to every variant so that an unparseable file is scored rather
than silently dropped; it leaves well-formed files byte-identical, and reports
which files it had to touch. `verify_sync.py` guards the corpus itself: one
candidate clip was dropped because its Commons subtitle track was offset ~3.3s
against the media, which penalized every variant equally and masked the
differences being measured.

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
