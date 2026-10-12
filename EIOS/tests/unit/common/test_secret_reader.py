"""T064 (FR-017): secrets are read at call time through a source, rotatable, never printed."""

from __future__ import annotations

import logging
import sys
import types
from datetime import datetime, timedelta

import pytest

from eios.common.errors import BoundaryValidationError, EiosError
from eios.common.secret_reader import (
    DEFAULT_REFRESH_SECONDS,
    InMemorySecretSource,
    SecretManagerSource,
    SecretNotFoundError,
    SecretReader,
    SecretSource,
    SecretSourceError,
    SecretValue,
)
from tests.support.clock import FixedClock
from tests.support.secret_shapes import api_key, vcs_token

_NAME = "db-password"


class _Ticker:
    """Mutable test clock; the production reader only needs a callable returning a datetime."""

    def __init__(self) -> None:
        self._clock = FixedClock()

    def now(self) -> datetime:
        return self._clock.now()

    def advance(self, seconds: float) -> None:
        self._clock = self._clock.advanced(timedelta(seconds=seconds))


class _CountingSource:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = dict(values)
        self.calls = 0

    def fetch(self, name: str) -> str | None:
        self.calls += 1
        return self.values.get(name)


def _reader(source: SecretSource, refresh_seconds: float = 60.0) -> tuple[SecretReader, _Ticker]:
    ticker = _Ticker()
    return SecretReader(source, refresh_seconds=refresh_seconds, clock=ticker.now), ticker


def test_value_is_read_at_call_time_not_construction() -> None:
    source = _CountingSource({_NAME: vcs_token()})
    reader, _ = _reader(source)
    assert source.calls == 0
    assert reader.get(_NAME).reveal() == vcs_token()
    assert source.calls == 1


def test_memory_source_satisfies_the_protocol() -> None:
    source: SecretSource = InMemorySecretSource({_NAME: vcs_token()})
    assert source.fetch(_NAME) == vcs_token()
    assert source.fetch("absent") is None


def test_reads_inside_the_interval_use_the_cache() -> None:
    source = _CountingSource({_NAME: vcs_token()})
    reader, ticker = _reader(source, refresh_seconds=60)
    reader.get(_NAME)
    ticker.advance(59)
    reader.get(_NAME)
    assert source.calls == 1


def test_rotation_is_visible_on_the_next_read_after_the_interval() -> None:
    source = InMemorySecretSource({_NAME: vcs_token()})
    reader, ticker = _reader(source, refresh_seconds=60)
    assert reader.get(_NAME).reveal() == vcs_token()
    source.rotate(_NAME, api_key())
    ticker.advance(60)
    assert reader.get(_NAME).reveal() == api_key()


def test_zero_interval_reads_through_every_time() -> None:
    source = InMemorySecretSource({_NAME: vcs_token()})
    reader, _ = _reader(source, refresh_seconds=0)
    reader.get(_NAME)
    source.rotate(_NAME, api_key())
    assert reader.get(_NAME).reveal() == api_key()


def test_default_interval_is_positive() -> None:
    assert DEFAULT_REFRESH_SECONDS > 0


def test_value_never_appears_in_repr_str_or_format() -> None:
    secret = vcs_token()
    value = SecretValue(secret)
    reader, _ = _reader(InMemorySecretSource({_NAME: secret}))
    reader.get(_NAME)
    for rendered in (
        repr(value),
        str(value),
        f"{value}",
        f"{value!r}",
        "%s" % value,  # noqa: UP031
        repr(reader),
        str(reader),
        repr(InMemorySecretSource({_NAME: secret})),
    ):
        assert secret not in rendered


def test_value_never_appears_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    secret = vcs_token()
    reader, _ = _reader(InMemorySecretSource({_NAME: secret}))
    with caplog.at_level(logging.DEBUG):
        reader.get(_NAME)
    assert secret not in caplog.text
    assert all(secret not in record.getMessage() for record in caplog.records)


def test_missing_secret_names_only_the_secret() -> None:
    reader, _ = _reader(InMemorySecretSource({"other": vcs_token()}))
    with pytest.raises(SecretNotFoundError) as info:
        reader.get(_NAME)
    assert info.value.secret_name == _NAME
    assert _NAME in str(info.value)
    assert vcs_token() not in str(info.value)
    assert isinstance(info.value, EiosError)


def test_empty_value_counts_as_missing() -> None:
    reader, _ = _reader(InMemorySecretSource({_NAME: ""}))
    with pytest.raises(SecretNotFoundError):
        reader.get(_NAME)


def test_missing_secret_is_not_cached() -> None:
    source = InMemorySecretSource({})
    reader, _ = _reader(source)
    with pytest.raises(SecretNotFoundError):
        reader.get(_NAME)
    source.rotate(_NAME, vcs_token())
    assert reader.get(_NAME).reveal() == vcs_token()


@pytest.mark.parametrize("bad", ["", "has space", "../etc", "a/b", "x" * 256, "naïve"])
def test_invalid_secret_names_are_rejected_without_echo(bad: str) -> None:
    reader, _ = _reader(InMemorySecretSource({}))
    with pytest.raises(BoundaryValidationError) as info:
        reader.get(bad)
    assert bad == "" or bad not in str(info.value)


