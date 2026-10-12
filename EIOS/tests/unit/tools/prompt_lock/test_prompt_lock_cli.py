"""T189 (FR-037): ``python -m tools.prompt_lock check|update`` guards the locked prompt files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tests.support.llm_gateway import DEFAULT_PROMPTS, write_prompt_tree
from tools.prompt_lock.__main__ import main

ID, V1 = "smoke-echo", "v1"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tree(tmp_path: Path) -> Path:
    write_prompt_tree(tmp_path / "prompts")
    return tmp_path


def _run(root: Path, command: str, *extra: str) -> int:
    return main([command, "--repo-root", str(root), *extra])


def _lock(root: Path) -> dict[str, list[dict[str, str]]]:
    loaded: dict[str, list[dict[str, str]]] = json.loads(
        (root / "prompts" / "prompts.lock.json").read_text(encoding="utf-8")
    )
    return loaded


def _findings(root: Path) -> list[dict[str, object]]:
    report = json.loads((root / "evals/reports/prompt_lock.json").read_text(encoding="utf-8"))
    findings: list[dict[str, object]] = report["findings"]
    return findings


def _entry(root: Path, prompt_id: str, version: str) -> dict[str, str]:
    (found,) = [
        e for e in _lock(root)["prompts"] if e["id"] == prompt_id and e["version"] == version
    ]
    return found


def test_check_passes_on_a_consistent_tree(tmp_path: Path) -> None:
    assert _run(_tree(tmp_path), "check") == 0


def test_check_fails_naming_id_and_version_when_the_hash_differs(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "prompts" / ID / "v1.md").write_text("edited\n", encoding="utf-8")
    assert _run(root, "check") == 1
    (finding,) = _findings(root)
    assert finding["rule_id"] == "prompt_lock.hash_mismatch"
    assert ID in str(finding["message"]) and V1 in str(finding["message"])
    assert finding["file"] == "prompts/smoke-echo/v1.md"


def test_check_fails_on_a_prompt_file_absent_from_the_lock(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "prompts" / ID / "v2.md").write_text("new\n", encoding="utf-8")
    assert _run(root, "check") == 1
    (finding,) = _findings(root)
    assert finding["rule_id"] == "prompt_lock.unlocked_file"
    assert ID in str(finding["message"]) and "v2" in str(finding["message"])


def test_check_fails_on_a_lock_entry_with_no_file(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    shutil_target = root / "prompts" / "triage-note"
    for child in shutil_target.iterdir():
        child.unlink()
    shutil_target.rmdir()
    assert _run(root, "check") == 1
    (finding,) = _findings(root)
    assert finding["rule_id"] == "prompt_lock.missing_file"
    assert "triage-note" in str(finding["message"])


def test_check_fails_when_a_locked_version_is_deleted(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    assert _run(root, "update") == 0  # nothing new, lock unchanged
    (root / "prompts" / ID / "v2.md").write_text("second\n", encoding="utf-8")
    assert _run(root, "update") == 0
    (root / "prompts" / ID / "v1.md").unlink()
    assert _run(root, "check") == 1
    (finding,) = _findings(root)
    assert finding["rule_id"] == "prompt_lock.missing_file"
    assert V1 in str(finding["message"])
    assert _entry(root, ID, "v2")["sha256"] == _sha("second\n")


def test_update_adds_a_new_version_and_check_then_passes(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "prompts" / ID / "v2.md").write_text("second\n", encoding="utf-8")
    assert _run(root, "update") == 0
    assert _entry(root, ID, "v2")["sha256"] == _sha("second\n")
    assert _run(root, "check") == 0


def test_update_adds_a_brand_new_prompt_id(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "prompts" / "fresh-prompt").mkdir()
    (root / "prompts" / "fresh-prompt" / "v1.md").write_text("hi {{x}}\n", encoding="utf-8")
    assert _run(root, "update") == 0
    assert _entry(root, "fresh-prompt", "v1")["sha256"] == _sha("hi {{x}}\n")


def test_update_creates_the_lock_when_it_does_not_exist(tmp_path: Path) -> None:
    prompt = tmp_path / "prompts" / "a-prompt" / "v1.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("text\n", encoding="utf-8")
    assert _run(tmp_path, "update") == 0
    assert _entry(tmp_path, "a-prompt", "v1")["sha256"] == _sha("text\n")


def test_update_never_rewrites_the_hash_of_an_existing_version(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    before = (root / "prompts" / "prompts.lock.json").read_bytes()
    (root / "prompts" / ID / "v1.md").write_text("edited\n", encoding="utf-8")
    assert _run(root, "update") == 1  # the edit is reported, not accepted
    assert (root / "prompts" / "prompts.lock.json").read_bytes() == before
    (finding,) = _findings(root)
    assert finding["rule_id"] == "prompt_lock.hash_mismatch"
    assert "new version" in str(finding["message"])


def test_update_keeps_entries_whose_file_was_deleted(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    before = (root / "prompts" / "prompts.lock.json").read_bytes()
    (root / "prompts" / ID / "v1.md").unlink()
    assert _run(root, "update") == 1
    assert (root / "prompts" / "prompts.lock.json").read_bytes() == before


def test_update_output_is_sorted_and_byte_stable(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    for name in ("v10", "v2", "v3"):
        (root / "prompts" / ID / f"{name}.md").write_text(f"{name}\n", encoding="utf-8")
    (root / "prompts" / "alpha-first").mkdir()
    (root / "prompts" / "alpha-first" / "v1.md").write_text("a\n", encoding="utf-8")
    assert _run(root, "update") == 0
    first = (root / "prompts" / "prompts.lock.json").read_bytes()
    keys = [(e["id"], e["version"]) for e in _lock(root)["prompts"]]
    assert keys == [
        ("alpha-first", "v1"),
        (ID, "v1"),
        (ID, "v2"),
        (ID, "v3"),
        (ID, "v10"),
        ("triage-note", "v1"),
    ]
    assert _run(root, "update") == 0
    assert (root / "prompts" / "prompts.lock.json").read_bytes() == first
    assert first.endswith(b"}\n") and b"\r" not in first
    expected = json.dumps(_lock(root), indent=2) + "\n"
    assert first.decode("utf-8") == expected


def test_findings_are_sorted(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "prompts" / "triage-note" / "v2.md").write_text("n\n", encoding="utf-8")
    (root / "prompts" / ID / "v1.md").write_text("edited\n", encoding="utf-8")
    assert _run(root, "check") == 1
    files = [str(f["file"]) for f in _findings(root)]
    assert files == sorted(files)


def test_prompts_dir_option_selects_a_directory_outside_the_default(tmp_path: Path) -> None:
    other = write_prompt_tree(tmp_path / "elsewhere", DEFAULT_PROMPTS)
    root = tmp_path / "repo"
    root.mkdir()
    assert _run(root, "check", "--prompts-dir", str(other)) == 0
    (other / ID / "v1.md").write_text("edited\n", encoding="utf-8")
    assert _run(root, "check", "--prompts-dir", str(other)) == 1


def test_relative_prompts_dir_is_resolved_against_the_repo_root(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_prompt_tree(root / "alt")
    assert _run(root, "check", "--prompts-dir", "alt") == 0


def test_exit_2_without_a_lockfile(tmp_path: Path) -> None:
    (tmp_path / "prompts").mkdir()
    assert _run(tmp_path, "check") == 2


def test_exit_2_for_a_malformed_lockfile(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "prompts" / "prompts.lock.json").write_text("{not json", encoding="utf-8")
    assert _run(root, "check") == 2
    assert _run(root, "update") == 2


def test_exit_2_for_a_bad_command_or_repo_root(tmp_path: Path) -> None:
    assert main(["frobnicate", "--repo-root", str(tmp_path)]) == 2
    assert main(["--repo-root", str(tmp_path)]) == 2
    assert main(["check", "--repo-root", str(tmp_path / "missing")]) == 2
    assert main(["check", "--no-such-flag"]) == 2


def test_a_misnamed_prompt_file_is_a_finding(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "prompts" / ID / "notes.md").write_text("x\n", encoding="utf-8")
    assert _run(root, "check") == 1
    (finding,) = _findings(root)
    assert finding["rule_id"] == "prompt_lock.invalid_name"


def test_check_reports_via_stdout_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(_tree(tmp_path), "check") == 0
    assert "prompt_lock" in capsys.readouterr().out
