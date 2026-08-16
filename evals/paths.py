"""Where the fetched corpus lives.

Media is never stored in the repository. `corpus.py` records the Commons
download URL in `manifest.json`, and the files themselves are cached outside the
working tree so a checkout stays text-only. Override the location with
``SUB_TOOLS_EVAL_CACHE``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent
MANIFEST = ROOT / "manifest.json"


def model_variant(model: str) -> str:
    """Return a filesystem-safe, stable name for a Gemini model ID."""

    variant = re.sub(r"[^A-Za-z0-9._-]+", "-", model.strip()).strip(".-_")
    if not variant:
        raise SystemExit("model must contain at least one alphanumeric character")
    return variant


def cache_dir() -> Path:
    override = os.environ.get("SUB_TOOLS_EVAL_CACHE")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "sub-tools" / "evals"


MEDIA_DIR = cache_dir() / "media"
AUDIO_DIR = cache_dir() / "audio"
REFERENCE_DIR = cache_dir() / "reference"


def audio_path(sample: dict) -> Path:
    return AUDIO_DIR / f"{sample['name']}.mp3"


def reference_path(sample: dict) -> Path:
    return REFERENCE_DIR / f"{sample['name']}.srt"


def load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        raise SystemExit("manifest.json is missing; run evals/corpus.py first")
    manifest = json.loads(MANIFEST.read_text())
    missing = [s["name"] for s in manifest if not audio_path(s).exists()]
    if missing:
        raise SystemExit(
            f"corpus audio missing from {AUDIO_DIR} for: {', '.join(missing)}\n"
            "run evals/corpus.py to download it"
        )
    return manifest
