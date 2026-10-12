"""T013: safe YAML loading and schema validation errors that name file and path."""

from __future__ import annotations

from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tests.support.repo_builder import build_repo
from tools.common.yaml_io import load_validated, load_yaml

_SCHEMA = {
    "type": "object",
    "required": ["gates"],
    "additionalProperties": False,
    "properties": {
        "gates": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "threshold"],
                "properties": {"id": {"type": "string"}, "threshold": {"type": "number"}},
            },
        }
    },
}


def _write(tmp_path: Path, text: str, name: str = "config/x.yaml") -> Path:
    build_repo(tmp_path, {name: text})
    return tmp_path / name


def test_load_yaml_returns_plain_data(tmp_path: Path) -> None:
    path = _write(tmp_path, "gates:\n  - id: g1\n    threshold: 0.5\n")
    assert load_yaml(path) == {"gates": [{"id": "g1", "threshold": 0.5}]}


def test_load_yaml_empty_file_is_none(tmp_path: Path) -> None:
    assert load_yaml(_write(tmp_path, "")) is None


def test_load_yaml_is_safe_and_rejects_python_object_tags(tmp_path: Path) -> None:
    path = _write(tmp_path, "x: !!python/object/apply:os.system ['echo pwned']\n")
    with pytest.raises(ConfigError) as info:
        load_yaml(path)
    assert str(path) in str(info.value)


def test_load_yaml_malformed_names_file_and_location(tmp_path: Path) -> None:
    path = _write(tmp_path, "a: [1, 2\nb: : :\n")
    with pytest.raises(ConfigError) as info:
        load_yaml(path)
    assert info.value.file == str(path)
    assert "line" in str(info.value)
    assert "Traceback" not in str(info.value)


def test_load_yaml_missing_file_is_a_config_error(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    with pytest.raises(ConfigError) as info:
        load_yaml(missing)
    assert str(missing) in str(info.value)


def test_load_yaml_non_utf8_is_a_config_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(ConfigError) as info:
        load_yaml(path)
    assert str(path) in str(info.value)


def test_load_validated_returns_data_when_valid(tmp_path: Path) -> None:
    path = _write(tmp_path, "gates:\n  - id: g1\n    threshold: 1\n")
    assert load_validated(path, _SCHEMA) == {"gates": [{"id": "g1", "threshold": 1}]}


def test_load_validated_names_file_and_path_of_violation(tmp_path: Path) -> None:
    path = _write(tmp_path, "gates:\n  - id: g1\n    threshold: high\n")
    with pytest.raises(ConfigError) as info:
        load_validated(path, _SCHEMA)
    assert info.value.file == str(path)
    assert info.value.path == "gates[0].threshold"
    assert str(path) in str(info.value)
    assert "gates[0].threshold" in str(info.value)


def test_load_validated_reports_every_violation(tmp_path: Path) -> None:
    path = _write(tmp_path, "gates:\n  - id: 7\n  - threshold: 1\nextra: 1\n")
    with pytest.raises(ConfigError) as info:
        load_validated(path, _SCHEMA)
    text = str(info.value)
    assert "gates[0].id" in text
    assert "gates[0]" in text
    assert "gates[1]" in text


def test_load_validated_root_violation_uses_root_marker(tmp_path: Path) -> None:
    path = _write(tmp_path, "- just\n- a list\n")
    with pytest.raises(ConfigError) as info:
        load_validated(path, _SCHEMA)
    assert info.value.path == "$"


def test_load_validated_propagates_load_failures_as_config_error(tmp_path: Path) -> None:
    path = _write(tmp_path, "a: [1, 2\n")
    with pytest.raises(ConfigError):
        load_validated(path, _SCHEMA)


def test_load_validated_invalid_schema_is_a_config_error(tmp_path: Path) -> None:
    path = _write(tmp_path, "gates: []\n")
    with pytest.raises(ConfigError) as info:
        load_validated(path, {"type": "not-a-type"})
    assert str(path) in str(info.value)
