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

### Results

Measured on 23.3 minutes of public-domain speech: three White House weekly
addresses (single speaker, prepared remarks) and two NASA videos (narration and a
multi-speaker interview). Each clip comes from Wikimedia Commons with a
human-authored English subtitle track as the reference. No media is checked in —
`evals/manifest.json` records each clip's download URL and `evals/corpus.py`
fetches it on demand. The harness is in [`evals/`](evals/); run artifacts are not
committed, so the numbers below are the record of the run.

"Without sub-tools" means the model was handed the audio and asked for a subtitle
file, so it did both transcription and segmentation. "With sub-tools" is the
shipped pipeline: WhisperX transcribes, and the model proofreads that transcript.
Both Gemini configurations use identical generation settings, so the comparison
isolates the pipeline rather than the sampling knobs.

Macro-averaged over the five clips:

| variant | SubER ↓ | AS-WER ↓ | AS-CER ↓ | AS-BLEU ↑ | AS-TER ↓ | AS-chrF ↑ | valid SRT |
|---|---:|---:|---:|---:|---:|---:|---:|
| whisperx | 15.34 | 2.60 | 1.36 | 87.78 | 7.00 | 95.67 | 5/5 |
| gemini-3.7-flash (without sub-tools) | **12.55** | **2.46** | 1.33 | **90.54** | **5.75** | **96.77** | 5/5 |
| gemini-3.5-flash-lite (without sub-tools) | 21.30 | 4.35 | 1.91 | 84.69 | 8.73 | 95.03 | 1/5 |
| gemini-3.7-flash (with sub-tools) | 15.27 | 2.52 | 1.46 | 88.12 | 6.82 | 95.69 | 5/5 |
| gemini-3.5-flash-lite (with sub-tools) | 15.34 | 2.54 | **1.32** | 87.92 | 6.94 | 95.78 | 5/5 |

SubER per clip (lower is better), showing how each variant holds up across
content types:

| clip | whisperx | 3.7-flash<br>direct | 3.5-flash-lite<br>direct | 3.7-flash<br>sub-tools | 3.5-flash-lite<br>sub-tools |
|---|---:|---:|---:|---:|---:|
| obama-2009-06-13 | 14.69 | 15.13 | 19.08 | 14.69 | 14.69 |
| obama-2009-09-12 | 15.69 | 13.04 | 15.47 | 16.02 | 15.47 |
| obama-2009-11-28 | 19.81 | 16.47 | 19.57 | 19.57 | 19.81 |
| nasa-hubble-36th | 14.64 | 7.81 | 20.22 | 14.23 | 14.78 |
| nasa-orion-10-days | 11.85 | 10.31 | **32.18** | 11.85 | 11.95 |
| **macro-average** | **15.34** | **12.55** | **21.30** | **15.27** | **15.34** |
| worst-to-best spread | 7.96 | 8.66 | 16.71 | 7.72 | 7.86 |

**The pipeline makes a cheap model behave like an expensive one.** Gemini 3.5
Flash Lite on its own averages SubER 21.30, the worst of the five variants, and it
is erratic: it ranks worst on three of the five clips and blows up on the
multi-speaker NASA interview at 32.18, more than double its own best clip. Run
through sub-tools, the same model scores 15.34 — a 28% improvement that lands
level with Gemini 3.7 Flash run the same way (15.27) — and its per-clip spread
collapses from 16.71 to 7.86. Sub-tools buys roughly a model tier, and buys
consistency outright.

**It also makes output structurally reliable.** Used directly, Flash Lite emitted
syntactically invalid SRT on four of five clips — dropping the hours field from
timestamps, or omitting the blank lines between cues — and once collapsed an
entire five-minute clip into a single subtitle. Through sub-tools it produced
valid SRT every time, because WhisperX supplies the timing and structure and the
model only edits text. That structural guarantee is the pipeline's most practical
property: proofreading cannot invent a broken timeline.

**Proofreading improves the words.** Both models beat raw WhisperX on AS-WER
(2.52 and 2.54 vs 2.60), so the Gemini pass is doing real correction work on top
of the transcript it is given.

**Where the pipeline costs you: segmentation.** For the strongest model, direct
use scores better on SubER (12.55 vs 15.27). Proofreading must preserve the input
timestamps, so the sub-tools variants inherit WhisperX's cue boundaries: the
references carry 423 cues, Gemini 3.7 Flash produces 370 on its own, and WhisperX
produces 208. WhisperX cues run about twice as long as human subtitle cues, and
SubER — which scores timing and segmentation, not just words — charges for that.
If you want the pipeline's reliability *and* human-like cue density, the
segmentation stage is where to spend the effort, not the proofreading prompt.

To reproduce:

```shell
uv run python evals/corpus.py         # download media by URL into a local cache
uv run python evals/run_gemini_direct.py --model MODEL --variant NAME --api-key "$GEMINI_API_KEY"
uv run python evals/run_subtools.py --model MODEL --variant NAME
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
