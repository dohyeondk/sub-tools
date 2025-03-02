import os
import subprocess
import ffmpeg
from ..system.console import info, warning, error
from rich.progress import Progress


def hls_to_media(
    hls_url: str,
    output_file: str,
    overwrite: bool = False,
) -> None:
    """
    Downloads media from an HLS URL and saves it as video or audio.
    """
    if os.path.exists(output_file) and not overwrite:
        warning(f"File {output_file} already exists. Skipping download...")
        return

    probe = ffmpeg.probe(hls_url)
    total_duration = float(probe['format']['duration'])

    with Progress() as progress:
        task = progress.add_task("Downloading...", total=100)

        def on_progress(progress_data):
            if 'out_time_ms' in progress_data:
                time_ms = int(progress_data['out_time_ms'])
                current_time = time_ms / 1_000_000
                percent_complete = min(100, (current_time / total_duration * 100))
                progress.update(task, completed=percent_complete)

        try:
            ffmpeg.input(hls_url).output(output_file, c='copy').run(
                quiet=True,
                overwrite_output=True,
                progress=on_progress
            )
        except ffmpeg.Error as e:
            error(f"Error: {e.stderr.decode()}")
            exit(1)


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

    info(f"Converting {video_file} to {audio_file}...")

    subprocess.run(
        [
            "ffmpeg", "-y", 
            "-i", video_file, 
            "-vn", 
            "-c:a", "libmp3lame", 
            audio_file,
        ],
        check=True,
        capture_output=True,
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
        warning(f"Skipping signature generation: Signature file {signature_file} already exists.")
        return
    
    try:
        subprocess.run("shazam", capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        warning("Skipping signature generation: Shazam CLI not available.")
        return

    info(f"Generating signature for {media_file}...")

    subprocess.run(
        [
            "shazam",
            "signature",
            "--input", media_file,
            "--output", signature_file,
        ],
        check=True,
        capture_output=True,
    )
