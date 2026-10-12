"""Load and validate ``config/labels.yaml`` into an immutable rule set."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from eios.common.errors import ConfigError
from eios.common.provenance import Tag
from tools.common.yaml_io import load_validated

CONFIG_PATH = "config/labels.yaml"

UNLABELLED = "label.unlabelled-claim"
MULTIPLE_TAGS = "label.multiple-tags"
UNKNOWN_TAG = "label.unknown-tag"
BRIEF_CITATION = "label.brief-citation"
SPIKE_REFERENCE = "label.spike-reference"
ORIGIN_INCOMPLETE = "label.origin-incomplete"
ORIGIN_PATH = "label.origin-path"
FORBIDDEN = "label.forbidden-literal"
ALLOWLIST_STALE = "label.allowlist-stale"
STRUCTURED = "label.structured-missing-tag"

_KINDS = ["brief_citation", "owner_and_verify_by", "none", "metric_and_report", "spike_id"]
_NONEMPTY = {"type": "string", "minLength": 1}
_LIST = {"type": "array", "items": _NONEMPTY}
_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "tags",
        "claim_scope",
        "non_claim_patterns",
        "numeric_claims",
        "scope",
        "prototype_excluded",
        "brief_root",
        "spike_dir",
        "spike_index",
        "structured_rules",
    ],
    "properties": {
        "tags": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": False,
                "required": ["evidence", "description"],
                "properties": {"evidence": {"enum": _KINDS}, "description": _NONEMPTY},
            },
        },
        "claim_scope": _LIST,
        "non_claim_patterns": _LIST,
        "numeric_claims": {
            "type": "object",
            "additionalProperties": False,
            "required": ["units", "duration_units"],
            "properties": {"units": _LIST, "duration_units": _LIST},
        },
        "scope": {
            "type": "object",
            "additionalProperties": False,
            "required": ["include", "exclude"],
            "properties": {"include": _LIST, "exclude": _LIST},
        },
        "prototype_excluded": _LIST,
        "brief_root": _NONEMPTY,
        "spike_dir": _NONEMPTY,
        "spike_index": _NONEMPTY,
        "structured_rules": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["kind", "glob"],
                "properties": {"kind": {"enum": ["yaml_verification", "csv_tag_column"]}},
            },
        },
    },
}
_CLAIM_SCOPE = {"sentence", "table_row", "list_item"}


@dataclass(frozen=True, slots=True)
class LabelRules:
    evidence: dict[str, str]
    claim_scope: tuple[str, ...]
    non_claim: tuple[re.Pattern[str], ...]
    count_pattern: re.Pattern[str]
    duration_pattern: re.Pattern[str]
    tag_pattern: re.Pattern[str]
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    prototype_excluded: tuple[str, ...]
    brief_root: str
    spike_dir: str
    spike_index: str
    structured_rules: tuple[dict[str, str], ...]

    def tags_with(self, kind: str) -> frozenset[str]:
        return frozenset(tag for tag, k in self.evidence.items() if k == kind)


def _check_tag_set(file: str, evidence: dict[str, str]) -> None:
    expected = {t.value for t in Tag}
    for tag in sorted(set(evidence) - expected):
        raise ConfigError(file, f"tags.{tag}", f"unknown tag {tag}; not in the provenance Tag enum")
    for tag in sorted(expected - set(evidence)):
        raise ConfigError(file, "tags", f"missing tag {tag}; every provenance tag needs a rule")


def _compile(file: str, path: str, patterns: list[str]) -> tuple[re.Pattern[str], ...]:
    out = []
    for index, pattern in enumerate(patterns):
        try:
            out.append(re.compile(pattern))
        except re.error as exc:
            raise ConfigError(
                file, f"{path}[{index}]", f"invalid regular expression: {exc}"
            ) from exc
    return tuple(out)


def _alternation(words: list[str], *, stem_plural: bool) -> str:
    stems = [w[:-1] if stem_plural and w.endswith("s") and len(w) > 2 else w for w in words]
    return "|".join(re.escape(w) for w in sorted(set(stems), key=len, reverse=True))


def load_rules(path: Path) -> LabelRules:
    """Load ``path``; raises ``ConfigError`` naming the file and the offending key."""
    file = str(path)
    data = load_validated(path, _SCHEMA)
    assert isinstance(data, dict)  # noqa: S101 - the schema guarantees an object
    evidence = {tag: str(rule["evidence"]) for tag, rule in data["tags"].items()}
    _check_tag_set(file, evidence)
    if set(data["claim_scope"]) != _CLAIM_SCOPE or len(data["claim_scope"]) != 3:
        raise ConfigError(file, "claim_scope", f"must be exactly {sorted(_CLAIM_SCOPE)}")
    numeric = data["numeric_claims"]
    unit_alt = _alternation(numeric["units"], stem_plural=True)
    duration_alt = _alternation(numeric["duration_units"], stem_plural=False)
    count = rf"(?<![\w.])\d[\d,]*(?:\.\d+)?[kKmM]?[\s-]+(?:{unit_alt})s?\b"
    duration = rf"(?<![\w.-])\d+(?:\.\d+)?[\s-]?(?:{duration_alt})s?\b"
    scope = data["scope"]
    return LabelRules(
        evidence=evidence,
        claim_scope=tuple(data["claim_scope"]),
        non_claim=_compile(file, "non_claim_patterns", data["non_claim_patterns"]),
        count_pattern=re.compile(count, re.IGNORECASE),
        duration_pattern=re.compile(duration),
        tag_pattern=re.compile("|".join(re.escape(t) for t in evidence)),
        include=tuple(scope["include"]),
        exclude=tuple(scope["exclude"]),
        prototype_excluded=tuple(data["prototype_excluded"]),
        brief_root=data["brief_root"].strip("/"),
        spike_dir=data["spike_dir"].strip("/"),
        spike_index=data["spike_index"],
        structured_rules=tuple({k: str(v) for k, v in r.items()} for r in data["structured_rules"]),
    )
