"""T184 (FR-036): correlation identifiers are opaque, validated, isolated per task."""

from __future__ import annotations

import asyncio
import re

import pytest

from eios.common import correlation
from eios.common.correlation import (
    CORRELATION_HEADER,
    MAX_ID_LENGTH,
    MissingCorrelationError,
    correlation_scope,
    current_id,
    is_valid_correlation_id,
    new_correlation_id,
    outbound_headers,
    resolve_inbound_id,
)

_INVALID = (
    "",
    "A" * (MAX_ID_LENGTH + 1),
    "has space",
    "line\nbreak",
    "trailing-newline\n",
    "tab\there",
    "nul\x00byte",
    "escape\x1b[31m",
    "under_score",
    "١٢٣",
    "emoji-\U0001f600",
    'quote"injection',
)


def test_new_ids_are_valid_and_unique() -> None:
    ids = {new_correlation_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(is_valid_correlation_id(i) for i in ids)


def test_new_id_embeds_no_host_or_personal_data() -> None:
    import getpass
    import platform

    value = new_correlation_id().lower()
    assert platform.node().lower() not in value
    assert getpass.getuser().lower() not in value
    assert re.fullmatch(r"[0-9a-f-]+", value)


@pytest.mark.parametrize("value", ["abc", "A-1-b", "0", "x" * MAX_ID_LENGTH, "a-b-c-d"])
def test_valid_inbound_ids_are_preserved(value: str) -> None:
    assert is_valid_correlation_id(value)
    assert resolve_inbound_id(value) == value


@pytest.mark.parametrize("value", _INVALID)
def test_invalid_inbound_ids_are_replaced_and_never_reflected(value: str) -> None:
    assert not is_valid_correlation_id(value)
    replaced = resolve_inbound_id(value)
    assert replaced != value
    assert is_valid_correlation_id(replaced)


def test_absent_and_non_string_inbound_ids_are_replaced() -> None:
    assert is_valid_correlation_id(resolve_inbound_id(None))
    assert not is_valid_correlation_id(None)
    assert not is_valid_correlation_id(123)


def test_header_name_is_a_single_constant() -> None:
    assert CORRELATION_HEADER == "X-Correlation-ID"


def test_current_id_is_none_outside_a_scope() -> None:
    assert current_id() is None


def test_scope_sets_and_restores_the_id() -> None:
    with correlation_scope("outer"):
        assert current_id() == "outer"
        with correlation_scope("inner"):
            assert current_id() == "inner"
        assert current_id() == "outer"
    assert current_id() is None


def test_scope_restores_after_an_exception() -> None:
    with pytest.raises(RuntimeError), correlation_scope("boom"):
        raise RuntimeError("x")
    assert current_id() is None


def test_scope_rejects_an_invalid_id() -> None:
    with pytest.raises(ValueError, match="correlation"), correlation_scope("bad id"):
        pass


def test_concurrent_tasks_never_see_each_others_id() -> None:
    async def worker(own: str, delay: float) -> str | None:
        with correlation_scope(own):
            await asyncio.sleep(delay)
            return current_id()

    async def run() -> list[str | None]:
        return list(
            await asyncio.gather(
                asyncio.create_task(worker("task-a", 0.02)),
                asyncio.create_task(worker("task-b", 0.0)),
                asyncio.create_task(worker("task-c", 0.01)),
            )
        )

    assert asyncio.run(run()) == ["task-a", "task-b", "task-c"]


def test_outbound_headers_add_the_current_id_without_mutating_input() -> None:
    original = {"Accept": "application/json"}
    with correlation_scope("abc-1"):
        out = outbound_headers(original)
    assert out == {"Accept": "application/json", CORRELATION_HEADER: "abc-1"}
    assert original == {"Accept": "application/json"}
    assert out is not original


def test_outbound_headers_without_input_returns_only_the_header() -> None:
    with correlation_scope("abc-2"):
        assert outbound_headers() == {CORRELATION_HEADER: "abc-2"}


def test_outbound_headers_without_a_current_id_is_an_explicit_error() -> None:
    with pytest.raises(MissingCorrelationError):
        outbound_headers()


def test_module_exposes_immutable_public_values_only() -> None:
    allowed = (str, int, re.Pattern, tuple, frozenset)
    for name in dir(correlation):
        if name.startswith("_") or name == "annotations":
            continue
        value = getattr(correlation, name)
        if callable(value) or isinstance(value, type(correlation)):
            continue
        assert isinstance(value, allowed), f"{name} is mutable: {type(value)}"
