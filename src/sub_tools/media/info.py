from pydub import AudioSegment


def get_duration(path):
    audio = AudioSegment.from_file(path)
    return audio.duration_seconds
