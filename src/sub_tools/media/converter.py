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
