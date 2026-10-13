"""VertexProvider talks to Gemini through google-genai on the global endpoint with real token counts."""

from unittest.mock import MagicMock

import pytest
from google.genai import errors

from eios.llm_gateway.providers.base import ProviderUnavailable
from eios.llm_gateway.providers.vertex import VertexProvider


def _provider(client: MagicMock) -> VertexProvider:
    provider = VertexProvider(project="example-project")
    provider._client = client
    return provider


def test_defaults_to_global_location() -> None:
    assert VertexProvider(project="example-project").location == "global"


def test_requires_a_project(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(ProviderUnavailable, match="GOOGLE_CLOUD_PROJECT"):
        VertexProvider()


def test_generate_returns_text_and_reported_token_counts() -> None:
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(
        text="hello", usage_metadata=MagicMock(prompt_token_count=11, candidates_token_count=3)
    )
    result = _provider(client).generate("prompt", "gemini-3.8-flash", {"max_output_tokens": 64})
    assert (result.content, result.tokens_in, result.tokens_out) == ("hello", 11, 3)
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-3.8-flash"
    assert kwargs["config"].temperature == 0.0
    assert kwargs["config"].max_output_tokens == 64


def test_api_errors_become_provider_unavailable() -> None:
    client = MagicMock()
    client.models.generate_content.side_effect = errors.APIError(
        404, {"error": {"message": "not found"}}
    )
    with pytest.raises(ProviderUnavailable):
        _provider(client).generate("prompt", "gemini-3.8-flash", {})


def test_missing_model_id_is_rejected() -> None:
    with pytest.raises(ProviderUnavailable, match="model_id"):
        _provider(MagicMock()).generate("prompt", None, {})


def test_empty_answer_is_invalid_not_silent() -> None:
    from eios.llm_gateway.providers.base import ProviderOutputInvalid

    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=None, usage_metadata=None)
    with pytest.raises(ProviderOutputInvalid):
        _provider(client).generate("prompt", "gemini-3.8-flash", {})
