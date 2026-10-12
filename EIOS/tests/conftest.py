"""Shared pytest configuration: skip tests that need external resources unless opted in."""

from __future__ import annotations

import os

import pytest

# marker name -> environment flag that opts in
_OPT_IN_FLAGS: dict[str, str] = {
    "requires_network": "EIOS_TEST_NETWORK",
    "requires_emulator": "EIOS_TEST_EMULATOR",
    "requires_cloud": "EIOS_TEST_CLOUD",
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        for marker, flag in _OPT_IN_FLAGS.items():
            if marker in item.keywords and os.environ.get(flag) != "1":
                item.add_marker(pytest.mark.skip(reason=f"{marker}: set {flag}=1 to run"))
