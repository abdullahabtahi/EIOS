"""Unit tests for GeminiClientManager and Context Caching (T038)."""

import os
from unittest.mock import MagicMock, patch

from eios.conversation.client import GeminiClientManager


def test_client_manager_offline_mode():
    mgr = GeminiClientManager(offline_mode=True)
    assert mgr.get_client() is None
    assert mgr.ensure_context_cache("system instructions", "catalog schema") is None


def test_client_manager_online_mocked():
    with patch.dict(os.environ, {"EIOS_OFFLINE_REPLAY": "0"}):
        mgr = GeminiClientManager(offline_mode=False, project="test-proj", location="us-central1")
        mgr.offline_mode = False
        with patch("eios.conversation.client.genai.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value = mock_instance

            # 1. Client initialization
            client = mgr.get_client()
            assert client is not None
            mock_client_cls.assert_called_once_with(
                vertexai=True, project="test-proj", location="us-central1"
            )

            # 2. Context Caching
            mock_cache = MagicMock()
            mock_cache.name = "projects/test-proj/locations/us-central1/cachedContents/c123"
            mock_instance.caches.create.return_value = mock_cache

            cache_name = mgr.ensure_context_cache("instructions", "schema")
            assert cache_name == "projects/test-proj/locations/us-central1/cachedContents/c123"

            # Subsequent call returns cached name without calling create again
            cached_again = mgr.ensure_context_cache("instructions", "schema")
            assert cached_again == cache_name
            assert mock_instance.caches.create.call_count == 1


def test_client_manager_exception_fallback():
    with patch.dict(os.environ, {"EIOS_OFFLINE_REPLAY": "0"}):
        mgr = GeminiClientManager(offline_mode=False)
        mgr.offline_mode = False
        with patch("eios.conversation.client.genai.Client", side_effect=RuntimeError("Auth error")):
            client = mgr.get_client()
            assert client is None
            assert mgr.offline_mode is True
