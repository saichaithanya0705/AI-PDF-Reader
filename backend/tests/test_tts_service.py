import pytest

from backend.app import tts_service


def test_tts_provider_missing_configuration_raises_instead_of_silent_fallback(monkeypatch):
    monkeypatch.delenv("AZURE_TTS_KEY", raising=False)
    monkeypatch.setenv("TTS_PROVIDER", "azure")

    with pytest.raises(tts_service.TTSConfigurationError):
        tts_service.get_tts_provider()


def test_azure_provider_does_not_print_secret_prefix(monkeypatch, capsys):
    class FakeSpeechConfig:
        def __init__(self, subscription, region):
            self.subscription = subscription
            self.region = region
            self.speech_synthesis_voice_name = None

        def set_speech_synthesis_output_format(self, _format):
            return None

    monkeypatch.setattr(tts_service.speechsdk, "SpeechConfig", FakeSpeechConfig)
    monkeypatch.setenv("AZURE_TTS_KEY", "super-secret-tts-key")
    monkeypatch.setenv("AZURE_TTS_REGION", "eastasia")

    tts_service.AzureTTSProvider()

    captured = capsys.readouterr()
    assert "super-secret" not in captured.out
    assert "super-secret-tts-key" not in captured.out
