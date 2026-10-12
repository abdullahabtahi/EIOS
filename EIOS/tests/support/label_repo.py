"""Materialise label_check fixture trees: real config copied in, placeholders filled at run time."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from tests.support import secret_shapes

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "label_check"
_COPIED_CONFIG = ("labels.yaml", "label_allowlist.yaml", "forbidden_literals.yaml")


def brand_literal() -> str:
    """First competitor-brand alternative from the real forbidden-literals config."""
    text = (REPO_ROOT / "config" / "forbidden_literals.yaml").read_text(encoding="utf-8")
    entry = text.split("id: competitor-brand", 1)[1]
    group = re.search(r"\(\?:([^)]+)\)", entry)
    assert group is not None, "competitor-brand regex has no alternation group"
    return group.group(1).split("|")[0]


def materialise(name: str, dest: Path) -> Path:
    """Copy fixture ``name`` into ``dest``, add the real config and fill the placeholders."""
    shutil.copytree(FIXTURES / name, dest, dirs_exist_ok=True)
    (dest / "config").mkdir(exist_ok=True)
    for config in _COPIED_CONFIG:
        shutil.copy(REPO_ROOT / "config" / config, dest / "config" / config)
    replacements = {"{{BRAND}}": brand_literal(), "{{SECRET}}": secret_shapes.cloud_access_key()}
    for doc in dest.rglob("*.md"):
        text = doc.read_text(encoding="utf-8")
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)
        doc.write_text(text, encoding="utf-8")
    return dest
