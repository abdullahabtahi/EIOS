"""T028: a missing lockfile, or one out of sync with pyproject.toml, fails."""

from __future__ import annotations

from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tests.support.repo_builder import build_repo
from tools.repo_checks.pinned_deps import RULE_ID, check_pinned_deps


def _pyproject(deps: tuple[str, ...] = (), dev: tuple[str, ...] = (), name: str = "demo") -> str:
    deps_toml = ", ".join(f'"{d}"' for d in deps)
    dev_toml = ", ".join(f'"{d}"' for d in dev)
    return (
        f'[project]\nname = "{name}"\nversion = "0.0.0"\ndependencies = [{deps_toml}]\n\n'
        f"[dependency-groups]\ndev = [{dev_toml}]\n"
    )


def _lock(
    deps: tuple[str, ...] = (),
    dev: tuple[str, ...] = (),
    name: str = "demo",
    root_source: str = "virtual",
) -> str:
    requires = "".join(f'    {{ name = "{d}", specifier = ">=1" }},\n' for d in deps)
    requires_dev = "".join(f'    {{ name = "{d}", specifier = ">=1" }},\n' for d in dev)
    text = "version = 1\n\n"
    for dep in (*deps, *dev):
        text += f'[[package]]\nname = "{dep}"\nversion = "1.0.0"\n\n'
    text += (
        f'[[package]]\nname = "{name}"\nversion = "0.0.0"\nsource = {{ {root_source} = "." }}\n\n'
    )
    if deps:
        text += f"[package.metadata]\nrequires-dist = [\n{requires}]\n\n"
    if dev:
        text += f"[package.metadata.requires-dev]\ndev = [\n{requires_dev}]\n"
    return text


def _check(tmp_path: Path, pyproject: str | None, lock: str | None) -> list[str]:
    files = {}
    if pyproject is not None:
        files["pyproject.toml"] = pyproject
    if lock is not None:
        files["uv.lock"] = lock
    return [f.message for f in check_pinned_deps(build_repo(tmp_path, files))]


def test_directory_without_pyproject_is_skipped(tmp_path: Path) -> None:
    assert check_pinned_deps(build_repo(tmp_path, {"a.py": "x = 1\n"})) == ()


def test_lock_without_pyproject_is_skipped(tmp_path: Path) -> None:
    assert _check(tmp_path, None, _lock(("a",))) == []


def test_pyproject_without_lockfile_fails(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"pyproject.toml": _pyproject(("a",))})
    (finding,) = check_pinned_deps(root)
    assert finding.rule_id == RULE_ID
    assert "uv.lock" in finding.message


def test_pyproject_without_dependencies_still_needs_a_lockfile(tmp_path: Path) -> None:
    assert len(_check(tmp_path, _pyproject(), None)) == 1


def test_lock_in_sync_passes(tmp_path: Path) -> None:
    assert _check(tmp_path, _pyproject(("a", "b"), ("t",)), _lock(("a", "b"), ("t",))) == []


def test_project_with_no_dependencies_and_a_bare_lock_passes(tmp_path: Path) -> None:
    assert _check(tmp_path, _pyproject(), _lock()) == []


def test_dependency_missing_from_lock_fails_and_is_named(tmp_path: Path) -> None:
    messages = _check(tmp_path, _pyproject(("a", "newdep")), _lock(("a",)))
    assert len(messages) == 1
    assert "newdep" in messages[0]


def test_dev_dependency_missing_from_lock_fails(tmp_path: Path) -> None:
    messages = _check(tmp_path, _pyproject(("a",), ("pytest",)), _lock(("a",)))
    assert len(messages) == 1 and "pytest" in messages[0]


def test_dependency_removed_from_pyproject_but_still_locked_fails(tmp_path: Path) -> None:
    messages = _check(tmp_path, _pyproject(("a",)), _lock(("a", "gone")))
    assert len(messages) == 1 and "gone" in messages[0]


def test_names_are_normalised_and_extras_and_markers_ignored(tmp_path: Path) -> None:
    pyproject = _pyproject(
        ("PyYAML>=6", "typing_extensions", "pydantic[email]>=2 ; python_version >= '3.12'")
    )
    lock = _lock(("pyyaml", "typing-extensions", "pydantic"))
    assert _check(tmp_path, pyproject, lock) == []


def test_include_group_entries_are_not_dependencies(tmp_path: Path) -> None:
    pyproject = (
        '[project]\nname = "demo"\nversion = "0"\ndependencies = ["a"]\n\n'
        '[dependency-groups]\ndev = ["t", {include-group = "lint"}]\nlint = ["ruff"]\n'
    )
    lock = _lock(("a",), ("t", "ruff"))
    assert _check(tmp_path, pyproject, lock) == []


def test_root_entry_is_found_by_editable_source_too(tmp_path: Path) -> None:
    assert _check(tmp_path, _pyproject(("a",)), _lock(("a",), root_source="editable")) == []


def test_lock_without_a_root_project_entry_fails(tmp_path: Path) -> None:
    messages = _check(tmp_path, _pyproject(("a",), name="mine"), _lock(("a",), name="other"))
    assert len(messages) == 1 and "mine" in messages[0]


def test_findings_point_at_the_lockfile(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"pyproject.toml": _pyproject(("a",)), "uv.lock": _lock()})
    assert [f.file for f in check_pinned_deps(root)] == ["uv.lock"]


@pytest.mark.parametrize("which", ["pyproject.toml", "uv.lock"])
def test_malformed_toml_is_a_config_error(tmp_path: Path, which: str) -> None:
    files = {"pyproject.toml": _pyproject(("a",)), "uv.lock": _lock(("a",))}
    root = build_repo(tmp_path, {**files, which: "not = [valid\n"})
    with pytest.raises(ConfigError, match=which):
        check_pinned_deps(root)


def test_project_table_without_name_is_a_config_error(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"pyproject.toml": "[tool.x]\na = 1\n", "uv.lock": "version = 1\n"})
    with pytest.raises(ConfigError, match="pyproject.toml"):
        check_pinned_deps(root)


_WITH_EXTRA = (
    '[project]\nname = "demo"\nversion = "0"\ndependencies = ["a"]\n\n'
    '[project.optional-dependencies]\ncloud = ["Cloud-Lib>=1"]\n'
)


def test_optional_dependency_locked_as_an_extra_passes(tmp_path: Path) -> None:
    assert _check(tmp_path, _WITH_EXTRA, _lock(("a", "cloud-lib"))) == []


def test_optional_dependency_missing_from_lock_fails_and_is_named(tmp_path: Path) -> None:
    messages = _check(tmp_path, _WITH_EXTRA, _lock(("a",)))
    assert len(messages) == 1 and "cloud-lib" in messages[0]
