import pysrt

from sub_tools.system.directory import paths_with_offsets


def combine_subtitles(language_codes):
    for language_code in language_codes:
        combine_subtitles_for_language(language_code)


def combine_subtitles_for_language(language_code):
    subs = pysrt.SubRipFile()
    for path, offset in paths_with_offsets(language_code, "srt"):
        current_subs = pysrt.open(path)
        subs += current_subs
    subs.clean_indexes()
    subs.save(f"{language_code}.srt", encoding="utf-8")
