"""Gateway-to-driver linkage: token prices in the gateway configuration must match the model."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from eios.common.errors import ConfigError
from eios.common.provenance import Tag
from tools.common.findings import Finding
from tools.common.yaml_io import load_yaml
from tools.cost_check.config import COST_MODEL_PATH, GATEWAY_GLOB, PRICE_KEYS, LinkageConfig
from tools.cost_check.model import CostRow, parse_decimal
from tools.repo_checks._walk import relative_posix

UNLINKED = "linkage.unlinked_price"
MISMATCH = "linkage.price_mismatch"
UNVERIFIED = "linkage.price_unverified"
UNIT_MISMATCH = "linkage.unit_mismatch"

# A gateway price carrying one of these tags claims no real tariff, so a model row without a
# verified price is consistent with it. Any other tag claims a price the model must back.
_NON_AUTHORITATIVE = frozenset({Tag.ILLUSTRATIVE.value, Tag.SPIKE.value})


@dataclass(frozen=True, slots=True)
class GatewayPrice:
    key: str
    value: Decimal
    unit: str | None
    tag: str | None


def _read_number(value: object, file: str, key: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        raise ConfigError(file, key, f"price must be a number >= 0, got {value!r}")
    number = parse_decimal(repr(value))
    if number is None:
        raise ConfigError(file, key, f"price is not a finite number: {value!r}")
    return number


def read_gateway_prices(root: Path, file: str) -> tuple[GatewayPrice, ...]:
    """The token prices a gateway configuration sets (none when it has no ``prices`` block)."""
    data = load_yaml(root / file)
    if not isinstance(data, dict):
        raise ConfigError(file, "$", "gateway configuration must be a mapping")
    prices = data.get("prices")
    if prices is None:
        return ()
    if not isinstance(prices, dict):
        raise ConfigError(file, "prices", "prices must be a mapping")
    verification = data.get("verification")
    tag = verification.get("prices") if isinstance(verification, dict) else None
    unit = prices.get("unit")
    found = []
    for key in PRICE_KEYS:
        name = key.split(".", 1)[1]
        if name in prices:
            value = _read_number(prices[name], file, key)
            found.append(GatewayPrice(key, value, unit if isinstance(unit, str) else None, tag))
    return tuple(found)


def _gateway_files(root: Path, config: LinkageConfig) -> list[str]:
    on_disk = {relative_posix(root, p) for p in root.glob(GATEWAY_GLOB) if p.is_file()}
    return sorted(on_disk | set(config.gateways))


def _drivers(rows: tuple[CostRow, ...], config: LinkageConfig) -> Mapping[str, CostRow]:
    """Resolve every linked driver name to its (first) row; an unknown name is a config error."""
    by_name: dict[str, CostRow] = {}
    for row in rows:
        by_name.setdefault(row.driver, row)
    for file, keys in config.gateways.items():
        for key, driver in keys.items():
            if driver not in by_name:
                message = f"links {key} to driver {driver!r}, which is not in {COST_MODEL_PATH}"
                raise ConfigError("config/cost_linkage.yaml", f"gateways.{file}.{key}", message)
    return by_name


def _compare(price: GatewayPrice, row: CostRow, file: str) -> list[Finding]:
    model_price = parse_decimal(row.unit_price)
    where = f"{COST_MODEL_PATH} line {row.line}"
    if model_price is None:
        if price.tag in _NON_AUTHORITATIVE:
            return []
        message = (
            f"{file} sets {price.key}={price.value} ({price.tag}) but driver {row.driver!r} "
            f"in {where} has no unit_price to back it"
        )
        return [Finding(file, 0, UNVERIFIED, message)]
    out: list[Finding] = []
    if model_price != price.value:
        message = (
            f"{file} sets {price.key}={price.value} but driver {row.driver!r} in {where} "
            f"has unit_price {model_price}"
        )
        out.append(Finding(file, 0, MISMATCH, message))
    if price.unit is not None and price.unit != row.unit:
        message = (
            f"{file} prices {price.key} per {price.unit!r} but driver {row.driver!r} "
            f"in {where} is billed per {row.unit!r}"
        )
        out.append(Finding(file, 0, UNIT_MISMATCH, message))
    return out


def check_linkage(root: Path, config: LinkageConfig, rows: tuple[CostRow, ...]) -> list[Finding]:
    """Compare every gateway price with its linked driver row (see contracts/cost-model.md)."""
    drivers = _drivers(rows, config)
    findings: list[Finding] = []
    for file in _gateway_files(root, config):
        links = config.gateways.get(file, {})
        for price in read_gateway_prices(root, file):
            driver = links.get(price.key)
            if driver is None:
                message = (
                    f"{file} sets {price.key} but config/cost_linkage.yaml links it to no driver"
                )
                findings.append(Finding(file, 0, UNLINKED, message))
            else:
                findings.extend(_compare(price, drivers[driver], file))
    return findings
