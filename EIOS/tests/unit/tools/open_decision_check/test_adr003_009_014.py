"""T160 (FR-035, SC-011): ADR-003, ADR-009 and ADR-014 rule sets against planted trees."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.open_decision_repo import (
    ALL_OPEN,
    CONFIG_RELATIVE,
    INDEX_RELATIVE,
    REPO_ROOT,
    all_open_tree,
    concrete,
    config_with_lift,
    decision_section,
    rule_values,
    stub_tree,
    with_files,
)
from tests.support.repo_builder import build_repo
from tools.common.findings import Finding
from tools.open_decision_check.config import load_config
from tools.open_decision_check.engine import run_checks
from tools.open_decision_check.report import decision_states

_A3 = "open_decision.ADR-003."
_A9 = "open_decision.ADR-009."
_A14 = "open_decision.ADR-014."


def _run(
    tmp_path: Path, extra: dict[str, str], tree: dict[str, str] | None = None
) -> list[Finding]:
    root = build_repo(tmp_path, with_files(tree or all_open_tree(), extra))
    return list(run_checks(root))


def _ids(findings: list[Finding]) -> list[tuple[str, str]]:
    return [(f.file, f.rule_id) for f in findings]


def _plain(adr: str, rule_id: str, key: str) -> str:
    """A listed value that has no glob character, usable verbatim."""
    return next(v for v in rule_values(adr, rule_id, key) if "*" not in v)


def _engine_package() -> str:
    return _plain("ADR-003", "engine_manifest_dependencies", "names")


def test_clean_tree_passes_and_all_four_adrs_report_open(tmp_path: Path) -> None:
    root = build_repo(tmp_path, all_open_tree())
    assert list(run_checks(root)) == []
    states = decision_states(root, load_config(root))
    assert [(s.adr, s.state, s.index_status) for s in states] == [
        (adr, "open", "Open") for adr in ALL_OPEN
    ]


# --- ADR-003: metric engine -----------------------------------------------------------------


def _pyproject(dependencies: str) -> str:
    return f'[project]\nname = "x"\nversion = "0"\ndependencies = [{dependencies}]\n'


def _manifest_files(package: str) -> dict[str, str]:
    return {
        "package.json": json.dumps({"dependencies": {package: "1.0.0"}}, indent=2),
        "services/web/package.json": json.dumps({"devDependencies": {package: "^1"}}),
        "pyproject.toml": _pyproject(f'"{package}>=1"'),
        "requirements.txt": f"requests\n{package}==1.0  # pinned\n",
        "requirements-dev.txt": f"{package}\n",
        "uv.lock": f'[[package]]\nname = "{package}"\nversion = "1.0"\n',
        "package-lock.json": json.dumps(
            {"packages": {"": {"name": "x"}, f"node_modules/{package}": {"version": "1"}}}
        ),
    }


@pytest.mark.parametrize("path", sorted(_manifest_files("p")))
def test_adr003_flags_a_metric_engine_package_in_every_manifest_format(
    tmp_path: Path, path: str
) -> None:
    findings = _run(tmp_path, {path: _manifest_files(_engine_package())[path]})
    assert _ids(findings) == [(path, _A3 + "engine_manifest_dependencies")]
    assert findings[0].line >= 1


def test_adr003_reports_the_line_of_the_dependency(tmp_path: Path) -> None:
    text = f"requests\nnumpy\n{_engine_package()}\n"
    findings = _run(tmp_path, {"requirements.txt": text})
    assert [f.line for f in findings] == [3]


def test_adr003_every_listed_package_pattern_is_caught(tmp_path: Path) -> None:
    for number, pattern in enumerate(
        rule_values("ADR-003", "engine_manifest_dependencies", "names")
    ):
        extra = {"requirements.txt": concrete(pattern) + "\n"}
        if pattern.startswith("@"):
            extra = {"package.json": json.dumps({"dependencies": {concrete(pattern): "1"}})}
        findings = _run(tmp_path / str(number), extra)
        assert [f.rule_id for f in findings] == [_A3 + "engine_manifest_dependencies"], pattern


def test_adr003_does_not_flag_unrelated_or_look_alike_dependencies(tmp_path: Path) -> None:
    extra = {
        "pyproject.toml": _pyproject('"duckdb", "cubed"'),
        "requirements.txt": "duckdb>=1\ncubed\n",
        "package.json": json.dumps({"dependencies": {"lodash": "1"}}),
    }
    assert _run(tmp_path, extra) == []


def test_adr003_flags_a_metric_engine_schema_file(tmp_path: Path) -> None:
    for number, pattern in enumerate(rule_values("ADR-003", "engine_schema_files", "patterns")):
        path = concrete(pattern).removeprefix("**/")
        findings = _run(tmp_path / str(number), {path: "anything\n"})
        assert _ids(findings) == [(path, _A3 + "engine_schema_files")], pattern


def test_adr003_flags_a_metric_engine_import(tmp_path: Path) -> None:
    module = _plain("ADR-003", "engine_imports", "modules")
    findings = _run(tmp_path, {"src/eios/metrics.py": f"import {module}\n"})
    assert _ids(findings) == [("src/eios/metrics.py", _A3 + "engine_imports")]


# --- ADR-009: frontend framework and design system -------------------------------------------


def test_adr009_flags_a_frontend_framework_manifest(tmp_path: Path) -> None:
    framework = _plain("ADR-009", "frontend_manifest_dependencies", "names")
    extra = {"ui/package.json": json.dumps({"dependencies": {framework: "1"}})}
    findings = _run(tmp_path, extra)
    assert _ids(findings) == [("ui/package.json", _A9 + "frontend_manifest_dependencies")]


def test_adr009_flags_a_design_system_dependency(tmp_path: Path) -> None:
    names = rule_values("ADR-009", "frontend_manifest_dependencies", "names")
    design = next(n for n in names if "quantumblack" in n.lower())
    extra = {"ui/package.json": json.dumps({"devDependencies": {concrete(design): "1"}})}
    assert _ids(_run(tmp_path, extra)) == [
        ("ui/package.json", _A9 + "frontend_manifest_dependencies")
    ]


def test_adr009_every_listed_dependency_is_caught(tmp_path: Path) -> None:
    for number, pattern in enumerate(
        rule_values("ADR-009", "frontend_manifest_dependencies", "names")
    ):
        extra = {"package.json": json.dumps({"dependencies": {concrete(pattern): "1"}})}
        findings = _run(tmp_path / str(number), extra)
        assert [f.rule_id for f in findings] == [_A9 + "frontend_manifest_dependencies"], pattern


def test_adr009_flags_a_framework_config_file(tmp_path: Path) -> None:
    for number, pattern in enumerate(rule_values("ADR-009", "frontend_config_files", "patterns")):
        path = "ui/" + concrete(pattern).removeprefix("**/").replace("core", "ts")
        findings = _run(tmp_path / str(number), {path: "{}\n"})
        assert _ids(findings) == [(path, _A9 + "frontend_config_files")], pattern


def test_adr009_prototype_paths_are_excluded_by_configuration(tmp_path: Path) -> None:
    framework = _plain("ADR-009", "frontend_manifest_dependencies", "names")
    manifest = json.dumps({"dependencies": {framework: "1"}})
    extra = {
        "web-prototype/package.json": manifest,
        "web-prototype/next.config.ts": "export default {}\n",
        "FEIOS/web-prototype/package.json": manifest,
        "DESIGN.MD": "We will use React.\n",
        "DESIGN_PLAN.md": "We will use React.\n",
    }
    assert _run(tmp_path, extra) == []
    listed = load_config(build_repo(tmp_path / "cfg", all_open_tree())).scan.prototype_paths
    assert {"FEIOS", "DESIGN.MD", "DESIGN_PLAN.md"} <= set(listed)


# --- ADR-014: API surface ---------------------------------------------------------------------


@pytest.mark.parametrize("path", ["schema.graphql", "api/schema.gql", "api/v1/types.graphqls"])
def test_adr014_flags_a_graphql_schema_file(tmp_path: Path, path: str) -> None:
    findings = _run(tmp_path, {path: "type Query { x: Int }\n"})
    assert _ids(findings) == [(path, _A14 + "graphql_schema_files")]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ('from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/clients")\ndef c(): ...\n', 4),
        ('@router.post("/orders/{id}")\nasync def o(): ...\n', 1),
        ('@bp.route("/clients", methods=["GET"])\ndef c(): ...\n', 1),
        ('@api.delete(path="/partners")\ndef p(): ...\n', 1),
        ('app.add_api_route("/metrics", handler)\n', 1),
        ('app.add_url_rule("/briefing", view_func=v)\n', 1),
    ],
)
def test_adr014_flags_a_business_resource_route(tmp_path: Path, source: str, line: int) -> None:
    findings = _run(tmp_path, {"src/eios/api.py": source})
    assert [(f.file, f.line, f.rule_id) for f in findings] == [
        ("src/eios/api.py", line, _A14 + "business_resource_routes")
    ]


def test_adr014_skeleton_health_and_forward_routes_pass(tmp_path: Path) -> None:
    source = '@app.get("/health")\ndef h(): ...\n\n@app.post("/forward")\ndef f(): ...\n'
    extra = {
        "services/skeleton_edge/app.py": source,
        "services/skeleton_core/app.py": source,
    }
    assert _run(tmp_path, extra) == []
    other = {"services/skeleton_core/other.py": source}
    assert len(_run(tmp_path / "b", other)) == 2


def test_adr014_allowed_paths_are_only_the_two_skeleton_apps() -> None:
    assert decision_section("ADR-014")["allowed_paths"] == [
        "services/skeleton_edge/app.py",
        "services/skeleton_core/app.py",
    ]


def test_adr014_calls_that_are_not_route_registrations_pass(tmp_path: Path) -> None:
    source = (
        'value = settings.get("/not-a-route")\n'
        'response = client.get("/health")\n'
        '@app.get("no-leading-slash")\ndef f(): ...\n'
        "@cache.get(key_for(1))\ndef g(): ...\n"
    )
    assert _run(tmp_path, {"src/eios/a.py": source}) == []


def test_adr014_flags_graphql_dependencies_and_imports(tmp_path: Path) -> None:
    package = _plain("ADR-014", "graphql_manifest_dependencies", "names")
    module = _plain("ADR-014", "graphql_imports", "modules")
    extra = {"requirements.txt": f"{package}\n", "src/eios/g.py": f"import {module}\n"}
    assert _ids(_run(tmp_path, extra)) == [
        ("requirements.txt", _A14 + "graphql_manifest_dependencies"),
        ("src/eios/g.py", _A14 + "graphql_imports"),
    ]


# --- spec text --------------------------------------------------------------------------------

_SETTLED = [
    ("docs/design.md", "# Design\n\nWe will use Cube Core as the metric engine.\n", 3, "ADR-003"),
    ("specs/001/spec.md", "The team decided on GraphQL for the edge API.\n", 1, "ADR-014"),
    ("docs/a.md", "Intro.\n\nThe cockpit is built on React and Vite.\n", 3, "ADR-009"),
    ("docs/b.md", "| Edge | uses REST |\n", 1, "ADR-014"),
    ("docs/c.md", "- The gateway selected Gemini as default.\n", 1, "ADR-002"),
    ("docs/d.md", "The registry is\nchosen: lightweight metric registry.\n", 1, "ADR-003"),
]


@pytest.mark.parametrize(("path", "text", "line", "adr"), _SETTLED)
def test_a_sentence_stating_a_decision_as_settled_is_flagged(
    tmp_path: Path, path: str, text: str, line: int, adr: str
) -> None:
    findings = _run(tmp_path, {path: text})
    assert len(findings) == 1, findings
    assert (findings[0].file, findings[0].line) == (path, line)
    assert findings[0].rule_id.startswith(f"open_decision.{adr}.")
    assert findings[0].rule_id.endswith("_stated_as_settled")


@pytest.mark.parametrize(
    "text",
    [
        "Cube Core is one option for the metric engine; we might use it.\n",
        "Candidates for the edge API: GraphQL or REST. We may use either.\n",
        "The frontend could use React, Vue or Svelte, but this is open.\n",
        "Whether to use GraphQL is decided with the frontend stack.\n",
        "Cube Core vs lightweight metric registry over DuckDB.\n",
        "If we choose React, the design system follows.\n",
        "The spike compares Gemini against other candidate models.\n",
        "We use Reactive streams and a restful style.\n",
        "The metric engine is the invariant.\n",
        "```\nuse Cube Core here\n```\n",
    ],
)
def test_the_same_candidate_named_as_an_option_passes(tmp_path: Path, text: str) -> None:
    assert _run(tmp_path, {"docs/design.md": text}) == []


def test_prose_outside_the_configured_globs_is_not_read(tmp_path: Path) -> None:
    extra = {"README.md": "We will use Cube Core.\n", "src/notes.md": "We will use GraphQL.\n"}
    assert _run(tmp_path, extra) == []


# --- lifting: config AND the index, per decision ------------------------------------------------


def _lift_tree(adr: str, status: str, *, lifted: bool) -> dict[str, str]:
    tree = stub_tree({**ALL_OPEN, adr: status})
    tree[CONFIG_RELATIVE] = config_with_lift(adr, lifted=lifted)
    return tree


def _violations() -> dict[str, str]:
    package = _engine_package()
    return {"requirements.txt": f"{package}\n", "schema.graphql": "type Q { a: Int }\n"}


def test_a_decision_lifts_only_when_config_says_so_and_the_index_shows_accepted(
    tmp_path: Path,
) -> None:
    findings = _run(tmp_path, _violations(), _lift_tree("ADR-003", "Accepted", lifted=True))
    assert _ids(findings) == [("schema.graphql", _A14 + "graphql_schema_files")]


def test_config_lift_without_an_accepted_index_stays_enforced_and_is_reported(
    tmp_path: Path,
) -> None:
    findings = _run(tmp_path, _violations(), _lift_tree("ADR-003", "Open", lifted=True))
    assert sorted(f.rule_id for f in findings) == sorted(
        [
            _A3 + "engine_manifest_dependencies",
            _A3 + "lift_without_acceptance",
            _A14 + "graphql_schema_files",
        ]
    )


def test_an_accepted_index_without_config_lift_stays_enforced(tmp_path: Path) -> None:
    findings = _run(tmp_path, _violations(), _lift_tree("ADR-003", "Accepted", lifted=False))
    assert (("requirements.txt", _A3 + "engine_manifest_dependencies")) in _ids(findings)


def test_lifting_one_decision_does_not_lift_another(tmp_path: Path) -> None:
    tree = _lift_tree("ADR-014", "Accepted", lifted=True)
    findings = _run(tmp_path, _violations(), tree)
    assert _ids(findings) == [("requirements.txt", _A3 + "engine_manifest_dependencies")]


def test_a_lifted_decision_reports_lifted(tmp_path: Path) -> None:
    root = build_repo(tmp_path, _lift_tree("ADR-009", "Accepted", lifted=True))
    states = {s.adr: s.state for s in decision_states(root, load_config(root))}
    assert states == {"ADR-002": "open", "ADR-003": "open", "ADR-009": "lifted", "ADR-014": "open"}


# --- the shipped config and the real tree -----------------------------------------------------


@pytest.mark.parametrize("adr", ["ADR-003", "ADR-009", "ADR-014"])
def test_shipped_sections_have_the_fixed_structure_and_are_unlifted(adr: str) -> None:
    section = decision_section(adr)
    assert set(section) == {"adr", "rules", "allowed_paths", "lifted_when"}
    assert section["lifted_when"] == {"lifted": False, "adr_status": "Accepted"}
    rules = section["rules"]
    assert isinstance(rules, list)
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids))


def test_the_real_index_shows_all_four_decisions_open() -> None:
    index = (REPO_ROOT / INDEX_RELATIVE).read_text(encoding="utf-8")
    for adr in ALL_OPEN:
        row = next(line for line in index.splitlines() if line.startswith(f"| {adr} "))
        assert "Open" in row


def test_the_real_tree_passes_every_rule_and_reports_all_four_open() -> None:
    assert list(run_checks(REPO_ROOT)) == []
    states = decision_states(REPO_ROOT, load_config(REPO_ROOT))
    assert {(s.adr, s.state) for s in states} == {(adr, "open") for adr in ALL_OPEN}
