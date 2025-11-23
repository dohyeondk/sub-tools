import os
import subprocess

from ..system.console import status, warning


def download_from_url(
    url: str,
    video_file: str,
    audio_only: bool = False,
    overwrite: bool = False,
) -> None:
    """
    Downloads media from a URL (HLS stream or direct file) and saves it as video or audio.

    Args:
        url: URL to download from (can be HLS stream or direct file URL)
        video_file: Path to save the downloaded video file
        audio_only: If True, extract audio only
        overwrite: If True, overwrite existing files
    """
    if os.path.exists(video_file) and not overwrite:
        warning(f"File {video_file} already exists. Skipping download...")
        return

    cmd = ["ffmpeg", "-y", "-i", url]

    if audio_only:
        cmd.extend(["-vn", "-c:a", "libmp3lame"])

    cmd.append(video_file)

    try:
        with status("Downloading media..."):
            subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to download media from {url}: {e.stderr.decode() if e.stderr else str(e)}"
        )


def video_to_audio(
    video_file: str,
    audio_file: str,
    overwrite: bool = False,
) -> None:
    """
    Converts a video file to an audio file using ffmpeg.
    """
    if os.path.exists(audio_file) and not overwrite:
        warning(f"Audio file {audio_file} already exists. Skipping conversion...")
        return

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_file,
        "-vn",
        "-c:a",
        "libmp3lame",
        audio_file,
    ]

    try:
        with status("Converting video to audio..."):
            subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to convert video to audio: {e.stderr.decode() if e.stderr else str(e)}"
        )


def media_to_signature(
    media_file: str,
    signature_file: str,
    overwrite: bool = False,
) -> None:
    """
    Generates a signature for the media file using the shazam CLI.
    """
    if os.path.exists(signature_file) and not overwrite:
        warning(
            f"Skipping signature generation: Signature file {signature_file} already exists."
        )
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
        media_file,
        "--output",
        signature_file,
    ]

    try:
        with status("Generating signature..."):
            subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to generate signature: {e.stderr.decode() if e.stderr else str(e)}"
        )
