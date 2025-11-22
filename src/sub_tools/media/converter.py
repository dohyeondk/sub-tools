import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from ..system.console import status, warning


def _is_hls_url(url: str) -> bool:
    """
    Determines if a URL is an HLS stream based on file extension.
    """
    ext = _get_file_extension(url)
    return ext in (".m3u8", ".m3u")


def _get_file_extension(url: str) -> str:
    """
    Extracts the file extension from a URL.
    """
    parsed = urlparse(url)
    path = Path(parsed.path)
    return path.suffix.lower()


def download_from_url(
    url: str,
    output_file: str,
    audio_only: bool = False,
    overwrite: bool = False,
) -> None:
    """
    Downloads media from a URL (HLS stream or direct file) and saves it as video or audio.

    Args:
        url: URL to download from (can be HLS stream or direct file URL)
        output_file: Path to save the downloaded file
        audio_only: If True, extract audio only
        overwrite: If True, overwrite existing files
    """
    if os.path.exists(output_file) and not overwrite:
        warning(f"File {output_file} already exists. Skipping download...")
        return

    is_hls = _is_hls_url(url)
    cmd = ["ffmpeg", "-y", "-i", url]

    if audio_only:
        cmd.extend(["-vn", "-c:a", "libmp3lame"])
    elif not is_hls:
        # For direct file URLs, try to use copy codec if formats match
        output_ext = Path(output_file).suffix.lower()
        input_ext = _get_file_extension(url)
        if output_ext == input_ext:
            # Same format, use copy to avoid re-encoding
            cmd.extend(["-c", "copy"])
    # For HLS or when formats differ for direct URLs, ffmpeg handles conversion automatically.

    cmd.append(output_file)

    status_message = (
        "Downloading media from HLS stream..."
        if is_hls
        else "Downloading media from URL..."
    )
    with status(status_message):
        subprocess.run(cmd, check=True, capture_output=True)


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

    with status("Converting video to audio..."):
        subprocess.run(cmd, check=True, capture_output=True)


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

    with status("Generating signature..."):
        subprocess.run(cmd, check=True, capture_output=True)
