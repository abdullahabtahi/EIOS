"""T108: the replay key hashes prompt id, version, inputs and configuration identity."""

from __future__ import annotations

import re

import pytest

from eios.llm_gateway.replay_cache import replay_key

BASE: dict[str, object] = {
    "prompt_id": "smoke-echo",
    "prompt_version": "v1",
    "inputs": {"message": "hello"},
    "config_identity": "cfg-1",
}


def _key(**overrides: object) -> str:
    return replay_key(**{**BASE, **overrides})  # type: ignore[arg-type]


def test_identical_requests_produce_the_same_key() -> None:
    assert _key() == _key()
    assert _key(inputs={"message": "hello"}) == _key(inputs=dict(BASE["inputs"]))  # type: ignore[call-overload]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("prompt_id", "other-prompt"),
        ("prompt_version", "v2"),
        ("inputs", {"message": "goodbye"}),
        ("inputs", {"message": "hello", "extra": "x"}),
        ("inputs", {"other_name": "hello"}),
        ("config_identity", "cfg-2"),
    ],
)
def test_changing_any_one_component_changes_the_key(field: str, value: object) -> None:
    assert _key(**{field: value}) != _key()


def test_input_order_does_not_matter() -> None:
    assert _key(inputs={"a": "1", "b": "2"}) == _key(inputs={"b": "2", "a": "1"})


def test_component_boundaries_are_unambiguous() -> None:
    assert _key(prompt_id="ab", prompt_version="c") != _key(prompt_id="a", prompt_version="bc")
    assert _key(inputs={"a": "bc"}) != _key(inputs={"ab": "c"})


def test_key_is_a_hex_sha256_digest() -> None:
    assert re.fullmatch(r"[0-9a-f]{64}", _key())
