from pathlib import Path


LLM_PROVIDERS = Path(__file__).resolve().parents[1] / "app" / "llm_providers.py"


def test_llm_providers_do_not_return_placeholder_snippets_or_connections():
    source = LLM_PROVIDERS.read_text(encoding="utf-8")

    assert "Related information about the selected text." not in source
    assert "Common themes found across documents." not in source
    assert "Key insight from the document analysis." not in source
