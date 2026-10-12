"""SC-007: label_check finds every seeded violation and none in the clean tree."""

from __future__ import annotations

import json
from pathlib import Path

from tests.support.label_repo import FIXTURES, materialise
from tools.label_check.scanner import scan_repo


def test_seeded_recall_is_one(tmp_path: Path) -> None:
    root = materialise("seeded", tmp_path / "seeded")
    expected = {
        (e["file"], e["line"], e["rule_id"])
        for e in json.loads((FIXTURES / "seeded" / "expected.json").read_text("utf-8"))
    }
    found = {(f.file, f.line, f.rule_id) for f in scan_repo(root).findings}
    assert expected <= found
    assert len(expected) / len(expected & found) == 1.0


def test_clean_tree_has_zero_findings_and_scans_files(tmp_path: Path) -> None:
    result = scan_repo(materialise("clean", tmp_path / "clean"))
    assert result.findings == ()
    assert len(result.scanned) > 0
