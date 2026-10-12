"""The F00 governed documents themselves carry valid labels."""

from __future__ import annotations

from tests.support.label_repo import REPO_ROOT
from tools.label_check.scanner import scan_repo


def test_f00_docs_have_zero_findings() -> None:
    result = scan_repo(REPO_ROOT)
    assert [(f.file, f.line, f.rule_id) for f in result.findings] == []
    assert len(result.scanned) > 0
