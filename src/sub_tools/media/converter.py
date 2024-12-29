import os
import subprocess


def hls_to_video(hls_url, video_file, overwrite=False):
    if os.path.exists(video_file) and not overwrite:
        print(f"Video file {video_file} already exists. Skipping conversion...")
        return

    # TODO: validate HLS URL

    # Download video from the HLS URL
    subprocess.run([
        "ffmpeg", "-y",
        "-i", hls_url,
        video_file
    ], check=True)


def video_to_audio(video_file, audio_file, overwrite=False):
    if os.path.exists(audio_file) and not overwrite:
        print(f"Audio file {audio_file} already exists. Skipping conversion...")
        return

    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_file,
        "-vn",
        "-c:a", "libmp3lame",
        audio_file
    ], check=True)


def media_to_signature(media_file, signature_file, overwrite=False):
    if os.path.exists(signature_file) and not overwrite:
        print(f"Signature file {signature_file} already exists. Skipping conversion...")
        return

    subprocess.run([
        "shazam", "signature",
        "--input", media_file,
        "output", signature_file,
    ], check=True)