def test_negative_refresh_interval_is_rejected() -> None:
    with pytest.raises(BoundaryValidationError):
        SecretReader(InMemorySecretSource({}), refresh_seconds=-1)


def test_source_failure_is_wrapped_without_leaking_the_cause() -> None:
    class Failing:
        def fetch(self, name: str) -> str | None:
            raise RuntimeError("backend said " + vcs_token())

    reader, _ = _reader(Failing())
    with pytest.raises(SecretSourceError) as info:
        reader.get(_NAME)
    assert vcs_token() not in str(info.value)
    assert _NAME in str(info.value)
    assert info.value.__cause__ is None


def test_secret_value_equality_and_hash_follow_content() -> None:
    assert SecretValue("a") == SecretValue("a")
    assert SecretValue("a") != SecretValue("b")
    assert hash(SecretValue("a")) == hash(SecretValue("a"))


# --- Secret Manager source (client injected; the real library is never imported here) -------------


class _Payload:
    def __init__(self, data: bytes) -> None:
        self.data = data


class _Response:
    def __init__(self, data: bytes) -> None:
        self.payload = _Payload(data)


class _FakeClient:
    def __init__(self, data: bytes | Exception) -> None:
        self._data = data
        self.requests: list[dict[str, str]] = []

    def access_secret_version(self, request: dict[str, str]) -> _Response:
        self.requests.append(request)
        if isinstance(self._data, Exception):
            raise self._data
        return _Response(self._data)


def test_secret_manager_source_reads_the_latest_version() -> None:
    client = _FakeClient(vcs_token().encode("utf-8"))
    source = SecretManagerSource("proj-1", client=client)
    assert source.fetch(_NAME) == vcs_token()
    assert client.requests == [{"name": f"projects/proj-1/secrets/{_NAME}/versions/latest"}]


def test_secret_manager_not_found_maps_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    class NotFound(Exception):  # noqa: N818 - mirrors the third-party class name
        pass

    exceptions = types.ModuleType("google.api_core.exceptions")
    exceptions.NotFound = NotFound  # type: ignore[attr-defined]
    for name, module in (
        ("google", types.ModuleType("google")),
        ("google.api_core", types.ModuleType("google.api_core")),
        ("google.api_core.exceptions", exceptions),
    ):
        monkeypatch.setitem(sys.modules, name, module)
    source = SecretManagerSource("proj-1", client=_FakeClient(NotFound("gone")))
    assert source.fetch(_NAME) is None


def test_secret_manager_other_errors_are_wrapped() -> None:
    source = SecretManagerSource("proj-1", client=_FakeClient(RuntimeError(vcs_token())))
    with pytest.raises(SecretSourceError) as info:
        source.fetch(_NAME)
    assert vcs_token() not in str(info.value)
    assert _NAME in str(info.value)


def test_secret_manager_without_the_library_is_a_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "google.cloud.secretmanager", None)
    monkeypatch.setitem(sys.modules, "google.cloud", None)
    source = SecretManagerSource("proj-1")
    with pytest.raises(SecretSourceError):
        source.fetch(_NAME)


def test_secret_manager_rejects_a_bad_project_id() -> None:
    with pytest.raises(BoundaryValidationError):
        SecretManagerSource("bad project/../x")


def test_default_clock_works_without_injection() -> None:
    reader = SecretReader(InMemorySecretSource({_NAME: vcs_token()}))
    assert reader.get(_NAME).reveal() == vcs_token()


def test_secret_manager_builds_the_real_client_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(vcs_token().encode("utf-8"))
    module = types.ModuleType("google.cloud.secretmanager")
    module.SecretManagerServiceClient = lambda: client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google.cloud", types.ModuleType("google.cloud"))
    monkeypatch.setitem(sys.modules, "google.cloud.secretmanager", module)
    source = SecretManagerSource("proj-1")
    assert source.fetch(_NAME) == vcs_token()
    assert source.fetch(_NAME) == vcs_token()  # the client is reused


def test_secret_manager_client_creation_failure_is_typed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode() -> object:
        raise RuntimeError(vcs_token())

    module = types.ModuleType("google.cloud.secretmanager")
    module.SecretManagerServiceClient = explode  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google.cloud", types.ModuleType("google.cloud"))
    monkeypatch.setitem(sys.modules, "google.cloud.secretmanager", module)
    with pytest.raises(SecretSourceError) as info:
        SecretManagerSource("proj-1").fetch(_NAME)
    assert vcs_token() not in str(info.value)


def test_source_errors_pass_through_unchanged() -> None:
    class Failing:
        def fetch(self, name: str) -> str | None:
            raise SecretSourceError(name, "custom reason")

    reader, _ = _reader(Failing())
    with pytest.raises(SecretSourceError, match="custom reason"):
        reader.get(_NAME)


def test_reprs_name_the_source_but_not_values() -> None:
    assert "proj-1" in repr(SecretManagerSource("proj-1", client=_FakeClient(b"x")))
    reader, _ = _reader(InMemorySecretSource({}), refresh_seconds=5)
    assert "InMemorySecretSource" in repr(reader)
