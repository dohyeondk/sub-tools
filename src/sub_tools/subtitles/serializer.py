import pysrt


def serialize_subtitles(
    content: str,
    language_code: str,
    offset: int = 0,
) -> None:
    """
    Serializes subtitles to a file.
    """
    subs = pysrt.from_string(content)
    subs.shift(milliseconds=offset)
    subs.save(f"{language_code}_{offset}.srt", encoding="utf-8", eol="\r\n")
