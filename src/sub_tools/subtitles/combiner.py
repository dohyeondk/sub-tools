import os

import pysrt

from ..config import Config
from ..system.console import error, status
from ..system.directory import paths_with_offsets
from ..system.language import get_language_name


def combine_subtitles(
    language_codes: list[str],
    audio_segment_prefix: str,
    audio_segment_format: str,
    config: Config = Config(),
) -> None:
    """
    Combines subtitles for a list of languages.
    """
    with status("Combining subtitles..."):
        for language_code in language_codes:
            combine_subtitles_for_language(
                language_code,
                audio_segment_prefix,
                audio_segment_format,
                config,
            )


def combine_subtitles_for_language(
    language_code: str,
    audio_segment_prefix: str,
    audio_segment_format: str,
    config: Config,
) -> None:
    """
    Combines subtitles for a single language.
    """
    audio_segments_paths_with_offset = list(
        paths_with_offsets(audio_segment_prefix, audio_segment_format, config.directory)
    )
    audio_count = len(audio_segments_paths_with_offset)

    subtitles_paths_with_offsets = paths_with_offsets(
        language_code, "srt", config.directory
    )
    subtitles_count = len(subtitles_paths_with_offsets)

    if subtitles_count < audio_count:
        language = get_language_name(language_code)
        error(
            f"Skipping language {language} because there are not enough subtitles."
            f"Expected {audio_count}, found {subtitles_count}."
        )
        return

    subs = pysrt.SubRipFile()
    for path, offset in subtitles_paths_with_offsets:
        subtitle_path = os.path.join(config.directory, path)
        current_subs = pysrt.open(subtitle_path)
        subs += current_subs
    subs.clean_indexes()

    # Use custom output filename if provided, otherwise default to {language_code}.srt
    if config.output_file:
        filename, extension = os.path.splitext(config.output_file)
        output_filename = f"{filename}_{language_code}{extension}"
    else:
        output_filename = os.path.join("output", f"{language_code}.srt")

    subs.save(output_filename, encoding="utf-8")
