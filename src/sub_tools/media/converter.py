import os
import ffmpeg
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

    stream = ffmpeg.input(hls_url)
    if audio_only:
        stream = stream.audio
        stream = ffmpeg.output(stream, output_file, acodec="libmp3lame")
    else:
        stream = ffmpeg.output(stream, output_file)
    ffmpeg.run(
        stream, 
        overwrite_output=overwrite,
        capture_stdout=True,
        capture_stderr=True
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
        print(f"Audio file {audio_file} already exists. Skipping conversion...")
        return

    print(f"Converting {video_file} to {audio_file}...")

    stream = ffmpeg.input(video_file)
    stream = stream.audio
    stream = ffmpeg.output(stream, audio_file, acodec="libmp3lame")
    ffmpeg.run(
        stream, 
        overwrite_output=overwrite,
        capture_stdout=True,
        capture_stderr=True
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
