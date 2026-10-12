"""Gateway configuration: schema-validated, tagged, and without any default model.

``parse_config`` is the single boundary. Every configured value that could drift from reality
needs a verification tag; deployed environments (stage, prod-like) refuse to start without an
explicit ``model_id`` (FR-022, FR-028). Errors name the file and path, never the value.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Any, Literal

import yaml
from jsonschema.exceptions import ValidationError as SchemaError
from pydantic import Field, field_validator, model_validator

from eios.common.errors import BoundaryValidationError, ConfigError
from eios.common.provenance import Tag
from eios.common.validation import StrictModel, validate_at_boundary
from eios.llm_gateway._schemas import CONFIG_SCHEMA, validator_for
from eios.llm_gateway.providers import REGISTERED_PROVIDERS

DEPLOYED_ENVIRONMENTS = frozenset({"stage", "prod-like"})
_UNIT = re.compile(r"[1-9][0-9]* tokens")
_SAFE_NAME = re.compile(r"[a-z_][a-z0-9_]{0,63}")
_ROOT = "<root>"
Price = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Prices(StrictModel):
    input_per_unit: Price
    output_per_unit: Price
    currency: Annotated[str, Field(min_length=3, max_length=3)]
    unit: Annotated[str, Field(pattern=_UNIT.pattern)]

    def cost(self, *, tokens_in: int, tokens_out: int) -> float:
        """Cost of a call, derived only from the configured prices and unit."""
        unit_size = int(self.unit.split(" ", 1)[0])
        return (tokens_in * self.input_per_unit + tokens_out * self.output_per_unit) / unit_size


class Verification(StrictModel):
    model_id: Tag | None = None
    prices: Tag | None = None
    rate_limits: Tag | None = None
    daily_token_cap: Tag
    cap_warning_thresholds_percent: Tag | None = None


class GatewayConfig(StrictModel):
    environment: Literal["dev", "stage", "prod-like"]
    provider: str
    model_id: str | None = None
    prices: Prices | None = None
    rate_limits: Mapping[str, int] = Field(default_factory=lambda: MappingProxyType({}))
    daily_token_cap: Annotated[int, Field(strict=True, ge=1)]
    cap_warning_thresholds_percent: tuple[int, ...] = ()
    verification: Verification

    @field_validator("rate_limits", mode="after")
    @classmethod
    def _freeze_rate_limits(cls, value: Mapping[str, int]) -> Mapping[str, int]:
        return MappingProxyType(dict(value))

    @model_validator(mode="after")
    def _check_provider(self) -> GatewayConfig:
        if self.provider not in REGISTERED_PROVIDERS:
            raise ValueError("provider is not registered")
        return self


def _path_text(parts: list[str]) -> str:
    return ".".join(parts) if parts else _ROOT


def _schema_findings(error: SchemaError) -> list[tuple[str, str]]:
    """(path, message) pairs for one schema error; values are never included."""
    base = [str(p) for p in error.absolute_path]
    required = error.validator_value
    if (
        error.validator == "required"
        and isinstance(error.instance, dict)
        and isinstance(required, list)
    ):
        missing = [n for n in required if n not in error.instance]
        return [(_path_text([*base, str(n)]), "is required") for n in missing]
    if error.validator == "additionalProperties" and isinstance(error.instance, dict):
        schema = error.schema
        known = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
        names = [str(k) for k in error.instance if k not in known]
        return [
            (_path_text([*base, n if _SAFE_NAME.fullmatch(n) else "<redacted>"]), "is not allowed")
            for n in names
        ]
    return [(_path_text(base), f"fails schema rule '{error.validator}'")]


def _check_schema(data: Mapping[str, Any], source: str) -> None:
    findings: list[tuple[str, str]] = []
    for error in validator_for(CONFIG_SCHEMA).iter_errors(data):
        findings.extend(_schema_findings(error))
    if findings:
        path, message = sorted(findings)[0]
        extra = f" (+{len(findings) - 1} more)" if len(findings) > 1 else ""
        raise ConfigError(source, path, f"{message}{extra}")


def _check_threshold_tag(data: Mapping[str, Any], source: str) -> None:
    verification = data.get("verification")
    tagged = isinstance(verification, Mapping) and "cap_warning_thresholds_percent" in verification
    if data.get("cap_warning_thresholds_percent") and not tagged:
        raise ConfigError(source, "verification.cap_warning_thresholds_percent", "is required")


def parse_config(data: object, *, source: str) -> GatewayConfig:
    """Validate raw configuration data. ``source`` names the file for error messages."""
    if not isinstance(data, Mapping):
        raise ConfigError(source, _ROOT, "configuration must be a mapping")
    _check_schema(data, source)
    _check_threshold_tag(data, source)
    try:
        config = validate_at_boundary(GatewayConfig, dict(data))
    except BoundaryValidationError as exc:
        raise ConfigError(source, ", ".join(exc.field_paths) or _ROOT, "invalid value") from None
    if config.environment in DEPLOYED_ENVIRONMENTS and config.model_id is None:
        raise ConfigError(
            source,
            "model_id",
            f"required in the {config.environment} environment; there is no default model "
            "(ADR-002 is open)",
        )
    return config


def load_config(path: Path) -> GatewayConfig:
    """Read and validate a YAML configuration file."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError:
        raise ConfigError(str(path), "<file>", "cannot be read") from None
    except yaml.YAMLError:
        raise ConfigError(str(path), "<file>", "is not valid YAML") from None
    return parse_config(raw, source=str(path))


def config_identity(config: GatewayConfig) -> str:
    """Stable sha256 of the canonical configuration; part of every replay key and trace."""
    content = {
        **config.model_dump(exclude={"rate_limits"}),
        "rate_limits": dict(config.rate_limits),
    }
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
