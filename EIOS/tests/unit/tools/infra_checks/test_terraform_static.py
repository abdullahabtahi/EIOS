"""T068: static Terraform rules, on synthetic trees and on the real ``infra/`` tree."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.support import secret_shapes
from tests.support.infra_tree import (
    ENVIRONMENTS,
    env_main,
    good_files,
    identity_rows,
    patched,
    render_identities,
    with_file,
)
from tests.support.repo_builder import build_repo
from tools.common.findings import Finding
from tools.infra_checks.environments import check_environments
from tools.infra_checks.hcl import InfraTree, load_infra
from tools.infra_checks.identities import (
    check_identities,
    check_identity_wiring,
    load_identities,
)
from tools.infra_checks.literals import check_literals
from tools.infra_checks.policy import check_eval_truth, check_module_structure, check_prod_like

REPO_ROOT = Path(__file__).resolve().parents[4]
DEV = "infra/envs/dev/main.tf"
TRUTH_MODULE = "infra/modules/eval_truth_store/main.tf"


def _tree(tmp_path: Path, files: dict[str, str]) -> tuple[Path, InfraTree]:
    root = build_repo(tmp_path, files)
    return root, load_infra(root)


def _rules(findings: tuple[Finding, ...]) -> set[str]:
    return {f.rule_id for f in findings}


def _structure(tmp_path: Path, files: dict[str, str]) -> tuple[Finding, ...]:
    return check_module_structure(_tree(tmp_path, files)[1])


def _literals(tmp_path: Path, files: dict[str, str]) -> tuple[Finding, ...]:
    root, tree = _tree(tmp_path, files)
    return check_literals(root, tree)


def _truth(tmp_path: Path, files: dict[str, str]) -> tuple[Finding, ...]:
    root, tree = _tree(tmp_path, files)
    return check_eval_truth(tree, load_identities(root))


# --- module structure ---------------------------------------------------------------------


def test_valid_modules_pass(tmp_path: Path) -> None:
    assert _structure(tmp_path, good_files()) == ()


def test_module_without_variables_is_flagged(tmp_path: Path) -> None:
    files = with_file(good_files(), "infra/modules/run_service/variables.tf", "# none\n")
    findings = _structure(tmp_path, files)
    assert _rules(findings) == {"infra.module.no_variables"}
    assert findings[0].file == "infra/modules/run_service"


def test_module_without_outputs_is_flagged(tmp_path: Path) -> None:
    files = with_file(good_files(), "infra/modules/run_service/outputs.tf", "# none\n")
    assert _rules(_structure(tmp_path, files)) == {"infra.module.no_outputs"}


def test_empty_module_directory_lacks_both(tmp_path: Path) -> None:
    files = with_file(good_files(), "infra/modules/empty/README.md", "x\n")
    assert _rules(_structure(tmp_path, files)) == set()  # no .tf files: not a module yet


def test_module_declaring_in_any_file_counts(tmp_path: Path) -> None:
    files = {k: v for k, v in good_files().items() if "run_service/outputs.tf" not in k}
    files = with_file(files, "infra/modules/run_service/main.tf", 'output "url" {\n value = 1\n}\n')
    files = with_file(files, "infra/modules/run_service/vars.tf", 'variable "name" {}\n')
    assert _structure(tmp_path, files) == ()


def test_unparseable_terraform_is_reported_with_its_file(tmp_path: Path) -> None:
    files = with_file(good_files(), "infra/modules/run_service/broken.tf", 'module "a" {\n')
    root = build_repo(tmp_path, files)
    findings = load_infra(root).parse_findings
    assert [f.rule_id for f in findings] == ["infra.hcl.parse"]
    assert findings[0].file == "infra/modules/run_service/broken.tf"


# --- literals -----------------------------------------------------------------------------


def test_valid_tree_has_no_literals(tmp_path: Path) -> None:
    assert _literals(tmp_path, good_files()) == ()


@pytest.mark.parametrize(
    "extra",
    [
        'locals {\n  project_id = "acme-trading-4821"\n}\n',
        'provider "google" {\n  project = "acme-trading-4821"\n}\n',
        (
            'module "x" {\n  source = "../../modules/run_service"\n'
            '  project_id = "acme-trading-4821"\n}\n'
        ),
        'variable "project_id" {\n  default = "acme-trading-4821"\n}\n',
        'locals {\n  sa = "runner@acme-trading-4821.iam.gserviceaccount.com"\n}\n',
    ],
)
def test_literal_project_ids_are_flagged(tmp_path: Path, extra: str) -> None:
    text = (
        env_main("dev")
        .replace(
            (
                'variable "project_id" {\n  type    = string\n'
                '  default = "placeholder-dev-project"\n}\n'
            ),
            "",
        )
        .replace("var.project_id", "var.other")
    )
    files = with_file(good_files(), DEV, text + extra)
    findings = _literals(tmp_path, files)
    assert "infra.literal.project_id" in _rules(findings)
    assert all(f.file == DEV and f.line > 0 for f in findings)


def test_tfvars_literal_project_id_is_flagged(tmp_path: Path) -> None:
    files = with_file(
        good_files(), "infra/envs/dev/terraform.tfvars", 'project_id = "acme-trading-4821"\n'
    )
    findings = _literals(tmp_path, files)
    assert _rules(findings) == {"infra.literal.project_id"}
    assert findings[0].file == "infra/envs/dev/terraform.tfvars"


@pytest.mark.parametrize(
    "value", ["placeholder-dev-project", "REPLACE_WITH_DEV_PROJECT_ID", "<dev-project>", ""]
)
def test_placeholder_project_ids_are_accepted(tmp_path: Path, value: str) -> None:
    files = patched(good_files(), DEV, "placeholder-dev-project", value)
    assert _literals(tmp_path, files) == ()


def test_project_taken_from_a_reference_is_accepted(tmp_path: Path) -> None:
    extra = 'provider "google" {\n  project = var.project_id\n}\n'
    files = with_file(good_files(), DEV, env_main("dev", extra=extra))
    assert _literals(tmp_path, files) == ()


@pytest.mark.parametrize(
    "extra",
    [
        'provider "google" {\n  credentials = file("service-account.json")\n}\n',
        'provider "google" {\n  credentials = "inline-credential-value"\n}\n',
        'resource "x" "y" {\n  client_secret = "hunter2hunter2"\n}\n',
        'resource "google_secret_manager_secret_version" "v" {\n  secret_data = "plain"\n}\n',
        'locals {\n  nested = {\n    password = "plain"\n  }\n}\n',
    ],
)
def test_literal_credentials_are_flagged(tmp_path: Path, extra: str) -> None:
    files = with_file(good_files(), DEV, env_main("dev", extra=extra))
    assert _rules(_literals(tmp_path, files)) == {"infra.literal.credential"}


def test_credential_taken_from_a_reference_is_accepted(tmp_path: Path) -> None:
    extra = 'resource "x" "y" {\n  client_secret = var.client_secret\n}\n'
    files = with_file(good_files(), DEV, env_main("dev", extra=extra))
    assert _literals(tmp_path, files) == ()


def test_stored_service_account_keys_are_flagged(tmp_path: Path) -> None:
    extra = 'resource "google_service_account_key" "k" {\n  service_account_id = "x"\n}\n'
    files = with_file(good_files(), DEV, env_main("dev", extra=extra))
    assert _rules(_literals(tmp_path, files)) == {"infra.literal.stored_key"}


@pytest.mark.parametrize("shape", sorted(secret_shapes.all_shapes()))
def test_secret_shaped_text_is_flagged_in_any_infra_file(tmp_path: Path, shape: str) -> None:
    text = secret_shapes.all_shapes()[shape]
    files = with_file(good_files(), "infra/envs/dev/notes.yaml", f"note: {text}\n")
    findings = _literals(tmp_path, files)
    assert _rules(findings) == {"infra.literal.secret"}
    assert text not in findings[0].message


def test_literals_outside_infra_are_not_this_checks_business(tmp_path: Path) -> None:
    files = with_file(
        good_files(), "src/app.tf", 'locals {\n  project_id = "acme-trading-4821"\n}\n'
    )
    assert _literals(tmp_path, files) == ()


# --- eval truth ---------------------------------------------------------------------------


def test_valid_eval_truth_grants_pass(tmp_path: Path) -> None:
    assert _truth(tmp_path, good_files()) == ()


def test_grant_to_a_runtime_identity_is_flagged(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        DEV,
        "    pipeline     = module.identity_pipeline.member\n",
        "    skeleton_core = module.identity_skeleton_core.member\n",
    )
    findings = _truth(tmp_path, files)
    assert _rules(findings) == {"infra.eval_truth.grant"}
    assert findings[0].file == DEV
    assert findings[0].line > 0
    assert "skeleton_core" in findings[0].message


def test_release_candidate_may_not_read_the_open_splits(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        "infra/envs/stage/main.tf",
        "    pipeline     = module.identity_pipeline.member\n",
        "    rc = module.identity_release_candidate.member\n",
    )
    assert _rules(_truth(tmp_path, files)) == {"infra.eval_truth.grant"}


def test_sealed_split_is_for_the_release_candidate_only(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        DEV,
        "    release_candidate = module.identity_release_candidate.member\n",
        "    pipeline = module.identity_pipeline.member\n",
    )
    findings = _truth(tmp_path, files)
    assert _rules(findings) == {"infra.eval_truth.grant"}
    assert "sealed" in findings[0].message


def test_grant_follows_the_flag_in_the_identities_file(tmp_path: Path) -> None:
    rows = [
        {**r, "can_read_eval_truth": False}
        if (r["service"], r["environment"]) == ("pipeline", "dev")
        else r
        for r in identity_rows()
    ]
    files = with_file(good_files(), "infra/identities.yaml", render_identities(rows))
    findings = _truth(tmp_path, files)
    assert _rules(findings) == {"infra.eval_truth.grant"}
    assert "dev" in findings[0].message


def test_reader_that_maps_to_no_identity_is_flagged(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        DEV,
        "module.identity_pipeline.member\n    eval_harness",
        "module.stranger.member\n    eval_harness",
    )
    assert _rules(_truth(tmp_path, files)) == {"infra.eval_truth.unknown_reader"}


def test_literal_principal_in_a_grant_is_flagged(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        DEV,
        "    pipeline     = module.identity_pipeline.member\n",
        '    pipeline     = module.identity_pipeline.member\n    all = "group:everyone"\n',
    )
    assert _rules(_truth(tmp_path, files)) == {"infra.eval_truth.literal_principal"}


def test_readers_passed_as_a_whole_variable_are_unknown(tmp_path: Path) -> None:
    files = patched(
        good_files(),
        DEV,
        "  reader_members = {\n    pipeline     = module.identity_pipeline.member\n"
        "    eval_harness = module.identity_eval_harness.member\n  }\n",
        "  reader_members = var.readers\n",
    )
    assert _rules(_truth(tmp_path, files)) == {"infra.eval_truth.unknown_reader"}


def test_public_member_inside_the_module_is_flagged(tmp_path: Path) -> None:
    extra = (
        'resource "google_storage_bucket_iam_member" "public" {\n'
        '  bucket = google_storage_bucket.truth.name\n  role = "roles/storage.objectViewer"\n'
        '  member = "allAuthenticatedUsers"\n}\n'
    )
    files = with_file(good_files(), TRUTH_MODULE, good_files()[TRUTH_MODULE] + extra)
    assert _rules(_truth(tmp_path, files)) == {"infra.eval_truth.literal_principal"}


def test_iam_resource_in_an_environment_is_checked_like_the_module_call(tmp_path: Path) -> None:
    extra = (
        'resource "google_storage_bucket_iam_member" "extra" {\n'
        "  bucket = module.eval_truth_store.bucket\n"
        '  role   = "roles/storage.objectViewer"\n'
        "  member = module.identity_skeleton_edge.member\n}\n"
    )
    files = with_file(good_files(), DEV, env_main("dev", extra=extra))
    assert _rules(_truth(tmp_path, files)) == {"infra.eval_truth.grant"}


def test_unrelated_bucket_grants_are_not_judged(tmp_path: Path) -> None:
    extra = (
        'resource "google_storage_bucket_iam_member" "other" {\n'
        "  bucket = module.evidence_store.bucket\n"
        '  role   = "roles/storage.objectViewer"\n'
        "  member = module.identity_skeleton_edge.member\n}\n"
    )
    files = with_file(good_files(), DEV, env_main("dev", extra=extra))
    assert _truth(tmp_path, files) == ()


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("  uniform_bucket_level_access = true\n", ""),
        ('  public_access_prevention    = "enforced"\n', ""),
        ("uniform_bucket_level_access = true", "uniform_bucket_level_access = false"),
        ('"enforced"', '"inherited"'),
    ],
)
def test_bucket_must_be_restricted(tmp_path: Path, old: str, new: str) -> None:
    files = patched(good_files(), TRUTH_MODULE, old, new)
    findings = _truth(tmp_path, files)
    assert _rules(findings) == {"infra.eval_truth.not_restricted"}
    assert findings[0].file == TRUTH_MODULE and findings[0].line > 0


def test_missing_identities_do_not_flood_the_grant_check(tmp_path: Path) -> None:
    files = {k: v for k, v in good_files().items() if k != "infra/identities.yaml"}
    root, tree = _tree(tmp_path, files)
    assert check_eval_truth(tree, ()) == ()
    assert _rules(check_identities(root)) == {"infra.identity.file"}


# --- the real tree --------------------------------------------------------------------------

_REAL: dict[str, Callable[[Path, InfraTree], tuple[Finding, ...]]] = {
    "modules declare variables and outputs": lambda _r, t: check_module_structure(t),
    "no literal project id, credential or secret": check_literals,
    "environments are isolated": lambda _r, t: check_environments(t),
    "identity rows": lambda r, _t: check_identities(r),
    "identity wiring": lambda _r, t: check_identity_wiring(t),
    "prod-like policy": lambda _r, t: check_prod_like(t),
    "eval-truth grants follow can_read_eval_truth": lambda r, t: check_eval_truth(
        t, load_identities(r)
    ),
}


@pytest.mark.parametrize("name", sorted(_REAL))
def test_real_infra_tree(name: str) -> None:
    tree = load_infra(REPO_ROOT)
    assert tree.parse_findings == ()
    findings = _REAL[name](REPO_ROOT, tree)
    assert findings == (), "\n".join(f"{f.file}:{f.line} {f.rule_id} {f.message}" for f in findings)


def test_real_tree_has_every_environment_and_module() -> None:
    tree = load_infra(REPO_ROOT)
    assert set(tree.envs) == set(ENVIRONMENTS)
    for module in (
        "project_baseline",
        "service_identity",
        "secret_store",
        "eval_truth_store",
        "evidence_store",
        "artifact_registry",
        "run_service",
        "state_stores",
    ):
        assert module in tree.modules, module


# --- terraform validate (needs provider download) -----------------------------------------------


@pytest.mark.requires_network
@pytest.mark.skipif(shutil.which("terraform") is None, reason="terraform is not installed")
@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_terraform_validate_with_backend_disabled(environment: str, tmp_path: Path) -> None:
    copy = tmp_path / "infra"
    shutil.copytree(
        REPO_ROOT / "infra", copy, ignore=shutil.ignore_patterns(".terraform", "*.tfstate*")
    )
    directory = copy / "envs" / environment
    terraform = shutil.which("terraform") or "terraform"
    for argv in (["init", "-backend=false", "-input=false"], ["validate"]):
        result = subprocess.run(  # noqa: S603 - fixed argv, resolved binary
            [terraform, *argv], cwd=directory, capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stdout + result.stderr
