import os

import pysrt


def serialize_subtitles(
    content: str,
    language_code: str,
    offset: int = 0,
    directory: str = ".",
) -> None:
    """
    Serializes subtitles to a file.
    """
    subs = pysrt.from_string(content)
    subs.shift(milliseconds=offset)
    output_path = os.path.join(directory, f"{language_code}_{offset}.srt")
    subs.save(output_path, encoding="utf-8", eol="\r\n")
