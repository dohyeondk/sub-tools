"""
Tests for SRT repair.

Every case here is a shape a model actually returned, not an invented one.
"""

import pytest

from sub_tools.subtitles.repair import repair_subtitles
from sub_tools.subtitles.validator import find_problems, parse_strict


def cues(content):
    """
    Parse repaired content, which must always be strictly valid SRT.

    Deliberately strict: a lenient parser would accept the very output these
    tests exist to catch.
    """
    parsed, errors = parse_strict(content)
    assert not errors, f"repair produced invalid SRT: {errors}"
    return parsed


class TestWellFormedInput:
    """A correct file must survive untouched."""

    def test_leaves_valid_subtitles_alone(self):
        content = (
            "1\n00:00:01,000 --> 00:00:03,000\nHello.\n\n"
            "2\n00:00:04,000 --> 00:00:06,000\nGoodbye.\n"
        )
        repaired, notes = repair_subtitles(content)

        assert notes == []
        assert len(cues(repaired)) == 2
        assert cues(repaired)[1].text == "Goodbye."


class TestTimestampSyntax:
    """Models drift out of HH:MM:SS,mmm in several distinct ways."""

    def test_supplies_missing_hours_field(self):
        # Seen after ~10 minutes of audio: "11:45,980" meaning 00:11:45,980.
        content = "1\n11:45,980 --> 11:51,540\nText.\n"
        repaired, notes = repair_subtitles(content)

        assert cues(repaired)[0].start == pytest.approx(705.98)
        assert any("normalized" in note for note in notes)

    def test_accepts_colon_before_milliseconds(self):
        content = "1\n00:10:06:660 --> 00:10:16,780\nText.\n"
        repaired, _ = repair_subtitles(content)

        assert cues(repaired)[0].start == pytest.approx(606.66)

    def test_rejoins_timestamp_split_across_lines(self):
        content = "1\n00:00:17,200 -->\n00:00:21,800\nText.\n"
        repaired, notes = repair_subtitles(content)

        assert len(cues(repaired)) == 1
        assert cues(repaired)[0].end == pytest.approx(21.8)
        assert any("rejoined" in note for note in notes)

    def test_strips_markdown_code_fences(self):
        content = "```srt\n1\n00:00:01,000 --> 00:00:02,000\nText.\n```"
        repaired, notes = repair_subtitles(content)

        assert len(cues(repaired)) == 1
        assert any("fence" in note for note in notes)

    def test_inserts_missing_blank_lines_between_cues(self):
        content = (
            "1\n00:00:01,000 --> 00:00:02,000\nFirst.\n"
            "2\n00:00:03,000 --> 00:00:04,000\nSecond.\n"
        )
        repaired, notes = repair_subtitles(content)

        assert len(cues(repaired)) == 2
        assert any("blank line" in note for note in notes)


class TestStructuralDamage:
    """Damage that changes which timestamp belongs to which line."""

    def test_recovers_timestamp_demoted_into_text(self):
        # A junk cue emitted just before a real one leaves the real timestamp
        # sitting as the first line of text, where it would render on screen.
        content = (
            "1\n00:12:00,000 --> 00:12:01,500\n"
            "00:11:45,980 --> 00:11:51,540\nReal text.\n"
        )
        repaired, notes = repair_subtitles(content)

        result = cues(repaired)
        assert len(result) == 1
        assert result[0].start == pytest.approx(705.98)
        assert result[0].text == "Real text."
        assert any("demoted" in note for note in notes)

    def test_drops_zero_length_cue(self):
        content = (
            "1\n00:12:00,000 --> 00:12:00,000\nJunk.\n\n"
            "2\n00:00:01,000 --> 00:00:03,000\nKeep.\n"
        )
        repaired, _ = repair_subtitles(content)

        assert [c.text for c in cues(repaired)] == ["Keep."]

    def test_reorders_out_of_sequence_cues(self):
        content = (
            "1\n00:00:10,000 --> 00:00:12,000\nSecond.\n\n"
            "2\n00:00:01,000 --> 00:00:03,000\nFirst.\n"
        )
        repaired, notes = repair_subtitles(content)

        assert [c.text for c in cues(repaired)] == ["First.", "Second."]
        assert any("reordered" in note for note in notes)

    def test_renumbers_sequentially(self):
        content = (
            "7\n00:00:01,000 --> 00:00:02,000\nA.\n\n"
            "9\n00:00:03,000 --> 00:00:04,000\nB.\n"
        )
        repaired, _ = repair_subtitles(content)

        assert [c.index for c in cues(repaired)] == [1, 2]


class TestAudioBounds:
    """Timestamps outside the recording cannot be right."""

    def test_leaves_cue_beyond_end_for_validation(self):
        # "10:00:42,420" parses as ten hours on a 33-minute recording.
        content = (
            "1\n00:00:01,000 --> 00:00:03,000\nFirst.\n\n"
            "2\n10:00:42,420 --> 10:00:46,000\nSecond.\n"
        )
        repaired, notes = repair_subtitles(content, duration=1964.0)

        result = cues(repaired)
        errors, _ = find_problems(repaired, duration=1964.0)
        assert len(result) == 2
        assert notes == []
        assert any("after the audio does" in error for error in errors)

    def test_leaves_backwards_timestamp_for_validation(self):
        content = "1\n00:19:22,456 --> 00:19:20,000\nText.\n"
        repaired, _ = repair_subtitles(content)

        cue = cues(repaired)[0]
        errors, _ = find_problems(repaired)
        assert cue.end < cue.start
        assert any("ends before it starts" in error for error in errors)

    def test_keeps_all_cues_when_the_tail_runs_past_audio(self):
        # Clamping a tail cue to the duration can turn later cues into
        # zero-length entries and silently remove the end of a transcription.
        content = (
            "1\n00:00:09,800 --> 00:00:11,000\nFinal words.\n\n"
            "2\n00:00:11,000 --> 00:00:13,000\nMore final words.\n"
        )
        repaired, _ = repair_subtitles(content, duration=10.0)

        result = cues(repaired)
        errors, _ = find_problems(repaired, duration=10.0)
        assert len(result) == 2
        assert [cue.text for cue in result] == ["Final words.", "More final words."]
        assert any("after the audio does" in error for error in errors)


class TestTranslationReference:
    """A translation must not move the timings it was given."""

    SOURCE = (
        "1\n00:00:01,000 --> 00:00:03,000\nOne.\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\nTwo.\n"
    )

    def test_restores_drifted_timestamps_from_source(self):
        # Observed drift: a start time snapped to a round minute.
        translated = (
            "1\n00:00:02,000 --> 00:00:03,000\n하나.\n\n"
            "2\n00:00:04,000 --> 00:00:06,000\n둘.\n"
        )
        repaired, notes = repair_subtitles(translated, reference=self.SOURCE)

        result = cues(repaired)
        assert result[0].start == pytest.approx(1.0)
        assert result[0].text == "하나."
        assert any("restored" in note for note in notes)

    def test_aligns_by_timestamp_when_a_cue_was_dropped(self):
        # Models drop the occasional cue from a long file. Matching on start
        # times still corrects the drift in the cues that did come back, which
        # a strict cue-for-cue mapping could not do.
        translated = "1\n00:00:04,200 --> 00:00:06,000\n둘.\n"
        repaired, notes = repair_subtitles(translated, reference=self.SOURCE)

        result = cues(repaired)
        assert len(result) == 1
        assert result[0].start == pytest.approx(4.0)
        assert result[0].text == "둘."
        assert any("restored" in note for note in notes)
