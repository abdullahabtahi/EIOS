"""Live Gemini smoke test. Skipped unless a real project is configured (marker: requires_cloud)."""

import os

import pytest

from eios.llm_gateway.providers.vertex import VertexProvider

pytestmark = pytest.mark.requires_cloud


@pytest.mark.skipif(
    not os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("EIOS_TEST_CLOUD") != "1",
    reason="set GOOGLE_CLOUD_PROJECT and EIOS_TEST_CLOUD=1 to call Vertex AI",
)
def test_gemini_answers_on_the_global_endpoint() -> None:
    model = os.getenv("EIOS_GEMINI_MODEL", "gemini-3.8-flash")
    result = VertexProvider().generate(
        "Reply with the single word OK.", model, {"max_output_tokens": 256}
    )
    assert "ok" in result.content.lower()
    assert result.tokens_in > 0
