"""T010: frozen strict models, typed boundary validation, no value echo."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eios.common.errors import BoundaryValidationError, ConfigError, EiosError, ToolError
from eios.common.validation import StrictModel, validate_at_boundary
from tests.support.secret_shapes import all_shapes


class _Inner(StrictModel):
    count: int


class _Sample(StrictModel):
    name: str
    inner: _Inner


def _valid() -> dict[str, object]:
    return {"name": "alpha", "inner": {"count": 3}}


def test_frozen_model_rejects_attribute_assignment() -> None:
    model = validate_at_boundary(_Sample, _valid())
    with pytest.raises(ValidationError):
        model.name = "beta"


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(BoundaryValidationError) as info:
        validate_at_boundary(_Sample, {**_valid(), "surprise": 1})
    assert "surprise" in info.value.field_paths


def test_valid_input_returns_model_and_does_not_mutate_input() -> None:
    data = _valid()
    snapshot = {"name": "alpha", "inner": {"count": 3}}
    model = validate_at_boundary(_Sample, data)
    assert model.inner.count == 3
    assert data == snapshot


def test_error_carries_nested_field_paths() -> None:
    with pytest.raises(BoundaryValidationError) as info:
        validate_at_boundary(_Sample, {"name": "alpha", "inner": {"count": "x"}})
    assert info.value.field_paths == ("inner.count",)
    assert "inner.count" in str(info.value)


def test_missing_field_is_reported() -> None:
    with pytest.raises(BoundaryValidationError) as info:
        validate_at_boundary(_Sample, {"name": "alpha"})
    assert info.value.field_paths == ("inner",)


@pytest.mark.parametrize("bad", [None, [], "text", 42])
def test_non_mapping_input_is_rejected_with_typed_error(bad: object) -> None:
    with pytest.raises(BoundaryValidationError):
        validate_at_boundary(_Sample, bad)


@pytest.mark.parametrize("shape_name", sorted(all_shapes()))
def test_secret_shaped_values_never_echoed(shape_name: str) -> None:
    secret = all_shapes()[shape_name]
    bad_inputs: list[object] = [
        {"name": secret, "inner": {"count": secret}},
        {**_valid(), secret: secret},
        {"name": 1, "inner": secret},
    ]
    for bad in bad_inputs:
        with pytest.raises(BoundaryValidationError) as info:
            validate_at_boundary(_Sample, bad)
        assert secret not in str(info.value)
        assert secret not in repr(info.value)
        assert secret not in info.value.message
        assert all(secret not in p for p in info.value.field_paths)


def test_ordinary_rejected_values_are_also_redacted() -> None:
    with pytest.raises(BoundaryValidationError) as info:
        validate_at_boundary(_Sample, {"name": "alpha", "inner": {"count": "plain-bad-value"}})
    assert "plain-bad-value" not in str(info.value)


def test_error_hierarchy_and_messages() -> None:
    assert issubclass(BoundaryValidationError, EiosError)
    assert issubclass(ConfigError, EiosError)
    assert issubclass(ToolError, EiosError)
    assert str(EiosError("boom")) == "boom"
    assert EiosError("boom").message == "boom"
    assert BoundaryValidationError("bad").field_paths == ()


def test_config_error_message_includes_file_and_path() -> None:
    err = ConfigError("config/x.yaml", "a.b", "must be positive")
    assert err.file == "config/x.yaml"
    assert err.path == "a.b"
    assert "config/x.yaml" in str(err)
    assert "a.b" in str(err)
    assert "must be positive" in str(err)
