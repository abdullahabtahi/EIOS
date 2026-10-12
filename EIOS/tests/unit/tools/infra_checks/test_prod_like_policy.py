"""T060 (FR-015): prod-like keeps stateful services warm and has a real signing key."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.infra_tree import env_main, good_files, patched, with_file
from tests.support.repo_builder import build_repo
from tools.common.findings import Finding
from tools.infra_checks.hcl import load_infra
from tools.infra_checks.policy import check_prod_like

PROD = "infra/envs/prod-like/main.tf"


def _check(tmp_path: Path, files: dict[str, str]) -> tuple[Finding, ...]:
    return check_prod_like(load_infra(build_repo(tmp_path, files)))


def _rules(findings: tuple[Finding, ...]) -> set[str]:
    return {f.rule_id for f in findings}


def test_valid_tree_passes(tmp_path: Path) -> None:
    assert _check(tmp_path, good_files()) == ()


def test_dev_and_stage_are_exempt(tmp_path: Path) -> None:
    files = good_files()
    for env in ("dev", "stage"):
        assert "min_instances         = 0" in files[f"infra/envs/{env}/main.tf"]
        assert "signing_key_enabled = false" in files[f"infra/envs/{env}/main.tf"]
    assert _check(tmp_path, files) == ()


def test_prod_like_with_zero_minimum_instances_is_flagged(tmp_path: Path) -> None:
    files = with_file(good_files(), PROD, env_main("prod-like", min_instances=0))
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.prod_like.min_instances"}
    assert len(findings) == 2
    assert findings[0].file == PROD
    assert findings[0].line > 0


def test_one_warm_service_is_not_enough(tmp_path: Path) -> None:
    text = env_main("prod-like")
    first = text.index("min_instances         = 1")
    files = with_file(
        good_files(),
        PROD,
        text[:first]
        + "min_instances         = 0"
        + text[first + len("min_instances         = 1") :],
    )
    findings = _check(tmp_path, files)
    assert [f.rule_id for f in findings] == ["infra.prod_like.min_instances"]


def test_missing_min_instances_argument_is_flagged(tmp_path: Path) -> None:
    files = patched(good_files(), PROD, "  min_instances         = 1\n", "")
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.prod_like.min_instances"}
    assert "does not set" in findings[0].message


def test_min_instances_from_a_variable_default_is_resolved(tmp_path: Path) -> None:
    text = env_main("prod-like").replace(
        "min_instances         = 1", "min_instances         = var.warm"
    )
    text += 'variable "warm" {\n  type    = number\n  default = 2\n}\n'
    assert _check(tmp_path, with_file(good_files(), PROD, text)) == ()


def test_unresolvable_min_instances_is_flagged(tmp_path: Path) -> None:
    text = env_main("prod-like").replace(
        "min_instances         = 1", "min_instances         = var.warm"
    )
    text += 'variable "warm" {\n  type = number\n}\n'
    findings = _check(tmp_path, with_file(good_files(), PROD, text))
    assert _rules(findings) == {"infra.prod_like.min_instances"}
    assert "cannot be proven" in findings[0].message


def test_variable_default_of_zero_is_flagged(tmp_path: Path) -> None:
    text = env_main("prod-like").replace(
        "min_instances         = 1", "min_instances         = var.warm"
    )
    text += 'variable "warm" {\n  default = 0\n}\n'
    findings = _check(tmp_path, with_file(good_files(), PROD, text))
    assert _rules(findings) == {"infra.prod_like.min_instances"}


def test_signing_key_disabled_is_flagged(tmp_path: Path) -> None:
    files = with_file(good_files(), PROD, env_main("prod-like", signing=False))
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.prod_like.signing_key"}


def test_signing_key_flag_from_variable_default_true_is_accepted(tmp_path: Path) -> None:
    text = env_main("prod-like").replace(
        "signing_key_enabled = true", "signing_key_enabled = var.sign"
    )
    text += 'variable "sign" {\n  default = true\n}\n'
    assert _check(tmp_path, with_file(good_files(), PROD, text)) == ()


def test_prod_like_without_a_secret_store_module_is_flagged(tmp_path: Path) -> None:
    text = env_main("prod-like")
    start = text.index('module "secret_store"')
    end = text.index('module "eval_truth_store"')
    files = with_file(good_files(), PROD, text[:start] + text[end:])
    assert _rules(_check(tmp_path, files)) == {"infra.prod_like.signing_key"}


def test_enabled_flag_without_a_key_resource_in_the_module_is_flagged(tmp_path: Path) -> None:
    files = with_file(
        good_files(), "infra/modules/secret_store/main.tf", 'resource "terraform_data" "x" {}\n'
    )
    assert _rules(_check(tmp_path, files)) == {"infra.prod_like.signing_key"}


def test_a_direct_kms_signing_key_resource_is_accepted(tmp_path: Path) -> None:
    text = env_main("prod-like", signing=False) + (
        'resource "google_kms_crypto_key" "signing" {\n'
        '  name    = "signing"\n  purpose = "ASYMMETRIC_SIGN"\n'
        '  version_template {\n    algorithm = "EC_SIGN_P256_SHA256"\n  }\n}\n'
    )
    assert _check(tmp_path, with_file(good_files(), PROD, text)) == ()


def test_encryption_only_key_is_not_a_signing_key(tmp_path: Path) -> None:
    text = env_main("prod-like", signing=False) + (
        'resource "google_kms_crypto_key" "data" {\n  name = "d"\n'
        '  purpose = "ENCRYPT_DECRYPT"\n}\n'
    )
    findings = _check(tmp_path, with_file(good_files(), PROD, text))
    assert _rules(findings) == {"infra.prod_like.signing_key"}


@pytest.mark.parametrize("algorithm", ["RSA_SIGN_PKCS1_2048_SHA256", "EC_SIGN_P384_SHA384"])
def test_signing_key_must_be_ecdsa_p256(tmp_path: Path, algorithm: str) -> None:
    files = patched(
        good_files(), "infra/modules/secret_store/main.tf", "EC_SIGN_P256_SHA256", algorithm
    )
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.kms.signing_algorithm"}
    assert findings[0].file == "infra/modules/secret_store/main.tf"


def test_a_tree_without_prod_like_has_nothing_to_check(tmp_path: Path) -> None:
    files = {k: v for k, v in good_files().items() if "prod-like" not in k}
    assert _check(tmp_path, files) == ()
