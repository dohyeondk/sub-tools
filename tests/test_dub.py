import asyncio
import importlib
import sys
import wave
from copy import deepcopy
from dataclasses import fields
from types import SimpleNamespace

import pytest

from sub_tools.config import Config, config
from sub_tools.intelligence import gemini
from sub_tools.media import converter
from sub_tools.subtitles.validator import Cue

VALID_SPANISH_SRT = """1
00:00:00,000 --> 00:00:01,000
Hola mundo.

2
00:00:01,000 --> 00:00:02,000
¿Cómo estás?
"""


@pytest.fixture(autouse=True)
def restore_config():
    original = {
        field.name: deepcopy(getattr(config, field.name)) for field in fields(Config)
    }
    yield
    for name, value in original.items():
        setattr(config, name, value)


def test_tts_request_uses_audio_modality_and_configured_voice(monkeypatch):
    pcm = b"\x01\x00\x02\x00"
    captured = {}
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            inline_data=SimpleNamespace(
                                data=pcm,
                                mime_type="audio/L16;codec=pcm;rate=24000",
                            )
                        )
                    ]
                )
            )
        ]
    )

    class Models:
        async def generate_content(self, **kwargs):
            captured.update(kwargs)
            return response

    client = SimpleNamespace(aio=SimpleNamespace(models=Models()))
    monkeypatch.setattr(gemini.genai, "Client", lambda api_key: client)
    config.gemini_api_key = "test-key"
    config.gemini_tts_model = "gemini-3.1-flash-tts-preview"
    config.gemini_tts_voice = "Puck"

    audio, mime_type = asyncio.run(gemini._call_tts_api("Hola mundo."))

    assert audio == pcm
    assert mime_type == "audio/L16;codec=pcm;rate=24000"
    assert captured["model"] == "gemini-3.1-flash-tts-preview"
    assert captured["contents"] == "Hola mundo."
    assert captured["config"].response_modalities == ["AUDIO"]
    voice = captured["config"].speech_config.voice_config.prebuilt_voice_config
    assert voice.voice_name == "Puck"


def test_generates_wav_from_translated_subtitle_text(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "es.srt").write_text(VALID_SPANISH_SRT, encoding="utf-8")
    captured = {}

    async def fake_call_tts_api(text):
        captured["text"] = text
        return b"\x01\x00\x02\x00", "audio/L16;codec=pcm;rate=16000"

    monkeypatch.setattr(gemini, "_call_tts_api", fake_call_tts_api)
    monkeypatch.setattr(gemini, "audio_duration", lambda path: 1.5)
    monkeypatch.setattr(
        gemini,
        "_fit_pcm_duration",
        lambda pcm, sample_rate, duration: (
            b"\x01\x00" * round(duration * gemini.PCM_SAMPLE_RATE)
        ),
    )
    config.audio_file = "audio.mp3"

    asyncio.run(gemini._generate_dub_language("es", lambda: None))

    assert "Hola mundo." in captured["text"]
    assert "¿Cómo estás?" in captured["text"]
    assert "00:00:00,000" not in captured["text"]
    with wave.open(str(tmp_path / "es.wav"), "rb") as wav_file:
        assert wav_file.getframerate() == 24000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.readframes(2) == b"\x01\x00\x01\x00"
        assert wav_file.getnframes() == 36000


def test_dub_groups_preserve_long_gaps_and_limit_drift():
    config.dub_chunk_duration = 60
    config.dub_gap_threshold = 2
    cues = [
        Cue(index=1, start=0, end=10, text="one"),
        Cue(index=2, start=10, end=20, text="two"),
        Cue(index=3, start=23, end=30, text="three"),
        Cue(index=4, start=31, end=95, text="four"),
    ]

    groups = gemini._dub_groups(cues)

    assert [[cue.index for cue in group] for group in groups] == [
        [1, 2],
        [3],
        [4],
    ]


def test_audio_duration_falls_back_to_ffmpeg(monkeypatch):
    def fake_run(cmd, **kwargs):
        if cmd[0] == "ffprobe":
            raise FileNotFoundError
        return SimpleNamespace(stderr="Duration: 00:33:47.62, start: 0.011")

    monkeypatch.setattr(converter.subprocess, "run", fake_run)

    assert converter.audio_duration("audio.mp3") == pytest.approx(2027.62)


def test_audio_response_must_contain_audio():
    response = SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=[]))]
    )

    with pytest.raises(RuntimeError, match="contained no audio"):
        gemini._audio_response(response)


def test_tts_retries_transient_internal_server_errors(monkeypatch):
    calls = 0
    response = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            inline_data=SimpleNamespace(
                                data=b"\x01\x00",
                                mime_type="audio/L16;rate=24000",
                            )
                        )
                    ]
                )
            )
        ]
    )

    class Models:
        async def generate_content(self, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise gemini.google_exceptions.InternalServerError("temporary")
            return response

    async def no_sleep(delay):
        return None

    client = SimpleNamespace(aio=SimpleNamespace(models=Models()))
    monkeypatch.setattr(gemini.genai, "Client", lambda api_key: client)
    monkeypatch.setattr(gemini.asyncio, "sleep", no_sleep)
    config.retry = 2

    audio, _ = asyncio.run(gemini._call_tts_api("Hola mundo."))

    assert audio == b"\x01\x00"
    assert calls == 2


def test_main_wires_dub_task(monkeypatch, tmp_path):
    main_module = importlib.import_module("sub_tools.main")
    calls = []
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sub-tools",
            "--tasks",
            "dub",
            "--gemini-api-key",
            "test-key",
            "--output",
            str(tmp_path),
            "--dub-chunk-duration",
            "30",
            "--dub-gap-threshold",
            "1.5",
        ],
    )
    monkeypatch.setattr(main_module, "ensure_output_directory", lambda path: None)
    monkeypatch.setattr(main_module, "header", lambda title: None)
    monkeypatch.setattr(
        main_module,
        "dub",
        lambda: calls.append(
            ("dub", config.dub_chunk_duration, config.dub_gap_threshold)
        ),
    )

    main_module.main()

    assert calls == [("dub", 30, 1.5)]


def test_dub_remains_opt_in():
    assert "dub" not in Config().tasks
