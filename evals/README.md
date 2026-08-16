# Evaluation harness

Runs the sub-tools transcription pipeline with one selected Gemini model and
scores the generated subtitles against human-authored references.

No media is stored in this repository. manifest.json records the Commons
download URL for each clip, and corpus.py fetches the media, extracts the audio,
and writes the reference subtitles into a cache outside the working tree —
~/.cache/sub-tools/evals by default, overridable with SUB_TOOLS_EVAL_CACHE.
A clean checkout is text-only; run corpus.py to rebuild the corpus.

## Corpus

Five public-domain clips (23.3 min), each with a human-authored English subtitle
track published alongside the media on Commons. Source URLs are in
manifest.json.

| clip | source | length | reference cues |
|---|---|---:|---:|
| obama-2009-06-13 | White House weekly address | 289s | 89 |
| obama-2009-09-12 | White House weekly address | 261s | 85 |
| obama-2009-11-28 | White House weekly address | 243s | 78 |
| nasa-hubble-36th | NASA narration | 299s | 86 |
| nasa-orion-10-days | NASA multi-speaker interview | 306s | 85 |

Two references needed documented syntax fixes, both applied in corpus.py:
speaker labels are stripped because sub-tools is not asked to perform
diarization, and one track's stray blank line between a timestamp and its text
is rejoined so the file parses.

## Pipeline

Set the Gemini API key, then run the four commands below:

~~~shell
export GEMINI_API_KEY=...

uv run python evals/corpus.py
uv run python evals/run_subtools.py --model gemini-3.7-flash
uv run python evals/normalize.py
uv run python evals/score.py
~~~

run_subtools.py runs sub-tools with --tasks transcribe once per clip. The model
passed with --model is the only evaluation variable. Raw outputs are written to
evals/output/sub-tools, and existing files are skipped so interrupted runs can
resume.

normalize.py applies syntax-only repairs such as removing code fences,
normalizing timestamps, and restoring missing blank lines. It writes the
normalized files to evals/scored/sub-tools before scoring.

score.py runs sub-tools-eval once per clip and macro-averages the metrics. It
writes the generated report files under evals/reports and the aggregate files
evals/results.json and evals/results.md.

All run artifacts are gitignored and can be regenerated at any time.
