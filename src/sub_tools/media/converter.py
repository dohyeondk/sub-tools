import os
import subprocess


def hls_to_video(
    hls_url: str,
    video_file: str,
    overwrite: bool = False,
) -> None:
    """
    Downloads a video from an HLS URL and saves it to a file.
    """
    if os.path.exists(video_file) and not overwrite:
        print(f"Video file {video_file} already exists. Skipping conversion...")
        return

    print(f"Downloading video from {hls_url}...")

    # Download video from the HLS URL
    subprocess.run([
        "ffmpeg", "-y",
        "-i", hls_url,
        video_file
    ], check=True, capture_output=True)


def video_to_audio(
    video_file: str,
    audio_file: str,
    overwrite: bool = False,
) -> None:
    """
    Converts a video file to an audio file using ffmpeg.
    """
    if os.path.exists(audio_file) and not overwrite:
        print(f"Audio file {audio_file} already exists. Skipping conversion...")
        return
    
    print(f"Converting {video_file} to {audio_file}...")

    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_file,
        "-vn",
        "-c:a", "libmp3lame",
        audio_file
    ], check=True, capture_output=True)


def media_to_signature(
    media_file: str,
    signature_file: str,
    overwrite: bool = False,
) -> None:
    """
    Generates a signature for the media file using the shazam CLI.
    """
    if os.path.exists(signature_file) and not overwrite:
        print(f"Signature file {signature_file} already exists. Skipping conversion...")
        return

    print(f"Generating signature for {media_file}...")

    subprocess.run([
        "shazam", "signature",
        "--input", media_file,
        "--output", signature_file,
    ], check=True, capture_output=True)
