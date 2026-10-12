from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from eios.llm_gateway.config import load_config
from tests.support.label_repo import REPO_ROOT, materialise
from tests.support.repo_builder import build_repo
from tools.label_check.scanner import scan_repo

GATEWAY = REPO_ROOT / "config" / "llm_gateway.dev.yaml"


def _tree(tmp_path: Path) -> Path:
    root = materialise("clean", tmp_path / "r")
    shutil.copy(GATEWAY, root / "config" / "llm_gateway.dev.yaml")
    return root


def test_shipped_gateway_config_is_clean(tmp_path: Path) -> None:
    assert scan_repo(_tree(tmp_path)).findings == ()


def test_removing_a_gateway_tag_fails_label_check_and_the_loader(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    path = root / "config" / "llm_gateway.dev.yaml"
    path.write_text(
        path.read_text("utf-8").replace('  daily_token_cap: "[ASSUMPTION]"\n', ""), "utf-8"
    )
    findings = scan_repo(root).findings
    assert [f.rule_id for f in findings] == ["label.structured-missing-tag"]
    assert "daily_token_cap" in findings[0].message
    with pytest.raises(ConfigError, match="daily_token_cap"):
        load_config(path)


def test_invalid_tag_value_is_flagged(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    path = root / "config" / "llm_gateway.dev.yaml"
    path.write_text(path.read_text("utf-8").replace('"[TARGET]"', '"[WISH]"'), "utf-8")
    assert [f.rule_id for f in scan_repo(root).findings] == ["label.structured-missing-tag"]


def test_cost_model_rows_need_a_tag(tmp_path: Path) -> None:
    root = materialise("clean", tmp_path / "r")
    build_repo(
        root, {"docs/cost_model.csv": "item,monthly,tag\ncompute,100,[ASSUMPTION]\nstore,40,\n"}
    )
    findings = scan_repo(root).findings
    assert [(f.file, f.line, f.rule_id) for f in findings] == [
        ("docs/cost_model.csv", 3, "label.structured-missing-tag")
    ]


def test_cost_model_without_tag_column_is_flagged(tmp_path: Path) -> None:
    root = materialise("clean", tmp_path / "r")
    build_repo(root, {"docs/cost_model.csv": "item,monthly\ncompute,100\n"})
    assert [f.rule_id for f in scan_repo(root).findings] == ["label.structured-missing-tag"]


def test_glob_matching_no_file_is_fine(tmp_path: Path) -> None:
    assert scan_repo(materialise("clean", tmp_path / "r")).findings == ()
