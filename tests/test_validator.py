"""
Tests for subtitle validation.

The distinction that matters is errors versus warnings: an error means ask the
model again, a warning means ship it and say something.
"""

import pytest

from sub_tools.config import Config
from sub_tools.subtitles.validator import (
    SubtitleValidationError,
    find_problems,
    parse_strict,
    validate_subtitles,
)

VALID = (
    "1\n00:00:01,000 --> 00:00:03,000\nFirst.\n\n"
    "2\n00:00:04,000 --> 00:00:06,000\nSecond.\n"
)


class TestMalformedFilesLenientParsersAccept:
    """
    The defects that motivated writing a strict parser.

    Each of these was accepted without complaint by pysrt, in one case turning
    337 cues of transcript into 101 without any error being raised.
    """

    def test_rejects_timestamp_missing_hours_field(self):
        content = (
            "1\n00:09:57,260 --> 10:00,420\nBefore.\n\n"
            "2\n10:06,660 --> 10:16,780\nAfter.\n"
        )
        errors, _ = find_problems(content)

        assert any("malformed timestamp" in e for e in errors)

    def test_rejects_colon_before_milliseconds(self):
        content = "1\n00:10:06:660 --> 00:10:16,780\nText.\n"
        errors, _ = find_problems(content)

        assert any("malformed timestamp" in e for e in errors)

    def test_rejects_timestamp_split_across_lines(self):
        content = "1\n00:00:17,200 -->\n00:00:21,800\nText.\n"
        errors, _ = find_problems(content)

        assert any("malformed timestamp" in e for e in errors)

    def test_rejects_timestamp_sitting_in_subtitle_text(self):
        content = (
            "1\n00:12:00,000 --> 00:12:01,500\n"
            "00:11:45,980 --> 00:11:51,540\nReal text.\n"
        )
        errors, _ = find_problems(content)

        assert any("where subtitle text belongs" in e for e in errors)

    def test_rejects_block_with_no_text(self):
        content = "1\n00:00:01,000 --> 00:00:03,000\n"
        errors, _ = find_problems(content)

        assert errors

    def test_rejects_missing_cue_number(self):
        content = "00:00:01,000 --> 00:00:03,000\nText.\nmore text\n"
        errors, _ = find_problems(content)

        assert any("cue number" in e for e in errors)


class TestStrictParser:
    """parse_strict is the only parser the pipeline trusts."""

    def test_returns_cues_for_valid_content(self):
        cues, errors = parse_strict(VALID)

        assert errors == []
        assert [c.text for c in cues] == ["First.", "Second."]
        assert cues[0].start == pytest.approx(1.0)

    def test_reports_empty_file(self):
        _, errors = parse_strict("   ")

        assert errors == ["file is empty"]


class TestErrors:
    """Conditions that make subtitles unusable."""

    def test_accepts_valid_subtitles(self):
        errors, warnings = find_problems(VALID)

        assert errors == []
        assert warnings == []

    def test_rejects_unparseable_content(self):
        errors, _ = find_problems("this is not a subtitle file")

        assert errors

    def test_rejects_cue_ending_before_it_starts(self):
        content = "1\n00:00:05,000 --> 00:00:02,000\nText.\n"
        errors, _ = find_problems(content)

        assert any("ends before it starts" in e for e in errors)

    def test_rejects_cues_that_run_backwards(self):
        content = (
            "1\n00:00:10,000 --> 00:00:12,000\nSecond.\n\n"
            "2\n00:00:01,000 --> 00:00:03,000\nFirst.\n"
        )
        errors, _ = find_problems(content)

        assert any("starts before" in e for e in errors)

    def test_rejects_cue_past_end_of_audio(self):
        content = "1\n00:00:01,000 --> 00:10:00,000\nText.\n"
        errors, _ = find_problems(content, duration=60.0)

        assert any("after the audio does" in e for e in errors)

    def test_rejects_subtitles_that_stop_early(self):
        # The Gemini-only Korean run ended 49s before the audio did.
        content = "1\n00:00:01,000 --> 00:00:03,000\nText.\n"
        errors, _ = find_problems(content, duration=600.0)

        assert any("before the audio ends" in e for e in errors)

    def test_rejects_translation_that_lost_a_meaningful_share(self):
        translated = "1\n00:00:01,000 --> 00:00:03,000\nOnly one.\n"
        errors, _ = find_problems(translated, reference=VALID)

        assert any("lost 1 of 2 subtitles" in e for e in errors)

    def test_tolerates_one_dropped_cue_in_a_long_translation(self):
        # Gemini routinely returns 410 of 411 cues. Rejecting that made every
        # retry fail identically instead of converging, so it warns instead.
        source = "".join(
            f"{i}\n00:{i // 60:02d}:{i % 60:02d},000 --> 00:{i // 60:02d}:{i % 60:02d},500\nLine {i}.\n\n"
            for i in range(1, 201)
        )
        translated = "".join(
            f"{i}\n00:{i // 60:02d}:{i % 60:02d},000 --> 00:{i // 60:02d}:{i % 60:02d},500\n번역 {i}.\n\n"
            for i in range(1, 200)
        )
        errors, warnings = find_problems(translated, reference=source)

        assert errors == []
        assert any("missing 1 of 200" in w for w in warnings)

    def test_accepts_translation_with_matching_cue_count(self):
        translated = (
            "1\n00:00:01,000 --> 00:00:03,000\n하나.\n\n"
            "2\n00:00:04,000 --> 00:00:06,000\n둘.\n"
        )
        errors, _ = find_problems(translated, reference=VALID)

        assert errors == []


class TestWarnings:
    """Unusual timing is reported, never a reason to retry."""

    def test_long_cue_warns_but_does_not_fail(self):
        content = "1\n00:00:00,000 --> 00:00:25,000\nA very long cue.\n"
        errors, warnings = find_problems(content, config=Config(max_valid_duration=20_000))

        assert errors == []
        assert any("longer than" in w for w in warnings)

    def test_large_gap_warns_but_does_not_fail(self):
        content = (
            "1\n00:00:01,000 --> 00:00:03,000\nBefore silence.\n\n"
            "2\n00:00:30,000 --> 00:00:32,000\nAfter silence.\n"
        )
        errors, warnings = find_problems(content, config=Config(inter_item_gap_threshold=6_000))

        assert errors == []
        assert any("gap" in w for w in warnings)


class TestValidateSubtitles:
    """The raising wrapper used as the pipeline's gate."""

    def test_raises_on_error(self):
        with pytest.raises(SubtitleValidationError):
            validate_subtitles("1\n00:00:05,000 --> 00:00:02,000\nText.\n")

    def test_returns_warnings_when_usable(self):
        content = "1\n00:00:00,000 --> 00:00:25,000\nLong.\n"
        warnings = validate_subtitles(content, config=Config(max_valid_duration=20_000))

        assert any("longer than" in w for w in warnings)
