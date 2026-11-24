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


def test_azure_provider_synthesizes_headless_without_default_speaker_and_reports_cancellation(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    captured = {}

    class FakeSpeechConfig:
        def __init__(self, subscription, region):
            self.subscription = subscription
            self.region = region
            self.speech_synthesis_voice_name = None

        def set_speech_synthesis_output_format(self, _format):
            return None

    class FakeResult:
        def __init__(self, reason, cancellation_details=None, audio_data=b""):
            self.reason = reason
            self.cancellation_details = cancellation_details
            self.audio_data = audio_data

    class FakeSynthesizer:
        def __init__(self, speech_config=None, audio_config=None):
            captured["audio_config"] = audio_config

        def speak_text_async(self, _text):
            class _Future:
                def get(self_inner):
                    return FakeResult(
                        tts_service.speechsdk.ResultReason.Canceled,
                        cancellation_details=SimpleNamespace(
                            reason="Canceled",
                            error_details="401 AuthenticationFailure",
                        ),
                    )

            return _Future()

    fake_reasons = SimpleNamespace(SynthesizingAudioCompleted="completed", Canceled="canceled")
    monkeypatch.setattr(tts_service.speechsdk, "ResultReason", fake_reasons, raising=False)
    monkeypatch.setattr(tts_service.speechsdk, "SpeechConfig", FakeSpeechConfig)
    monkeypatch.setattr(tts_service.speechsdk, "SpeechSynthesizer", FakeSynthesizer, raising=False)
    monkeypatch.setenv("AZURE_TTS_KEY", "fake-key")
    monkeypatch.setenv("AZURE_TTS_REGION", "eastasia")

    provider = tts_service.AzureTTSProvider()

    with pytest.raises(Exception, match="401 AuthenticationFailure"):
        asyncio.run(provider.generate_audio("Hello world"))

    assert captured["audio_config"] is None
