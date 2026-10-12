"""T028: config patterns are flagged with file and line unless the path is allowlisted."""

from __future__ import annotations

from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tests.support.repo_builder import build_repo
from tools.repo_checks.forbidden_literals import (
    CONFIG_PATH,
    RULE_ID,
    check_forbidden_literals,
    load_patterns,
)

_NEEDLE = "zzneedle"


def _config(*entries: str) -> str:
    return "patterns:\n" + "".join(entries) if entries else "patterns: []\n"


def _entry(
    ident: str = "needle",
    regex: str = _NEEDLE,
    allowlist: tuple[str, ...] = (),
    reason: str = "test pattern",
) -> str:
    allow = "".join(f"      - {path}\n" for path in allowlist)
    allow_block = f"    allowlist:\n{allow}" if allowlist else "    allowlist: []\n"
    return f"  - id: {ident}\n    regex: '{regex}'\n{allow_block}    reason: {reason}\n"


def _repo(tmp_path: Path, config: str, files: dict[str, str]) -> Path:
    return build_repo(tmp_path, {CONFIG_PATH: config, **files})


def test_empty_pattern_list_flags_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path, _config(), {"a.py": f"x = '{_NEEDLE}'\n"})
    assert check_forbidden_literals(root) == ()


def test_missing_config_means_no_patterns(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"a.py": f"x = '{_NEEDLE}'\n"})
    assert check_forbidden_literals(root) == ()


def test_match_is_flagged_with_file_and_line(tmp_path: Path) -> None:
    root = _repo(tmp_path, _config(_entry()), {"src/a.py": f"ok = 1\nbad = '{_NEEDLE}'\n"})
    findings = check_forbidden_literals(root)
    assert [(f.file, f.line, f.rule_id) for f in findings] == [("src/a.py", 2, RULE_ID)]


def test_message_names_pattern_and_reason_but_not_the_matched_text(tmp_path: Path) -> None:
    root = _repo(tmp_path, _config(_entry(ident="p1", reason="no needles")), {"a.py": _NEEDLE})
    message = check_forbidden_literals(root)[0].message
    assert "p1" in message
    assert "no needles" in message
    assert _NEEDLE not in message


def test_each_matching_line_is_reported(tmp_path: Path) -> None:
    root = _repo(tmp_path, _config(_entry()), {"a.txt": f"{_NEEDLE}\nclean\n{_NEEDLE}\n"})
    assert [f.line for f in check_forbidden_literals(root)] == [1, 3]


def test_several_patterns_are_all_applied(tmp_path: Path) -> None:
    config = _config(_entry("one", "alpha"), _entry("two", "beta"))
    root = _repo(tmp_path, config, {"a.txt": "alpha\nbeta\n"})
    messages = [f.message for f in check_forbidden_literals(root)]
    assert len(messages) == 2
    assert "one" in messages[0] and "two" in messages[1]


def test_exact_path_allowlist_suppresses_the_finding(tmp_path: Path) -> None:
    config = _config(_entry(allowlist=("src/a.py",)))
    root = _repo(tmp_path, config, {"src/a.py": _NEEDLE, "src/b.py": _NEEDLE})
    assert [f.file for f in check_forbidden_literals(root)] == ["src/b.py"]


def test_directory_allowlist_covers_nested_files(tmp_path: Path) -> None:
    config = _config(_entry(allowlist=("tests/fixtures/",)))
    root = _repo(tmp_path, config, {"tests/fixtures/x/a.txt": _NEEDLE, "tests/b.txt": _NEEDLE})
    assert [f.file for f in check_forbidden_literals(root)] == ["tests/b.txt"]


def test_glob_allowlist_is_supported(tmp_path: Path) -> None:
    config = _config(_entry(allowlist=("docs/*.md",)))
    root = _repo(tmp_path, config, {"docs/a.md": _NEEDLE, "src/a.py": _NEEDLE})
    assert [f.file for f in check_forbidden_literals(root)] == ["src/a.py"]


def test_allowlist_is_per_pattern(tmp_path: Path) -> None:
    config = _config(_entry("one", "alpha", allowlist=("a.txt",)), _entry("two", "beta"))
    root = _repo(tmp_path, config, {"a.txt": "alpha beta\n"})
    findings = check_forbidden_literals(root)
    assert len(findings) == 1 and "two" in findings[0].message


def test_binary_and_non_utf8_files_are_skipped(tmp_path: Path) -> None:
    root = _repo(tmp_path, _config(_entry()), {})
    (root / "blob.bin").write_bytes(b"\xff\xfe\x00" + _NEEDLE.encode())
    assert check_forbidden_literals(root) == ()


@pytest.mark.parametrize("skipped", [".venv/a.py", "node_modules/a.js", "evals/reports/a.json"])
def test_vendored_and_generated_trees_are_skipped(tmp_path: Path, skipped: str) -> None:
    root = _repo(tmp_path, _config(_entry()), {skipped: _NEEDLE})
    assert check_forbidden_literals(root) == ()


def test_exclude_paths_are_skipped(tmp_path: Path) -> None:
    root = _repo(tmp_path, _config(_entry()), {"FEIOS/a.js": _NEEDLE})
    assert check_forbidden_literals(root, exclude=("FEIOS",)) == ()


def test_symlink_pointing_outside_the_repo_is_never_read(tmp_path: Path) -> None:
    outside = build_repo(tmp_path / "outside", {"s.txt": _NEEDLE})
    root = _repo(tmp_path / "repo", _config(_entry()), {})
    (root / "link.txt").symlink_to(outside / "s.txt")
    assert check_forbidden_literals(root) == ()


@pytest.mark.parametrize(
    "config",
    [
        "patterns: [{regex: x, allowlist: [], reason: r}]\n",
        "patterns: [{id: a, allowlist: [], reason: r}]\n",
        "patterns: [{id: a, regex: x, allowlist: []}]\n",
        "patterns: [{id: a, regex: x, allowlist: [], reason: r, extra: 1}]\n",
        "patterns: [{id: a, regex: '(', allowlist: [], reason: r}]\n",
        "patterns: [{id: a, regex: '', allowlist: [], reason: r}]\n",
        "patterns: [{id: a, regex: x, allowlist: [], reason: r},"
        " {id: a, regex: y, allowlist: [], reason: r}]\n",
        "patterns: not-a-list\n",
        "other: []\n",
        "patterns: [unclosed\n",
    ],
)
def test_malformed_config_is_a_config_error_naming_the_file(tmp_path: Path, config: str) -> None:
    root = build_repo(tmp_path, {CONFIG_PATH: config})
    with pytest.raises(ConfigError, match="forbidden_literals.yaml"):
        load_patterns(root / CONFIG_PATH)


def test_load_patterns_returns_immutable_entries(tmp_path: Path) -> None:
    root = _repo(tmp_path, _config(_entry(allowlist=("a.py",))), {})
    (pattern,) = load_patterns(root / CONFIG_PATH)
    assert (pattern.id, pattern.allowlist, pattern.reason) == ("needle", ("a.py",), "test pattern")
    assert pattern.regex.search(_NEEDLE)


def test_the_pattern_config_is_never_scanned_against_itself(tmp_path: Path) -> None:
    root = _repo(tmp_path, _config(_entry()), {})
    assert check_forbidden_literals(root) == ()
