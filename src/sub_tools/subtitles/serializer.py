import pysrt


def serialize_subtitles(content, language_code, offset=0):
    subs = pysrt.from_string(content)
    subs.shift(milliseconds=offset)
    subs.save(f"{language_code}_{offset}.srt", encoding="utf-8", eol="\r\n")
