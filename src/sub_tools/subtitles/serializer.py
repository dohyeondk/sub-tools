import pysrt


def serialize_subtitles(
    segments: list,
    output_path: str,
) -> None:
    """
    Serializes WhisperX segments to an SRT file.

    Args:
        segments: List of WhisperX segment dictionaries with 'start', 'end', 'text' keys
        output_path: Path to save the SRT file
    """
    subs = pysrt.SubRipFile()

    for i, segment in enumerate(segments, start=1):
        start_ms = int(segment["start"] * 1000)
        end_ms = int(segment["end"] * 1000)
        text = segment["text"].strip()

        # Create SubRipItem
        item = pysrt.SubRipItem(
            index=i,
            start=pysrt.SubRipTime(milliseconds=start_ms),
            end=pysrt.SubRipTime(milliseconds=end_ms),
            text=text,
        )
        subs.append(item)

    subs.save(output_path, encoding="utf-8", eol="\r\n")
