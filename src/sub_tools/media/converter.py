import os
import subprocess


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
        print(f"File {output_file} already exists. Skipping download...")
        return

    print(f"Downloading {'audio' if audio_only else 'video'} from {hls_url}...")

    cmd = ["ffmpeg", "-y", "-i", hls_url]
    if audio_only:
        cmd.extend(["-vn", "-c:a", "libmp3lame"])
    cmd.append(output_file)

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
        print(f"Audio file {audio_file} already exists. Skipping conversion...")
        return

    print(f"Converting {video_file} to {audio_file}...")

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
        print(f"Skipping signature generation: Signature file {signature_file} already exists.")
        return
    
    try:
        subprocess.run("shazam", capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Skipping signature generation: Shazam CLI not available.")
        return

    print(f"Generating signature for {media_file}...")

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
