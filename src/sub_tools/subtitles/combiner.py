import pysrt

from dataclasses import dataclass
from sub_tools.system.directory import paths_with_offsets


@dataclass
class CombineConfig:
    directory: str = "tmp"


def combine_subtitles(language_codes: list[str], config: CombineConfig = CombineConfig()) -> None:
    """
    Combines subtitles for a list of languages.
    """
    print("Combining subtitles...")
    for language_code in language_codes:
        combine_subtitles_for_language(language_code, config)


def combine_subtitles_for_language(
    language_code: str,
    config: CombineConfig,
) -> None:
    """
    Combines subtitles for a single language.
    """
    subs = pysrt.SubRipFile()
    for path, offset in paths_with_offsets(language_code, "srt", f"./{config.directory}"):
        current_subs = pysrt.open(f"{config.directory}/{path}")
        subs += current_subs
    subs.clean_indexes()
    subs.save(f"{language_code}.srt", encoding="utf-8")
