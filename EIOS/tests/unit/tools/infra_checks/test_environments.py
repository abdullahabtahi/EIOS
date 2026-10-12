"""T058: Environment entity rules (names, unique project and state prefix, no sharing)."""

from __future__ import annotations

from pathlib import Path

from tests.support.infra_tree import (
    ENVIRONMENTS,
    env_main,
    good_files,
    patched,
    with_file,
)
from tests.support.repo_builder import build_repo
from tools.common.findings import Finding
from tools.infra_checks.environments import (
    Environment,
    check_environments,
    describe_environments,
)
from tools.infra_checks.hcl import load_infra


def _check(tmp_path: Path, files: dict[str, str]) -> tuple[Finding, ...]:
    root = build_repo(tmp_path, files)
    return check_environments(load_infra(root))


def _rules(findings: tuple[Finding, ...]) -> set[str]:
    return {f.rule_id for f in findings}


def test_valid_tree_has_no_findings(tmp_path: Path) -> None:
    assert _check(tmp_path, good_files()) == ()


def test_describe_returns_one_environment_per_directory(tmp_path: Path) -> None:
    root = build_repo(tmp_path, good_files())
    environments = describe_environments(load_infra(root))
    assert [e.name for e in environments] == sorted(ENVIRONMENTS)
    prod = next(e for e in environments if e.name == "prod-like")
    assert prod == Environment(
        name="prod-like",
        directory="infra/envs/prod-like",
        project_ref="placeholder-prod-like-project",
        state_prefix="envs/prod-like",
        approval_required=True,
    )


def test_approval_required_for_prod_like_only(tmp_path: Path) -> None:
    root = build_repo(tmp_path, good_files())
    flags = {e.name: e.approval_required for e in describe_environments(load_infra(root))}
    assert flags == {"dev": False, "stage": False, "prod-like": True}


def test_unknown_environment_name_is_rejected(tmp_path: Path) -> None:
    files = with_file(good_files(), "infra/envs/qa/main.tf", env_main("qa"))
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.env.unknown"}
    assert findings[0].file == "infra/envs/qa"


def test_missing_environment_is_reported(tmp_path: Path) -> None:
    files = {k: v for k, v in good_files().items() if "envs/stage/" not in k}
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.env.missing"}
    assert "stage" in findings[0].message


def test_tree_without_infra_reports_every_environment_missing(tmp_path: Path) -> None:
    findings = _check(tmp_path, {"README.md": "x\n"})
    assert [f.rule_id for f in findings] == ["infra.env.missing"] * 3


def test_two_environments_with_one_project_are_flagged(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        "infra/envs/stage/main.tf",
        "placeholder-stage-project",
        "placeholder-dev-project",
    )
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.env.shared_project"}
    assert {f.file for f in findings} == {"infra/envs/dev", "infra/envs/stage"}


def test_shared_state_prefix_is_flagged(tmp_path: Path) -> None:
    files = patched(good_files(), "infra/envs/stage/main.tf", "envs/stage", "envs/dev")
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.env.shared_state_prefix"}
    assert len(findings) == 2


def test_backend_without_a_bucket_is_valid(tmp_path: Path) -> None:
    # The bucket is supplied at init time from the bootstrap output; only the prefix is fixed.
    assert _check(tmp_path, good_files()) == ()


def test_environment_split_across_files_is_read_as_one_unit(tmp_path: Path) -> None:
    text = env_main("dev")
    head, _, rest = text.partition("locals {")
    files = with_file(good_files(), "infra/envs/dev/main.tf", head)
    files = with_file(files, "infra/envs/dev/stores.tf", "locals {" + rest)
    assert _check(tmp_path, files) == ()


def test_missing_state_backend_is_flagged(tmp_path: Path) -> None:
    text = env_main("dev").split("variable", 1)[1]
    files = with_file(good_files(), "infra/envs/dev/main.tf", "variable" + text)
    assert _rules(_check(tmp_path, files)) == {"infra.env.no_state_prefix"}


def test_non_literal_state_prefix_is_flagged(tmp_path: Path) -> None:
    files = patched(good_files(), "infra/envs/dev/main.tf", '"envs/dev"', "var.prefix")
    assert _rules(_check(tmp_path, files)) == {"infra.env.no_state_prefix"}


def test_environment_without_project_reference_is_flagged(tmp_path: Path) -> None:
    text = env_main("dev")
    text = text.replace('variable "project_id"', 'variable "region"').replace(
        "var.project_id", "var.region"
    )
    files = with_file(good_files(), "infra/envs/dev/main.tf", text)
    assert _rules(_check(tmp_path, files)) == {"infra.env.no_project_ref"}


def test_project_variable_without_default_counts_as_a_reference(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        "infra/envs/dev/main.tf",
        '  default = "placeholder-dev-project"\n',
        "",
    )
    assert _check(tmp_path, files) == ()


def test_environment_referencing_another_state_prefix_is_flagged(tmp_path: Path) -> None:
    extra = (
        'data "terraform_remote_state" "other" {\n'
        '  backend = "gcs"\n'
        '  config = {\n    bucket = "placeholder-state-bucket"\n    prefix = "envs/stage"\n  }\n}\n'
    )
    files = with_file(good_files(), "infra/envs/dev/main.tf", env_main("dev", extra=extra))
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.env.cross_reference"}
    assert findings[0].file == "infra/envs/dev"


def test_environment_referencing_another_project_is_flagged(tmp_path: Path) -> None:
    extra = 'locals {\n  peer = "placeholder-stage-project"\n}\n'
    files = with_file(good_files(), "infra/envs/dev/main.tf", env_main("dev", extra=extra))
    assert _rules(_check(tmp_path, files)) == {"infra.env.cross_reference"}


def test_module_source_pointing_into_another_environment_is_flagged(tmp_path: Path) -> None:
    extra = 'module "borrowed" {\n  source = "../stage"\n}\n'
    files = with_file(good_files(), "infra/envs/dev/main.tf", env_main("dev", extra=extra))
    assert _rules(_check(tmp_path, files)) == {"infra.env.cross_reference"}


def test_shared_literal_credential_or_bucket_is_flagged(tmp_path: Path) -> None:
    extra = (
        'module "files" {\n  source = "../../modules/eval_truth_store"\n  bucket = "shared-b"\n}\n'
    )
    files = good_files()
    for env in ("dev", "stage"):
        files = with_file(files, f"infra/envs/{env}/main.tf", env_main(env, extra=extra))
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.env.shared_literal"}
    assert {f.file for f in findings} == {"infra/envs/dev", "infra/envs/stage"}


def test_approval_flag_that_disagrees_with_policy_is_flagged(tmp_path: Path) -> None:
    extra = "locals {\n  approval_required = true\n}\n"
    files = with_file(good_files(), "infra/envs/dev/main.tf", env_main("dev", extra=extra))
    findings = _check(tmp_path, files)
    assert _rules(findings) == {"infra.env.approval_required"}


def test_prod_like_declaring_no_approval_is_flagged(tmp_path: Path) -> None:
    extra = "locals {\n  approval_required = false\n}\n"
    files = with_file(
        good_files(), "infra/envs/prod-like/main.tf", env_main("prod-like", extra=extra)
    )
    assert _rules(_check(tmp_path, files)) == {"infra.env.approval_required"}


def test_declared_approval_matching_policy_is_accepted(tmp_path: Path) -> None:
    extra = "locals {\n  approval_required = true\n}\n"
    files = with_file(
        good_files(), "infra/envs/prod-like/main.tf", env_main("prod-like", extra=extra)
    )
    assert _check(tmp_path, files) == ()
