import os
import subprocess

from ..system.console import warning, status


def hls_to_media(
    hls_url: str,
    output_file: str,
    audio_only: bool = False,
    overwrite: bool = False,
) -> None:
    """
    Downloads media from an HLS URL and saves it as video or audio.
    """
    if os.path.exists(output_file) and not overwrite:
        warning(f"File {output_file} already exists. Skipping download...")
        return

    cmd = ["ffmpeg", "-y", "-i", hls_url]
    if audio_only:
        cmd.extend(["-vn", "-c:a", "libmp3lame"])
    cmd.append(output_file)

    with status("Downloading media..."):
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
        "ffmpeg", "-y",
        "-i", video_file,
        "-vn",
        "-c:a", "libmp3lame",
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
        warning(f"Skipping signature generation: Signature file {signature_file} already exists.")
        return
    
    try:
        subprocess.run("shazam", capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        warning("Skipping signature generation: Shazam CLI not available.")
        return

    cmd = [
        "shazam",
        "signature",
        "--input", media_file,
        "--output", signature_file,
    ]

    with status("Generating signature..."):
        subprocess.run(cmd, check=True, capture_output=True)
