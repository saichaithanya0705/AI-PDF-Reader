import verify_env


def test_environment_verifier_succeeds_with_required_hosted_configuration(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("NVIDIA_EMBEDDING_DIMENSION", "3")

    assert verify_env.main() == 0


def test_environment_verifier_fails_when_hosted_key_is_missing(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    assert verify_env.main() == 1
