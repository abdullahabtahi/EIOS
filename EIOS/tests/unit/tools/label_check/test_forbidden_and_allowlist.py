from __future__ import annotations

from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tests.support import secret_shapes
from tests.support.label_repo import REPO_ROOT, brand_literal, materialise
from tests.support.repo_builder import build_repo
from tools.label_check.allowlist import load_allowlist
from tools.label_check.scanner import scan_repo


def _rules(result) -> list[str]:  # type: ignore[no-untyped-def]
    return sorted(f.rule_id for f in result.findings)


def _tree(tmp_path: Path, doc: str) -> Path:
    root = materialise("clean", tmp_path / "t")
    (root / "docs" / "clean.md").unlink()
    build_repo(root, {"docs/extra.md": doc})
    return root


def test_brand_and_secret_shapes_are_forbidden(tmp_path: Path) -> None:
    doc = f"Rival {brand_literal()} here.\n\nKey {secret_shapes.cloud_access_key()}\n"
    result = scan_repo(_tree(tmp_path, doc))
    assert _rules(result) == ["label.forbidden-literal"] * 2
    assert brand_literal() not in "".join(f.message for f in result.findings)


def _allow(root: Path, entries: str) -> None:
    build_repo(root, {"config/label_allowlist.yaml": f"entries:\n{entries}"})


def test_allowlist_entry_suppresses_a_matching_finding(tmp_path: Path) -> None:
    root = _tree(tmp_path, f"Rival {brand_literal()} here.\n")
    _allow(
        root, f"  - path: docs/extra.md\n    literal: {brand_literal()}\n    reason: cited once\n"
    )
    assert scan_repo(root).findings == ()


def test_stale_allowlist_entry_is_reported(tmp_path: Path) -> None:
    root = _tree(tmp_path, "Nothing forbidden here.\n")
    _allow(root, "  - path: docs/extra.md\n    literal: nothing\n    reason: stale one\n")
    assert _rules(scan_repo(root)) == ["label.allowlist-stale"]


@pytest.mark.parametrize("reason", ['""', '"   "'])
def test_empty_reason_is_a_config_error(tmp_path: Path, reason: str) -> None:
    root = _tree(tmp_path, "Plain.\n")
    _allow(root, f"  - path: docs/extra.md\n    literal: x\n    reason: {reason}\n")
    with pytest.raises(ConfigError):
        scan_repo(root)


def test_shipped_allowlist_is_empty_and_loads() -> None:
    assert load_allowlist(REPO_ROOT / "config" / "label_allowlist.yaml") == ()
