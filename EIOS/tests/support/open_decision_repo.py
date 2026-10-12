"""Trees for the open-decision tests: the real decision config, a stub-only layout, plants.

Planted literals (model identifiers, provider names, prices) are assembled from fragments at
call time, so no test file contains a literal the repository's own scans would flag.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_RELATIVE = "config/open_decisions.yaml"
INDEX_RELATIVE = "docs/spikes_and_adrs.md"
PROVIDERS_DIR = "src/eios/llm_gateway/providers"

_STUB_PROVIDER = '''"""Deterministic stub provider; it never calls a model."""


def complete(prompt: str) -> str:
    return "stub:" + prompt[:16]
'''


def real_config_text() -> str:
    return (REPO_ROOT / CONFIG_RELATIVE).read_text(encoding="utf-8")


def load_real_config() -> dict[str, object]:
    data = yaml.safe_load(real_config_text())
    assert isinstance(data, dict)
    return data


def decision_section(adr: str) -> dict[str, object]:
    """The decision section for ``adr`` from the real config."""
    decisions = load_real_config()["decisions"]
    assert isinstance(decisions, list)
    return next(d for d in decisions if d["adr"] == adr)


def rule_params(adr: str, rule_id: str) -> dict[str, object]:
    rules = decision_section(adr)["rules"]
    assert isinstance(rules, list)
    return next(r for r in rules if r["id"] == rule_id)


def adr002_modules() -> tuple[str, ...]:
    modules = rule_params("ADR-002", "vendor_sdk_modules")["modules"]
    assert isinstance(modules, list)
    return tuple(str(m) for m in modules)


def adr_index_text(statuses: Mapping[str, str]) -> str:
    """A minimal ``docs/spikes_and_adrs.md`` whose ADR index carries ``statuses``."""
    rows = "".join(
        f"| {adr} | Decision {adr} | {status} | lean | — |\n" for adr, status in statuses.items()
    )
    return (
        "# Spikes and ADRs\n\n## 2. ADR index\n\n"
        "| ADR | Decision | Status | Default / current lean | Depends on |\n"
        "|---|---|---|---|---|\n" + rows
    )


def model_identifiers() -> tuple[str, ...]:
    """Model-identifier-shaped strings, assembled so they never appear literally here."""
    return (
        "".join(("gp", "t-", "4o")),
        "".join(("cla", "ude-", "3-5-sonnet")),
        "".join(("gem", "ini-", "2.5-flash")),
    )


def provider_name() -> str:
    return "".join(("Open", "AI"))


def price_shapes() -> tuple[str, ...]:
    return ("".join(("$", "3 per 1M tokens")), "".join(("input_", "price_", "per_mtok = 3")))


def stub_tree(statuses: Mapping[str, str] | None = None) -> dict[str, str]:
    """A tree holding only the stub provider, the real decision config and an ADR index."""
    return {
        CONFIG_RELATIVE: real_config_text(),
        INDEX_RELATIVE: adr_index_text(statuses or {"ADR-002": "Open"}),
        "src/eios/llm_gateway/__init__.py": "",
        f"{PROVIDERS_DIR}/__init__.py": "",
        f"{PROVIDERS_DIR}/stub.py": _STUB_PROVIDER,
        "config/gateway.yaml": "provider: stub\n",
    }


def with_files(tree: Mapping[str, str], extra: Mapping[str, str]) -> dict[str, str]:
    """A new tree: ``tree`` overlaid with ``extra`` (neither input is changed)."""
    return {**tree, **extra}


ALL_OPEN = {"ADR-002": "Open", "ADR-003": "Open", "ADR-009": "Open", "ADR-014": "Open"}


def rule_values(adr: str, rule_id: str, key: str) -> tuple[str, ...]:
    """A list parameter (``names``, ``patterns``, ``modules``, ``candidates``...) of a real rule."""
    values = rule_params(adr, rule_id)[key]
    assert isinstance(values, list)
    return tuple(str(v) for v in values)


def concrete(pattern: str) -> str:
    """A plain name or path that ``pattern`` matches (each ``*`` becomes ``core``)."""
    return pattern.replace("*", "core")


def config_with_lift(adr: str, *, lifted: bool) -> str:
    """The real config text with ``lifted_when.lifted`` of ``adr`` set to ``lifted``."""
    data = load_real_config()
    decisions = data["decisions"]
    assert isinstance(decisions, list)
    for decision in decisions:
        if decision["adr"] == adr:
            decision["lifted_when"]["lifted"] = lifted
    return yaml.safe_dump(data, sort_keys=False)


def all_open_tree() -> dict[str, str]:
    """The stub tree with the real config and an ADR index showing the four decisions open."""
    return stub_tree(ALL_OPEN)
