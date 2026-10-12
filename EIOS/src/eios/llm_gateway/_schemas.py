"""Loads the JSON Schemas that define the gateway's configuration and trace shapes."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "schemas"
CONFIG_SCHEMA = "llm-gateway-config.schema.json"
TRACE_SCHEMA = "llm-call-trace.schema.json"


@cache
def _load(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))
    return loaded


def validator_for(name: str) -> Draft202012Validator:
    """A validator for a schema file under ``schemas/``."""
    return Draft202012Validator(_load(name))
