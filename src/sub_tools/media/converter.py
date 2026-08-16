import re
import subprocess

from sub_tools.system.file import should_skip

from ..config import config
from ..system.console import status, warning


def download_from_url() -> None:
    """
    Downloads media from a URL (HLS stream or direct file) and saves it as video or audio.
    """
    if should_skip(config.video_file):
        return

    cmd = ["ffmpeg", "-y", "-i", config.url]

    cmd.append(config.video_file)

    try:
        with status("Downloading media..."):
            subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to download media from {config.url}: {e.stderr.decode() if e.stderr else str(e)}"
        )


def video_to_audio() -> None:
    """
    Converts a video file to an audio file using ffmpeg.
    """
    if should_skip(config.audio_file):
        return

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        config.video_file,
        "-vn",
        "-c:a",
        "libmp3lame",
        config.audio_file,
    ]

    try:
        with status("Converting video to audio..."):
            subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to convert video to audio: {e.stderr.decode() if e.stderr else str(e)}"
        )


def audio_duration(path: str) -> float | None:
    """
    Return the length of the audio in seconds, or None if it cannot be measured.

    Used to check that subtitles span the recording. A missing ffprobe is not
    fatal; the checks that need a duration are skipped instead.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass

    # ffprobe is normally installed with ffmpeg, but some distributions package
    # only the latter. Its input summary still contains the exact media duration.
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", path],
            check=False,
            capture_output=True,
            text=True,
        )
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
        if match:
            hours, minutes, seconds = match.groups()
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    warning("Could not measure audio duration; skipping coverage checks.")
    return None


def media_to_signature() -> None:
    """
    Generates a signature for the media file using the shazam CLI.
    """
    if should_skip(config.signature_file):
        return

    try:
        subprocess.run("shazam", capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        warning("Skipping signature generation: Shazam CLI not available.")
        return

    cmd = [
        "shazam",
        "signature",
        "--input",
        config.audio_file,
        "--output",
        config.signature_file,
    ]

    try:
        with status("Generating signature..."):
            subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to generate signature: {e.stderr.decode() if e.stderr else str(e)}"
        )
