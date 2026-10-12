"""config/cost_linkage.yaml: the staleness threshold and the gateway-to-driver linkage map."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import cast

from eios.common.errors import ConfigError
from eios.common.provenance import Tag
from tools.common.yaml_io import load_validated

LINKAGE_PATH = "config/cost_linkage.yaml"
COST_MODEL_PATH = "docs/cost_model.csv"
GATEWAY_GLOB = "config/llm_gateway.*.yaml"

# The only gateway keys that carry a token price (schemas/llm-gateway-config.schema.json).
PRICE_KEYS = ("prices.input_per_unit", "prices.output_per_unit")

_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["staleness_threshold_days", "gateways", "verification"],
    "properties": {
        "staleness_threshold_days": {"type": "integer", "minimum": 1},
        "gateways": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "propertyNames": {"enum": list(PRICE_KEYS)},
                "additionalProperties": {"type": "string", "minLength": 1},
            },
        },
        "verification": {
            "type": "object",
            "additionalProperties": False,
            "required": ["staleness_threshold_days"],
            "properties": {"staleness_threshold_days": {"enum": [t.value for t in Tag]}},
        },
    },
}


@dataclass(frozen=True, slots=True)
class LinkageConfig:
    """``gateways`` maps a gateway file (repo-relative) to ``{price key: driver name}``."""

    staleness_threshold_days: int
    gateways: Mapping[str, Mapping[str, str]]


def load_linkage(repo_root: Path) -> LinkageConfig:
    """Load and validate the linkage file; any problem is a ``ConfigError`` naming the file."""
    data = cast(dict[str, object], load_validated(repo_root / LINKAGE_PATH, _SCHEMA))
    raw = cast(dict[str, dict[str, str]], data["gateways"])
    gateways = {file: MappingProxyType(dict(keys)) for file, keys in raw.items()}
    for file in gateways:
        if not (repo_root / file).is_file():
            raise ConfigError(
                LINKAGE_PATH, f"gateways.{file}", "names a gateway file that does not exist"
            )
    return LinkageConfig(
        staleness_threshold_days=cast(int, data["staleness_threshold_days"]),
        gateways=MappingProxyType(gateways),
    )
