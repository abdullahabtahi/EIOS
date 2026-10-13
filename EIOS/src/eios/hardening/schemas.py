"""JSON Schema registry and contract validators for Hardening & Disaster Recovery (015-hardening-dr)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry, Resource

_CONTRACTS_DIR = Path(__file__).resolve().parents[4] / "specs" / "015-hardening-dr" / "contracts"

_SCHEMAS: dict[str, dict[str, Any]] = {}
_REGISTRY: Registry | None = None


def get_contracts_dir() -> Path:
    """Returns the absolute path to the contracts directory."""
    return _CONTRACTS_DIR


def _get_referencing_registry() -> Registry:
    global _REGISTRY
    if _REGISTRY is not None:
        return _REGISTRY

    registry = Registry()
    if _CONTRACTS_DIR.exists():
        for p in _CONTRACTS_DIR.glob("*.json"):
            try:
                with open(p, encoding="utf-8") as f:
                    content = json.load(f)
                    resource = Resource.from_contents(content)
                    registry = registry.with_resource(p.name, resource)
                    registry = registry.with_resource(p.resolve().as_uri(), resource)
            except Exception:  # noqa: S110
                pass
    _REGISTRY = registry
    return _REGISTRY


def load_schema(name: str) -> dict[str, Any]:
    """Loads a contract schema by name (e.g. 'chaos-experiment-record' or 'chaos-experiment-record.schema.json')."""
    if not name.endswith(".schema.json"):
        name = f"{name}.schema.json"
    if name in _SCHEMAS:
        return _SCHEMAS[name]

    schema_path = _CONTRACTS_DIR / name
    if not schema_path.exists():
        raise FileNotFoundError(f"Contract schema not found: {schema_path}")

    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
        _SCHEMAS[name] = schema
        return schema


def validate_contract(data: dict[str, Any], schema_name: str) -> bool:
    """Validates a payload against a registered JSON schema contract with cross-file references.

    Raises jsonschema.ValidationError if invalid.
    """
    schema = load_schema(schema_name)
    registry = _get_referencing_registry()
    validator = jsonschema.Draft202012Validator(schema, registry=registry)
    validator.validate(data)
    return True


def list_registered_schemas() -> list[str]:
    """Lists all registered schema file names found in the contracts directory."""
    if not _CONTRACTS_DIR.exists():
        return []
    return sorted([p.name for p in _CONTRACTS_DIR.glob("*.schema.json")])
