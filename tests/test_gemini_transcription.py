from types import SimpleNamespace

from sub_tools.intelligence import gemini


def test_transcription_models_are_recognised_by_name():
    assert gemini.uses_transcription_api("gemini-3.5-transcribe") is True
    assert gemini.uses_transcription_api("gemini-3.5-transcribe-live") is True
    assert gemini.uses_transcription_api("gemini-3.8-flash") is False


def test_offsets_accept_numbers_and_protobuf_durations():
    assert gemini._offset_seconds(1.5) == 1.5
    assert gemini._offset_seconds("12.300s") == 12.3
    assert gemini._offset_seconds(None) is None
    assert gemini._offset_seconds("later") is None


def test_words_are_grouped_into_cues_at_sentence_ends():
    words = [
        ("This", 0.0, 0.3),
        ("first", 0.3, 0.6),
        ("sentence", 0.6, 1.1),
        ("is", 1.1, 1.2),
        ("long", 1.2, 1.5),
        ("enough.", 1.5, 2.0),
        ("So", 2.4, 2.6),
        ("is", 2.6, 2.7),
        ("the", 2.7, 2.8),
        ("second", 2.8, 3.2),
        ("one", 3.2, 3.5),
        ("here.", 3.5, 3.9),
    ]

    srt = gemini._words_to_srt(words)

    assert srt.startswith("1\n00:00:00,000 --> 00:00:02,000\n")
    assert "This first sentence is long enough." in srt
    assert "\n2\n00:00:02,400 --> 00:00:03,900\n" in srt
    assert "So is the second one here." in srt


def test_long_cues_wrap_over_two_lines():
    wrapped = gemini._wrap(
        "a line that is definitely longer than a single subtitle line allows"
    )
    lines = wrapped.split("\n")

    assert len(lines) == 2
    assert all(len(line) <= gemini.MAX_LINE_CHARACTERS for line in lines)


def test_word_timings_are_read_from_every_transcribed_part():
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            audio_transcription=SimpleNamespace(
                                words=[
                                    SimpleNamespace(
                                        word="second",
                                        start_offset="1.0s",
                                        end_offset="1.4s",
                                    )
                                ]
                            )
                        ),
                        SimpleNamespace(
                            audio_transcription=SimpleNamespace(
                                words=[
                                    SimpleNamespace(
                                        word=" first ",
                                        start_offset="0.0s",
                                        end_offset="0.5s",
                                    ),
                                    SimpleNamespace(
                                        word="",
                                        start_offset="0.6s",
                                        end_offset="0.7s",
                                    ),
                                ]
                            )
                        ),
                        SimpleNamespace(audio_transcription=None),
                    ]
                )
            )
        ]
    )

    assert gemini._transcribed_words(response) == [
        ("first", 0.0, 0.5),
        ("second", 1.0, 1.4),
    ]
