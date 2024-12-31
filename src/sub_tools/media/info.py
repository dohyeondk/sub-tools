from pydub import AudioSegment


def get_duration(path):
    """
    Returns the duration of an audio file in seconds.
    """
    audio = AudioSegment.from_file(path)
    return audio.duration_seconds
