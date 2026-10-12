"""T028: a non-frozen model class under src/eios is flagged (ast based)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.repo_builder import build_repo
from tools.repo_checks.frozen_models import RULE_ID, check_frozen_models

_PYDANTIC = "from pydantic import BaseModel, ConfigDict\n\n"
_DATACLASS_IMPORTS = "import dataclasses\nfrom dataclasses import dataclass\n\n"


def _flagged(tmp_path: Path, source: str, name: str = "src/eios/m.py") -> list[tuple[str, int]]:
    root = build_repo(tmp_path, {name: source})
    return [(f.file, f.line) for f in check_frozen_models(root)]


def test_plain_basemodel_is_flagged_with_file_and_line(tmp_path: Path) -> None:
    source = _PYDANTIC + "\nclass M(BaseModel):\n    x: int\n"
    assert _flagged(tmp_path, source) == [("src/eios/m.py", 4)]


def test_rule_id_and_message_name_the_class(tmp_path: Path) -> None:
    root = build_repo(
        tmp_path, {"src/eios/m.py": _PYDANTIC + "class Thing(BaseModel):\n    x: int\n"}
    )
    (finding,) = check_frozen_models(root)
    assert finding.rule_id == RULE_ID
    assert "Thing" in finding.message


def test_basemodel_with_frozen_model_config_is_fine(tmp_path: Path) -> None:
    source = _PYDANTIC + "class M(BaseModel):\n    model_config = ConfigDict(frozen=True)\n"
    assert _flagged(tmp_path, source) == []


def test_basemodel_with_frozen_class_keyword_is_fine(tmp_path: Path) -> None:
    assert _flagged(tmp_path, _PYDANTIC + "class M(BaseModel, frozen=True):\n    x: int\n") == []


def test_basemodel_with_dict_model_config_is_fine(tmp_path: Path) -> None:
    source = _PYDANTIC + "class M(BaseModel):\n    model_config = {'frozen': True}\n"
    assert _flagged(tmp_path, source) == []


def test_annotated_model_config_is_fine(tmp_path: Path) -> None:
    source = (
        "from typing import ClassVar\n" + _PYDANTIC + "class M(BaseModel):\n"
        "    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)\n"
    )
    assert _flagged(tmp_path, source) == []


@pytest.mark.parametrize(
    "config", ["ConfigDict(frozen=False)", "ConfigDict(extra='forbid')", "ConfigDict(frozen=FLAG)"]
)
def test_basemodel_config_that_is_not_provably_frozen_is_flagged(
    tmp_path: Path, config: str
) -> None:
    source = _PYDANTIC + f"FLAG = True\n\nclass M(BaseModel):\n    model_config = {config}\n"
    assert len(_flagged(tmp_path, source)) == 1


def test_attribute_form_of_basemodel_is_flagged(tmp_path: Path) -> None:
    source = "import pydantic\n\nclass M(pydantic.BaseModel):\n    x: int\n"
    assert len(_flagged(tmp_path, source)) == 1


def test_strictmodel_subclass_is_already_frozen(tmp_path: Path) -> None:
    source = "from eios.common.validation import StrictModel\n\nclass M(StrictModel):\n    x: int\n"
    assert _flagged(tmp_path, source) == []


def test_strictmodel_subclass_that_unfreezes_itself_is_flagged(tmp_path: Path) -> None:
    source = (
        "from pydantic import ConfigDict\n"
        "from eios.common.validation import StrictModel\n\n"
        "class M(StrictModel):\n    model_config = ConfigDict(frozen=False)\n"
    )
    assert len(_flagged(tmp_path, source)) == 1


def test_bare_dataclass_is_flagged(tmp_path: Path) -> None:
    source = "from dataclasses import dataclass\n\n@dataclass\nclass D:\n    x: int\n"
    assert _flagged(tmp_path, source) == [("src/eios/m.py", 4)]


@pytest.mark.parametrize(
    "decorator",
    [
        "@dataclass()",
        "@dataclass(slots=True)",
        "@dataclass(frozen=False)",
        "@dataclasses.dataclass",
    ],
)
def test_dataclass_without_frozen_true_is_flagged(tmp_path: Path, decorator: str) -> None:
    source = _DATACLASS_IMPORTS + f"{decorator}\nclass D:\n    x: int\n"
    assert len(_flagged(tmp_path, source)) == 1


@pytest.mark.parametrize(
    "decorator",
    [
        "@dataclass(frozen=True)",
        "@dataclass(frozen=True, slots=True)",
        "@dataclasses.dataclass(frozen=True)",
    ],
)
def test_frozen_dataclass_is_fine(tmp_path: Path, decorator: str) -> None:
    source = _DATACLASS_IMPORTS + f"{decorator}\nclass D:\n    x: int\n"
    assert _flagged(tmp_path, source) == []


def test_ordinary_classes_are_ignored(tmp_path: Path) -> None:
    source = "class Plain:\n    x = 1\n\nclass Child(Plain, dict):\n    pass\n"
    assert _flagged(tmp_path, source) == []


def test_nested_classes_are_checked(tmp_path: Path) -> None:
    source = (
        _PYDANTIC + "def make():\n    class Inner(BaseModel):\n        x: int\n    return Inner\n"
    )
    assert _flagged(tmp_path, source) == [("src/eios/m.py", 4)]


def test_subpackages_are_walked(tmp_path: Path) -> None:
    source = _PYDANTIC + "class M(BaseModel):\n    x: int\n"
    assert _flagged(tmp_path, source, "src/eios/llm_gateway/types.py") == [
        ("src/eios/llm_gateway/types.py", 3)
    ]


def test_code_outside_src_eios_is_not_checked(tmp_path: Path) -> None:
    source = _PYDANTIC + "class M(BaseModel):\n    x: int\n"
    root = build_repo(
        tmp_path, {"tools/m.py": source, "tests/m.py": source, "src/other/m.py": source}
    )
    assert check_frozen_models(root) == ()


def test_exclude_paths_are_skipped(tmp_path: Path) -> None:
    source = _PYDANTIC + "class M(BaseModel):\n    x: int\n"
    root = build_repo(tmp_path, {"src/eios/gen/m.py": source})
    assert check_frozen_models(root, exclude=("src/eios/gen",)) == ()


def test_absent_src_tree_means_nothing_to_check(tmp_path: Path) -> None:
    assert check_frozen_models(tmp_path) == ()


def test_unparsable_file_is_reported_as_a_finding(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"src/eios/bad.py": "class (:\n"})
    (finding,) = check_frozen_models(root)
    assert (finding.file, finding.rule_id) == ("src/eios/bad.py", RULE_ID)
    assert "parse" in finding.message
