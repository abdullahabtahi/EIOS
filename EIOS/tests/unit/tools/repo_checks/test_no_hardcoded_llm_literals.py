"""T113 (SC-006): no model identifiers, prices or provider names are hard-coded in application code.

Also proves the ruff banned-API list equals the vendor-SDK list in ``config/open_decisions.yaml``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.support.open_decision_repo import (
    PROVIDERS_DIR,
    REPO_ROOT,
    adr002_modules,
    model_identifiers,
    price_shapes,
    provider_name,
    rule_params,
)
from tests.support.repo_builder import build_repo
from tools.repo_checks.forbidden_literals import (
    CONFIG_PATH,
    RULE_ID,
    ForbiddenPattern,
    load_patterns,
    scan_patterns,
)

PYPROJECT = REPO_ROOT / "pyproject.toml"
SOURCE_TREES = ("src", "services", "tools")
ID_MODEL = "llm-model-identifier"
ID_PRICE = "llm-price-shape"
ID_PROVIDER = "llm-provider-name"
LLM_PATTERN_IDS = (ID_MODEL, ID_PRICE, ID_PROVIDER)


def _llm_patterns(root: Path) -> tuple[ForbiddenPattern, ...]:
    return tuple(p for p in load_patterns(root / CONFIG_PATH) if p.id in LLM_PATTERN_IDS)


def _plant(tmp_path: Path, files: dict[str, str]) -> Path:
    """A throwaway repo that carries the real pattern config plus ``files``."""
    config = (REPO_ROOT / CONFIG_PATH).read_text(encoding="utf-8")
    return build_repo(tmp_path, {CONFIG_PATH: config, **files})


def _banned_api() -> dict[str, dict[str, str]]:
    with PYPROJECT.open("rb") as handle:
        data = tomllib.load(handle)
    table = data["tool"]["ruff"]["lint"]["flake8-tidy-imports"]["banned-api"]
    assert isinstance(table, dict)
    return {k: v for k, v in table.items() if not k.startswith("opentelemetry.")}


def test_the_three_llm_literal_classes_are_configured() -> None:
    assert {p.id for p in _llm_patterns(REPO_ROOT)} == set(LLM_PATTERN_IDS)


def test_the_literal_classes_are_allowed_only_in_config_and_providers() -> None:
    for pattern in _llm_patterns(REPO_ROOT):
        assert "config/" in pattern.allowlist, pattern.id
        assert "src/eios/llm_gateway/providers/" in pattern.allowlist, pattern.id
        assert pattern.reason, pattern.id


def test_application_code_has_no_model_identifier_price_or_provider_name() -> None:
    other = [e.name for e in REPO_ROOT.iterdir() if e.name not in SOURCE_TREES]
    findings = scan_patterns(REPO_ROOT, _llm_patterns(REPO_ROOT), exclude=other)
    assert findings == (), [(f.file, f.line, f.message) for f in findings]


@pytest.mark.parametrize(
    ("pattern_id", "text"),
    [
        *((ID_MODEL, f"MODEL = '{m}'\n") for m in model_identifiers()),
        *((ID_PRICE, f"PRICE = '{p}'\n") for p in price_shapes()),
        (ID_PROVIDER, f"client = {provider_name()}()\n"),
        (ID_PROVIDER, f"# provider: {provider_name().lower()}\n"),
    ],
)
def test_planted_violation_is_detected_with_file_and_line(
    tmp_path: Path, pattern_id: str, text: str
) -> None:
    root = _plant(tmp_path, {"src/eios/agent.py": "ok = 1\n" + text})
    findings = scan_patterns(root, _llm_patterns(root))
    assert [(f.file, f.line, f.rule_id) for f in findings] == [("src/eios/agent.py", 2, RULE_ID)]
    assert pattern_id in findings[0].message


def test_the_same_text_is_allowed_in_config_and_in_providers(tmp_path: Path) -> None:
    text = f"m = '{model_identifiers()[0]}'\nc = {provider_name()}()\np = '{price_shapes()[0]}'\n"
    root = _plant(tmp_path, {"config/gateway.yaml": text, f"{PROVIDERS_DIR}/real.py": text})
    assert scan_patterns(root, _llm_patterns(root)) == ()


def test_unrelated_text_is_not_flagged(tmp_path: Path) -> None:
    benign = "model = 'stub'\nprovider = 'stub'\nbudget_tokens = 1000\nrate = 3\nname = 'gpt'\n"
    root = _plant(tmp_path, {"src/eios/a.py": benign})
    assert scan_patterns(root, _llm_patterns(root)) == ()


# --- ruff banned-API list equals the vendor-SDK list ----------------------------------------


def test_ruff_banned_api_equals_the_vendor_sdk_list() -> None:
    assert set(_banned_api()) == set(adr002_modules())
    assert len(_banned_api()) == len(adr002_modules()), "duplicate vendor SDK entries"


def test_every_banned_api_entry_explains_itself() -> None:
    for module, entry in _banned_api().items():
        assert entry.get("msg"), module


def test_open_decision_model_patterns_agree_with_the_literal_config() -> None:
    wanted = rule_params("ADR-002", "model_identifier_patterns")["patterns"]
    assert isinstance(wanted, list)
    literal = next(p for p in _llm_patterns(REPO_ROOT) if p.id == ID_MODEL).regex
    benign = ("model = 'stub'", "name = 'gpt'", "x = 1", "llama = 'animal'")
    for line in (*model_identifiers(), *benign):
        by_decision = any(re.search(pattern, line) for pattern in wanted)
        assert bool(literal.search(line)) == by_decision, line
    for pattern in wanted:
        assert re.compile(pattern).flags & re.IGNORECASE, pattern


def test_forbidden_literal_config_mentions_no_single_pattern_twice() -> None:
    raw = yaml.safe_load((REPO_ROOT / CONFIG_PATH).read_text(encoding="utf-8"))
    ids = [entry["id"] for entry in raw["patterns"]]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("module", sorted(adr002_modules()))
def test_ruff_flags_a_vendor_import_through_banned_api(tmp_path: Path, module: str) -> None:
    ruff = shutil.which("ruff")
    if ruff is None:
        pytest.skip("ruff executable not on PATH")
    probe = tmp_path / "probe.py"
    probe.write_text(f"import {module}\n", encoding="utf-8")
    command = [ruff, "check", "--config", str(PYPROJECT), "--select", "TID251", "--no-cache"]
    done = subprocess.run(  # noqa: S603
        [*command, "--output-format", "concise", str(probe)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1, done.stdout + done.stderr
    assert "TID251" in done.stdout
