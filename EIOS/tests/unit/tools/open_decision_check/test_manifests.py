"""Manifest parsers behind the ``manifest_dependency`` rule kind."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.repo_builder import build_repo
from tools.open_decision_check.config import RuleSpec, ScanScope
from tools.open_decision_check.manifests import (
    ManifestError,
    dependency_names,
    names_matching,
    normalize,
)
from tools.open_decision_check.rules import build_rule
from tools.open_decision_check.rules_base import SourceFile
from tools.open_decision_check.scan import read_files


def _names(filename: str, text: str) -> list[str]:
    return [name for name, _ in dependency_names(filename, text)]


def test_normalize_folds_case_and_separators() -> None:
    assert normalize(" Foo_Bar.Baz ") == "foo-bar-baz"


def test_names_matching_uses_normalized_globs() -> None:
    declared = (("Cube_JS", 1), ("lodash", 2), ("@scope/pkg", 3))
    assert names_matching(declared, ["cube-js", "@scope/*"]) == (("Cube_JS", 1), ("@scope/pkg", 3))


def test_npm_lockfile_v1_nested_dependencies_are_read() -> None:
    text = json.dumps({"dependencies": {"a": {"dependencies": {"b": {}}}}})
    assert _names("package-lock.json", text) == ["a", "b"]


def test_pyproject_groups_and_poetry_tables_are_read() -> None:
    text = """
[project]
name = "x"
dependencies = ["alpha>=1"]
[project.optional-dependencies]
extra = ["beta[x]; python_version > '3'"]
[dependency-groups]
dev = ["gamma", {include-group = "other"}]
[build-system]
requires = ["delta"]
[tool.uv]
dev-dependencies = ["epsilon"]
[tool.poetry.dependencies]
zeta = "^1"
[tool.poetry.dev-dependencies]
eta = "^1"
"""
    assert set(_names("pyproject.toml", text)) == {
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta",
    }  # fmt: skip


def test_poetry_lock_and_requirements_comments_and_options() -> None:
    assert _names("poetry.lock", '[[package]]\nname = "pkg"\n') == ["pkg"]
    text = "# comment\n-r base.txt\n\nfoo==1 # note\nBar_Baz>=2\n"
    assert _names("requirements.txt", text) == ["foo", "Bar_Baz"]


def test_yarn_and_pnpm_lockfiles_are_read() -> None:
    yarn = (
        '# yarn lockfile v1\n\n"@scope/pkg@^1.0.0", "@scope/pkg@^1.1":\n  version "1"\n'
        '\nfoo@^1:\n  version "1"\n'
    )
    assert set(_names("yarn.lock", yarn)) >= {"@scope/pkg", "foo"}
    pnpm = "packages:\n\n  /foo@1.0.0:\n    resolution: {}\n  /@scope/pkg@2.0.0:\n"
    assert set(_names("pnpm-lock.yaml", pnpm)) >= {"foo", "@scope/pkg"}


@pytest.mark.parametrize(
    ("filename", "text"),
    [
        ("package.json", "{not json"),
        ("package.json", "[1, 2]"),
        ("pyproject.toml", "not = = toml"),
        ("uv.lock", "[[package"),
        ("Cargo.toml", ""),
    ],
)
def test_unparseable_or_unsupported_manifests_raise(filename: str, text: str) -> None:
    with pytest.raises(ManifestError):
        dependency_names(filename, text)


def test_the_rule_fails_closed_on_an_unparseable_manifest() -> None:
    rule = build_rule(RuleSpec("r", "manifest_dependency", {"names": ["x"]}, "w"))
    hits = list(rule.check([SourceFile("a/package.json", "{broken")]))
    assert [(h.file, h.line) for h in hits] == [("a/package.json", 1)]
    assert "cannot be ruled out" in hits[0].message


def test_a_non_utf8_file_is_read_as_empty_but_still_matches_by_name(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {})
    (root / "blob.graphql").write_bytes(b"\xff\xfe\x00")
    rule = build_rule(RuleSpec("r", "file_pattern", {"patterns": ["**/*.graphql"]}, "w"))
    scope = ScanScope((".graphql",), ())
    files = read_files(root, scope, [rule])
    assert [(f.path, f.text) for f in files] == [("blob.graphql", "")]
