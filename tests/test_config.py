"""
Provider selection follows from the model name alone.
"""

from sub_tools.config import Config


class TestProviderInference:
    def test_gemini_models_use_gemini(self):
        assert Config(model="gemini-3.7-flash").provider == "gemini"

    def test_gpt_models_use_openai(self):
        assert Config(model="gpt-5.6-luna").provider == "openai"

    def test_case_is_ignored(self):
        assert Config(model="GPT-5.6-Luna").provider == "openai"


class TestOpenAIAudioRouting:
    def test_text_models_route_audio_requests_to_the_audio_model(self, monkeypatch):
        from sub_tools.config import config
        from sub_tools.intelligence import openai as provider

        monkeypatch.setattr(config, "model", "gpt-5.6-luna")
        monkeypatch.setattr(config, "audio_model", None)
        assert provider.accepts_audio() is False
        assert provider.generation_model(with_audio=True) == "whisper-1"
        assert provider.generation_model(with_audio=False) == "gpt-5.6-luna"
        assert provider.uses_transcription_api("whisper-1") is True
        assert provider.uses_transcription_api("gpt-audio-1.5") is False

    def test_audio_models_hear_the_audio_themselves(self, monkeypatch):
        from sub_tools.config import config
        from sub_tools.intelligence import openai as provider

        monkeypatch.setattr(config, "model", "gpt-audio-1.5")
        assert provider.accepts_audio() is True
        assert provider.generation_model(with_audio=True) == "gpt-audio-1.5"

    def test_audio_model_override_is_respected(self, monkeypatch):
        from sub_tools.config import config
        from sub_tools.intelligence import openai as provider

        monkeypatch.setattr(config, "model", "gpt-5.6-luna")
        monkeypatch.setattr(config, "audio_model", "gpt-audio-mini")
        assert provider.generation_model(with_audio=True) == "gpt-audio-mini"


class TestApiKeySelection:
    def test_gemini_key_is_used_for_gemini_models(self):
        config = Config(model="gemini-3.7-flash", gemini_api_key="g", openai_api_key="o")
        assert config.api_key == "g"

    def test_openai_key_is_used_for_openai_models(self):
        config = Config(model="gpt-5.6-luna", gemini_api_key="g", openai_api_key="o")
        assert config.api_key == "o"
