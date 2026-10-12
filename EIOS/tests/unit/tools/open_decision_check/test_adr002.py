"""T114 (FR-035, SC-011): the ADR-002 rule set against planted trees; RED until T126/T127."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.support.open_decision_repo import (
    INDEX_RELATIVE,
    PROVIDERS_DIR,
    REPO_ROOT,
    adr002_modules,
    adr_index_text,
    decision_section,
    model_identifiers,
    stub_tree,
    with_files,
)
from tests.support.repo_builder import build_repo
from tools.common.findings import Finding
from tools.open_decision_check.engine import run_checks

_RULE_VENDOR = "open_decision.ADR-002.vendor_sdk_modules"
_RULE_MODEL = "open_decision.ADR-002.model_identifier_patterns"
_RULE_LIFT = "open_decision.ADR-002.lift_without_acceptance"


def _run(
    tmp_path: Path, extra: dict[str, str], statuses: dict[str, str] | None = None
) -> list[Finding]:
    root = build_repo(tmp_path, with_files(stub_tree(statuses), extra))
    return list(run_checks(root))


def _vendor() -> str:
    """A listed SDK root that is a plain (undotted) identifier, usable in any import form."""
    return next(m for m in adr002_modules() if "." not in m)


def test_stub_provider_only_tree_passes(tmp_path: Path) -> None:
    assert _run(tmp_path, {}) == []


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ("import {m}\n", 2),
        ("import {m} as client\n", 2),
        ("from {m} import Client\n", 2),
        ("from {m}.types import Message\n", 2),
        ("def late():\n    import {m}\n    return {m}\n", 3),
        ("import importlib\nmod = importlib.import_module('{m}')\n", 3),
        ("mod = __import__('{m}')\n", 2),
    ],
)
def test_vendor_sdk_import_outside_providers_fails_with_file_and_line(
    tmp_path: Path, source: str, line: int
) -> None:
    body = "x = 1\n" + source.format(m=_vendor())
    findings = _run(tmp_path, {"src/eios/agent.py": body})
    assert [(f.file, f.rule_id) for f in findings] == [("src/eios/agent.py", _RULE_VENDOR)]
    assert findings[0].line == line


def test_every_listed_sdk_root_is_caught_including_dotted_roots(tmp_path: Path) -> None:
    for number, module in enumerate(adr002_modules()):
        parent, _, leaf = module.rpartition(".")
        statement = f"from {parent} import {leaf}\n" if parent else f"import {module}\n"
        findings = _run(tmp_path / str(number), {"src/eios/a.py": statement})
        assert [f.rule_id for f in findings] == [_RULE_VENDOR], module


def test_vendor_sdk_import_inside_providers_passes(tmp_path: Path) -> None:
    extra = {f"{PROVIDERS_DIR}/real.py": f"import {_vendor()}\n"}
    assert _run(tmp_path, extra) == []


def test_similar_but_different_module_names_are_not_flagged(tmp_path: Path) -> None:
    extra = {"src/eios/a.py": f"import {_vendor()}_helpers\nfrom . import {_vendor()}\n"}
    assert _run(tmp_path, extra) == []


def test_unparseable_python_fails_closed(tmp_path: Path) -> None:
    findings = _run(tmp_path, {"src/eios/broken.py": "def (:\n"})
    # Every Python rule of every open decision fails closed on a file it cannot parse; this
    # decision's own rule must be among them, and nothing else may name another file.
    assert ("src/eios/broken.py", _RULE_VENDOR) in [(f.file, f.rule_id) for f in findings]
    assert {f.file for f in findings} == {"src/eios/broken.py"}


@pytest.mark.parametrize(
    "path",
    [
        "src/eios/agent.py",
        "services/skeleton_core/settings.yaml",
        "infra/envs/dev/main.tf",
        "infra/envs/dev/terraform.tfvars",
        "services/skeleton_core/Dockerfile",
        ".github/workflows/ci.yml",
    ],
)
@pytest.mark.parametrize("model", model_identifiers())
def test_model_identifier_bound_in_code_config_or_infrastructure_fails(
    tmp_path: Path, path: str, model: str
) -> None:
    findings = _run(tmp_path, {path: f"# header\nDEFAULT_MODEL = '{model}'\n"})
    assert [(f.file, f.line, f.rule_id) for f in findings] == [(path, 2, _RULE_MODEL)]
    assert model not in findings[0].message


def test_model_identifier_in_the_config_directory_or_providers_is_allowed(tmp_path: Path) -> None:
    model = model_identifiers()[0]
    extra = {
        "config/gateway_models.yaml": f"model: {model}\n",
        f"{PROVIDERS_DIR}/stub.py": f"MODEL = '{model}'\n",
    }
    assert _run(tmp_path, extra) == []


def test_documentation_and_prototype_trees_are_not_scanned(tmp_path: Path) -> None:
    model = model_identifiers()[0]
    extra = {"docs/notes.md": f"{model}\n", "web-prototype/x/plan.yaml": f"model: {model}\n"}
    assert _run(tmp_path, extra) == []


def test_findings_are_deterministic_and_sorted(tmp_path: Path) -> None:
    model = model_identifiers()[0]
    extra = {"src/eios/b.py": f"m = '{model}'\n", "src/eios/a.py": f"m = '{model}'\n"}
    first = _run(tmp_path / "one", extra)
    assert [f.file for f in first] == ["src/eios/a.py", "src/eios/b.py"]
    assert first == _run(tmp_path / "two", extra)


# --- lifting: config AND the ADR index; never by editing the tool --------------------------


def _violation() -> dict[str, str]:
    return {"src/eios/agent.py": f"import {_vendor()}\n"}


def _lifted_config(tmp_path: Path, statuses: dict[str, str], *, lifted: bool) -> list[Finding]:
    tree = with_files(stub_tree(statuses), _violation())
    text = tree["config/open_decisions.yaml"]
    flag = "true" if lifted else "false"
    tree["config/open_decisions.yaml"] = re.sub(
        r"(?m)^(\s+)lifted: (true|false)", rf"\1lifted: {flag}", text, count=1
    )
    return list(run_checks(build_repo(tmp_path, tree)))


def test_rule_is_lifted_only_when_config_says_so_and_index_shows_accepted(tmp_path: Path) -> None:
    assert _lifted_config(tmp_path, {"ADR-002": "Accepted"}, lifted=True) == []


def test_config_lift_without_accepted_index_stays_enforced_and_is_reported(tmp_path: Path) -> None:
    findings = _lifted_config(tmp_path, {"ADR-002": "Open"}, lifted=True)
    assert sorted(f.rule_id for f in findings) == sorted([_RULE_VENDOR, _RULE_LIFT])
    lift = next(f for f in findings if f.rule_id == _RULE_LIFT)
    assert lift.file == "config/open_decisions.yaml"
    assert lift.line > 0


def test_accepted_index_without_config_lift_stays_enforced(tmp_path: Path) -> None:
    findings = _lifted_config(tmp_path, {"ADR-002": "Accepted"}, lifted=False)
    assert [f.rule_id for f in findings] == [_RULE_VENDOR]


@pytest.mark.parametrize("status", ["Proposed", "Open", "Rejected", ""])
def test_only_accepted_lifts(tmp_path: Path, status: str) -> None:
    findings = _lifted_config(tmp_path, {"ADR-002": status}, lifted=True)
    assert _RULE_VENDOR in [f.rule_id for f in findings]


def test_the_tool_never_names_a_specific_decision() -> None:
    """Lifting is data; no ADR number may be written into the tool itself."""
    sources = sorted((REPO_ROOT / "tools" / "open_decision_check").glob("*.py"))
    assert sources, "tool sources not found"
    for source in sources:
        assert not re.search(r"ADR-\d", source.read_text(encoding="utf-8")), source.name


# --- the shipped config and the real tree ---------------------------------------------------


def test_shipped_adr002_section_has_the_fixed_structure() -> None:
    section = decision_section("ADR-002")
    assert set(section) == {"adr", "rules", "allowed_paths", "lifted_when"}
    assert section["allowed_paths"] == ["src/eios/llm_gateway/providers/", "config/"]
    assert section["lifted_when"] == {"lifted": False, "adr_status": "Accepted"}
    assert len(adr002_modules()) >= 5


def test_the_real_adr_index_still_shows_adr002_open() -> None:
    index = (REPO_ROOT / INDEX_RELATIVE).read_text(encoding="utf-8")
    row = next(line for line in index.splitlines() if line.startswith("| ADR-002 "))
    assert "Open" in row


def test_real_tree_passes_the_adr002_rules() -> None:
    findings = [f for f in run_checks(REPO_ROOT) if "ADR-002" in f.rule_id]
    assert findings == [], findings


def test_index_helper_round_trips_through_the_real_parser() -> None:
    from tools.records.index import parse_adr_index

    rows = parse_adr_index(adr_index_text({"ADR-002": "Open", "ADR-006": "Accepted"}))
    assert [(r.adr_id, r.status) for r in rows] == [("ADR-002", "Open"), ("ADR-006", "Accepted")]
