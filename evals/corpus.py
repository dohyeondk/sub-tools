"""Fetch the public-domain evaluation corpus from Wikimedia Commons.

Each sample is a media file whose Commons ``TimedText`` page carries a
human-authored English SRT track. Nothing fetched here is stored in the
repository: `manifest.json` records the download URL for each clip and the files
themselves are cached outside the working tree (see `paths.py`). Audio is
extracted to MP3 so every variant scores the same input.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from paths import AUDIO_DIR, MANIFEST, MEDIA_DIR, REFERENCE_DIR, cache_dir

API = "https://commons.wikimedia.org/w/api.php"
UA = "sub-tools-eval/0.8 (https://github.com/dohyeondk/sub-tools)"

# name -> Commons file title
SAMPLES = {
    # 2009-04-11 was tried first and dropped: its Commons subtitle track is
    # offset ~3.3s against the media, which penalises every variant equally and
    # swamps the differences being measured. verify_sync.py checks for this.
    "obama-2009-06-13": "2009-06-13 President Obama's Weekly Address.ogv",
    "obama-2009-09-12": "2009-09-12 President Obama's Weekly Address.ogv",
    "obama-2009-11-28": "2009-11-28 President Obama's Weekly Address.ogv",
    "nasa-hubble-36th": '"Cosmic Sea Slug" Appears in Hubble’s 36th Birthday Image (SVS15002).webm',
    "nasa-orion-10-days": "10 Days in Orion (jsc2026m000044).webm",
}

# Reference tracks label the speaker on the first cue; no ASR system is asked to
# do diarization, so the labels are dropped rather than charged to every variant.
SPEAKER_LABEL = re.compile(r"^(The President|Mr\. President|PRESIDENT OBAMA)\s*:\s*", re.M)

# One upstream track has a stray blank line between a cue's timestamp and its
# text, which orphans the text into a block of its own and makes the file
# unparseable. Rejoin those; this is a syntax fix, not an edit to the wording.
ORPHANED_TEXT = re.compile(r"(-->[^\n]*)\n\n+(?!\s*\d+\s*\n\s*\d{2}:)", re.M)


def _post(params: dict) -> dict:
    params["format"] = "json"
    request = urllib.request.Request(
        API, data=urllib.parse.urlencode(params).encode(), headers={"User-Agent": UA}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=600) as response:
        destination.write_bytes(response.read())


def _duration(seconds: float, audio_path: Path) -> float:
    """Commons reports no length for some WebM files; measure the audio instead."""

    if seconds:
        return seconds
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(audio_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(probe.stdout.strip())


def main() -> None:
    for directory in (MEDIA_DIR, AUDIO_DIR, REFERENCE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    print(f"corpus cache: {cache_dir()}")

    info = _post(
        {
            "action": "query",
            "prop": "imageinfo",
            "iiprop": "url|mime|metadata",
            "titles": "|".join("File:" + title for title in SAMPLES.values()),
        }
    )
    urls = {}
    durations = {}
    for page in info["query"]["pages"].values():
        image = page["imageinfo"][0]
        metadata = {m["name"]: m["value"] for m in image.get("metadata") or []}
        title = page["title"][len("File:") :]
        # The API appends analytics query params; keep the bare download URL.
        urls[title] = urllib.parse.urljoin(image["url"], urllib.parse.urlparse(image["url"]).path)
        durations[title] = float(metadata.get("length", 0))

    tracks = _post(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(f"TimedText:{title}.en.srt" for title in SAMPLES.values()),
        }
    )
    subtitles = {
        page["title"][len("TimedText:") : -len(".en.srt")]: page["revisions"][0]["slots"]["main"]["*"]
        for page in tracks["query"]["pages"].values()
    }

    manifest = []
    for name, title in SAMPLES.items():
        reference_path = REFERENCE_DIR / f"{name}.srt"
        text = subtitles[title].replace("﻿", "").replace("\r\n", "\n")
        text = ORPHANED_TEXT.sub(r"\1\n", text)
        reference_path.write_text(SPEAKER_LABEL.sub("", text).strip() + "\n", encoding="utf-8")

        audio_path = AUDIO_DIR / f"{name}.mp3"
        if not audio_path.exists():
            source = MEDIA_DIR / title
            if not source.exists():
                _download(urls[title], source)
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
                 "-b:a", "64k", str(audio_path)],
                check=True,
                capture_output=True,
            )

        duration = _duration(durations[title], audio_path)
        manifest.append(
            {
                "name": name,
                "commons_file": title,
                "source_url": urls[title],
                "subtitle_url": f"https://commons.wikimedia.org/wiki/TimedText:{urllib.parse.quote(title)}.en.srt",
                "duration_seconds": round(duration, 1),
                "cues": subtitles[title].count("-->"),
            }
        )
        print(f"{name}: {duration:.0f}s, {manifest[-1]['cues']} reference cues")

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"total {sum(m['duration_seconds'] for m in manifest) / 60:.1f} min")


if __name__ == "__main__":
    main()
