import pysrt

from dataclasses import dataclass
from sub_tools.system.directory import paths_with_offsets
from sub_tools.system.language import get_language_name


@dataclass
class CombineConfig:
    directory: str = "tmp"


def combine_subtitles(
    language_codes: list[str],
    audio_segment_prefix: str,
    audio_segment_format: str,
    config: CombineConfig = CombineConfig(),
) -> None:
    """
    Combines subtitles for a list of languages.
    """
    print("Combining subtitles...")
    for language_code in language_codes:
        combine_subtitles_for_language(language_code, audio_segment_prefix, audio_segment_format, config)


def combine_subtitles_for_language(
    language_code: str,
    audio_segment_prefix: str,
    audio_segment_format: str,
    config: CombineConfig,
) -> None:
    """
    Combines subtitles for a single language.
    """
    audio_segments_paths_with_offset = list(paths_with_offsets(audio_segment_prefix, audio_segment_format, f"./{config.directory}"))
    audio_count = len(audio_segments_paths_with_offset)

    subtitles_paths_with_offsets = paths_with_offsets(language_code, "srt", f"./{config.directory}")
    subtitles_count = len(subtitles_paths_with_offsets)

    if subtitles_count < audio_count:
        language = get_language_name(language_code)
        print(
            f"Skipping language {language} because there are not enough subtitles.",
            f"Expected {audio_count}, found {subtitles_count}."
        )
        return
    
    subs = pysrt.SubRipFile()
    for path, offset in subtitles_paths_with_offsets:
        current_subs = pysrt.open(f"{config.directory}/{path}")
        subs += current_subs
    subs.clean_indexes()
    subs.save(f"{language_code}.srt", encoding="utf-8")
