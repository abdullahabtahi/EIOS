"""Runtime code must not read from specs/, and the schema copies must not drift.

The authoring source of the contracts is the planning tree next to this repository
(``../specs``). It is not part of the pushed repository, so the drift checks run only when it
is present; the copies themselves are always validated.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, validators

REPO = Path(__file__).resolve().parents[2]
SOURCE_DIRS = [
    REPO.parent / "specs" / "001-platform-foundations" / "contracts",
    REPO.parent / "specs" / "002-synthetic-foundry" / "contracts",
    REPO.parent / "specs" / "003-contracts-ingestion" / "contracts",
    REPO.parent / "specs" / "018-genai-conversational-agent" / "contracts",
]
COPY_DIR = REPO / "schemas"

_sources_map = {p.name: p for sdir in SOURCE_DIRS for p in sdir.glob("*.schema.json")}
SOURCES = sorted(_sources_map.values())
COPIES = sorted(COPY_DIR.glob("*.schema.json"))
needs_sources = pytest.mark.skipif(not SOURCES, reason="planning tree (../specs) not present")


def test_copies_exist() -> None:
    assert COPIES, f"no *.schema.json found under {COPY_DIR}"


@pytest.mark.parametrize("source", SOURCES, ids=lambda p: p.name)
def test_copy_is_byte_identical(source: Path) -> None:
    copy = COPY_DIR / source.name
    assert copy.is_file(), f"missing schema copy: {copy.relative_to(REPO)}"
    assert copy.read_bytes() == source.read_bytes()


@pytest.mark.parametrize("copy", COPIES, ids=lambda p: p.name)
def test_copy_is_a_valid_json_schema(copy: Path) -> None:
    schema = json.loads(copy.read_text(encoding="utf-8"))
    validator_class = validators.validator_for(schema, default=Draft202012Validator)
    validator_class.check_schema(schema)


@needs_sources
def test_no_unexpected_schemas_in_copy_dir() -> None:
    expected = {p.name for p in SOURCES}
    actual = {p.name for p in COPIES}
    assert actual == expected, f"schemas/ differs from contracts/: {sorted(actual ^ expected)}"
