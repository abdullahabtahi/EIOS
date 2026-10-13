"""Load and validate ``config/open_decisions.yaml`` into frozen models.

Per decision the structure is fixed: ``adr``, ``rules``, ``allowed_paths``, ``lifted_when``.
A rule is ``{id, kind, ...kind parameters}``; parameters are validated by the rule kind
(``rules*.py``). Any rule may carry its own ``include`` / ``exclude`` path globs. Top-level keys:

* ``decisions`` (required).
* ``scan`` - ``include`` (suffixes or file names) and ``exclude`` (paths) define the default
  scope for rules without their own ``include``; ``exclude_all`` paths are skipped by every
  rule; ``prototype_paths`` are skipped by every rule and listed in the tool's report.
* ``spec_text`` - shared parameters (``include``, ``exclude``, ``verbs``, ``qualifiers``) merged
  into every rule of kind ``spec_text`` that does not set them itself.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from eios.common.errors import ConfigError
from tools.common.yaml_io import load_validated

CONFIG_PATH = "config/open_decisions.yaml"
ADR_ID_PATTERN = r"^ADR-[0-9]+$"
SPEC_TEXT_KIND = "spec_text"  # the one rule kind that reads the top-level ``spec_text`` section
# Default scan scope: code, configuration and infrastructure text (not prose or generated output).
DEFAULT_INCLUDE = (".py", ".yaml", ".yml", ".json", ".toml", ".tf", ".tfvars", ".sh", "Dockerfile")

_STRING_LIST = {"type": "array", "items": {"type": "string", "minLength": 1}}
_DECISION_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["adr", "rules", "allowed_paths", "lifted_when"],
    "properties": {
        "adr": {"type": "string", "pattern": ADR_ID_PATTERN},
        "rules": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "kind"],
                "properties": {
                    "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
                    "kind": {"type": "string", "minLength": 1},
                    "include": _STRING_LIST,
                    "exclude": _STRING_LIST,
                },
            },
        },
        "allowed_paths": _STRING_LIST,
        "lifted_when": {
            "type": "object",
            "additionalProperties": False,
            "required": ["lifted", "adr_status"],
            "properties": {"lifted": {"type": "boolean"}, "adr_status": {"enum": ["Accepted"]}},
        },
    },
}
_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decisions"],
    "properties": {
        "scan": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "include": {**_STRING_LIST, "minItems": 1},
                "exclude": _STRING_LIST,
                "exclude_all": _STRING_LIST,
                "prototype_paths": _STRING_LIST,
            },
        },
        "decisions": {"type": "array", "minItems": 1, "items": _DECISION_SCHEMA},
        "spec_text": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "include": _STRING_LIST,
                "exclude": _STRING_LIST,
                "verbs": _STRING_LIST,
                "qualifiers": _STRING_LIST,
            },
        },
    },
}
_ADR_LINE = re.compile(r"^\s*-?\s*adr:\s*(ADR-[0-9]+)\b")


@dataclass(frozen=True, slots=True)
class RuleSpec:
    """One rule of a decision: its id, its kind, and the kind's raw parameters."""

    rule_id: str
    kind: str
    params: Mapping[str, object]
    where: str  # config path such as ``decisions[0].rules[1]`` for error messages


@dataclass(frozen=True, slots=True)
class Lift:
    """A decision is lifted only when ``lifted`` is true AND the ADR index shows ``adr_status``."""

    lifted: bool
    adr_status: str


@dataclass(frozen=True, slots=True)
class Decision:
    adr: str
    rules: tuple[RuleSpec, ...]
    allowed_paths: tuple[str, ...]
    lift: Lift
    line: int  # line of the ``adr:`` key in the config file, for findings about the section


@dataclass(frozen=True, slots=True)
class ScanScope:
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    exclude_all: tuple[str, ...] = ()
    prototype_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OpenDecisionsConfig:
    scan: ScanScope
    decisions: tuple[Decision, ...]


def _adr_lines(path: Path) -> dict[str, int]:
    """First line number of each ``adr:`` key; used only to locate findings."""
    lines: dict[str, int] = {}
    for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = _ADR_LINE.match(text)
        if match:
            lines.setdefault(match.group(1), number)
    return lines


def _rule(raw: Mapping[str, object], where: str, shared: Mapping[str, object]) -> RuleSpec:
    kind = str(raw["kind"])
    defaults = shared if kind == SPEC_TEXT_KIND else {}
    params = {**defaults, **{k: v for k, v in raw.items() if k not in ("id", "kind")}}
    return RuleSpec(str(raw["id"]), kind, MappingProxyType(params), where)


def _decision(
    raw: Mapping[str, object], index: int, lines: Mapping[str, int], shared: Mapping[str, object]
) -> Decision:
    raw_rules = raw["rules"]
    assert isinstance(raw_rules, list)  # noqa: S101
    rules = tuple(
        _rule(rule, f"decisions[{index}].rules[{j}]", shared) for j, rule in enumerate(raw_rules)
    )
    lifted = raw["lifted_when"]
    assert isinstance(lifted, Mapping)  # noqa: S101
    adr = str(raw["adr"])
    return Decision(
        adr=adr,
        rules=rules,
        allowed_paths=tuple(str(p) for p in raw["allowed_paths"]),  # type: ignore[attr-defined]
        lift=Lift(bool(lifted["lifted"]), str(lifted["adr_status"])),
        line=lines.get(adr, index + 1),
    )


def _check_unique(path: Path, decisions: tuple[Decision, ...]) -> None:
    seen: set[str] = set()
    for index, decision in enumerate(decisions):
        if decision.adr in seen:
            raise ConfigError(str(path), f"decisions[{index}].adr", f"duplicate {decision.adr!r}")
        seen.add(decision.adr)
        rule_ids: set[str] = set()
        for rule in decision.rules:
            if rule.rule_id in rule_ids:
                raise ConfigError(str(path), f"{rule.where}.id", f"duplicate id {rule.rule_id!r}")
            rule_ids.add(rule.rule_id)


def load_config(repo_root: Path) -> OpenDecisionsConfig:
    """Read and validate the config; raises ``ConfigError`` naming file and path."""
    path = repo_root / CONFIG_PATH
    if not path.is_file():
        raise ConfigError(CONFIG_PATH, "$", "open-decision configuration file not found")
    data = load_validated(path, _SCHEMA)
    assert isinstance(data, dict)  # noqa: S101
    lines = _adr_lines(path)
    shared = data.get("spec_text", {})
    decisions = tuple(_decision(raw, i, lines, shared) for i, raw in enumerate(data["decisions"]))
    _check_unique(path, decisions)
    scan = data.get("scan", {})
    scope = ScanScope(
        include=tuple(scan.get("include", DEFAULT_INCLUDE)),
        exclude=tuple(scan.get("exclude", ())),
        exclude_all=tuple(scan.get("exclude_all", ())),
        prototype_paths=tuple(scan.get("prototype_paths", ())),
    )
    return OpenDecisionsConfig(scope, decisions)
